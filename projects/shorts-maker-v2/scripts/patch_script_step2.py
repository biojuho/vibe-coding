import re

filepath = r"c:\Users\박주호\Desktop\Vibe coding\shorts-maker-v2\src\shorts_maker_v2\pipeline\script_step.py"

with open(filepath, encoding="utf-8") as f:
    content = f.read()

# 1. TONE_PRESETS (Indent 4 spaces)
content = re.sub(
    r"(?m)^ +TONE_PRESETS: list\[tuple\[str, str\]\] = \[.*?\]",
    """    TONE_PRESETS: list[tuple[str, str]] = [
        ("professor", "Calm, analytical, and evidence-first. Sound like a clear university lecture."),
        ("friend", "Casual, conversational, and easy to follow. Sound like a smart friend explaining something exciting."),
        ("storyteller", "Narrative and cinematic. Build momentum like you're telling a gripping short story."),
        ("news_anchor", "Crisp, factual, and composed. Keep the delivery clean and broadcast-like."),
        ("excited_fan", "Energetic and delighted, but still specific. Let the excitement come from real details."),
    ]""",
    content,
    flags=re.DOTALL,
)

# 2. _CHANNEL_PERSONA
content = re.sub(
    r"(?m)^ +_CHANNEL_PERSONA: dict\[str, dict\[str, str\]\] = \{.*?^    \}",
    """    _CHANNEL_PERSONA: dict[str, dict[str, str]] = {
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
    }""",
    content,
    flags=re.DOTALL,
)

# 3. _CTA_FORBIDDEN_WORDS
content = re.sub(
    r"(?m)^ +_CTA_FORBIDDEN_WORDS: tuple\[str, \.\.\.\] = \([^)]+\)",
    """    _CTA_FORBIDDEN_WORDS: tuple[str, ...] = (
        "subscribe",
        "like",
        "follow",
        "bell",
        "comment below",
        "smash that",
        "don't forget to",
        "hit the",
    )""",
    content,
    flags=re.DOTALL,
)

# 4. _PERSONA_KEYWORDS
content = re.sub(
    r"(?m)^ +_PERSONA_KEYWORDS: dict\[str, tuple\[str, \.\.\.\]\] = \{.*?^    \}",
    """    _PERSONA_KEYWORDS: dict[str, tuple[str, ...]] = {
        "ai_tech": ("AI", "model", "data", "release", "benchmark", "developer", "algorithm", "software", "product", "company"),
        "psychology": ("emotion", "mind", "anxiety", "relationship", "self", "understand", "feeling", "pattern", "stress", "trust"),
        "history": ("empire", "war", "king", "century", "battle", "revolution", "civilization", "dynasty", "historian", "event"),
        "space": ("space", "planet", "galaxy", "star", "light-year", "orbit", "black hole", "telescope", "cosmic", "universe"),
        "health": ("health", "sleep", "exercise", "nutrition", "study", "habit", "body", "risk", "recovery", "guideline"),
    }""",
    content,
    flags=re.DOTALL,
)

# 5. _PROMPT_COPY
content = re.sub(
    r"(?m)^ +_PROMPT_COPY: dict\[str, str\] = \{.*?^    \}",
    r"""    _PROMPT_COPY: dict[str, str] = {
        "system_intro": (
            "You are a YouTube Shorts scriptwriter. You write in the Hook-Body-CTA format.\n"
            "Output ONLY valid JSON.\n"
            "Schema:\n"
            "{\n"
            '  "title": "string",\n'
            '  "scenes": [...],\n'
            '  "no_reliable_source": false\n'
            "}\n"
        ),
        "source_rule": (
            "CRITICAL SOURCE RULE:\n"
            "  - You MUST base all claims on verifiable facts you are confident about.\n"
            "  - If you cannot recall specific data, studies, or established facts for this topic,\n"
            "    DO NOT invent or guess. Instead, return:\n"
            '    {"title": "", "scenes": [], "no_reliable_source": true,\n'
            '     "reason": "<why no reliable source was found>"}\n'
            "  - It is FAR BETTER to admit 'I don't have reliable data' than to hallucinate facts.\n"
            "  - For each factual claim in the Body, mentally ask: 'Can a viewer Google this and confirm it?'\n"
            "    If the answer is no, either remove the claim or flag no_reliable_source.\n"
        ),
        "hook_rules": (
            "Hook rules:\n"
            "  - {hook_rule}\n"
            "  - Stop the scroll within 3 seconds. One or two punchy spoken sentences.\n"
            "  - narration_ko: up to {hook_max} English characters (short and punchy).\n"
        ),
        "body_rules": (
            "Body rules:\n"
            "  - Build depth in this order: analogy first -> fact or data -> cause or solution.\n"
            "  - Each body scene should naturally flow into the next. No bullet points.\n"
            "  - narration_ko: {body_min}-{body_max} English characters (detailed and spoken).\n"
        ),
        "cta_rules": (
            "CTA rules:\n"
            "  - Suggest ONE specific, immediate real-world action the viewer can do right now.\n"
            "  - Do NOT mention subscriptions, likes, follows, or channel actions.\n"
            "  - After the action, add one sentence of creator insight, like a personal takeaway or observation.\n"
            "  - narration_ko: up to {cta_max} English characters (brief and direct).\n"
        ),
        "general_rules": (
            "General rules:\n"
            "  - narration_ko must be in {language}\n"
            "  - return exactly {scene_count} scenes\n"
            "  - narration must sound natural when spoken aloud, not like bullet points\n"
            "  - Do NOT use '...' (ellipsis) in narration_ko. Write complete sentences.\n"
            "  - estimated_seconds must realistically match the spoken length of that scene\n"
            "  - visual_prompt_en: English only, describe camera angle, lighting, action, artistic style for DALL-E 3\n"
            "  - visual_prompt_en MUST be DALL-E safe: NO medical imagery, anatomical details, injuries, blood,\n"
            "    violence, weapons, drugs, or explicit body parts. Use abstract metaphors instead.\n"
            "    (e.g. 'a person resting on a couch' instead of 'sedentary lifestyle causing muscle atrophy')\n"
            "  - do not include markdown\n"
        ),
        "korean_rules": (
            "English Writing Rules (CRITICAL):\n"
            "  - All narration_ko text must be natural spoken English.\n"
            "  - Check spelling, punctuation, and contractions for fluency.\n"
            "  - Avoid stiff textbook phrasing or unnatural repetition.\n"
            "  - Proofread each narration_ko line before outputting.\n"
        ),
        "user_header": (
            "Topic: {topic}\n"
            "Target total duration: {target_min}-{target_max} seconds.\n"
            "Target midpoint: about {target_mid:.1f} seconds.\n"
        ),
        "user_instructions": (
            "Write a Hook-Body-CTA script for YouTube Shorts in natural spoken English:\n"
            "  Hook  - Open with a surprising fact or relatable problem. Stop the scroll instantly.\n"
            "  Body  - Guide through analogy -> data or fact -> cause or solution. Build naturally.\n"
            "  CTA   - One specific action the viewer can do right now. No subscription requests.\n"
        ),
        "retry_too_short": (
            "The previous draft was too short at about {previous_total_sec:.1f} seconds.\n"
            "Make each scene narration meaningfully longer with more spoken detail.\n"
        ),
        "retry_too_long": (
            "The previous draft was too long at about {previous_total_sec:.1f} seconds.\n"
            "Tighten each scene narration while keeping the same clarity.\n"
        ),
        "retry_keep_scene_count": "Keep exactly {previous_scene_count} scenes unless that prevents the duration target.\n",
    }""",
    content,
    flags=re.DOTALL,
)

# 6. _REVIEW_COPY
content = re.sub(
    r"(?m)^ +_REVIEW_COPY: dict\[str, str\] = \{.*?^    \}",
    r"""    _REVIEW_COPY: dict[str, str] = {
        "base_review_system": (
            "You are a YouTube Shorts script quality evaluator. "
            "Score the given script on these dimensions from 1-10:\n"
            "  hook_score : How well does the Hook stop the scroll? (1=boring, 10=irresistible)\n"
            "  flow_score : How naturally does the Body build and connect? (1=choppy, 10=seamless)\n"
            "  cta_score  : How clear and actionable is the CTA? (1=vague, 10=immediately doable)\n"
            "  verifiability_score : Can a viewer verify the factual claims easily? "
            "(1=not credible, 10=highly verifiable)\n"
            "  spelling_score : Is the English spelling, grammar, and punctuation clean and natural for spoken delivery? "
            "(1=many issues, 10=excellent)\n"
        ),
        "feedback_rule": "Also provide a brief 'feedback' string (max 80 chars) with the main weakness.\n",
        "output_rule": 'Output ONLY valid JSON: {{{json_example}, "feedback": "..."}}',
    }""",
    content,
    flags=re.DOTALL,
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully with correct indentation.")
