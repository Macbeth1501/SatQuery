"""Shared pieces of B5, the caption/VQA LoRA adapter: model loading, example formatting, scoring.

Recipe (Development Plan B5 / M3, thinned for a first run):
  * backbone Qwen/Qwen2-VL-2B-Instruct at a pinned revision, loaded 4-bit NF4 (QLoRA);
  * vision encoder and the vision-to-language merger stay frozen, and so do the language model's own
    weights; only LoRA matrices on the language model's attention projections (q, k, v, o) train;
  * loss is computed on the answer tokens only, never on the prompt or the image tokens;
  * input is a Sentinel-2 true-colour render. The plan's modality-specific S1/S2 projections need Sentinel-1
    inputs, which this first slice does not carry, so they are deferred rather than faked.
"""
import json
import re
from pathlib import Path

import torch
from PIL import Image

MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
REVISION = "895c3a49bc3fa70a340399125c650a463535e71c"  # read from the Hub and downloaded at this commit, 2026-09-20
# Attention projections of the LANGUAGE model. The vision tower names its attention `qkv` / `proj`, so
# these four names cannot match anything in the frozen vision encoder.
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj"]
END_OF_TURN = "<|im_end|>"


def pick_dtype():
    """bfloat16 on Ampere or newer; float16 otherwise. A Kaggle T4 (compute capability 7.5) has no bf16."""
    if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8:
        return torch.bfloat16
    return torch.float16


def load_model(adapter=None, dtype=None):
    from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration

    dtype = dtype or pick_dtype()
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype,
    )
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_ID, revision=REVISION, quantization_config=quant, device_map={"": 0}, dtype=dtype,
    )
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=REVISION)
    processor.tokenizer.padding_side = "right"
    if adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, adapter)
    return model, processor, dtype


def prompt_text(processor, question):
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": question}]}]
    return processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def open_image(root, rel, size):
    return Image.open(Path(root) / rel).convert("RGB").resize((size, size), Image.BICUBIC)


def collate(processor, root, size, batch):
    """Tokenises a batch and masks everything except the answer (and its end-of-turn token) from the loss."""
    images = [open_image(root, ex["image"], size) for ex in batch]
    prompts = [prompt_text(processor, ex["question"]) for ex in batch]
    fulls = [p + ex["answer"] + END_OF_TURN for p, ex in zip(prompts, batch)]
    enc = processor(text=fulls, images=images, padding=True, return_tensors="pt")
    labels = enc["input_ids"].clone()
    labels[enc["attention_mask"] == 0] = -100
    for i, (p, img) in enumerate(zip(prompts, images)):
        prompt_len = processor(text=[p], images=[img], return_tensors="pt")["input_ids"].shape[1]
        labels[i, :prompt_len] = -100
    enc["labels"] = labels
    return enc


@torch.no_grad()
def generate(model, processor, root, size, example, max_new_tokens, blank_image=False):
    """`blank_image` swaps the picture for a constant mid-grey one, so the reply can only come from the text."""
    image = Image.new("RGB", (size, size), (128, 128, 128)) if blank_image else open_image(root, example["image"], size)
    enc = processor(text=[prompt_text(processor, example["question"])], images=[image], return_tensors="pt").to(model.device)
    out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
    return processor.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()


# ---- scoring: fixed rules, written down so a base run and an adapter run are judged identically ----------

def normalise_choice(text, kind):
    """Reduces a free-form reply to yes/no or a-d; returns None when no answer can be read."""
    text = text.strip().lower()
    if kind == "binary":
        m = re.match(r"^\W*(yes|no)\b", text)
    else:
        m = re.match(r"^\W*\(?([a-d])\b", text)
    return m.group(1) if m else None


def score_choice(example, output):
    return normalise_choice(output, example["type"]) == normalise_choice(example["answer"], example["type"])


def caption_mentions(example, output):
    """Whether a caption names the patch's country and season, the two facts an image can support here."""
    low = output.lower()
    return {
        "country": example["country"].lower() in low,
        "season": example["season"].lower() in low or (example["season"] == "Fall" and "autumn" in low),
    }
