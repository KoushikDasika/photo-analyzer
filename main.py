"""
face-analyzer  —  entry point

Iteration roadmap
─────────────────
Round 1  Define your rubric in configs/rubric.py, then implement
         agents/grading_agent.py to evaluate images and write to OpenSearch.
Round 2  Open http://localhost:5601 (OpenSearch Dashboards) and explore
         the image_evaluations index you built in Round 1.
Round 3  Build a selection agent that reads all evaluations and picks
         the best images based on aggregated scores.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from data_store.opensearch_client import (
    ensure_indices,
    populate_queue,
    queue_stats,
    get_pending_images,
)
from utils.image_utils import list_images
from agents.grading_agent import evaluate_image
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# Logs go to ./logs/app.log (Logstash picks them up and sends to OpenSearch)
os.makedirs(os.getenv("LOG_DIR", "./logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.getenv("LOG_DIR", "./logs"), "app.log")),
    ],
)
log = logging.getLogger(__name__)


def execute_agent_grading_pool(images):
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(evaluate_image, p["image_path"]): p for p in images}
        for future in as_completed(futures):
            path, result = future.result()
            print(queue_stats())
            print(f"Done: {path.name}")


def execute_image_grading():
    print("Executing pool of workers")
    print(queue_stats())
    pending_images = get_pending_images()
    execute_agent_grading_pool(pending_images)
    print("Finished Processing images")
    return


def setup_indices():
    print("SETUP IMAGE QUEUE AND INDICES")
    images = list_images("./input_images/")
    ensure_indices()
    populate_queue(images)
    return


def main() -> None:
    log.info("face-analyzer starting")
    # TODO (Round 1): replace the lines below with your grading pipeline.
    #
    # Suggested structure:
    #
    #   from utils.image_utils import list_images
    #   from agents.grading_agent import grading_agent
    #   from data_store.opensearch_client import ensure_indices
    #
    #   ensure_indices()
    #   log.info(f"Found {len(images)} images to evaluate")
    #
    #   for image_path in images:
    #       result = grading_agent(f"Evaluate this image: {image_path}")
    #       log.info(f"Evaluated {image_path.name}: {result}")

    print()
    print("IMAGE ANALYZER START")
    print("─" * 40)
    setup_indices()

    print("─" * 40)
    execute_image_grading()


if __name__ == "__main__":
    main()
