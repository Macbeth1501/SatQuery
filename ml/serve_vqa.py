"""Serves the trained LoRA adapters over HTTP so the backend can call a real model (Plan steps C2 and B2).

    .venv-ml/Scripts/python.exe ml/serve_vqa.py --adapter data/b5_run2/adapter_final --port 8001
    .venv-ml/Scripts/python.exe ml/serve_vqa.py --adapter run2=data/b5_run2/adapter_final \
        --adapter run3=data/b5_run3/adapter_final --port 8001     # both resident; also the default with no --adapter

Runs in `.venv-ml`, apart from the backend, so torch never enters `backend/`. The backend is pointed at it with
SATQUERY_VQA_MODEL_URL=http://127.0.0.1:8001 and names the adapter with SATQUERY_VQA_MODEL_ADAPTER (default run2).

Every adapter given is loaded onto the one 4-bit backbone at start-up and stays resident (PEFT named adapters);
a request picks one, and switching is PEFT's set_adapter, not a reload. `--adapter NAME=PATH` names it; a bare
path is named after its run folder without the "b5_" prefix (data/b5_run2/adapter_final -> run2). The first one
given is the default. "base" is reserved: the backbone with every adapter switched off. An adapter folder may carry
satquery_adapter.json listing the tasks it was trained for (b5_common.adapter_manifest); run 2 and run 3 have
none and serve vqa and caption. Endpoints:

  * GET  /health    model id, pinned revision, resident adapters, the default, GPU memory.
  * GET  /adapters  each resident adapter: name, path, tasks, whether its prompt carries the task token.
  * POST /infer     {"image_path", "question", "task": vqa|caption|ground|change|fusion, "adapter"?} -> as /vqa,
                    plus the task and adapter name. A task the chosen adapter was not trained for is a 422.
  * POST /vqa       {"image_path", "question", "adapter"?} -> the answer, its probability and the raw reply. The
                    original endpoint, kept so existing callers work; it does not check a task.

For run 2 and run 3 the task token decides nothing about the answer format: as before, the question does (yes/no,
a-d, or free).

The image arrives as a local path, not bytes: the two processes share one machine and the backend has already
written the upload under its storage root. The server binds to loopback only.

How an answer is produced, matching training and `b5_eval.py` so the demo behaves as the evaluation measured:
  * the image is opened, converted to RGB and resized to --size (448) bicubic, as `b5_common.open_image` does;
  * binary (yes/no) and multiple-choice (a-d) questions: one forward pass, and the next-token distribution is
    restricted to the candidate answers; the winner and its share of that restricted probability are returned.
    The greedy reply (8 tokens) is returned too, as `raw_output`, for the trace;
  * anything else is "free": a greedy reply of up to 128 tokens and no probability. The adapter did see
    BigEarthNet captions (1,431 of 19,489 training examples), whose template names a country, season and
    climate zone that a 120 px patch cannot show, and it fills those from memory. So --free-form base (the
    default) answers free-form questions with the adapter switched off; --free-form adapter restores the old
    behaviour. Either way the reply is unevaluated and the caller must not present it as a trained answer.

The probability is the model's own number, not a calibrated accuracy. On unseen tiles run 2 scores about 33% on
multiple choice (chance 25%) and 50% on yes/no, whatever the probability says.
"""
import argparse
import os
import re
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b5_text_only import parse_options  # noqa: E402  (pure Python, no torch)

# A question is yes/no when it opens with an auxiliary verb; BigEarthNet.txt's binary questions all do, and all
# end with "?" (every one of the 18,000+ in data/b1_v2). "Can you detect ...?" and "Would you classify ...?" are
# among them, so "can you" alone does not make a request.
BINARY_OPENERS = re.compile(
    r"^\s*(is|are|was|were|do|does|did|can|could|would|will|has|have|should|may|might)\b", re.IGNORECASE
)
# "Do" and "Did" also open imperatives ("Do descriptive analysis"), so without a "?" they are not questions.
IMPERATIVE_OPENERS = re.compile(r"^\s*(do|did)\b", re.IGNORECASE)
# A request for a description, however it opens: "Can you describe ...", "Could you please give ...".
DESCRIPTION_REQUEST = re.compile(
    r"^\s*\w+\s+(?:you\s+)?(?:please\s+)?"
    r"(describe|explain|summari[sz]e|analy[sz]e|tell|give|list|elaborate|characteri[sz]e|write|provide)\b"
    r"|\banalysis\b",
    re.IGNORECASE,
)
# Run 2 first: it is the live demo's adapter (owner decision 2026-09-22) and so the default for callers that name
# none. Run 3 is the model of record and rides along for the backend to name.
DEFAULT_ADAPTERS = [f"run2={ROOT / 'data' / 'b5_run2' / 'adapter_final'}",
                    f"run3={ROOT / 'data' / 'b5_run3' / 'adapter_final'}"]
BASE = "base"
# At 64 tokens 4 of the base model's 15 free-form replies in data/b5_eval/freeform_compare.json stopped mid-list.
FREE_FORM_TOKENS = 128


def parse_adapter_spec(spec):
    """'run3=data/x' -> ('run3', 'data/x'); a bare 'data/b5_run2/adapter_final' -> ('run2', that path), named
    after its run folder without the 'b5_' prefix. 'base' is reserved for the backbone with adapters off."""
    name, sep, path = spec.partition("=")
    if not sep or not name or "/" in name or "\\" in name:
        path = spec
        parent = Path(path).parent.name
        name = parent[3:] if parent.startswith("b5_") else parent
    if not name or name == BASE:
        raise ValueError(f"cannot name adapter {spec!r}: give it as NAME=PATH (and not '{BASE}')")
    return name, path


def question_kind(question):
    """'mcq' when the question lists a) to d) options; 'binary' when it opens with an auxiliary verb, is not a
    request for a description, and (for "do"/"did") ends with "?"; else 'free'."""
    if len(parse_options(question)) >= 2:
        return "mcq"
    if not BINARY_OPENERS.match(question) or DESCRIPTION_REQUEST.search(question):
        return "free"
    if IMPERATIVE_OPENERS.match(question) and not question.rstrip().endswith("?"):
        return "free"
    return "binary"


def candidates(question, kind):
    """The answer strings the model may give: ['yes', 'no'] or the option letters actually offered."""
    if kind == "binary":
        return ["yes", "no"]
    if kind == "mcq":
        return [letter for letter, _ in parse_options(question)]
    return []


def answer_text(question, kind, answer):
    """A readable answer: 'Yes' / 'No', or 'b) 30 to 60%' with the option text put back beside its letter."""
    if kind == "binary":
        return answer.capitalize()
    if kind == "mcq":
        options = dict(parse_options(question))
        return f"{answer}) {options[answer]}" if answer in options else answer
    return answer


class UnsupportedTask(ValueError):
    """The chosen adapter was not trained for the requested task."""


class Engine:
    """Holds the backbone and every adapter, all resident; one request at a time, since a 4 GB card has room for
    exactly one generation."""

    def __init__(self, adapters, size, free_form="base"):
        """`adapters`: [(name, path), ...]; the first is the default."""
        from peft import PeftModel

        from b5_common import MODEL_ID, REVISION, adapter_manifest, load_model

        self.model_id, self.revision, self.size = MODEL_ID, REVISION, size
        self.free_form = free_form
        self.adapters = {name: {"path": str(path), **adapter_manifest(path)} for name, path in adapters}
        self.default = adapters[0][0]
        base, self.processor, _ = load_model()
        first, *rest = adapters
        self.model = PeftModel.from_pretrained(base, first[1], adapter_name=first[0])
        for name, path in rest:
            self.model.load_adapter(path, adapter_name=name)
        self.model.eval()
        self.lock = threading.Lock()

    def _token_id(self, text):
        ids = self.processor.tokenizer.encode(text, add_special_tokens=False)
        return ids[0]

    def gpu(self):
        import torch

        free, total = torch.cuda.mem_get_info()
        mib = 1 << 20
        return {"allocated_mib": round(torch.cuda.memory_allocated() / mib),
                "reserved_mib": round(torch.cuda.memory_reserved() / mib),
                "peak_allocated_mib": round(torch.cuda.max_memory_allocated() / mib),
                "device_free_mib": round(free / mib), "device_total_mib": round(total / mib)}

    def resolve(self, adapter, task):
        """(name, manifest) of the adapter a request asked for; 'base' has no manifest. Raises KeyError for an
        adapter that is not resident, UnsupportedTask for a task it was not trained for (task None: no check)."""
        name = adapter or self.default
        if name == BASE:
            if task is not None and task not in ("vqa", "caption"):
                raise UnsupportedTask(f"the base model is not a {task} model")
            return name, None
        if name not in self.adapters:
            raise KeyError(name)
        manifest = self.adapters[name]
        if task is not None and task not in manifest["tasks"]:
            raise UnsupportedTask(f"adapter {name!r} was trained for {', '.join(manifest['tasks'])}, not {task}")
        return name, manifest

    def answer(self, image_path, question, free_form=None, adapter=None, task=None):
        """`free_form` ('base' or 'adapter') overrides the server's --free-form choice for this call. `adapter`
        names a resident adapter or 'base' (default: the first one loaded); `task` is a task token name."""
        import contextlib

        import torch
        from PIL import Image

        from b5_common import prompt_text, with_task_token

        name, manifest = self.resolve(adapter, task)
        kind = question_kind(question)
        if name == BASE:
            answered_by = "base"
        else:
            answered_by = "adapter" if kind != "free" else (free_form or self.free_form)
        in_prompt = bool(manifest and manifest["task_token_in_prompt"] and answered_by == "adapter")
        text = with_task_token(question, task, in_prompt) if task is not None else question
        image = Image.open(image_path).convert("RGB").resize((self.size, self.size), Image.BICUBIC)
        enc = self.processor(text=[prompt_text(self.processor, text)], images=[image], return_tensors="pt")
        enc = enc.to(self.model.device)
        # One generate call gives both the reply and the answer distribution. The distribution is computed in
        # float32 from the hidden state entering lm_head at the first step, captured by a hook: the model's own
        # logits are bfloat16, whose steps at logit sizes around 20 are coarse enough that yes and no often
        # come out exactly equal (measured: 3 of the sample's 5 questions tied at 0.5, and greedy decoding then
        # broke the tie by token order). lm_head is not quantised, so float32 here is exact up to its weights.
        # The lock covers the hook, the adapter switch and generation, so concurrent requests can neither see
        # each other's hidden states nor switch the adapter under one another.
        lm_head = self.model.get_output_embeddings()
        captured = []
        with self.lock:
            start = time.perf_counter()
            hook = lm_head.register_forward_hook(lambda _m, inputs, _o: captured.append(inputs[0][:, -1, :]))
            try:
                if name != BASE:
                    self.model.set_adapter(name)
                adapter_off = self.model.disable_adapter() if answered_by == "base" else contextlib.nullcontext()
                with torch.no_grad(), adapter_off:
                    out = self.model.generate(**enc, max_new_tokens=8 if kind != "free" else FREE_FORM_TOKENS,
                                              do_sample=False, return_dict_in_generate=True)
            finally:
                hook.remove()
        probability, answer, distribution = None, None, {}
        if kind != "free":
            cands = candidates(question, kind)
            ids = torch.tensor([self._token_id(c) for c in cands], device=captured[0].device)
            logits = captured[0][0].float() @ lm_head.weight[ids].float().T
            probs = torch.softmax(logits, dim=0).tolist()
            distribution = {c: round(p, 4) for c, p in zip(cands, probs)}
            answer = max(distribution, key=distribution.get)
            probability = distribution[answer]
        raw = self.processor.batch_decode(out.sequences[:, enc["input_ids"].shape[1]:],
                                          skip_special_tokens=True)[0].strip()
        latency_ms = round((time.perf_counter() - start) * 1000.0, 1)
        if kind == "free":
            answer = raw
        return {
            "kind": kind,
            # A yes/no or a-d answer is in the trained format only when an adapter gave it; the base model was
            # never trained on these questions.
            "trained_format": kind != "free" and answered_by == "adapter",
            "answered_by": answered_by,
            "answer": answer,
            "answer_text": answer_text(question, kind, answer),
            "probability": probability,
            "distribution": distribution,
            "raw_output": raw,
            "latency_ms": latency_ms,
            "model": self.model_id,
            "revision": self.revision,
            "task": task,
            "adapter_name": name,
            "adapter": manifest["path"] if manifest else None,
            "adapter_id": (f"{Path(manifest['path']).parent.name}_lora (Qwen2-VL-2B-Instruct 4-bit)"
                           if answered_by == "adapter" else "Qwen2-VL-2B-Instruct 4-bit (base, adapter off)"),
        }


def build_app(engine):
    from fastapi import FastAPI, HTTPException
    from typing import Literal, Optional

    from pydantic import BaseModel

    from b5_common import TASK_TOKENS

    app = FastAPI(title="SatQuery VQA model server")

    class VqaRequest(BaseModel):
        image_path: str
        question: str
        free_form: Optional[Literal["base", "adapter"]] = None
        adapter: Optional[str] = None

    class InferRequest(VqaRequest):
        task: Literal[TASK_TOKENS]

    def run(req, task):
        path = Path(req.image_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"image not found: {req.image_path}")
        if not req.question.strip():
            raise HTTPException(status_code=400, detail="empty question")
        try:
            return engine.answer(path, req.question.strip(), req.free_form, req.adapter, task)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"adapter {req.adapter!r} is not loaded; resident: "
                                f"{', '.join(engine.adapters)} (or '{BASE}')")
        except UnsupportedTask as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OSError as exc:  # PIL cannot decode the file
            raise HTTPException(status_code=400, detail=f"cannot read image: {exc}") from exc

    @app.get("/health")
    def health():
        return {"status": "ok", "loaded": True, "model": engine.model_id, "revision": engine.revision,
                "adapter": engine.adapters[engine.default]["path"], "default_adapter": engine.default,
                "adapters": list(engine.adapters), "free_form": engine.free_form, "gpu": engine.gpu()}

    @app.get("/adapters")
    def adapters():
        return {"default": engine.default, "task_tokens": list(TASK_TOKENS),
                "adapters": [{"name": name, **info} for name, info in engine.adapters.items()]}

    @app.post("/infer")
    def infer(req: InferRequest):
        return run(req, req.task)

    @app.post("/vqa")
    def vqa(req: VqaRequest):
        return run(req, None)

    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--adapter", action="append", default=None,
                    help="NAME=PATH or a bare PATH; repeat to load several (all stay resident). "
                         "Default: run2 and run3. The first is the default for requests that name none")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--size", type=int, default=448, help="square input size; 448 is what run 2 trained at")
    ap.add_argument("--free-form", choices=["base", "adapter"], default="base",
                    help="who answers free-form questions: the base model (adapter off) or the adapter")
    args = ap.parse_args()

    # The model is cached at the pinned revision; a demo must not reach the network.
    os.environ.setdefault("HF_HOME", str(ROOT / "data" / "hf_cache"))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    try:
        adapters = [parse_adapter_spec(spec) for spec in (args.adapter or DEFAULT_ADAPTERS)]
    except ValueError as exc:
        sys.exit(str(exc))
    names = [name for name, _ in adapters]
    if len(set(names)) != len(names):
        sys.exit(f"two adapters share a name: {names}")
    for name, path in adapters:
        if not Path(path).is_dir():
            sys.exit(f"adapter folder not found: {path}")

    import uvicorn

    print("loading " + ", ".join(f"{n}={p}" for n, p in adapters) + " ...", flush=True)
    engine = Engine(adapters, args.size, args.free_form)
    print("model loaded", flush=True)
    uvicorn.run(build_app(engine), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
