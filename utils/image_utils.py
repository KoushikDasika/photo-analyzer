"""
Image Utilities

Helpers for listing and loading images for the grading agents.
Follows the same format as the Strands community image_reader tool:
  https://github.com/strands-agents/tools/blob/main/src/strands_tools/image_reader.py

The Strands Converse API expects image content blocks in this shape:
  {"image": {"format": "jpeg", "source": {"bytes": <raw_bytes>}}}

Example usage:
    from utils.image_utils import list_images, image_content_block

    for image_path in list_images():
        block = image_content_block(image_path)
        result = grading_agent([
            block,
            {"type": "text", "text": f"Evaluate this image: {image_path.name}"},
        ])
"""
import logging
import os
from pathlib import Path

from PIL import Image
from wand.image import Image as WandImage

log = logging.getLogger(__name__)


# BMP excluded — not supported by the Strands Converse API
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# iPhone photos are 12 MP (4032×3024, 3–6 MB). Ollama rejects payloads that
# large with an HTML error. 1024 px on the long edge is plenty for a VLM to
# assess composition, lighting, expression, etc.
MAX_IMAGE_PX = int(os.getenv("MAX_IMAGE_PX", "1024"))


def list_images(directory: str | None = None) -> list[Path]:
    """Return a sorted list of image Paths found in `directory`.

    Defaults to the INPUT_IMAGES_DIR env var (or ./input_images).
    """
    directory = directory or os.getenv("INPUT_IMAGES_DIR", "./input_images")
    root = Path(directory)
    return sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_image_bytes(image_path: str | Path, max_px: int = MAX_IMAGE_PX) -> bytes:
    """Resize image to fit within max_px using Wand (ImageMagick) and return JPEG bytes.

    - auto_orient() corrects EXIF rotation (iPhone photos are often rotated).
    - transform(resize=...) with '>' only shrinks — never enlarges.
    - Phone photos (4032×3024, 3–6 MB) become ~100–300 KB.
    """
    path = Path(image_path)
    original_kb = path.stat().st_size // 1024
    log.debug(f"[{path.name}] resizing  original={original_kb} KB  max={max_px}px")

    with WandImage(filename=str(path)) as img:
        img.auto_orient()
        img.transform(resize=f"{max_px}x{max_px}>")
        img.format = "jpeg"
        data = img.make_blob()

    resized_kb = len(data) // 1024
    log.info(f"[{path.name}] resized  {original_kb} KB → {resized_kb} KB")
    return data


def image_format(image_path: str | Path) -> str:
    """Return the Strands-compatible format string for an image.

    Uses PIL to detect the actual format (handles mis-named files).
    Returns one of: "jpeg", "png", "gif", "webp".
    Defaults to "jpeg" if format is unrecognised.
    """
    with Image.open(image_path) as img:
        fmt = (img.format or "").lower()
    if fmt not in ("jpeg", "png", "gif", "webp"):
        fmt = "jpeg"
    return fmt


def image_content_block(image_path: str | Path) -> dict:
    """Return a Strands Converse API image content block for this image.

    Wand always outputs JPEG so format is hardcoded to "jpeg".

        result = agent([
            image_content_block(path),
            {"type": "text", "text": "Evaluate this image: photo.jpg"},
        ])
    """
    return {
        "image": {
            "format": "jpeg",
            "source": {"bytes": load_image_bytes(image_path)},
        }
    }


# ── Quick preview ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # python -m utils.image_utils
    images = list_images()
    print(f"Found {len(images)} images")
    for p in images[:5]:
        print(f"  {p.name}  (format: {image_format(p)},  size: {p.stat().st_size} bytes)")
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more")
