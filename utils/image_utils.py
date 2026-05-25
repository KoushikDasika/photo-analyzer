"""
Image Utilities

Helpers for listing and loading images for the grading agents.
Follows the same format as the Strands community image_reader tool:
  https://github.com/strands-agents/tools/blob/main/src/strands_tools/image_reader.py

The Strands Converse API expects image content blocks in this shape:
  {"image": {"format": "jpeg", "source": {"bytes": <raw_bytes>}}}

NOT base64 strings, and NOT "image/jpeg" MIME types — just raw bytes and
a short format string ("jpeg", "png", "gif", "webp").

Example usage:
    from utils.image_utils import list_images, image_content_block

    for image_path in list_images():
        block = image_content_block(image_path)
        result = grading_agent([
            block,
            {"type": "text", "text": f"Evaluate this image: {image_path.name}"},
        ])
"""
import io
import os
from pathlib import Path

from PIL import Image


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
    """Read an image, resize so the long edge ≤ max_px, and return JPEG bytes.

    Phone photos (3–6 MB) exceed Ollama's request size. Resizing to 1024 px
    keeps the image readable for a vision model at a fraction of the size.
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # normalise — handles RGBA, palette, etc.
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def image_format(image_path: str | Path) -> str:
    """Return the Strands-compatible format string for an image.

    Uses PIL to detect the actual format (handles mis-named files).
    Returns one of: "jpeg", "png", "gif", "webp".
    Defaults to "jpeg" if format is unrecognised.
    """
    with Image.open(image_path) as img:
        fmt = (img.format or "").lower()
    # PIL returns "jpeg" for both .jpg and .jpeg — already correct
    if fmt not in ("jpeg", "png", "gif", "webp"):
        fmt = "jpeg"
    return fmt


def image_content_block(image_path: str | Path) -> dict:
    """Return a Strands Converse API image content block for this image.

    The returned dict can be placed directly in an agent prompt list:

        result = agent([
            image_content_block(path),
            {"type": "text", "text": "Evaluate this image: photo.jpg"},
        ])
    """
    return {
        "image": {
            "format": image_format(image_path),
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
