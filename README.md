# image_to_avif

Bulk-convert images (jpg / png / webp / bmp / tiff / gif) to AVIF, WebP, JPEG or PNG,
with a friendly interactive CLI.

## Setup (once)

```bash
cd tools/image_to_avif
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Use

Drop the images you want to convert into `input/` (subfolders are preserved),
then run:

```bash
python convert.py
```

You'll be prompted to pick the output format (AVIF, WebP, JPEG, PNG), then a
progress bar tracks the conversion and a results table shows the size savings
per file.

Results appear under `output/` with the same folder structure and the
matching extension for the format you chose.

Optional flags (skip the prompt by passing `--format` or `--yes`):

```bash
python convert.py \
  --input path/to/src \
  --output path/to/dst \
  --format webp \
  --quality 55 \
  --speed 6 \
  --yes
```

- `--format` / `-f`: `avif`, `webp`, `jpeg`, or `png` (default: asked interactively).
- `--quality` / `-q`: 0-100, where the format supports it (default 60). Lower = smaller file, more artifacts. Ignored for `png`.
- `--speed` / `-s`: AVIF encoder speed 0-10, higher = faster (default 6). Only applies to `avif`.
- `--yes` / `-y`: skip the interactive format prompt and use the default (`avif`) or whatever `--format` was given.
