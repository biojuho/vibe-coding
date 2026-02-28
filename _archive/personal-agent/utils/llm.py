from __future__ import annotations

import os
import random
import sys
import time
import warnings
from pathlib import Path
from typing import Tuple

from config import GOOGLE_API_KEY, LLM_PROVIDER, OPENAI_API_KEY

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*_UnionGenericAlias.*deprecated.*",
            category=DeprecationWarning,
            module=r"google\.genai\.types",
        )
        from google import genai as google_genai
except ImportError:
    google_genai = None

legacy_genai = None
if google_genai is None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as legacy_genai
    except ImportError:
        legacy_genai = None

try:
    from execution.api_usage_tracker import log_api_call
except Exception:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from execution.api_usage_tracker import log_api_call
    except Exception:  # pragma: no cover - optional integration
        def log_api_call(**_kwargs):
            return None


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_google_usage(usage_metadata) -> Tuple[int, int]:
    if usage_metadata is None:
        return 0, 0
    input_tokens = _safe_int(
        getattr(usage_metadata, "prompt_token_count", None)
        or getattr(usage_metadata, "input_token_count", None)
    )
    output_tokens = _safe_int(
        getattr(usage_metadata, "candidates_token_count", None)
        or getattr(usage_metadata, "output_token_count", None)
    )
    return input_tokens, output_tokens


class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.client = None
        self.model = None
        self.model_name = ""
        self.google_backend = ""

        def fallback_to_mock(reason: str):
            print(f"LLM fallback to mock: {reason}")
            self.provider = "mock"
            self.client = None
            self.model = None
            self.model_name = "mock"

        if self.provider == "openai":
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            if OpenAI is None:
                fallback_to_mock("openai package not installed")
            elif not OPENAI_API_KEY:
                fallback_to_mock("OPENAI_API_KEY is not set")
            else:
                self.client = OpenAI(api_key=OPENAI_API_KEY)

        elif self.provider == "google":
            self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
            if not GOOGLE_API_KEY:
                fallback_to_mock("GOOGLE_API_KEY is not set")
            elif google_genai is not None:
                self.google_backend = "google.genai"
                self.client = google_genai.Client(api_key=GOOGLE_API_KEY)
            elif legacy_genai is not None:
                self.google_backend = "google.generativeai"
                legacy_genai.configure(api_key=GOOGLE_API_KEY)
                legacy_name = os.getenv("GOOGLE_MODEL_LEGACY", "models/gemini-flash-latest")
                self.model_name = legacy_name
                self.model = legacy_genai.GenerativeModel(legacy_name)
            else:
                fallback_to_mock("google genai libraries not installed")

        elif self.provider == "mock":
            self.model_name = "mock"
        else:
            fallback_to_mock(f"Unsupported provider '{self.provider}'")

    def _log_usage(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
        log_api_call(
            provider=provider,
            model=model,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            caller_script="projects/personal-agent/utils/llm.py",
        )

    def generate_text(self, prompt, max_retries=5):
        if self.provider == "mock":
            return "[MOCK] This is a simulated response from Jarvis. The API quota is currently exceeded, but the logic is working! Today's weather is perfect for coding."

        retries = 0
        while retries < max_retries:
            try:
                if self.provider == "openai":
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": "You are a helpful personal assistant named Jarvis."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    text = (response.choices[0].message.content or "").strip()
                    usage = getattr(response, "usage", None)
                    self._log_usage(
                        provider="openai",
                        model=self.model_name,
                        input_tokens=_safe_int(getattr(usage, "prompt_tokens", 0)),
                        output_tokens=_safe_int(getattr(usage, "completion_tokens", 0)),
                    )
                    return text

                if self.provider == "google":
                    if self.google_backend == "google.genai":
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                        )
                        text = (getattr(response, "text", None) or "").strip()
                        input_tokens, output_tokens = _extract_google_usage(
                            getattr(response, "usage_metadata", None)
                        )
                        self._log_usage(
                            provider="google",
                            model=self.model_name,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                        )
                        return text

                    response = self.model.generate_content(prompt)
                    text = (getattr(response, "text", None) or "").strip()
                    input_tokens, output_tokens = _extract_google_usage(
                        getattr(response, "usage_metadata", None)
                    )
                    self._log_usage(
                        provider="google",
                        model=self.model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                    return text

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota exceeded" in error_msg or "Resource exhausted" in error_msg:
                    wait_time = (2 ** retries) + random.uniform(1, 3)
                    print(f"⚠️ Rate limit hit. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    retries += 1
                    continue
                return f"Error generating text: {error_msg}"

        return "Error: Max retries exceeded due to rate limits."


if __name__ == "__main__":
    try:
        llm = LLMClient()
        print(llm.generate_text("Hello, who are you?"))
    except Exception as e:
        print(e)
