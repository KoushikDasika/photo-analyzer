"""
OpenSearch Client

Connects to OpenSearch and provides helpers for storing and reading
evaluation documents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK (Round 1, step 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Call ensure_indices() once at startup in main.py so the index and
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
from opensearchpy.helpers import bulk
from configs.rubric import RUBRIC


OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME     = os.getenv("OPENSEARCH_INDEX", "image_evaluations")
QUEUE_INDEX    = os.getenv("OPENSEARCH_QUEUE_INDEX", "image_queue")

# Tells OpenSearch the type of each field so it indexes them correctly.
# Add new criteria fields under "scores" → "properties" if you want
# per-criterion numeric aggregations in Dashboards.
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "image_id":        {"type": "keyword"},
            "image_path":      {"type": "keyword"},
            "rubric_version":  {"type": "keyword"},
            "model_id":        {"type": "keyword"},
            "photo_type":      {"type": "keyword"},
            "recommended_slot":{"type": "keyword"},
            "slot_confidence": {"type": "float"},
            "brief_reason":    {"type": "text"},
            "scores": {
                "type": "object",
                "properties": {
                    # Cluster A — Classification
                    "profile_slot_fit": {"type": "float"},
                    # Cluster B — How Handsome He Looks
                    "facial_attractiveness": {"type": "float"},
                    "grooming": {"type": "float"},
                    "style_outfit": {"type": "float"},
                    "posture_confidence": {"type": "float"},
                    # Cluster C — Expression & Magnetic Quality
                    "smile_expression": {"type": "float"},
                    "approachability": {"type": "float"},
                    "energy_vibe": {"type": "float"},
                    # Cluster D — Technical Quality
                    "lighting": {"type": "float"},
                    "composition": {"type": "float"},
                    "photo_sharpness": {"type": "float"},
                    "background_context": {"type": "float"},
                    # Cluster E — Dating Profile Intelligence
                    "authenticity": {"type": "float"},
                    "conversation_starter": {"type": "float"},
                    "red_flag_score": {"type": "float"},
                },
            },
            "total_score":    {"type": "float"},
            "weighted_score": {"type": "float"},
            "agent_id":       {"type": "keyword"},
            "evaluated_at":   {"type": "date"},
            "raw_response":   {"type": "text"},
        }
    }
}


# ── Image queue mapping ──────────────────────────────────────────────────
# Tracks every discovered image and whether it has been processed.
# The document _id is set to image_id so updates are O(1) and idempotent.
#
# status lifecycle:  pending → in_progress → completed
#                                          ↘ failed
QUEUE_MAPPING = {
    "mappings": {
        "properties": {
            "image_id":     {"type": "keyword"},
            "image_path":   {"type": "keyword"},
            # pending | in_progress | completed | failed
            "status":       {"type": "keyword"},
            "discovered_at":{"type": "date"},
            "started_at":   {"type": "date"},
            "completed_at": {"type": "date"},
            # _id of the matching document in image_evaluations (set on completion)
            "eval_doc_id":  {"type": "keyword"},
            "error":        {"type": "text"},
        }
    }
}


def get_client() -> OpenSearch:
    """Return a connected OpenSearch client."""
    return OpenSearch(OPENSEARCH_URL)


def ensure_indices(client: OpenSearch | None = None) -> None:
    """Create both indices + mappings if they don't already exist."""
    client = client or get_client()
    for name, mapping in [(INDEX_NAME, INDEX_MAPPING), (QUEUE_INDEX, QUEUE_MAPPING)]:
        if not client.indices.exists(index=name):
            client.indices.create(index=name, body=mapping)
            print(f"[opensearch] Created index '{name}'")
        else:
            print(f"[opensearch] Index '{name}' already exists")


_WEIGHT_MAP = {c.name: c.weight for c in RUBRIC}


def index_evaluation(
    image_id: str,
    image_path: str,
    scores: dict,
    photo_type: str = "",
    recommended_slot: str = "",
    slot_confidence: float = 0.0,
    brief_reason: str = "",
    rubric_version: str = "v1.0",
    agent_id: str = "grading_agent",
    model_id: str = "",
    raw_response: str = "",
    client: OpenSearch | None = None,
) -> str:
    """Write one evaluation document to OpenSearch.

    Returns the OpenSearch-assigned document ID (_id).
    """
    client = client or get_client()

    total_score = sum(scores.values()) / len(scores) if scores else 0.0
    total_weight = sum(_WEIGHT_MAP.get(k, 1.0) for k in scores)
    weighted_score = (
        sum(scores[k] * _WEIGHT_MAP.get(k, 1.0) for k in scores) / total_weight
        if scores else 0.0
    )

    doc = {
        "image_id":        image_id,
        "image_path":      image_path,
        "rubric_version":  rubric_version,
        "model_id":        model_id,
        "photo_type":      photo_type,
        "recommended_slot":recommended_slot,
        "slot_confidence": slot_confidence,
        "brief_reason":    brief_reason,
        "scores":          scores,
        "total_score":     total_score,
        "weighted_score":  weighted_score,
        "agent_id":        agent_id,
        "evaluated_at":    datetime.now(timezone.utc).isoformat(),
        "raw_response":    raw_response,
    }
    response = client.index(index=INDEX_NAME, body=doc)
    return response["_id"]


# ── Image queue helpers ───────────────────────────────────────────────────

def populate_queue(image_paths: list, client: OpenSearch | None = None) -> int:
    """Add images to the queue as 'pending'.

    Uses _op_type='create' so already-queued images (any status) are skipped.
    Safe to call on restart — completed/failed images will not be reset.

    Args:
        image_paths: List of Path objects or strings pointing to image files.

    Returns:
        Number of images newly added to the queue.
    """
    client = client or get_client()
    now = datetime.now(timezone.utc).isoformat()

    actions = []
    for p in image_paths:
        image_id   = str(p) if hasattr(p, "name") else p
        image_path = str(p)
        # Use filename as the stable ID if a Path object was passed
        if hasattr(p, "name"):
            image_id = p.name
        actions.append({
            "_op_type":    "create",   # skip if doc already exists
            "_index":      QUEUE_INDEX,
            "_id":         image_id,
            "image_id":    image_id,
            "image_path":  image_path,
            "status":      "pending",
            "discovered_at": now,
            "started_at":  None,
            "completed_at":None,
            "eval_doc_id": None,
            "error":       None,
        })

    if not actions:
        return 0

    # ignore_errors=True so 409-Conflict (already exists) doesn't raise
    success, _ = bulk(client, actions, raise_on_error=False)
    return success


def get_pending_images(limit: int = 100, client: OpenSearch | None = None) -> list[dict]:
    """Return up to `limit` images with status='pending'.

    Each entry is a dict with 'image_id' and 'image_path'.
    Call this at startup to get the next batch to process.
    """
    client = client or get_client()
    response = client.search(
        index=QUEUE_INDEX,
        body={
            "query": {"term": {"status": "pending"}},
            "size":  limit,
            "_source": ["image_id", "image_path"],
        },
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]


def mark_image_in_progress(image_id: str, client: OpenSearch | None = None) -> None:
    """Update a queued image to status='in_progress'."""
    client = client or get_client()
    client.update(
        index=QUEUE_INDEX,
        id=image_id,
        body={"doc": {
            "status":     "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }},
    )


def mark_image_completed(
    image_id: str,
    eval_doc_id: str = "",
    client: OpenSearch | None = None,
) -> None:
    """Update a queued image to status='completed' and link its evaluation doc."""
    client = client or get_client()
    client.update(
        index=QUEUE_INDEX,
        id=image_id,
        body={"doc": {
            "status":       "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "eval_doc_id":  eval_doc_id,
        }},
    )


def mark_image_failed(
    image_id: str,
    error: str = "",
    client: OpenSearch | None = None,
) -> None:
    """Update a queued image to status='failed' with an error message."""
    client = client or get_client()
    client.update(
        index=QUEUE_INDEX,
        id=image_id,
        body={"doc": {
            "status":       "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error":        error,
        }},
    )


def queue_stats(client: OpenSearch | None = None) -> dict:
    """Return counts of images by status.

    Example return value:
        {"pending": 1800, "in_progress": 0, "completed": 42, "failed": 3}
    """
    client = client or get_client()
    response = client.search(
        index=QUEUE_INDEX,
        body={
            "size": 0,
            "aggs": {
                "by_status": {
                    "terms": {"field": "status", "size": 10}
                }
            },
        },
    )
    return {
        bucket["key"]: bucket["doc_count"]
        for bucket in response["aggregations"]["by_status"]["buckets"]
    }


# ── Quick connectivity test ───────────────────────────────────────────────
if __name__ == "__main__":
    # python data_store/opensearch_client.py
    client = get_client()
    health = client.cluster.health()
    print(f"[opensearch] cluster status: {health['status']}")
    ensure_indices(client)
    print(f"[opensearch] queue stats: {queue_stats(client)}")
