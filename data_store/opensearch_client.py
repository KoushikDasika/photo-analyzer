"""
OpenSearch Client

Connects to OpenSearch and provides helpers for storing and reading
evaluation documents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK (Round 1, step 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Call ensure_index() once at startup in main.py so the index and
   mapping exist before the agents start writing.
2. Inside save_evaluation() in agents/grading_agent.py, replace the
   print stub with a call to index_evaluation().

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {
    "image_id":       "photo_001.jpg",
    "image_path":     "./input_images/photo_001.jpg",
    "rubric_version": "v0.1",
    "scores": {
      "criterion_1": 0.85,
      "criterion_2": 0.70
    },
    "total_score":    0.775,
    "agent_id":       "grading_agent",
    "evaluated_at":   "2026-05-25T10:00:00+00:00",
    "raw_response":   "..."
  }

The criteria inside `scores` are dynamic — they come from whatever keys
the agent puts in the dict, which should match your rubric.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBSERVING RESULTS (Round 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Open http://localhost:5601 → OpenSearch Dashboards
  1. Stack Management → Index Patterns → Create index pattern
  2. Pattern: image_evaluations  →  Time field: evaluated_at
  3. Discover tab → browse raw documents
  4. Visualize → build charts (bar chart of total_score, etc.)
"""
import os
from datetime import datetime, timezone
from opensearchpy import OpenSearch


OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME     = os.getenv("OPENSEARCH_INDEX", "image_evaluations")

# Tells OpenSearch the type of each field so it indexes them correctly.
# Add new criteria fields under "scores" → "properties" if you want
# per-criterion numeric aggregations in Dashboards.
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "image_id":       {"type": "keyword"},
            "image_path":     {"type": "keyword"},
            "rubric_version": {"type": "keyword"},
            "scores":         {"type": "object",  "dynamic": True},
            "total_score":    {"type": "float"},
            "agent_id":       {"type": "keyword"},
            "evaluated_at":   {"type": "date"},
            "raw_response":   {"type": "text"},
        }
    }
}


def get_client() -> OpenSearch:
    """Return a connected OpenSearch client."""
    return OpenSearch(OPENSEARCH_URL)


def ensure_index(client: OpenSearch | None = None) -> None:
    """Create the evaluation index + mapping if it doesn't already exist."""
    client = client or get_client()
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        print(f"[opensearch] Created index '{INDEX_NAME}'")
    else:
        print(f"[opensearch] Index '{INDEX_NAME}' already exists")


def index_evaluation(
    image_id: str,
    image_path: str,
    scores: dict,
    rubric_version: str = "v0.1",
    agent_id: str = "grading_agent",
    raw_response: str = "",
    client: OpenSearch | None = None,
) -> str:
    """Write one evaluation document to OpenSearch.

    Returns the OpenSearch-assigned document ID (_id).
    """
    client = client or get_client()
    total_score = sum(scores.values()) / len(scores) if scores else 0.0

    doc = {
        "image_id":       image_id,
        "image_path":     image_path,
        "rubric_version": rubric_version,
        "scores":         scores,
        "total_score":    total_score,
        "agent_id":       agent_id,
        "evaluated_at":   datetime.now(timezone.utc).isoformat(),
        "raw_response":   raw_response,
    }
    response = client.index(index=INDEX_NAME, body=doc)
    return response["_id"]


# ── Quick connectivity test ───────────────────────────────────────────────
if __name__ == "__main__":
    # python data_store/opensearch_client.py
    client = get_client()
    health = client.cluster.health()
    print(f"[opensearch] cluster status: {health['status']}")
    ensure_index(client)
