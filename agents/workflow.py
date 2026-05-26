"""
Evaluation Workflow

Implements the Strands sequential multi-agent pattern:
  each agent's output becomes the input for the next step.

  Step 1 — grading_agent (LLM):  read image → score rubric → save_evaluation_tool
  Step 2 — Python:               mark image completed in the queue

The queue lifecycle (in_progress / completed / failed) wraps the LLM work so
failures are always recorded regardless of what happens inside the agent.

Usage:
    from agents.workflow import run_evaluation_workflow
    run_evaluation_workflow({"image_id": "photo_001.jpg", "image_path": "./input_images/photo_001.jpg"})
"""

import json
import logging
import os

from agents.grading_agent import make_grading_agent
from data_store.opensearch_client import (
    get_client,
    index_evaluation,
    mark_image_in_progress,
    mark_image_completed,
    mark_image_failed,
)
from utils.image_utils import image_content_block

log = logging.getLogger(__name__)


def _parse_evaluation(raw: str) -> dict:
    """Extract JSON from the agent's text response, stripping markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"Could not parse JSON from response: {text[:300]}")


def run_evaluation_workflow(image: dict) -> str:
    """Full lifecycle for one image: in_progress → grade → completed/failed.

    Args:
        image: dict with 'image_id' and 'image_path' (from get_pending_images())

    Returns:
        OpenSearch document ID on success.

    Raises:
        Re-raises any exception after marking the image as failed in the queue.
    """
    image_id = image["image_id"]
    image_path = image["image_path"]

    log.info(f"[{image_id}] starting evaluation")
    client = get_client()
    mark_image_in_progress(image_id, client=client)
    try:
        log.info(f"[{image_id}] loading image and calling grading agent")
        agent = make_grading_agent()
        result = agent(
            [
                image_content_block(image_path),
                {"type": "text", "text": f"Evaluate this image: {image_id}"},
            ]
        )
        raw = str(result)
        parsed = _parse_evaluation(raw)

        doc_id = index_evaluation(
            image_id=image_id,
            image_path=image_path,
            scores=parsed.get("scores", {}),
            photo_type=parsed.get("photo_type", ""),
            recommended_slot=parsed.get("recommended_slot", ""),
            slot_confidence=float(parsed.get("slot_confidence", 0.0)),
            brief_reason=parsed.get("brief_reason", ""),
            model_id=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
            raw_response=raw,
            client=client,
        )
        mark_image_completed(image_id, eval_doc_id=doc_id, client=client)
        log.info(f"[{image_id}] completed ✓  doc={doc_id}")
        return doc_id
    except Exception as e:
        mark_image_failed(image_id, str(e), client=client)
        log.error(f"[{image_id}] failed: {e}")
        raise
