import re
import os

filepath = r"c:\Users\박주호\Desktop\Vibe coding\shorts-maker-v2\src\shorts_maker_v2\pipeline\script_step.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# TONE_PRESETS (Indent 4 spaces)
content = re.sub(
    r'TONE_PRESETS: list\[tuple\[str, str\]\] = \[.*?\]',
    '''    TONE_PRESETS: list[tuple[str, str]] = [
        ("professor", "Calm, analytical, and evidence-first. Sound like a clear university lecture."),
        ("friend", "Casual, conversational, and easy to follow. Sound like a smart friend explaining something exciting."),
        ("storyteller", "Narrative and cinematic. Build momentum like you're telling a gripping short story."),
        ("news_anchor", "Crisp, factual, and composed. Keep the delivery clean and broadcast-like."),
        ("excited_fan", "Energetic and delighted, but still specific. Let the excitement come from real details."),
    ]''',
    content, flags=re.DOTALL
)

# _CHANNEL_PERSONA (Indent 4 spaces)
content = re.sub(
    r'_CHANNEL_PERSONA: dict\[str, dict\[str, str\]\] = \{.*?    \}',
    '''    _CHANNEL_PERSONA: dict[str, dict[str, str]] = {
        "ai_tech": {
            "role_description": "You are a tech journalist delivering breaking AI and product news in sharp spoken English.",
            "tone": "Tone: Fast, precise, and data-rich. Keep every line specific and current.",
            "forbidden": "Forbidden: empty hype, vague superlatives, and filler phrases that say nothing concrete.",
            "required": "Required: mention at least one exact company, model, date, metric, or release detail."
        },
        "history": {
            "role_description": "You are a dramatic history storyteller turning true events into vivid spoken English.",
            "tone": "Tone: Cinematic and suspenseful. Make the audience feel the tension of the moment.",
            "forbidden": "Forbidden: dry timelines, textbook phrasing, and flat summaries without drama.",
            "required": "Required: frame the hook around a reversal, contradiction, or shocking historical twist."
        },
        "psychology": {
            "role_description": "You are a warm therapist-friend sharing psychology insights in emotionally safe spoken English.",
            "tone": "Tone: empathetic, validating, and human. Lead with understanding before explanation.",
            "forbidden": "Forbidden: judgmental framing, cold clinical jargon, and pushy advice.",
            "required": "Required: the viewer should feel understood in the hook, then gently guided in the body."
        },
        "space": {
            "role_description": "You are a cosmic explainer translating the scale of space into awe-filled spoken English.",
            "tone": "Tone: expansive, vivid, and wonder-driven. Use analogies to make scale feel real.",
            "forbidden": "Forbidden: sterile jargon dumps, mundane framing, and endings without wonder.",
            "required": "Required: include at least one memorable scale comparison or perspective shift."
        },
        "health": {
            "role_description": "You are a careful health guide sharing evidence-based advice in calm spoken English.",
            "tone": "Tone: supportive, trustworthy, and practical. Empower instead of alarming.",
            "forbidden": "Forbidden: fear tactics, miracle claims, and unsupported medical certainty.",
            "required": "Required: anchor claims to evidence or consensus guidance and end with one safe action."
        },
    }''',
    content, flags=re.DOTALL
)

# _CTA_FORBIDDEN_WORDS (Indent 4 spaces)
content = re.sub(
    r'_CTA_FORBIDDEN_WORDS: tuple\[str, \.\.\.\] = \([^)]+\)',
    '''    _CTA_FORBIDDEN_WORDS: tuple[str, ...] = (
        "subscribe",
        "like",
        "follow",
        "bell",
        "comment below",
        "smash that",
        "don't forget to",
        "hit the",
    )''',
    content, flags=re.DOTALL
)

# _PERSONA_KEYWORDS (Indent 4 spaces)
content = re.sub(
    r'_PERSONA_KEYWORDS: dict\[str, tuple\[str, \.\.\.\]\] = \{.*?    \}',
    '''    _PERSONA_KEYWORDS: dict[str, tuple[str, ...]] = {
        "ai_tech": ("AI", "model", "data", "release", "benchmark", "developer", "algorithm", "software", "product", "company"),
        "psychology": ("emotion", "mind", "anxiety", "relationship", "self", "understand", "feeling", "pattern", "stress", "trust"),
        "history": ("empire", "war", "king", "century", "battle", "revolution", "civilization", "dynasty", "historian", "event"),
        "space": ("space", "planet", "galaxy", "star", "light-year", "orbit", "black hole", "telescope", "cosmic", "universe"),
        "health": ("health", "sleep", "exercise", "nutrition", "study", "habit", "body", "risk", "recovery", "guideline"),
    }''',
    content, flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully with correct indentation.")
