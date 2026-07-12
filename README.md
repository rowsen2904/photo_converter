# image_to_avif

Bulk-convert images (jpg / png / webp / bmp / tiff / gif) to AVIF.

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

Results appear under `output/` with the same folder structure and `.avif`
extensions.

Optional flags:

```bash
python convert.py \
  --input path/to/src \
  --output path/to/dst \
  --quality 55 \
  --speed 6
```

- `--quality` 0-100 (default 60). Lower = smaller file, more artifacts.
- `--speed` 0-10 (default 6). Higher = faster encode, slightly larger file.
