#!/usr/bin/env python3
"""Bulk-convert images from an input folder to AVIF/WebP/JPEG/PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image
import pillow_avif  # noqa: F401  # side effect: registers AVIF plugin

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif"}

FORMATS: dict[str, dict] = {
    "avif": {"pillow": "AVIF", "ext": ".avif", "supports_quality": True, "supports_speed": True},
    "webp": {"pillow": "WEBP", "ext": ".webp", "supports_quality": True, "supports_speed": False},
    "jpeg": {"pillow": "JPEG", "ext": ".jpg", "supports_quality": True, "supports_speed": False},
    "png": {"pillow": "PNG", "ext": ".png", "supports_quality": False, "supports_speed": False},
}


def iter_images(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT
    )


def convert(src: Path, dst: Path, fmt: str, quality: int, speed: int) -> None:
    spec = FORMATS[fmt]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        save_kwargs = {}
        if spec["supports_quality"]:
            save_kwargs["quality"] = quality
        if spec["supports_speed"]:
            save_kwargs["speed"] = speed

        if spec["pillow"] == "JPEG" and im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        elif spec["pillow"] == "AVIF" and im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")

        im.save(dst, format=spec["pillow"], **save_kwargs)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Convert images to AVIF, WebP, JPEG or PNG.")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=here / "input",
        help="Source folder (default: ./input)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=here / "output",
        help="Destination folder (default: ./output)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=list(FORMATS),
        default="avif",
        help="Output format (default: avif)",
    )
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=60,
        help="Encoder quality 0-100, where supported (default: 60)",
    )
    parser.add_argument(
        "--speed", "-s",
        type=int,
        default=6,
        help="AVIF encoder speed 0-10, higher = faster (default: 6)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src_root: Path = args.input.resolve()
    dst_root: Path = args.output.resolve()

    if not src_root.exists():
        print(f"input folder not found: {src_root}", file=sys.stderr)
        return 1

    files = iter_images(src_root)
    if not files:
        print(f"no images found in {src_root}")
        return 0

    ext = FORMATS[args.format]["ext"]
    failures = 0
    for src in files:
        rel = src.relative_to(src_root).with_suffix(ext)
        dst = dst_root / rel
        try:
            convert(src, dst, args.format, args.quality, args.speed)
            saved = dst.stat().st_size
            original = src.stat().st_size
            ratio = saved / original * 100 if original else 0
            print(f"{rel}  ({original:,} → {saved:,} B, {ratio:.0f}%)")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"failed {rel}: {exc}", file=sys.stderr)

    print(f"\ndone: {len(files) - failures}/{len(files)} converted → {dst_root}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
