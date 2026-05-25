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
    "image_id":        "photo_001.jpg",
    "image_path":      "./input_images/photo_001.jpg",
    "rubric_version":  "v1.0",
    "photo_type":      "hero_portrait",       ← classified slot
    "recommended_slot":"hero_portrait",       ← agent's top recommendation
    "scores": {
      "profile_slot_fit":       0.9,
      "facial_attractiveness":  0.8,
      "grooming":               0.85,
      "style_outfit":           0.75,
      "posture_confidence":     0.8,
      "smile_expression":       0.9,
      "approachability":        0.85,
      "energy_vibe":            0.8,
      "lighting":               0.9,
      "composition":            0.75,
      "photo_sharpness":        0.95,
      "background_context":     0.7,
      "authenticity":           0.9,
      "conversation_starter":   0.7,
      "red_flag_score":         1.0
    },
    "total_score":     0.82,
    "agent_id":        "grading_agent",
    "evaluated_at":    "2026-05-25T10:00:00+00:00",
    "raw_response":    "..."
  }

photo_type and recommended_slot are extracted from the agent's notes JSON
and stored as top-level keyword fields for easy Dashboards filtering.

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
            "image_id":        {"type": "keyword"},
            "image_path":      {"type": "keyword"},
            "rubric_version":  {"type": "keyword"},
            "photo_type":      {"type": "keyword"},
            "recommended_slot":{"type": "keyword"},
            "scores": {
                "type": "object",
                "properties": {
                    # Cluster A — Classification
                    "profile_slot_fit":      {"type": "float"},
                    # Cluster B — How Handsome He Looks
                    "facial_attractiveness": {"type": "float"},
                    "grooming":              {"type": "float"},
                    "style_outfit":          {"type": "float"},
                    "posture_confidence":    {"type": "float"},
                    # Cluster C — Expression & Magnetic Quality
                    "smile_expression":      {"type": "float"},
                    "approachability":       {"type": "float"},
                    "energy_vibe":           {"type": "float"},
                    # Cluster D — Technical Quality
                    "lighting":              {"type": "float"},
                    "composition":           {"type": "float"},
                    "photo_sharpness":       {"type": "float"},
                    "background_context":    {"type": "float"},
                    # Cluster E — Dating Profile Intelligence
                    "authenticity":          {"type": "float"},
                    "conversation_starter":  {"type": "float"},
                    "red_flag_score":        {"type": "float"},
                },
            },
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
    rubric_version: str = "v1.0",
    agent_id: str = "grading_agent",
    raw_response: str = "",
    photo_type: str = "",
    recommended_slot: str = "",
    client: OpenSearch | None = None,
) -> str:
    """Write one evaluation document to OpenSearch.

    Returns the OpenSearch-assigned document ID (_id).
    """
    client = client or get_client()
    total_score = sum(scores.values()) / len(scores) if scores else 0.0

    doc = {
        "image_id":        image_id,
        "image_path":      image_path,
        "rubric_version":  rubric_version,
        "photo_type":      photo_type,
        "recommended_slot":recommended_slot,
        "scores":          scores,
        "total_score":     total_score,
        "agent_id":        agent_id,
        "evaluated_at":    datetime.now(timezone.utc).isoformat(),
        "raw_response":    raw_response,
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
