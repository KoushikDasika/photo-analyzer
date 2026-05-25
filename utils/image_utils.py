"""
Image Utilities

Helpers for listing and loading images for the agents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK (Round 1, step 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Call list_images() to get all image Paths, then load_image_base64() to
encode each one before passing it to the grading agent.

Example usage:
    from utils.image_utils import list_images, load_image_base64, image_media_type

    for image_path in list_images():
        b64  = load_image_base64(image_path)
        mime = image_media_type(image_path)
        # pass b64 + mime to your agent prompt
"""
import base64
import os
from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


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


def load_image_base64(image_path: str | Path) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def image_media_type(image_path: str | Path) -> str:
    """Return the MIME type string for the given image path."""
    suffix = Path(image_path).suffix.lower()
    return {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
        ".bmp":  "image/bmp",
    }.get(suffix, "image/jpeg")


# ── Quick preview ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # python utils/image_utils.py
    images = list_images()
    print(f"Found {len(images)} images")
    for p in images[:5]:
        print(f"  {p.name}  ({image_media_type(p)})")
    if len(images) > 5:
        print(f"  ... and {len(images) - 5} more")
