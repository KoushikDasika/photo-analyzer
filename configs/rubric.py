"""
Rubric Definition — Dating Profile Photo Evaluator

This rubric drives two things:
  1. The agent's system prompt  (what to look for, how to score)
  2. The OpenSearch document schema  (which keys appear in `scores`)

Photo types a complete dating profile needs:
  hero_portrait    — close-up solo face shot; must be most flattering
  full_body        — head-to-toe solo; honest physique + style
  social_group     — with 2–4 friends; social proof
  activity_sport   — doing something active; health + energy
  hobby_passion    — engaged in a skill/interest; personality depth
  travel_lifestyle — interesting location or event; ambition + curiosity
  candid_natural   — unposed moment; feels real and authentic
"""
from dataclasses import dataclass


@dataclass
class Criterion:
    name: str         # machine key  — must match key in agent's scores dict
    label: str        # human label  — shown in dashboards / reports
    weight: float     # relative importance (does not need to sum to 1)
    description: str  # what the model should look for and how to score it


RUBRIC: list[Criterion] = [
    # ── Cluster A: Classification ─────────────────────────────────────────
    Criterion(
        name="profile_slot_fit",
        label="Profile Slot Fit",
        weight=2.0,
        description=(
            "Does this photo clearly fill one of the seven needed dating-profile slots "
            "(hero_portrait, full_body, social_group, activity_sport, hobby_passion, "
            "travel_lifestyle, candid_natural)? "
            "1.0 = strongly and unambiguously fills one slot. "
            "0.5 = loosely fits a slot but has issues (e.g. group photo where subject is hard to spot). "
            "0.0 = screenshot, meme, landscape with no person, or completely unusable."
        ),
    ),

    # ── Cluster B: How Handsome He Looks ─────────────────────────────────
    Criterion(
        name="facial_attractiveness",
        label="Facial Attractiveness",
        weight=2.5,
        description=(
            "How handsome does the subject appear in this specific photo? "
            "Angle, lighting, and expression all affect this score — same person can score 0.3 or 0.9 "
            "depending on photo quality. "
            "1.0 = extremely handsome: strong jawline, symmetrical features, flattering angle, warm glow. "
            "0.7 = attractive with minor flaws in angle or light. "
            "0.5 = neutral — neither adds nor detracts. "
            "0.3 = unflattering angle or harsh shadow makes him look worse than he likely is. "
            "0.0 = clearly unflattering (double-chin angle, pained or weird expression, deep harsh shadows). "
            "If face is not visible enough to assess, score 0.2."
        ),
    ),
    Criterion(
        name="grooming",
        label="Grooming Quality",
        weight=2.0,
        description=(
            "Evaluate hair (clean, styled or intentionally casual), facial hair (clean lines or tastefully full, "
            "not patchy or scraggly), and visible skin/hygiene. "
            "1.0 = impeccably groomed — every detail looks deliberate. "
            "0.7 = well-groomed with minor imperfections. "
            "0.5 = average, nothing distracting. "
            "0.3 = visibly unkempt — flyaways, uneven stubble, disheveled in a neglect way, not intentional. "
            "0.0 = clearly unwashed, unkempt, or neglected appearance."
        ),
    ),
    Criterion(
        name="style_outfit",
        label="Style & Outfit",
        weight=1.5,
        description=(
            "Clothing fit, style coherence, and appropriateness for the photo context. "
            "1.0 = great fit, stylish, clothes enhance attractiveness, outfit matches the setting. "
            "0.7 = decent, nothing wrong, slightly generic. "
            "0.5 = fine but forgettable. "
            "0.3 = poor fit, mismatched, or wrong for context (e.g. gym clothes at a nice restaurant). "
            "0.0 = clothes are actively unattractive, dirty, or a red flag (offensive graphic tee, etc.)."
        ),
    ),
    Criterion(
        name="posture_confidence",
        label="Posture & Confidence",
        weight=1.5,
        description=(
            "Body language: upright, open, relaxed, grounded. "
            "1.0 = tall, shoulders back, natural open stance, quiet confidence. "
            "0.7 = good posture with minor awkwardness. "
            "0.5 = neutral — no strong signal either way. "
            "0.3 = slouched, arms crossed, or visibly tense. "
            "0.0 = extremely closed-off, hunched, or body language reads as insecure or aggressive."
        ),
    ),

    # ── Cluster C: Expression & Magnetic Quality ──────────────────────────
    Criterion(
        name="smile_expression",
        label="Smile & Expression",
        weight=2.5,
        description=(
            "Quality and authenticity of facial expression. "
            "1.0 = genuine Duchenne smile (eyes crinkle), warm, inviting, lights up the face. "
            "0.8 = nice smile, mostly genuine. "
            "0.6 = soft smile or relaxed neutral that still reads as warm. "
            "0.4 = forced or stiff smile that looks fake. "
            "0.2 = no smile, blank or serious expression that feels cold. "
            "0.0 = scowling, sneering, or hostile. "
            "Note: a cool candid with a relaxed non-smile can still score 0.7 if overall energy is appealing."
        ),
    ),
    Criterion(
        name="approachability",
        label="Approachability",
        weight=2.0,
        description=(
            "Would a woman feel comfortable and safe swiping right based solely on this photo's vibe? "
            "1.0 = immediately safe, warm, 'I want to meet him'. "
            "0.7 = friendly, no warning signs. "
            "0.5 = neutral — nothing draws you in or pushes away. "
            "0.3 = something feels slightly off (intense cold stare, overly posed, subtle discomfort). "
            "0.0 = actively intimidating, aggressive, or off-putting — a woman would feel uncomfortable."
        ),
    ),
    Criterion(
        name="energy_vibe",
        label="Energy & Vibe",
        weight=1.5,
        description=(
            "The overall emotional energy the photo radiates. "
            "1.0 = magnetic, fun, exciting, interesting — makes you want to know this person. "
            "0.7 = positive and engaging. "
            "0.5 = flat, generic, forgettable but harmless. "
            "0.3 = boring, zero personality showing, or energy feels off. "
            "0.0 = negative, depressing, cringe-inducing, or off-putting energy."
        ),
    ),

    # ── Cluster D: Photo Technical Quality ───────────────────────────────
    Criterion(
        name="lighting",
        label="Lighting Quality",
        weight=1.5,
        description=(
            "How well does the lighting flatter the subject? "
            "1.0 = golden hour, soft box, or well-diffused natural light that sculpts the face beautifully. "
            "0.7 = decent natural light, minor harsh spots. "
            "0.5 = average indoor or overcast light. "
            "0.3 = harsh overhead, strong backlight silhouetting the face, or flat camera flash. "
            "0.0 = so dark or blown-out the subject is barely readable."
        ),
    ),
    Criterion(
        name="composition",
        label="Composition",
        weight=1.0,
        description=(
            "Framing, rule of thirds, subject prominence. "
            "1.0 = expertly framed, subject prominent, background clean or intentionally interesting, photo feels considered. "
            "0.7 = well-framed, minor distractions. "
            "0.5 = adequate framing. "
            "0.3 = subject cut off, too small in frame, or obvious unwanted tilt. "
            "0.0 = unusably cropped or composed (face half cut off, extreme Dutch angle)."
        ),
    ),
    Criterion(
        name="photo_sharpness",
        label="Photo Sharpness",
        weight=1.0,
        description=(
            "Focus and overall image clarity. "
            "1.0 = tack-sharp, crisp details on face and clothing. "
            "0.7 = mostly sharp with minor motion blur. "
            "0.5 = acceptable sharpness. "
            "0.3 = noticeably soft or blurry. "
            "0.0 = so blurry or pixelated it cannot be clearly evaluated."
        ),
    ),
    Criterion(
        name="background_context",
        label="Background Quality",
        weight=1.0,
        description=(
            "Is the background appropriate, non-distracting, and ideally adding positive context? "
            "1.0 = clean or clearly adds context (great travel spot, nice venue, natural environment). "
            "0.7 = fine background, nothing wrong. "
            "0.5 = neutral, blank wall or undefined space. "
            "0.3 = messy, cluttered, or distracting background. "
            "0.0 = embarrassing background (toilet, dirty room, inappropriate signage)."
        ),
    ),

    # ── Cluster E: Dating Profile Intelligence ────────────────────────────
    Criterion(
        name="authenticity",
        label="Authenticity",
        weight=2.0,
        description=(
            "Does the photo feel like a real moment or a staged production? "
            "1.0 = clearly a genuine unscripted moment — candidness is palpable. "
            "0.7 = real setting, slightly posed but still feels genuine. "
            "0.5 = clearly posed but tastefully so. "
            "0.3 = try-hard staging (fake candid, prop you don't own, rented/borrowed status symbol). "
            "0.0 = obviously performative or dishonest (extreme filter, staged wealth, clearly not him)."
        ),
    ),
    Criterion(
        name="conversation_starter",
        label="Conversation Starter",
        weight=1.5,
        description=(
            "Does this photo give a woman an easy, natural reason to send the first message? "
            "1.0 = unique activity, visible interest, funny detail, recognizable location, or emotional moment "
            "that invites 'wait, is that X?' or 'I love that too!'. "
            "0.7 = something mildly interesting to comment on. "
            "0.5 = generic, nothing to grab onto. "
            "0.3 = so plain a woman has nothing to say. "
            "0.0 = the photo actively discourages engagement (rude, creepy, or confusing)."
        ),
    ),
    Criterion(
        name="red_flag_score",
        label="No Red Flags",
        weight=3.0,
        description=(
            "Absence of known dating-app red flags. Start at 1.0 and subtract for each flag present. "
            "Deductions: bathroom mirror selfie −0.5 | sunglasses hiding eyes in a solo shot −0.3 | "
            "dead fish held up −0.5 | shirtless gym selfie or gratuitous shirtlessness −0.4 | "
            "ex or ambiguous woman present −0.6 | you are not the most identifiable person in a group photo −0.4 | "
            "screenshot or very low-res image −0.3 | casually holding a weapon −0.8 | "
            "heavy filter or obvious face-tune artificiality −0.3 | car selfie with no context −0.2. "
            "Floor is 0.0. Score 1.0 if none of the above are present."
        ),
    ),
]

RUBRIC_VERSION = "v1.0"


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
