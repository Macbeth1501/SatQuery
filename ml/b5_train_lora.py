"""B5: train the caption/VQA LoRA adapter on the B1 slice.

    python ml/b5_train_lora.py --data data/b1_slice --out data/b5_run1 [--max-steps 3 --size 224]

Runs on one GPU. On Kaggle's 2 x T4 the second card sits idle: a 4-bit 2B model plus LoRA fits on one T4
with room to spare, and a single-process loop is far less likely to fail than a distributed one.

fp16 caveat (T4 has no bfloat16): Qwen2-VL is known to be touchier in float16 than in bfloat16. Adapter
weights stay float32 and a GradScaler is used, and any step whose loss is not finite is skipped and
counted, but this has not been run on a T4 by us. The local RTX 3050 uses bfloat16, so a clean local dry
run does NOT prove the T4 path. If `skipped_nonfinite` in the log is more than a handful, stop and look.
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import torch

from b5_common import LORA_TARGETS, MODEL_ID, REVISION, collate, generate, load_jsonl, load_model, score_choice


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/b1_slice")
    p.add_argument("--out", default="data/b5_run")
    p.add_argument("--size", type=int, default=448, help="square input side in pixels, a multiple of 28")
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--max-steps", type=int, default=0, help="stop after this many optimiser steps (dry runs)")
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--warmup", type=int, default=20)
    p.add_argument("--rank", type=int, default=16)
    p.add_argument("--alpha", type=int, default=32)
    p.add_argument("--dropout", type=float, default=0.05)
    p.add_argument("--eval-every", type=int, default=200, help="optimiser steps between validation passes")
    p.add_argument("--eval-n", type=int, default=100, help="validation examples scored per pass")
    p.add_argument("--save-every", type=int, default=200)
    p.add_argument("--seed", type=int, default=20260920)
    p.add_argument("--resume", default=None, metavar="DIR",
                   help="continue from the newest state_step{N}.pt and adapter_step{N} (or adapter_final) in DIR; "
                        "use the same --max-steps and hyperparameters as the run being resumed")
    return p.parse_args()


def save_state(path, opt, scaler, step, cursor, order, skipped, total):
    """Everything besides the adapter weights that a resumed run needs to continue exactly where this one stopped."""
    torch.save({"opt": opt.state_dict(), "scaler": scaler.state_dict(), "step": step, "cursor": cursor,
                "order": list(order), "skipped": skipped, "total": total, "py_rng": random.getstate(),
                "torch_rng": torch.get_rng_state(),
                "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None}, path)


def load_state(path, opt, scaler, total):
    """Restore what save_state wrote into `opt` and `scaler` and the RNGs; return step, cursor, order and skipped."""
    state = torch.load(path, map_location="cpu", weights_only=False)  # our own file, holds a random.getstate tuple
    if state["total"] != total:
        raise SystemExit(f"{path} was saved for a {state['total']}-step run but this run has {total} steps; the "
                         "learning-rate schedule would not match. Pass the same --max-steps / --epochs.")
    opt.load_state_dict(state["opt"])
    scaler.load_state_dict(state["scaler"])
    random.setstate(state["py_rng"])
    torch.set_rng_state(state["torch_rng"])
    if state["cuda_rng"] is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda_rng"])
    return state["step"], state["cursor"], state["order"], state["skipped"]


def newest_state(directory):
    """Path of the state_step{N}.pt with the largest N in `directory`, and N."""
    found = [(int(p.stem.removeprefix("state_step")), p) for p in Path(directory).glob("state_step*.pt")]
    if not found:
        raise SystemExit(f"no state_step*.pt in {directory}; nothing to resume from")
    step, path = max(found)
    return path, step


def lr_at(step, total, args):
    if step < args.warmup:
        return args.lr * (step + 1) / args.warmup
    progress = (step - args.warmup) / max(1, total - args.warmup)
    return args.lr * 0.5 * (1 + math.cos(math.pi * min(1.0, progress)))


@torch.no_grad()
def validate(model, processor, root, size, examples, n):
    """Loss over the sample, and exact-match accuracy on its binary / multiple-choice questions."""
    model.eval()
    sample = examples[:n]
    losses, hits, scored = [], 0, 0
    for ex in sample:
        batch = collate(processor, root, size, [ex]).to(model.device)
        losses.append(float(model(**batch).loss))
        if ex["type"] in ("binary", "mcq"):
            scored += 1
            hits += int(score_choice(ex, generate(model, processor, root, size, ex, max_new_tokens=8)))
    model.train()
    return {"val_loss": sum(losses) / max(1, len(losses)), "val_choice_acc": hits / scored if scored else None,
            "val_choice_n": scored}


def main():
    args = parse()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    root, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    train, val = load_jsonl(root / "train.jsonl"), load_jsonl(root / "validation.jsonl")

    from peft import LoraConfig, get_peft_model

    model, processor, dtype = load_model()
    for prm in model.parameters():
        prm.requires_grad_(False)
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout, target_modules=LORA_TARGETS,
        bias="none", task_type="CAUSAL_LM",
    ))
    model.print_trainable_parameters()
    trainable = [p for p in model.parameters() if p.requires_grad]

    steps_per_epoch = len(train) // (args.batch * args.grad_accum)
    total = args.max_steps or max(1, int(steps_per_epoch * args.epochs))
    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.0)
    scaler = torch.amp.GradScaler("cuda", enabled=(dtype == torch.float16))
    log = out / "train_log.jsonl"
    meta = {"model": MODEL_ID, "revision": REVISION, "dtype": str(dtype), "args": vars(args),
            "train_examples": len(train), "val_examples": len(val), "total_steps": total,
            "trainable_params": sum(p.numel() for p in trainable)}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1), flush=True)

    order, cursor, skipped, start, started = [], 0, 0, 0, time.time()
    if args.resume:
        from peft import set_peft_model_state_dict
        from safetensors.torch import load_file

        state_path, saved_step = newest_state(args.resume)
        adapter = Path(args.resume) / (f"adapter_step{saved_step}" if (Path(args.resume) / f"adapter_step{saved_step}").exists()
                                       else "adapter_final")
        set_peft_model_state_dict(model, load_file(adapter / "adapter_model.safetensors"))
        start, cursor, order, skipped = load_state(state_path, opt, scaler, total)
        print(f"resumed from {state_path} and {adapter}: continuing at step {start + 1} of {total}", flush=True)
    model.train()
    torch.cuda.reset_peak_memory_stats()

    def emit(record):
        record["t"] = round(time.time() - started, 1)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        print(record, flush=True)

    for step in range(start, total):
        for group in opt.param_groups:
            group["lr"] = lr_at(step, total, args)
        step_loss, counted = 0.0, 0
        for _ in range(args.grad_accum):
            if cursor + args.batch > len(order):
                order = list(range(len(train)))
                random.shuffle(order)
                cursor = 0
            batch = collate(processor, root, args.size, [train[i] for i in order[cursor:cursor + args.batch]])
            cursor += args.batch
            batch = batch.to(model.device)
            with torch.autocast("cuda", dtype=dtype):
                loss = model(**batch).loss
            if not torch.isfinite(loss):
                skipped += 1
                continue
            scaler.scale(loss / args.grad_accum).backward()
            step_loss += float(loss)
            counted += 1
        if counted:
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            scaler.step(opt)
            scaler.update()
        opt.zero_grad(set_to_none=True)
        emit({"step": step + 1, "train_loss": step_loss / max(1, counted), "lr": opt.param_groups[0]["lr"],
              "skipped_nonfinite": skipped, "peak_alloc_mib": round(torch.cuda.max_memory_allocated() / 2**20)})

        if args.eval_every and (step + 1) % args.eval_every == 0:
            emit({"step": step + 1, **validate(model, processor, root, args.size, val, args.eval_n)})
        if args.save_every and (step + 1) % args.save_every == 0:
            model.save_pretrained(out / f"adapter_step{step + 1}")
            save_state(out / f"state_step{step + 1}.pt", opt, scaler, step + 1, cursor, order, skipped, total)

    model.save_pretrained(out / "adapter_final")
    save_state(out / f"state_step{total}.pt", opt, scaler, total, cursor, order, skipped, total)
    emit({"done": True, "steps": total, "skipped_nonfinite": skipped,
          "peak_alloc_mib": round(torch.cuda.max_memory_allocated() / 2**20)})


if __name__ == "__main__":
    main()
