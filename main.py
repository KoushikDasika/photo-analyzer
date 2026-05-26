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
    get_unresized_images,
    mark_image_resized,
    reset_stuck_images,
    get_client,
)
from utils.image_utils import list_images, load_image_bytes, MAX_IMAGE_PX
from agents.workflow import run_evaluation_workflow
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


def resize_all_images():
    client = get_client()
    images = get_unresized_images(limit=5000, target_px=MAX_IMAGE_PX, client=client)
    if not images:
        log.info("resize pass: all images already resized")
        return
    total = len(images)
    done = 0
    log.info(f"resize pass: {total} images to resize, max_workers=16")
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(load_image_bytes, img["image_path"]): img for img in images}
        for future in as_completed(futures):
            img = futures[future]
            done += 1
            try:
                future.result()
                mark_image_resized(img["image_id"], resized_px=MAX_IMAGE_PX, client=client)
                log.info(f"[resize {done}/{total}] {img['image_id']}")
            except Exception as e:
                log.error(f"[resize {done}/{total}] failed: {img['image_id']}  error={e}")
    log.info("resize pass complete")


def execute_agent_grading_pool(images):
    total = len(images)
    done = 0
    log.info(f"pool starting — {total} images, max_workers=12")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(run_evaluation_workflow, img): img for img in images}
        for future in as_completed(futures):
            img = futures[future]
            done += 1
            try:
                future.result()
                stats = queue_stats()
                log.info(f"[{done}/{total}] done: {img['image_id']}  queue={stats}")
            except Exception as e:
                log.error(f"[{done}/{total}] failed: {img['image_id']}  error={e}")
    log.info("pool finished")


def execute_image_grading():
    stats = queue_stats()
    log.info(f"queue stats before run: {stats}")
    pending_images = get_pending_images()
    log.info(f"fetched {len(pending_images)} images to process")
    if not pending_images:
        log.info("nothing to process — exiting")
        return
    execute_agent_grading_pool(pending_images)
    log.info(f"queue stats after run:  {queue_stats()}")


def setup_indices():
    log.info("setting up indices and populating queue")
    images = list_images("./input_images/")
    log.info(f"found {len(images)} images in input_images/")
    ensure_indices()
    added = populate_queue(images)
    log.info(f"added {added} new images to queue")
    stuck = reset_stuck_images()
    if stuck:
        log.warning(
            f"reset {stuck} stuck in_progress images → failed (will be retried)"
        )


def main() -> None:
    log.info("─" * 40)
    log.info("IMAGE ANALYZER START")
    log.info("─" * 40)
    setup_indices()
    resize_all_images()
    execute_image_grading()


if __name__ == "__main__":
    main()
