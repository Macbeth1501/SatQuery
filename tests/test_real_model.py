"""The real-model path for single-image questions (SATQUERY_VQA_MODEL_URL set).

No GPU and no model server: `model_client.ask_vqa` is replaced by a fake that records its calls,
and the scenario engine is booby-trapped so a test fails if the real path ever consults it.
The live check against the running server is done by hand (see docs/STARTUP_GUIDE.md).
"""
import json
from pathlib import Path

import pytest

from backend.app import config
from backend.app.orchestrator.query_interpreter import QueryInterpreter
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskType
from backend.app.services import model_client

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "frontend" / "public" / "real"
SAMPLES = json.loads((ROOT / "frontend" / "src" / "data" / "realSamples.json").read_text(encoding="utf-8"))["samples"]
SAMPLE = SAMPLES[0]
RASTER = (SAMPLE_DIR / SAMPLE["rasterFile"]).read_bytes()


def fake_reply(probability=0.8, kind="binary", answer="no", answer_text="No"):
    return {
        "kind": kind, "trained_format": kind != "free", "answer": answer, "answer_text": answer_text,
        "probability": probability if kind != "free" else None,
        "distribution": {"yes": round(1 - probability, 4), "no": probability} if kind == "binary" else {},
        "raw_output": answer, "latency_ms": 412.0, "model": "Qwen/Qwen2-VL-2B-Instruct",
        "revision": "895c3a49", "adapter": "data/b5_run2/adapter_final",
        "adapter_id": "b5_run2_lora (Qwen2-VL-2B-Instruct 4-bit)",
    }


class Calls(list):
    """The fake server's received calls, plus `.reply`, the answer it gives."""


@pytest.fixture
def model_on(monkeypatch):
    """Switches the real path on with a fake server; returns the list of calls it received."""
    calls = Calls()
    reply = {"value": fake_reply()}

    async def fake_ask(image_path, question, task="vqa"):
        calls.append({"image_path": Path(image_path), "question": question, "task": task})
        return reply["value"]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("the scenario engine was consulted on the real-model path")

    from backend.app.specialists.scenario_engine import scenario_engine

    monkeypatch.setattr(config, "VQA_MODEL_URL", "http://model.invalid")
    monkeypatch.setattr(model_client, "ask_vqa", fake_ask)
    monkeypatch.setattr(scenario_engine, "get_dynamic_result", forbidden)
    calls.reply = reply  # lets a test change what the fake answers
    return calls


def ask(client, question, filename=None, raster=RASTER, expected_status=200):
    filename = filename or SAMPLE["rasterFile"]
    response = client.post("/v1/analyze", data={"query": question},
                           files=[("files", (filename, raster, "image/tiff"))])
    assert response.status_code == expected_status, response.text
    return response.json()


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_every_sample_question_is_routed_to_single_vqa(sample):
    image = ImageMetadata(image_id="img_1", name=sample["rasterFile"])
    for q in sample["questions"]:
        spec = QueryInterpreter().interpret(q["question"], [image])
        assert spec.status == "resolved", q["question"]
        assert spec.task_type == TaskType.SINGLE_VQA, q["question"]


def test_single_image_question_reaches_the_model_with_the_uploaded_file(client, model_on):
    question = SAMPLE["questions"][0]["question"]
    body = ask(client, question)

    assert len(model_on) == 1
    call = model_on[0]
    assert call["question"] == question
    assert call["image_path"].is_file()
    assert call["image_path"].read_bytes() == RASTER  # the upload itself, not a stand-in
    assert call["task"] == "vqa"
    assert body["answerText"].startswith("No")
    assert body["rejected"] is False


def test_real_answer_carries_no_invented_boxes(client, model_on):
    body = ask(client, SAMPLE["questions"][0]["question"])
    assert body["evidence"]["boxes"] == []
    components = [s["component"] for s in body["executionTrace"]["steps"]]
    assert "GroundingSpecialist" not in components


def test_trace_records_the_real_model_call(client, model_on):
    body = ask(client, SAMPLE["questions"][0]["question"])
    step = next(s for s in body["executionTrace"]["steps"] if s["component"] == "VqaCaptionSpecialist")
    assert step["adapterIdOrVersion"] == "b5_run2_lora (Qwen2-VL-2B-Instruct 4-bit)"
    params = step["parametersUsed"]
    assert params["model"] == "Qwen/Qwen2-VL-2B-Instruct"
    assert params["question_kind"] == "binary"
    assert params["model_latency_ms"] == 412.0
    assert params["answer_distribution"] == {"yes": 0.2, "no": 0.8}


@pytest.mark.parametrize("probability, tier", [(0.9, "Medium"), (0.75, "Medium"), (0.74, "Low"), (0.51, "Low")])
def test_tier_comes_from_the_model_probability_and_is_never_high(client, model_on, probability, tier):
    model_on.reply["value"] = fake_reply(probability=probability)
    body = ask(client, SAMPLE["questions"][0]["question"])
    assert body["confidence"]["tier"] == tier
    assert f"{probability * 100:.0f}%" in body["confidence"]["rationale"]


def test_free_form_reply_is_low_and_says_it_is_unevaluated(client, model_on):
    model_on.reply["value"] = fake_reply(kind="free", answer="Farmland with hedgerows.",
                                         answer_text="Farmland with hedgerows.")
    body = ask(client, "Describe the land-cover in this image.")
    assert body["taskSpec"]["taskType"] == "single_caption"
    assert model_on[0]["task"] == "caption"  # the task token the server checks against the adapter
    assert body["confidence"]["tier"] == "Low"
    assert "have not been evaluated" in body["answerText"]
    # the adapter did see captions (1,431 of 19,489 training examples); the old note denied it
    assert "trained only" not in body["answerText"]
    assert "BigEarthNet captions" in body["answerText"]


def test_free_form_reply_from_the_base_model_says_so(client, model_on):
    reply = fake_reply(kind="free", answer="Fields and a road.", answer_text="Fields and a road.")
    model_on.reply["value"] = {**reply, "answered_by": "base"}
    body = ask(client, "Describe the land-cover in this image.")
    assert "adapter switched off" in body["answerText"]
    assert body["confidence"]["tier"] == "Low"


def test_multiple_choice_answer_text_is_passed_through(client, model_on):
    model_on.reply["value"] = fake_reply(probability=0.34, kind="mcq", answer="b", answer_text="b) 30 to 60%")
    body = ask(client, SAMPLE["questions"][4]["question"])
    assert body["answerText"].startswith("b) 30 to 60%")
    assert body["confidence"]["tier"] == "Low"


DEMO_DIR = ROOT / "frontend" / "public" / "demo"
DEMO_PAIR = ("Sentinel2_Bengaluru_2023.tif", "Sentinel2_Bengaluru_2025.tif")


def post_pair(client, question, names_and_bytes):
    files = [("files", (name, data, "image/tiff")) for name, data in names_and_bytes]
    response = client.post("/v1/analyze", data={"query": question}, files=files)
    assert response.status_code == 200, response.text
    return response.json()


def test_other_tasks_on_demo_inputs_stay_on_the_demo_engine(client, monkeypatch):
    """Only single-image questions go to the model; the demo pair still gets its scripted change report."""
    calls = []

    async def fake_ask(image_path, question, task="vqa"):
        calls.append(question)
        return fake_reply()

    monkeypatch.setattr(config, "VQA_MODEL_URL", "http://model.invalid")
    monkeypatch.setattr(model_client, "ask_vqa", fake_ask)
    body = post_pair(client, "What changed between these two dates?",
                     [(n, (DEMO_DIR / n).read_bytes()) for n in DEMO_PAIR])
    assert calls == []
    assert body["rejected"] is False
    assert body["taskSpec"]["taskType"] == "change_vqa"


def test_change_on_real_images_says_no_trained_model_exists(client, model_on):
    """The owner's live session: "Do change anaylisis" on two real patches got the scripted report, rated High."""
    pair = [(SAMPLE["rasterFile"], RASTER)] * 2  # one real patch twice, so the footprints overlap
    body = post_pair(client, "What changed between these two dates?", pair)
    assert body["rejected"] is True
    assert body["rejectionDetails"]["reasonCode"] == "no_trained_model"
    assert "change_vqa" in body["rejectionDetails"]["humanReadableReason"]
    assert body["confidence"]["tier"] == "Low"
    assert model_on == []  # nor was the model asked; model_on also forbids the scenario engine


def test_grounding_on_a_real_image_says_no_trained_model_exists(client, model_on):
    body = ask(client, "Highlight the water bodies in this image.")
    assert body["taskSpec"]["taskType"] == "single_grounding"
    assert body["rejectionDetails"]["reasonCode"] == "no_trained_model"
    assert body["evidence"]["boxes"] == []


def test_a_real_image_beside_a_demo_image_is_still_refused(client, model_on):
    # the same real bytes in both slots, so the footprints overlap; slot 1 carries a demo file name
    pair = [(DEMO_PAIR[0], RASTER), (SAMPLE["rasterFile"], RASTER)]
    body = post_pair(client, "What changed between these two dates?", pair)
    assert body["rejectionDetails"]["reasonCode"] == "no_trained_model"


def test_without_the_live_model_real_images_keep_the_old_behaviour(client, monkeypatch):
    monkeypatch.setattr(config, "VQA_MODEL_URL", None)
    pair = [(SAMPLE["rasterFile"], RASTER)] * 2  # one real patch twice, so the footprints overlap
    body = post_pair(client, "What changed between these two dates?", pair)
    assert body["rejected"] is False


def test_demo_input_names_match_the_frontend_scenarios():
    """A renamed demo file would otherwise be refused as a user's image in live mode."""
    import re

    from backend.app.services.metadata_service import DEMO_INPUT_NAMES

    source = (ROOT / "frontend" / "src" / "data" / "mockScenarios.ts").read_text(encoding="utf-8")
    names = set(re.findall(r"name: '([^']+\.(?:tif|png))'", source))
    assert names == set(DEMO_INPUT_NAMES)


def test_demo_flag_never_reaches_the_wire():
    image = ImageMetadata(image_id="img_1", demo_input=True)
    assert "demoInput" not in image.model_dump(by_alias=True)


def test_unreachable_model_is_a_503_not_a_demo_answer(client, monkeypatch):
    monkeypatch.setattr(config, "VQA_MODEL_URL", "http://127.0.0.1:9")  # nothing listens on port 9
    monkeypatch.setattr(config, "VQA_MODEL_TIMEOUT_SECONDS", 2.0)
    body = ask(client, SAMPLE["questions"][0]["question"], expected_status=503)
    assert "not reachable" in body["detail"]


def test_unusable_model_reply_is_a_502(client, monkeypatch):
    async def broken(image_path, question, task="vqa"):
        raise model_client.ModelError("Model server reply is missing answer.")

    monkeypatch.setattr(config, "VQA_MODEL_URL", "http://model.invalid")
    monkeypatch.setattr(model_client, "ask_vqa", broken)
    body = ask(client, SAMPLE["questions"][0]["question"], expected_status=502)
    assert "missing answer" in body["detail"]


def test_switch_off_keeps_the_demo_engine(client, monkeypatch):
    async def must_not_run(image_path, question, task="vqa"):
        raise AssertionError("model called while SATQUERY_VQA_MODEL_URL is unset")

    monkeypatch.setattr(config, "VQA_MODEL_URL", None)
    monkeypatch.setattr(model_client, "ask_vqa", must_not_run)
    body = ask(client, SAMPLE["questions"][0]["question"])
    assert body["rejected"] is False
    assert body["confidence"]["tier"] in {"High", "Medium", "Low"}


def model_server(monkeypatch, status=200, body=None):
    """Points model_client at an in-process fake server (httpx.MockTransport); returns the requests it got."""
    import httpx

    seen = []

    def handler(request):
        seen.append({"path": request.url.path, "json": json.loads(request.content)})
        return httpx.Response(status, json=body if body is not None else fake_reply())

    real_client = httpx.AsyncClient

    def client_with_mock(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(config, "VQA_MODEL_URL", "http://model.invalid")
    monkeypatch.setattr(model_client.httpx, "AsyncClient", client_with_mock)
    return seen


def test_client_asks_infer_with_the_configured_adapter_and_task(monkeypatch, tmp_path):
    import asyncio

    seen = model_server(monkeypatch)
    monkeypatch.setattr(config, "VQA_MODEL_ADAPTER", "run3")
    image = tmp_path / "x.tif"
    image.write_bytes(b"x")
    asyncio.run(model_client.ask_vqa(image, "Is there water?", task="caption"))
    assert seen == [{"path": "/infer", "json": {"image_path": str(image.resolve()), "question": "Is there water?",
                                                "task": "caption", "adapter": "run3"}}]


def test_client_defaults_to_run2_the_live_demo_adapter():
    assert config.VQA_MODEL_ADAPTER == "run2"


def test_task_the_adapter_was_not_trained_for_is_a_model_error(monkeypatch, tmp_path):
    import asyncio

    model_server(monkeypatch, status=422, body={"detail": "adapter 'run2' was trained for vqa, caption, not ground"})
    image = tmp_path / "x.tif"
    image.write_bytes(b"x")
    with pytest.raises(model_client.ModelError, match="422"):
        asyncio.run(model_client.ask_vqa(image, "Where is the water?", task="ground"))


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_sample_raster_is_real_and_georeferenced(sample):
    rasterio = pytest.importorskip("rasterio")
    from PIL import Image

    with rasterio.open(SAMPLE_DIR / sample["rasterFile"]) as src:
        assert str(src.crs) == sample["crs"]
        assert abs(src.transform.a) == sample["gsdMeters"] == 10.0
        assert src.count == 3
        assert "Not synthetic" in src.tags()["SOURCE_NOTE"]
        assert src.tags()["BIGEARTHNET_PATCH"] == sample["patchId"]
    with Image.open(SAMPLE_DIR / sample["rasterFile"]) as img:
        assert img.size == (sample["widthPx"], sample["heightPx"])
    assert (SAMPLE_DIR / sample["previewFile"]).is_file()


def test_samples_are_distinct_and_carry_questions():
    assert len({s["patchId"] for s in SAMPLES}) == len(SAMPLES) >= 2
    for sample in SAMPLES:
        assert len(sample["questions"]) >= 3
        for q in sample["questions"]:
            assert q["type"] in {"binary", "mcq"}
            assert q["answer"] in ({"yes", "no"} if q["type"] == "binary" else {"a", "b", "c", "d"})
