"""
Grading Agent

Evaluates a single photo against the dating-profile rubric and writes the
result to OpenSearch. This agent has one responsibility: evaluate and save.
Queue lifecycle (in_progress / completed / failed) is handled by workflow.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW STRANDS WORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

An Agent is created with three things:
  model         — which LLM to call (OllamaModel here)
  tools         — Python functions the LLM can invoke during its reasoning
  system_prompt — instructions that shape the agent's role and behaviour

When you call  agent("some prompt")  the agent:
  1. Sends the prompt + system_prompt to the model
  2. If the model wants to call a tool, Strands calls your Python function
  3. The tool's return value is fed back to the model
  4. The model can call more tools, or produce a final text answer
  5. You get back an AgentResult — access the text with str(result)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARALLEL AGENTS PATTERN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Don't call grading_agent directly in a loop — use workflow.run_evaluation_workflow()
which handles the full queue lifecycle around the agent call.

    from agents.workflow import run_evaluation_workflow
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_evaluation_workflow, img): img for img in images}
        for future in as_completed(futures):
            future.result()

Tune max_workers so GPU VRAM isn't exhausted (start with 2–4).
"""

import os
from strands import Agent, tool
from strands_tools import image_reader
from strands.models.ollama import OllamaModel
from configs.rubric import rubric_text
from data_store.opensearch_client import index_evaluation

def _make_model() -> OllamaModel:
    """Create a fresh OllamaModel — called inside make_grading_agent() so each
    agent gets its own model instance with no shared session state."""
    return OllamaModel(
        host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model_id=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
    )

SYSTEM_PROMPT = f"""
You are an expert matchmaker and dating-profile photo evaluator. You assess photos
from the female perspective of modern dating apps (Hinge, Bumble, Tinder).

Your job:
1. Look at the provided image.
2. Classify it into one of these dating-profile slots:
   hero_portrait | full_body | social_group | activity_sport |
   hobby_passion | travel_lifestyle | candid_natural | other
3. Score it on every criterion below (0.0–1.0, higher = better).
4. Call save_evaluation_tool() ONCE with all scores and classification fields.

── Scoring criteria ─────────────────────────────────────────────────────────
{rubric_text()}
── Output format ────────────────────────────────────────────────────────────
Call save_evaluation_tool() with these arguments:
  image_id         — the filename you were given
  scores           — dict with ALL 15 criterion keys above, each a float 0.0–1.0
  photo_type       — one of: hero_portrait | full_body | social_group |
                     activity_sport | hobby_passion | travel_lifestyle |
                     candid_natural | other
  recommended_slot — same as photo_type, or a different slot if this photo
                     would serve even better there
  slot_confidence  — float 0.0–1.0, how sure you are about the classification
  brief_reason     — one sentence: the single most important thing about this
                     photo for a dating profile

Important rules:
- red_flag_score starts at 1.0 and is reduced by deductions listed in the criterion.
  Floor is 0.0. Score 1.0 if no red flags are present.
- Do NOT add extra keys to scores — use exactly the 15 names listed.
- Be honest and specific. The goal is to find the best photos, not to flatter.
- Evaluate each criterion independently based on what you can observe.
"""


# ── Tools ─────────────────────────────────────────────────────────────────

@tool
def save_evaluation_tool(
    image_id: str,
    scores: dict,
    photo_type: str,
    recommended_slot: str,
    slot_confidence: float,
    brief_reason: str,
) -> str:
    """Save the evaluation scores for one image to the data store.

    Call this tool ONCE per image after assessing all rubric criteria.

    Args:
        image_id:         Filename of the image (e.g. "photo_001.jpg")
        scores:           Mapping of criterion name → float in [0.0, 1.0].
                          Must contain exactly the 15 keys listed in the rubric.
        photo_type:       Which dating-profile slot this photo fills.
                          One of: hero_portrait | full_body | social_group |
                          activity_sport | hobby_passion | travel_lifestyle |
                          candid_natural | other
        recommended_slot: Best slot for this photo (usually same as photo_type,
                          but can differ if a better fit exists).
        slot_confidence:  How confident you are in the classification (0.0–1.0).
        brief_reason:     One sentence — the single most important insight about
                          this photo for a dating profile.

    Returns:
        Confirmation string with the OpenSearch document ID.
    """
    doc_id = index_evaluation(
        image_id=image_id,
        image_path=f"./input_images/{image_id}",
        scores=scores,
        photo_type=photo_type,
        recommended_slot=recommended_slot,
        slot_confidence=slot_confidence,
        brief_reason=brief_reason,
        model_id=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
    )
    status = f"Saved {image_id} → doc {doc_id}"
    print(status)
    return status


# ── Agent factory ─────────────────────────────────────────────────────────
# Strands agents are NOT thread-safe — concurrent calls on the same instance
# raise "Agent is already processing a request."
# Always call make_grading_agent() to get a fresh instance per worker thread.

def make_grading_agent() -> Agent:
    """Return a fully isolated grading agent instance.

    Each call creates a new Agent AND a new OllamaModel so no session state,
    message history, or model context is shared between concurrent workers.
    Call once per worker thread / workflow invocation.
    """
    return Agent(
        model=_make_model(),
        tools=[save_evaluation_tool, image_reader],
        system_prompt=SYSTEM_PROMPT,
    )


# Module-level singleton for single-threaded use (smoke test, REPL, etc.)
grading_agent = make_grading_agent()


# ── Smoke test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Verify the agent can reach ollama — no image, no OpenSearch needed.
    #   python -m agents.grading_agent
    result = grading_agent("Hello! Describe your role in one sentence.")
    print(result)
