#!/usr/bin/env python3
"""Bulk-convert images from an input folder to AVIF/WebP/JPEG/PNG."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
import pillow_avif  # noqa: F401  # side effect: registers AVIF plugin

try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.prompt import IntPrompt
    HAS_RICH = True
except ImportError:  # pragma: no cover - degrade gracefully without rich
    HAS_RICH = False

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif"}

FORMATS: dict[str, dict] = {
    "avif": {"pillow": "AVIF", "ext": ".avif", "supports_quality": True, "supports_speed": True},
    "webp": {"pillow": "WEBP", "ext": ".webp", "supports_quality": True, "supports_speed": False},
    "jpeg": {"pillow": "JPEG", "ext": ".jpg", "supports_quality": True, "supports_speed": False},
    "png": {"pillow": "PNG", "ext": ".png", "supports_quality": False, "supports_speed": False},
}

console = Console() if HAS_RICH else None


def pick_format_interactively() -> str:
    options = list(FORMATS)
    if HAS_RICH:
        console.print("\n[bold cyan]Choose an output format:[/bold cyan]")
        for i, name in enumerate(options, start=1):
            console.print(f"  [{i}] {name}")
        idx = IntPrompt.ask(
            "Format",
            choices=[str(i) for i in range(1, len(options) + 1)],
            default=1,
        )
        return options[idx - 1]

    print("\nChoose an output format:")
    for i, name in enumerate(options, start=1):
        print(f"  [{i}] {name}")
    while True:
        raw = input(f"Format [1-{len(options)}] (default 1): ").strip() or "1"
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("invalid choice, try again")


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
        default=None,
        help="Output format (default: ask interactively)",
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
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip interactive prompts and use defaults/flags as given",
    )
    return parser.parse_args()


@dataclass
class Result:
    rel: Path
    original: int
    saved: int
    ok: bool
    error: str = ""


def run_conversion(files: list[Path], src_root: Path, dst_root: Path, fmt: str, quality: int, speed: int) -> list[Result]:
    results: list[Result] = []
    ext = FORMATS[fmt]["ext"]

    if HAS_RICH:
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        )
        with progress:
            task = progress.add_task("converting", total=len(files))
            for src in files:
                results.append(_convert_one(src, src_root, dst_root, fmt, ext, quality, speed))
                progress.advance(task)
    else:
        for src in files:
            results.append(_convert_one(src, src_root, dst_root, fmt, ext, quality, speed))
            print(f"{results[-1].rel} ... {'ok' if results[-1].ok else 'FAILED'}")

    return results


def _convert_one(src: Path, src_root: Path, dst_root: Path, fmt: str, ext: str, quality: int, speed: int) -> Result:
    rel = src.relative_to(src_root).with_suffix(ext)
    dst = dst_root / rel
    try:
        convert(src, dst, fmt, quality, speed)
        return Result(rel, src.stat().st_size, dst.stat().st_size, ok=True)
    except Exception as exc:  # noqa: BLE001
        return Result(rel, src.stat().st_size, 0, ok=False, error=str(exc))


def print_summary(results: list[Result], dst_root: Path) -> None:
    failures = [r for r in results if not r.ok]
    successes = [r for r in results if r.ok]

    if HAS_RICH:
        table = Table(title="Conversion results")
        table.add_column("File")
        table.add_column("Original", justify="right")
        table.add_column("Saved", justify="right")
        table.add_column("Ratio", justify="right")
        for r in successes:
            ratio = r.saved / r.original * 100 if r.original else 0
            table.add_row(str(r.rel), f"{r.original:,} B", f"{r.saved:,} B", f"{ratio:.0f}%")
        for r in failures:
            table.add_row(str(r.rel), "-", "-", f"[red]failed: {r.error}[/red]")
        console.print(table)
        console.print(
            f"\n[bold green]done:[/bold green] {len(successes)}/{len(results)} converted → {dst_root}"
        )
    else:
        for r in successes:
            ratio = r.saved / r.original * 100 if r.original else 0
            print(f"{r.rel}  ({r.original:,} → {r.saved:,} B, {ratio:.0f}%)")
        for r in failures:
            print(f"failed {r.rel}: {r.error}", file=sys.stderr)
        print(f"\ndone: {len(successes)}/{len(results)} converted → {dst_root}")


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

    fmt = args.format
    if fmt is None and not args.yes:
        fmt = pick_format_interactively()
    elif fmt is None:
        fmt = "avif"

    results = run_conversion(files, src_root, dst_root, fmt, args.quality, args.speed)
    print_summary(results, dst_root)

    return 1 if any(not r.ok for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
