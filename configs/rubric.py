"""
Rubric Definition  —  Round 1 starting point

Define your scoring criteria here.  The rubric drives two things:
  1. The agent's system prompt  (what to look for, how to score)
  2. The OpenSearch document schema  (which keys appear in `scores`)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK (Round 1, step 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Replace the placeholder Criterion entries below with your real criteria.
2. Call rubric_text() and paste the output into grading_agent.py's system_prompt.
3. Make sure the `name` field of each Criterion matches the key you want in
   the `scores` dict that save_evaluation() will receive.
"""
from dataclasses import dataclass


@dataclass
class Criterion:
    name: str         # machine key  — must match key in agent's scores dict
    label: str        # human label  — shown in dashboards / reports
    weight: float     # relative importance (does not need to sum to 1)
    description: str  # what the model should look for and how to score it


# ── Define your rubric here ───────────────────────────────────────────────
# TODO: replace these placeholders with your actual evaluation dimensions.

RUBRIC: list[Criterion] = [
    Criterion(
        name="criterion_1",
        label="Criterion 1",
        weight=1.0,
        description="TODO: describe what to look for and what 0.0 vs 1.0 means.",
    ),
    Criterion(
        name="criterion_2",
        label="Criterion 2",
        weight=1.0,
        description="TODO: describe what to look for and what 0.0 vs 1.0 means.",
    ),
]

RUBRIC_VERSION = "v0.1"   # bump this string whenever you change criteria


# ── Helpers ───────────────────────────────────────────────────────────────

def rubric_text() -> str:
    """Return a formatted text block suitable for pasting into a system prompt."""
    lines = [f"Rubric version: {RUBRIC_VERSION}", ""]
    for c in RUBRIC:
        lines.append(f"- {c.label}  (scores key: '{c.name}',  weight: {c.weight})")
        lines.append(f"  {c.description}")
        lines.append("")
    return "\n".join(lines)


def criterion_names() -> list[str]:
    """Return just the machine-readable criterion keys."""
    return [c.name for c in RUBRIC]


# ── Quick preview ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(rubric_text())
