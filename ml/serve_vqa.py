"""Serves the B5 VQA adapter over HTTP so the backend can call a real model (Plan step C2, single-image path only).

    .venv-ml/Scripts/python.exe ml/serve_vqa.py --adapter data/b5_run2/adapter_final --port 8001

Runs in `.venv-ml`, apart from the backend, so torch never enters `backend/`. The backend is pointed at it with
SATQUERY_VQA_MODEL_URL=http://127.0.0.1:8001. Endpoints:

  * GET  /health  model id, pinned revision, adapter path, whether the model is loaded.
  * POST /vqa     {"image_path": ..., "question": ...} -> the answer, its probability and the raw reply.

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
DEFAULT_ADAPTER = ROOT / "data" / "b5_run2" / "adapter_final"
# At 64 tokens 4 of the base model's 15 free-form replies in data/b5_eval/freeform_compare.json stopped mid-list.
FREE_FORM_TOKENS = 128


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


class Engine:
    """Holds the model; one request at a time, since a 4 GB card has room for exactly one."""

    def __init__(self, adapter, size, free_form="base"):
        from b5_common import MODEL_ID, REVISION, load_model

        self.model_id, self.revision, self.adapter, self.size = MODEL_ID, REVISION, str(adapter), size
        self.free_form = free_form
        self.model, self.processor, _ = load_model(adapter=str(adapter))
        self.model.eval()
        self.lock = threading.Lock()

    def _token_id(self, text):
        ids = self.processor.tokenizer.encode(text, add_special_tokens=False)
        return ids[0]

    def answer(self, image_path, question, free_form=None):
        """`free_form` ('base' or 'adapter') overrides the server's --free-form choice for this call."""
        import contextlib

        import torch
        from PIL import Image

        from b5_common import prompt_text

        kind = question_kind(question)
        answered_by = "adapter" if kind != "free" else (free_form or self.free_form)
        image = Image.open(image_path).convert("RGB").resize((self.size, self.size), Image.BICUBIC)
        enc = self.processor(text=[prompt_text(self.processor, question)], images=[image], return_tensors="pt")
        enc = enc.to(self.model.device)
        start = time.perf_counter()
        # One generate call gives both the reply and the answer distribution. The distribution is computed in
        # float32 from the hidden state entering lm_head at the first step, captured by a hook: the model's own
        # logits are bfloat16, whose steps at logit sizes around 20 are coarse enough that yes and no often
        # come out exactly equal (measured: 3 of the sample's 5 questions tied at 0.5, and greedy decoding then
        # broke the tie by token order). lm_head is not quantised, so float32 here is exact up to its weights.
        lm_head = self.model.get_output_embeddings()
        captured = []
        hook = lm_head.register_forward_hook(lambda _m, inputs, _o: captured.append(inputs[0][:, -1, :]))
        try:
            adapter_off = self.model.disable_adapter() if answered_by == "base" else contextlib.nullcontext()
            with self.lock, torch.no_grad(), adapter_off:
                out = self.model.generate(**enc, max_new_tokens=8 if kind != "free" else FREE_FORM_TOKENS, do_sample=False,
                                          return_dict_in_generate=True)
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
            "trained_format": kind != "free",
            "answered_by": answered_by,
            "answer": answer,
            "answer_text": answer_text(question, kind, answer),
            "probability": probability,
            "distribution": distribution,
            "raw_output": raw,
            "latency_ms": latency_ms,
            "model": self.model_id,
            "revision": self.revision,
            "adapter": self.adapter,
            "adapter_id": (f"{Path(self.adapter).parent.name}_lora (Qwen2-VL-2B-Instruct 4-bit)"
                           if answered_by == "adapter" else "Qwen2-VL-2B-Instruct 4-bit (base, adapter off)"),
        }


def build_app(engine):
    from fastapi import FastAPI, HTTPException
    from typing import Literal, Optional

    from pydantic import BaseModel

    app = FastAPI(title="SatQuery VQA model server")

    class VqaRequest(BaseModel):
        image_path: str
        question: str
        free_form: Optional[Literal["base", "adapter"]] = None

    @app.get("/health")
    def health():
        return {"status": "ok", "loaded": True, "model": engine.model_id, "revision": engine.revision,
                "adapter": engine.adapter, "free_form": engine.free_form}

    @app.post("/vqa")
    def vqa(req: VqaRequest):
        path = Path(req.image_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"image not found: {req.image_path}")
        if not req.question.strip():
            raise HTTPException(status_code=400, detail="empty question")
        try:
            return engine.answer(path, req.question.strip(), req.free_form)
        except OSError as exc:  # PIL cannot decode the file
            raise HTTPException(status_code=400, detail=f"cannot read image: {exc}") from exc

    return app


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--adapter", default=str(DEFAULT_ADAPTER))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--size", type=int, default=448, help="square input size; 448 is what run 2 trained at")
    ap.add_argument("--free-form", choices=["base", "adapter"], default="base",
                    help="who answers free-form questions: the base model (adapter off) or the adapter")
    args = ap.parse_args()

    # The model is cached at the pinned revision; a demo must not reach the network.
    os.environ.setdefault("HF_HOME", str(ROOT / "data" / "hf_cache"))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if not Path(args.adapter).is_dir():
        sys.exit(f"adapter folder not found: {args.adapter}")

    import uvicorn

    print(f"loading {args.adapter} ...", flush=True)
    engine = Engine(args.adapter, args.size, args.free_form)
    print("model loaded", flush=True)
    uvicorn.run(build_app(engine), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
