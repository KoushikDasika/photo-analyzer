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

from agents.grading_agent import make_grading_agent
from data_store.opensearch_client import (
    mark_image_in_progress,
    mark_image_completed,
    mark_image_failed,
)
from utils.image_utils import image_content_block


def run_evaluation_workflow(image: dict) -> str:
    """Full lifecycle for one image: in_progress → grade → completed/failed.

    Args:
        image: dict with 'image_id' and 'image_path' (from get_pending_images())

    Returns:
        Agent result text on success.

    Raises:
        Re-raises any exception after marking the image as failed in the queue.
    """
    image_id   = image["image_id"]
    image_path = image["image_path"]

    mark_image_in_progress(image_id)
    try:
        agent = make_grading_agent()
        result = agent([
            image_content_block(image_path),
            {"type": "text", "text": f"Evaluate this image: {image_id}"},
        ])
        mark_image_completed(image_id)
        return str(result)
    except Exception as e:
        mark_image_failed(image_id, str(e))
        raise
