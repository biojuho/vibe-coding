import re

filepath = r"c:\Users\박주호\Desktop\Vibe coding\shorts-maker-v2\src\shorts_maker_v2\pipeline\script_step.py"

with open(filepath, encoding="utf-8") as f:
    content = f.read()

# 1. Add _load_script_step_locale_bundle at the module level
if "_load_script_step_locale_bundle" not in content:
    bundle_code = """
import yaml

def _load_script_step_locale_bundle(language_code: str) -> dict[str, Any]:
    \"\"\"Load script_step.yaml bundle for the given language code from locales/.\"\"\"
    try:
        current_dir = Path(__file__).resolve().parent
        locales_dir = current_dir.parent.parent.parent / "locales"
        yaml_path = locales_dir / language_code / "script_step.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load locale bundle for %s: %s", language_code, e)
    return {}
"""
    # Insert after imports. Find `class TopicUnsuitableError`
    content = content.replace("class TopicUnsuitableError(Exception):", bundle_code + "\nclass TopicUnsuitableError(Exception):")
    # also add Path import if not there
    if "from pathlib import Path" not in content:
        content = content.replace("import threading", "import threading\nfrom pathlib import Path")

# 2. Call _apply_locale_overrides in __init__
if "self._apply_locale_overrides()" not in content:
    init_end = "        self.channel_key: str = channel_key"
    replacement = init_end + "\n        self._apply_locale_overrides()"
    content = content.replace(init_end, replacement)

# 3. Define _apply_locale_overrides method
if "def _apply_locale_overrides" not in content:
    override_code = """
    def _apply_locale_overrides(self) -> None:
        self._tone_presets = list(self.TONE_PRESETS)
        self._channel_persona = dict(self._CHANNEL_PERSONA)
        self._cta_forbidden_words = list(self._CTA_FORBIDDEN_WORDS)
        self._persona_keywords = dict(self._PERSONA_KEYWORDS)
        self._prompt_copy = dict(self._PROMPT_COPY)
        self._review_copy = dict(self._REVIEW_COPY)

        self._prompt_field_names = {
            "narration": "narration_ko",
            "visual_prompt": "visual_prompt_en",
        }

        lang = self.config.project.language
        bundle = _load_script_step_locale_bundle(lang)
        if not bundle:
            return

        if "tone_presets" in bundle:
            self._tone_presets = [(t["name"], t["guide"]) for t in bundle["tone_presets"]]

        if "channel_persona" in bundle:
            for k, v in bundle["channel_persona"].items():
                if k not in self._channel_persona:
                    self._channel_persona[k] = {}
                self._channel_persona[k].update(v)

        if "cta_forbidden_words" in bundle:
            self._cta_forbidden_words = tuple(bundle["cta_forbidden_words"])

        if "persona_keywords" in bundle:
            self._persona_keywords = {k: tuple(v) for k, v in bundle["persona_keywords"].items()}

        if "prompt_copy" in bundle:
            self._prompt_copy.update(bundle["prompt_copy"])

        if "review_copy" in bundle:
            self._review_copy.update(bundle["review_copy"])

        if "field_names" in bundle:
            self._prompt_field_names.update(bundle["field_names"])

        if "channel_review_criteria" in bundle:
             for k, v in bundle["channel_review_criteria"].items():
                if k not in self._CHANNEL_REVIEW_CRITERIA:
                    self._CHANNEL_REVIEW_CRITERIA[k] = {}
                self._CHANNEL_REVIEW_CRITERIA[k].update(v)

"""
    # Insert it after __init__
    insert_idx = content.find("    @classmethod")
    if insert_idx != -1:
        content = content[:insert_idx] + override_code + content[insert_idx:]

# 4. Replace hardcoded `self.TONE_PRESETS` with `self._tone_presets`, etc.
content = content.replace("len(self.TONE_PRESETS)", "len(self._tone_presets)")
content = content.replace("self.TONE_PRESETS[idx]", "self._tone_presets[idx]")
content = content.replace("cls._CTA_FORBIDDEN_WORDS", "self._cta_forbidden_words")
content = content.replace("self._channel_persona.get", "self._channel_persona.get") # no change needed if we used it
content = content.replace("cls._PERSONA_KEYWORDS", "self._persona_keywords")
# Change class methods referencing `cls._PERSONA_KEYWORDS` and `cls._CTA_FORBIDDEN_WORDS` to instance methods context.
# Wait, `_score_persona_match` is a classmethod!
# Let's fix _score_persona_match to take persona_keywords from parameter or make it an instance method!
content = content.replace("    @classmethod\n    def _score_persona_match(cls, scenes: list[ScenePlan], channel_key: str) -> float:", "    @classmethod\n    def _score_persona_match(cls, scenes: list[ScenePlan], channel_key: str, persona_keywords: dict[str, tuple[str, ...]]) -> float:")
content = content.replace("        keywords = cls._PERSONA_KEYWORDS.get(channel_key)", "        keywords = persona_keywords.get(channel_key)")
content = content.replace("persona_score = self._score_persona_match(final_scenes, self.channel_key)", "persona_score = self._score_persona_match(final_scenes, self.channel_key, self._persona_keywords)")

content = content.replace("    @classmethod\n    def _validate_cta(cls, narration: str) -> list[str]:", "    @classmethod\n    def _validate_cta(cls, narration: str, forbidden_words: tuple[str, ...]) -> list[str]:")
content = content.replace("        return [w for w in cls._CTA_FORBIDDEN_WORDS if w in narration.lower()]", "        return [w for w in forbidden_words if w in narration.lower()]")
content = content.replace("violations = self._validate_cta(cta_scene.narration_ko)", "violations = self._validate_cta(cta_scene.narration_ko, self._cta_forbidden_words)")

# Make _build_system_prompt use self._prompt_copy
content = content.replace('self._BASE_REVIEW_SYSTEM', 'self._review_copy.get("base_review_system", "")')

# _build_review_system replacement:
content = re.sub(
    r'system_prompt = \(\n *self._review_copy\.get\("base_review_system", ""\).*?Also provide a brief \'feedback\' string \(max 80 chars\) with the main weakness\.\\n"\n *\)',
    r'system_prompt = (\n            self._review_copy.get("base_review_system", "")\n            + extra_dimensions\n            + self._review_copy.get("feedback_rule", "")\n        )',
    content,
    flags=re.DOTALL
)
content = re.sub(
    r'system_prompt \+= f\'Output ONLY valid JSON: \{\{\{json_example\}, "feedback": "\.\.\."\}\}\'',
    r'output_rule = self._review_copy.get("output_rule", "Output ONLY valid JSON: {{{json_example}, \\"feedback\\": \\"...\\"}}")\n        system_prompt += output_rule.format(json_example=json_example)',
    content
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Applied logic.")
