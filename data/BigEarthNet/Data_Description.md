# BigEarthNet.txt – Dataset Description

## Conceptual Structure

```
BigEarthNet
│
├── Satellite imagery
│     ├── Sentinel-1 (SAR)
│     └── Sentinel-2 (Multispectral)
│
└── BigEarthNet.txt
      │
      ├── Same/associated S1 + S2 image pairs
      │
      └── Text annotations
            ├── Binary VQA
            ├── Multiple-choice VQA
            ├── Captions
            └── Referring / localization instructions
```

**Key facts**

- The Hugging Face repository is **BigEarthNet.txt**.
- It is a multi-sensor image-text dataset based on **464,044 co-registered Sentinel-1 + Sentinel-2 image pairs**.
- These pairs are associated with approximately **9.55–9.6 million textual annotations**.
- Linked paper: arXiv 2603.29630.

---

## What is on Hugging Face

The dataset contains **9.55 million rows** in a single `all_data` split.

Each row contains fields such as:

| Field          | Description                                      |
|----------------|--------------------------------------------------|
| `s1_name`      | Sentinel-1 image identifier                      |
| `patch_id`     | Sentinel-2 patch identifier                      |
| `input`        | Question / instruction / text                    |
| `output`       | Answer                                           |
| `type`         | e.g. binary, mcq, captioning, bounding box       |
| `category`     | e.g. presence, area, count, adjacency, point, reference |
| `split`        | train / validation / test / bench                |
| `latitude`     | Latitude of the center of the image patch        |
| `longitude`    | Longitude of the center of the image patch       |
| `country`      | Acquisition country                              |
| `season`       | Acquisition season                               |
| `climate_zone` | Köppen-Geiger climate zone                       |

**Example**

- Question: *"Would you say that any arable land lies next to pastures in the image?"*
- Answer: `yes`
- Type: `binary`
- Category: `adjacency`

Other rows contain bounding-box instructions, captions, and multiple-choice questions.

---

## Parquet File Structure

The file `BigEarthNet.txt.parquet` contains the following attributes:

| Attribute       | Description |
|-----------------|-------------|
| `ID`            | Unique identifier for each sample |
| `s1_name`       | Name of the Sentinel-1 patch from BigEarthNet v2.0 |
| `patch_id`      | Name of the Sentinel-2 patch from BigEarthNet v2.0 |
| `input`         | Instruction or question for the VLM |
| `output`        | Reference answer |
| `type`          | Broader task type: `binary`, `mcq`, `captioning`, or `bounding box` |
| `category`      | Fine-grained task type (see dataset card for all type–category combinations) |
| `split`         | Associated split: `train`, `validation`, `test`, or `bench` |
| `latitude`      | Latitude of the center of the image patch |
| `longitude`     | Longitude of the center of the image patch |
| `country`       | Acquisition country of the image patch |
| `season`        | Acquisition season of the image patch |
| `climate_zone`  | Associated Köppen-Geiger climate zone |

---

## How to Use

Recommended way to prepare image and text data jointly: use the custom PyTorch Dataset `BENTxTDataset` or the Lightning DataModule `BENTxTDataModule` provided in `ben_txt_datamodule.py`.

### 1. Download BigEarthNet.txt.parquet

```bash
git clone https://huggingface.co/datasets/BIFOLD-BigEarthNetv2-0/BigEarthNet.txt
```

### 2. Download the Image Data

Download the Sentinel-1 and Sentinel-2 image data from the **BigEarthNet v2.0** website.

### 3. Preprocess the Image Data

Convert the Sentinel-1 and Sentinel-2 image data to safetensors stored in an LMDB database for higher throughput using **rico-hdl**.

Follow the installation instructions on GitHub, then run:

```bash
rico-hdl bigearthnet \
  --bigearthnet-s1-dir <S1_ROOT_DIR> \
  --bigearthnet-s2-dir <S2_ROOT_DIR> \
  --target-dir Encoded-BigEarthNet
```

### 4. Load the Data

Install `uv`, then install the required packages:

```bash
uv sync --extra <option>   # use "cpu" or "cu126"
```

You can then run the example:

```bash
uv run example_data_loading.py
```

#### Example A – BENTxTDataset (RGB bands)

```python
from ben_txt_datamodule import BENTxTDataset

ds_rgb = BENTxTDataset(
    lmdb_file="Encoded-BigEarthNet/",
    metadata_file="BigEarthNet.txt.parquet",
    bands=("B04", "B03", "B02"),
    img_size=120
)

sample = ds_rgb[0]
print(f"RGB input image: {sample['image_input'].shape}")
print(f"Text input: {sample['text_input']}")
print(f"Reference output: {sample['reference_output']}")
```

#### Example B – BENTxTDataModule (S1 + S2, with filters)

```python
from ben_txt_datamodule import BENTxTDataModule

# Lightning DataModule using 10m and 20m bands from Sentinel-1 and Sentinel-2
# with multiple metadata filters. Creates train / val / test / bench dataloaders.
dm = BENTxTDataModule(
    image_lmdb_file="Encoded-BigEarthNet/",
    metadata_file="BigEarthNet.txt.parquet",
    bands="S1S2-10m20m",
    img_size=120,
    batch_size=1,
    num_workers_dataloader=0,
    types=["mcq"],
    categories=["climate zone"],
    countries=["Portugal", "Finland"],
    seasons=["Summer"],
    climate_zones=None,
    point_token=["<point>", "</point>"],
    ref_token=["<ref>", "</ref>"]
)
dm.setup()

train_dl = dm.train_dataloader()
for batch in train_dl:
    print(f"Batch image input shape: {batch['image_input'].shape}")
    print(f"First batch sample text input: {batch['text_input'][0]}")
    print(f"First batch sample text reference output: {batch['reference_output']}")
    break
```

---

## Citation

If you use the BigEarthNet.txt dataset, please cite:

```
J. Herzog, M. Adler, L. Hackel, Y. Shu, A. Zavras, I. Papoutsis, P. Rota, B. Demir,
"BigEarthNet.txt: A Large-Scale Multi-Sensor Image-Text Dataset and Benchmark for Earth Observation",
Arxiv Preprint arXiv:2603.29630, 2026.
```

BibTeX:

```bibtex
@article{Herzog2026BigEarthNetTXT,
  title={BigEarthNet.txt: A Large-Scale Multi-Sensor Image-Text Dataset and Benchmark for Earth Observation},
  author={Johann-Ludwig Herzog and Mathis Jürgen Adler and Leonard Hackel and Yan Shu and Angelos Zavras and Ioannis Papoutsis and Paolo Rota and Begüm Demir},
  journal={Arxiv Preprint arXiv:2603.29630},
  year={2026},
}
```
