# 25 · Multimodal · Vision · Audio · Media Boundary

> Text LLM generation, vision input, image generation, TTS, STT, video generation, and local rendering are different operating surfaces.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `projects/shorts-maker-v2`, `projects/blind-to-x`, `.ai/PROJECTS.md`, and `.ai/DECISIONS.md`.

## Why This Is Separate

"LLM" is too broad for media work. A model that can read images is not automatically an image generator. A TTS endpoint is not the same as an audio-understanding model. A video generation API is not the same as MoviePy/FFmpeg rendering. If these are grouped together, cost estimates, safety checks, storage rules, fallback behavior, and quality gates become misleading.

Use these buckets before designing or debugging a feature:

| Bucket | Input | Output | Repo meaning |
|---|---|---|---|
| Text generation | text | text/JSON | `LLMClient`, `LLMRouter`, Blind-to-X draft generation |
| Vision / image understanding | image + text | text/JSON | analyze screenshots, source images, thumbnails, charts |
| Image generation/editing | text/image prompt | image | Blind-to-X AI image path, Shorts visual assets |
| TTS / speech generation | text | audio | Shorts narration and voice output |
| STT / audio understanding | audio | text/timestamps/JSON | word timing, transcript, diarization, QA on audio |
| Video generation | text/image prompt | video | Gemini Veo-style asset generation |
| Local rendering | media files + timeline | MP4/PNG/SRT | MoviePy/FFmpeg/Pillow composition, not provider inference |

## Current Code Facts

### 1) Workspace `LLMClient` Is Text-Only

`workspace/execution/llm_client.py` exposes `generate_json`, `generate_text`, and bridged text helpers. The public surface does not expose provider-neutral image input, image generation, audio input, TTS, STT, or video generation. Do not claim the workspace core has a multimodal abstraction just because provider docs support multimodal APIs.

### 2) Shorts Maker Has Media Providers Outside The Text Router

Shorts Maker's architecture explicitly separates `media_step.py` from `render_step.py`: media step creates TTS and image/video assets, while render step uses MoviePy/FFmpeg to produce MP4. Provider modules are also separate: `openai_client.py` handles DALL-E/image and TTS-style calls, `google_client.py` handles Gemini image, Imagen, Veo, and embeddings, and `edge_tts_client.py` handles Edge TTS.

Current config and shared context also show a live drift to record before making product claims:

- `.ai/PROJECTS.md` describes the active stack as Python, MoviePy, Edge TTS, and Streamlit.
- `projects/shorts-maker-v2/config.yaml` currently sets `providers.tts: "edge-tts"` and comments that `tts_model: "tts-1-hd"` is ignored when Edge TTS is used.
- `.ai/DECISIONS.md` ADR-012 records a decision to move from edge-tts to OpenAI `tts-1-hd` plus Whisper-1 word sync.

Operational conclusion: **ADR-012 is an intent/history record, not proof of the current runtime provider.** Check config/code before saying Shorts Maker is on OpenAI TTS.

The current media fallback shape is also explicit:

- `TTSFactory.generate_tts_with_fallback()` routes premium providers (`chatterbox`, `cosyvoice`, `openvoice`) through Edge fallback and calls OpenAI TTS only when the configured provider is `openai` and an OpenAI client is present.
- `edge_tts_client.py` captures WordBoundary timing, retries voices/rate/pitch, and falls back to local WhisperX/faster-whisper word timing when timing events are missing.
- `google_client.py` has separate methods for `generate_video()`, Gemini native image generation through `generate_content()`, Imagen generation through `generate_images()`, and `embed_content()`.
- `visual_mixin.py` and `fallback_mixin.py` route visual assets through google-veo, stock video, Imagen/Gemini/Pollinations/OpenAI-image, and placeholders depending on policy and availability.

### 3) Blind-to-X Has Image Prompt And Image Generation Boundaries

Blind-to-X is primarily a text-draft/review pipeline, but media fields are real:

- `rules/prompts.yaml` asks the draft response to include an `<image_prompt>` block.
- `draft_generator.py` caches and returns `(drafts, image_prompt)`.
- `persist_stage.py` can prefer original community images, build a Blind image prompt, or schedule AI image generation only when profile flags allow it.
- `pipeline/image_generator.py` is a multi-provider image generator with free-first routing (`gemini`, `pollinations`, optional `dalle`) and static fallback images when all providers fail.
- `cost_tracker.py` tracks text provider cost separately from image generation, with Gemini image count and DALL-E image cost paths.

Operational conclusion: Blind-to-X image prompt metadata is not the same thing as generating an image. The publish/review path must record whether the final media came from original source image, AI generation, fallback stock/static image, or no image.

## Provider Official Boundaries

### OpenAI

OpenAI has separate docs for image generation, images/vision, audio/speech, and speech-to-text. The image generation guide separates the Image API and Responses API image-generation tool; the images/vision guide covers image input for model understanding and bills image inputs as tokens. The audio overview separates Realtime speech-to-speech from chained STT -> text LLM -> TTS. The speech-to-text guide documents transcription/translation endpoints and file/input constraints.

Repo rule: OpenAI vision/image/TTS/STT features should not be hidden behind the generic text `LLMClient` without a new manifest for modality, MIME type, storage, cost, and safety behavior.

### Gemini

Gemini docs split image understanding, image generation, speech generation, audio understanding, and Veo video generation. Image understanding uses `generateContent` with inline image data or Files API. Image generation can use native Gemini image capabilities or specialized Imagen models. Speech generation is native TTS for text-to-audio and is different from Live API conversational audio. Audio understanding can transcribe/summarize/diarize audio into text, but current docs point real-time transcription to Live API or Cloud Speech-to-Text. Veo generation is a separate video generation flow.

Repo rule: Gemini "multimodal" does not mean every call can accept every media type. Match the exact method/model: `generate_content`, `generate_images`, `generate_videos`, TTS model, or embedding model.

### Claude / Anthropic

Claude vision docs cover image input for analysis through Claude.ai, Console Workbench, or API request. Images count toward token usage, and the docs give request/image-count, size, resolution, token, and format constraints. Claude vision is therefore an image-understanding surface for this repo, not a native image/TTS/video generation surface unless a separate official capability and code path is added later.

Repo rule: Claude image input can support analysis/review tasks, but it should not be presented as an image generator or local renderer.

### Edge TTS, WhisperX, MoviePy, FFmpeg, Pillow

These are pipeline dependencies, not LLM provider capabilities. They can be critical to output quality, but they need local smoke tests and media artifact validation rather than LLM provider prompt tests.

Repo rule: local rendering verification should check actual file existence, duration, dimensions, caption sync, audio mix, and nonblank frames. It should not be counted as "LLM API pass" evidence.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Treat all media as "LLM" | Simple label | False capabilities, bad costs, unsafe storage assumptions | Reject |
| B. Separate provider-native media APIs from local rendering | Accurate cost/safety/test boundaries | More manifests and provider adapters | Adopt |
| C. Add one generic multimodal `LLMClient` now | One entrypoint | Provider-specific methods and MIME contracts get flattened too early | Defer |
| D. Keep workflow-local adapters with provenance | Fits Shorts/Blind-to-X current shape | Duplicated policy until abstraction is justified | Current best path |

**Decision:** Adopt B and D. Keep text `LLMClient` as text-only until two or more production workflows need the same multimodal contract. For now, document modality at the workflow edge and preserve provenance for media assets.

## Implementation Checklist

1. Classify the task as text, vision, image generation, TTS, STT/audio understanding, video generation, embedding, or local render before picking a provider.
2. Record input/output MIME type, file path/URL, provider, model, voice, duration, dimensions, and prompt/schema version in the artifact manifest.
3. Separate original source media from AI-generated media and fallback/static media in Notion, DB, and upload metadata.
4. Never use image prompt text as proof that an image was generated.
5. Do not send user/private media to provider APIs without an explicit privacy boundary and retention note.
6. Treat audio/video size, duration, and frame sampling as token/cost/latency inputs, not only as file-system facts.
7. Keep TTS voice compatibility separate from model compatibility. Edge voice aliases and OpenAI voices are not interchangeable without mapping. See [34-language-bridge-locale-i18n-boundary](34-language-bridge-locale-i18n-boundary.md) for the split between script language evidence and TTS locale evidence.
8. Verify local render with deterministic media checks: duration, resolution, audio stream, subtitle timing, and nonblank frames.
9. Verify provider media calls with mocked unit tests plus one scoped live smoke only when credentials/cost policy allow it.
10. Update `source-inventory.json` after adding or changing official media API references.

## Pitfalls

- Vision input is not image generation.
- TTS is not speech-to-speech unless the endpoint/model is designed for interactive audio.
- STT transcript output is not grounding evidence unless timestamps/speaker/source provenance are preserved. See [28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md) for source artifact rules.
- MoviePy/FFmpeg success is local rendering success, not provider inference success.
- ADRs can drift from config. Check `config.yaml` and active code before claiming the current media provider.
- Media safety and privacy need MIME-aware review. Text-only prompt filters are not enough for uploaded images/audio/video.
- Generated images/video must carry provenance. Without it, reviewers cannot distinguish source media, AI media, and fallback media.
- Public media also needs publish-gate evidence. [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) separates provider image safety, stock/media fallback, YouTube AI-disclosure duty, and final human approval.

## 출처 (1차 우선, 2026-06-08 확인)

- Official: OpenAI API Docs, *Image generation*: <https://developers.openai.com/api/docs/guides/image-generation>
- Official: OpenAI API Docs, *Images and vision*: <https://developers.openai.com/api/docs/guides/images-vision>
- Official: OpenAI API Docs, *Audio and speech*: <https://developers.openai.com/api/docs/guides/audio>
- Official: OpenAI API Docs, *Speech to text*: <https://developers.openai.com/api/docs/guides/speech-to-text>
- Official: Google AI for Developers, *Image understanding*: <https://ai.google.dev/gemini-api/docs/image-understanding>
- Official: Google AI for Developers, *Image generation*: <https://ai.google.dev/gemini-api/docs/image-generation>
- Official: Google AI for Developers, *Speech generation*: <https://ai.google.dev/gemini-api/docs/speech-generation>
- Official: Google AI for Developers, *Audio understanding*: <https://ai.google.dev/gemini-api/docs/audio>
- Official: Google AI for Developers, *Generate videos with Veo*: <https://ai.google.dev/gemini-api/docs/video>
- Official: Claude API Docs, *Vision*: <https://platform.claude.com/docs/en/build-with-claude/vision>
- Code evidence: `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/ARCHITECTURE.md`, `projects/shorts-maker-v2/config.yaml`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/openai_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/google_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/tts_factory.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/edge_tts_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/visual_mixin.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/fallback_mixin.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/image_generator.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/cost_tracker.py`, `.ai/PROJECTS.md`, `.ai/DECISIONS.md`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
