"""HTTP client for the real VQA model server (`ml/serve_vqa.py`).

The model runs in its own process, in the ML environment, so torch never enters the backend
(Development Plan C2). Two failures are kept apart because they need different HTTP answers:
the server cannot be reached at all (503, the caller should start it), or it answered but not
with a usable result (502).
"""
from pathlib import Path
from typing import Any, Dict

import httpx

from backend.app import config


class ModelUnavailableError(RuntimeError):
    """The model server did not answer: not started, crashed, or timed out."""


class ModelError(RuntimeError):
    """The model server answered, but not with a usable result."""


REQUIRED_FIELDS = ("kind", "answer", "answer_text", "raw_output", "latency_ms", "model", "adapter_id")


def is_enabled() -> bool:
    return bool(config.VQA_MODEL_URL)


async def ask_vqa(image_path: Path, question: str, task: str = "vqa") -> Dict[str, Any]:
    """`task` is the server's task token ("vqa" or "caption" on this path); the adapter is
    config.VQA_MODEL_ADAPTER. A task the adapter was not trained for comes back as HTTP 422,
    which surfaces as ModelError like any other unusable reply."""
    url = config.VQA_MODEL_URL.rstrip("/") + "/infer"
    payload = {
        "image_path": str(Path(image_path).resolve()),
        "question": question,
        "task": task,
        "adapter": config.VQA_MODEL_ADAPTER,
    }
    try:
        async with httpx.AsyncClient(timeout=config.VQA_MODEL_TIMEOUT_SECONDS) as client:
            reply = await client.post(url, json=payload)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise ModelUnavailableError(
            f"Model server at {config.VQA_MODEL_URL} is not reachable ({type(exc).__name__}). "
            "Start it with: .venv-ml/Scripts/python.exe ml/serve_vqa.py --port 8001"
        ) from exc
    except httpx.HTTPError as exc:
        raise ModelUnavailableError(f"Model server request failed: {exc}") from exc

    if reply.status_code != 200:
        raise ModelError(f"Model server returned HTTP {reply.status_code}: {reply.text[:300]}")
    try:
        body = reply.json()
    except ValueError as exc:
        raise ModelError("Model server returned a body that is not JSON.") from exc
    missing = [f for f in REQUIRED_FIELDS if f not in body]
    if missing:
        raise ModelError(f"Model server reply is missing {', '.join(missing)}.")
    return body
