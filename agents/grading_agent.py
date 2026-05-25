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
from strands import Agent
from strands.models.ollama import OllamaModel
from configs.rubric import rubric_text


def _make_model() -> OllamaModel:
    """Create a fresh OllamaModel — called inside make_grading_agent() so each
    agent gets its own model instance with no shared session state."""
    return OllamaModel(
        host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model_id=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
        temperature=0.3,
        options={"think": False},
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
4. Respond with ONLY valid JSON — no markdown, no extra text.

── Scoring criteria ─────────────────────────────────────────────────────────
{rubric_text()}
── Output format ────────────────────────────────────────────────────────────
Respond with exactly this JSON structure (no markdown, no extra text):
{{
  "scores": {{
    "profile_slot_fit": 0.0,
    "facial_attractiveness": 0.0,
    "grooming": 0.0,
    "style_outfit": 0.0,
    "posture_confidence": 0.0,
    "smile_expression": 0.0,
    "approachability": 0.0,
    "energy_vibe": 0.0,
    "lighting": 0.0,
    "composition": 0.0,
    "photo_sharpness": 0.0,
    "background_context": 0.0,
    "authenticity": 0.0,
    "conversation_starter": 0.0,
    "red_flag_score": 0.0
  }},
  "photo_type": "hero_portrait",
  "recommended_slot": "hero_portrait",
  "slot_confidence": 0.0,
  "brief_reason": "one sentence"
}}

Important rules:
- red_flag_score starts at 1.0 and is reduced by deductions. Floor is 0.0. Score 1.0 if no red flags.
- Use exactly the 15 keys listed above in scores — no additions or omissions.
- Be honest and specific. The goal is to find the best photos, not to flatter.
"""


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
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )


# ── Smoke test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Verify the agent can reach ollama — no image, no OpenSearch needed.
    #   python agents/grading_agent.py
    agent = make_grading_agent()
    result = agent("Hello! Describe your role in one sentence.")
    print(result)
