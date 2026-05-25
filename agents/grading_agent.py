"""
Grading Agent

Build the agent (or group of agents) that:
  1. Takes an image from input_images/
  2. Evaluates it against your rubric  (configs/rubric.py)
  3. Saves the result to OpenSearch    (data_store/opensearch_client.py)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW STRANDS WORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

An Agent is created with three things:
  model        — which LLM to call (OllamaModel here)
  tools        — Python functions the LLM can invoke during its reasoning
  system_prompt — instructions that shape the agent's role and behaviour

When you call  agent("some prompt")  the agent:
  1. Sends the prompt + system_prompt to the model
  2. If the model wants to call a tool, Strands calls your Python function
  3. The tool's return value is fed back to the model
  4. The model can call more tools, or produce a final text answer
  5. You get back an AgentResult — access the text with str(result)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARALLEL AGENTS PATTERN (your Round 1 task)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For 1 800 images you want parallel agents, not sequential.
Use concurrent.futures.ThreadPoolExecutor:

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def evaluate_one(image_path):
        b64  = load_image_base64(image_path)
        mime = image_media_type(image_path)
        # TODO: build the prompt (text + image content)
        result = grading_agent("Evaluate this image ...")
        return image_path, result

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(evaluate_one, p): p for p in images}
        for future in as_completed(futures):
            path, result = future.result()
            print(f"Done: {path.name}")

Tune max_workers so GPU VRAM isn't exhausted (start with 2–4).
"""
import os
from strands import Agent, tool
from strands.models.ollama import OllamaModel
from configs.rubric import rubric_text, RUBRIC_VERSION

# ── Model ────────────────────────────────────────────────────────────────
# OllamaModel talks to your local ollama over HTTP.
# Swap the model by changing OLLAMA_MODEL in .env — no code change needed.
model = OllamaModel(
    host=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model_id=os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
)


# ── Tools ─────────────────────────────────────────────────────────────────
# A tool is a plain Python function decorated with @tool.
# The function's type hints and docstring become the tool's JSON schema —
# the model reads the docstring to decide when and how to call it.

@tool
def save_evaluation(image_id: str, scores: dict, notes: str = "") -> str:
    """Save the evaluation scores for one image to the data store.

    Call this tool once per image after you have assessed all rubric criteria.

    Args:
        image_id: Filename of the image being evaluated (e.g. "photo_001.jpg")
        scores:   Mapping of criterion name → float score in [0.0, 1.0]
                  Keys must match the criterion names in the rubric.
        notes:    Optional free-text observations from the evaluation.

    Returns:
        Confirmation string.
    """
    # TODO (Round 1): replace this stub with a real call to index_evaluation().
    #
    #   from data_store.opensearch_client import index_evaluation
    #   doc_id = index_evaluation(
    #       image_id=image_id,
    #       image_path=f"./input_images/{image_id}",
    #       scores=scores,
    #       raw_response=notes,
    #   )
    #   return f"Saved {image_id} → doc {doc_id}"

    print(f"[save_evaluation] {image_id}  scores={scores}")
    return f"Evaluation recorded for {image_id}"


# ── Agent ─────────────────────────────────────────────────────────────────
grading_agent = Agent(
    model=model,
    tools=[save_evaluation],
    system_prompt=(
        # TODO (Round 1): replace this placeholder with your rubric instructions.
        #
        # Good system prompts for grading agents typically:
        #   - State the agent's role clearly
        #   - List every rubric criterion (copy from configs/rubric.py)
        #   - Explain the scoring scale (e.g. 0.0 = fails, 1.0 = perfect)
        #   - Tell the agent to call save_evaluation() when done
        #
        # Example structure:
        #   "You are a photo-grading agent. Evaluate the provided image on the
        #    following criteria and score each 0.0–1.0:
        #    - composition (key: 'composition'): ...
        #    - lighting    (key: 'lighting'):    ...
        #    When you have finished evaluating all criteria, call save_evaluation()."
        "You are a grading agent. "
        "TODO: replace this system prompt with your rubric instructions."
    ),
)


# ── Smoke test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Run this file directly to verify the agent can reach ollama:
    #   python agents/grading_agent.py
    result = grading_agent("Hello! Describe your role in one sentence.")
    print(result)
