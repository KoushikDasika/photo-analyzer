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
from dotenv import load_dotenv

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


def main() -> None:
    log.info("face-analyzer starting")

    # TODO (Round 1): replace the lines below with your grading pipeline.
    #
    # Suggested structure:
    #
    #   from utils.image_utils import list_images
    #   from agents.grading_agent import grading_agent
    #   from data_store.opensearch_client import ensure_index
    #
    #   ensure_index()
    #   images = list_images()
    #   log.info(f"Found {len(images)} images to evaluate")
    #
    #   for image_path in images:
    #       result = grading_agent(f"Evaluate this image: {image_path}")
    #       log.info(f"Evaluated {image_path.name}: {result}")

    print()
    print("face-analyzer")
    print("─" * 40)
    print("Nothing runs yet — this is your scaffold.")
    print()
    print("Next steps:")
    print("  1.  configs/rubric.py          → define your scoring criteria")
    print("  2.  agents/grading_agent.py    → implement the grading loop")
    print("  3.  data_store/opensearch_client.py → wire up index_evaluation()")
    print("  4.  Come back here and connect it all in main()")
    print()
    print("Infrastructure:")
    print("  docker compose up opensearch opensearch-dashboards logstash -d")
    print("  OpenSearch Dashboards → http://localhost:5601")


if __name__ == "__main__":
    main()
