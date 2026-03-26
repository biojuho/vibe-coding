import re

filepath = r"c:\Users\박주호\Desktop\Vibe coding\shorts-maker-v2\src\shorts_maker_v2\pipeline\script_step.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
if "import yaml" not in content:
    content = content.replace("import threading", "import threading\nimport copy\nimport yaml\nfrom pathlib import Path")

# 2. Add _load_script_step_locale_bundle
bundle_code = """
def _load_script_step_locale_bundle(language_code: str) -> dict:
    \"\"\"Load script_step.yaml bundle for the given language code from locales/.\"\"\"
    try:
        current_dir = Path(__file__).resolve().parent
        yaml_path = current_dir.parent.parent.parent / "locales" / language_code / "script_step.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load locale bundle for {language_code}: {e}")
    return {}
"""
if "_load_script_step_locale_bundle" not in content:
    content = content.replace("class TopicUnsuitableError(Exception):", bundle_code + "\nclass TopicUnsuitableError(Exception):")

# 3. Modify class methods to regular methods for easier state access
content = content.replace("    @classmethod\n    def _score_persona_match(cls, scenes", "    def _score_persona_match(self, scenes")
content = content.replace("cls._PERSONA_KEYWORDS", "self._persona_keywords")
content = content.replace("        keywords = persona_keywords.get(channel_key)", "        keywords = self._persona_keywords.get(channel_key)")

content = content.replace("    @classmethod\n    def _validate_cta(cls, narration", "    def _validate_cta(self, narration")
content = content.replace("cls._CTA_FORBIDDEN_WORDS", "self._cta_forbidden_words")

# 4. Modify calls to these classmethods
content = content.replace("cls._score_persona_match", "self._score_persona_match")
content = content.replace("cls._validate_cta", "self._validate_cta")
# Also in run()
content = content.replace("self._score_persona_match(", "self._score_persona_match(") # Already correct if it was self.

# 5. In __init__, add self._apply_locale_overrides()
init_end = "        self.channel_key: str = channel_key"
if "self._apply_locale_overrides()" not in content:
    content = content.replace(init_end, init_end + "\n        self._apply_locale_overrides()")

# 6. Add _apply_locale_overrides definition right after __init__
override_code = """
    def _apply_locale_overrides(self) -> None:
        self._tone_presets = list(self.TONE_PRESETS)
        self._channel_persona = copy.deepcopy(self._CHANNEL_PERSONA)
        self._cta_forbidden_words = tuple(self._CTA_FORBIDDEN_WORDS)
        self._persona_keywords = copy.deepcopy(self._PERSONA_KEYWORDS)
        self._prompt_copy = copy.deepcopy(self._PROMPT_COPY)
        self._review_copy = copy.deepcopy(self._REVIEW_COPY)
        self._prompt_field_names = copy.deepcopy(self._PROMPT_FIELD_NAMES)
        
        # Load from yaml
        lang = self.config.project.language
        bundle = _load_script_step_locale_bundle(lang)
        if not bundle:
            return

        tone_presets = bundle.get("tone_presets")
        if isinstance(tone_presets, list):
            self._tone_presets = []
            for item in tone_presets:
                if isinstance(item, dict) and "name" in item and "guide" in item:
                    self._tone_presets.append((str(item["name"]).strip(), str(item["guide"]).strip()))

        channel_persona = bundle.get("channel_persona")
        if isinstance(channel_persona, dict):
            for k, v in channel_persona.items():
                if isinstance(v, dict):
                    if k not in self._channel_persona:
                        self._channel_persona[k] = {}
                    self._channel_persona[k].update(v)

        cta_forbidden_words = bundle.get("cta_forbidden_words")
        if isinstance(cta_forbidden_words, list):
            self._cta_forbidden_words = tuple(str(w).strip() for w in cta_forbidden_words)

        persona_keywords = bundle.get("persona_keywords")
        if isinstance(persona_keywords, dict):
            for k, v in persona_keywords.items():
                if isinstance(v, list):
                    self._persona_keywords[str(k)] = tuple(str(item).strip() for item in v)

        prompt_copy = bundle.get("prompt_copy")
        if isinstance(prompt_copy, dict):
            self._prompt_copy.update(prompt_copy)

        review_copy = bundle.get("review_copy")
        if isinstance(review_copy, dict):
            self._review_copy.update(review_copy)
            
        field_names = bundle.get("field_names")
        if isinstance(field_names, dict):
            for k, v in field_names.items():
                if k in self._prompt_field_names:
                    self._prompt_field_names[str(k)] = str(v)
"""
if "def _apply_locale_overrides(" not in content:
    init_decl = "    def __init__("
    next_method_idx = content.find("    def _build_system_prompt", content.find(init_decl))
    if next_method_idx != -1:
        content = content[:next_method_idx] + override_code + "\n" + content[next_method_idx:]
    else:
        print("Could not find _build_system_prompt to insert override_code")

# 7. Use the instance properties instead of CLASS properties
content = content.replace("len(self.TONE_PRESETS)", "len(self._tone_presets)")
content = content.replace("self.TONE_PRESETS[idx]", "self._tone_presets[idx]")
content = content.replace("self._prompt_copy.get", 'self._prompt_copy.get')
content = content.replace('cls._PROMPT_COPY', 'self._prompt_copy')

# 8. Adjust _build_system_prompt to use dynamic strings
# Find: system_prompt = (\n...
content = re.sub(
    r'system_prompt = \(\n *self\._BASE_REVIEW_SYSTEM\n.*?"\n *\)',
    r'system_prompt = (\n            self._review_copy.get("base_review_system", "")\n            + extra_dimensions\n            + self._review_copy.get("feedback_rule", "")\n        )',
    content,
    flags=re.DOTALL
)

content = content.replace('self._BASE_REVIEW_SYSTEM', 'self._review_copy.get("base_review_system", "")')
content = content.replace('self._PROMPT_COPY["system_intro"]', 'self._prompt_copy["system_intro"]')
content = content.replace('self._PROMPT_COPY["source_rule"]', 'self._prompt_copy["source_rule"]')
content = content.replace('self._PROMPT_COPY["hook_rules"]', 'self._prompt_copy["hook_rules"]')
content = content.replace('self._PROMPT_COPY["body_rules"]', 'self._prompt_copy["body_rules"]')
content = content.replace('self._PROMPT_COPY["cta_rules"]', 'self._prompt_copy["cta_rules"]')
content = content.replace('self._PROMPT_COPY["general_rules"]', 'self._prompt_copy["general_rules"]')
content = content.replace('self._PROMPT_COPY["korean_rules"]', 'self._prompt_copy.get("korean_rules", "")')

content = content.replace('self._PROMPT_COPY["user_header"]', 'self._prompt_copy["user_header"]')
content = content.replace('self._PROMPT_COPY["user_instructions"]', 'self._prompt_copy["user_instructions"]')
content = content.replace('self._PROMPT_COPY["retry_too_short"]', 'self._prompt_copy["retry_too_short"]')
content = content.replace('self._PROMPT_COPY["retry_too_long"]', 'self._prompt_copy["retry_too_long"]')

content = content.replace('self._PROMPT_FIELD_NAMES["narration"]', 'self._prompt_field_names["narration"]')
content = content.replace('self._PROMPT_FIELD_NAMES["visual_prompt"]', 'self._prompt_field_names["visual_prompt"]')

# Output rule correction
content = re.sub(
    r'system_prompt \+= f\'Output ONLY valid JSON: \{\{\{json_example\}, "feedback": "\.\.\."\}\}\'',
    r'output_rule = self._review_copy.get("output_rule", "Output ONLY valid JSON: {{{json_example}, \\"feedback\\": \\"...\\"}}")\n        system_prompt += output_rule.format(json_example=json_example)',
    content
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Patch applied successfully.")
