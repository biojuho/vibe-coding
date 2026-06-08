# 28 · Grounding · Citation · Source Attribution Boundary

> Grounding, citations, source attribution, and fact-checking are related but not interchangeable.
> Code facts were checked on 2026-06-08 from `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py`, `script_review.py`, `projects/blind-to-x/pipeline/research_context.py`, `fact_checker.py`, `process_stages/generate_review_stage.py`, `process_stages/persist_stage.py`, and `pipeline/notion/_upload.py`.

## Why This Is Separate

A model can produce a plausible answer without any retrieval. A provider search tool can return citation metadata, but that still does not prove every claim is correct. A local scraper can preserve a source URL, but that is not the same as provider-native grounding. A deterministic fact checker can catch numeric fabrication, but it does not identify the web source that supports a non-numeric claim.

Use these buckets before claiming "grounded" output:

| Bucket | What it proves | What it does not prove |
|---|---|---|
| Ungrounded generation | Model produced text from prompt/context | Currentness, source support, citation chain |
| Provider search grounding | Provider searched and returned structured source metadata | Full correctness or local retention rights |
| URL/document citation | Output spans point to provided URLs/documents/files | Source quality or claim sufficiency |
| App-owned source attribution | The product kept source title/URL/original post metadata | That the model actually used each source |
| Deterministic fact check | Specific local rule passed, such as number-in-source | Broader factual truth or citation validity |

## Current Code Facts

### 1) Shorts Maker Uses Gemini Search Grounding But Keeps Only Source Titles

`ResearchStep._research_with_grounding()` calls Gemini `generate_content()` with `types.Tool(google_search=types.GoogleSearch())`. It parses the model JSON for `facts`, `key_data_points`, `sources`, and `summary`, then reads `response.candidates[0].grounding_metadata.grounding_chunks` and appends each web chunk's `title` into `ResearchContext.sources`.

Operational conclusion:

- The workflow is truly provider-native Google Search Grounding, not a local scraper.
- Current `ResearchContext` does not preserve `webSearchQueries`, source URI, `groundingSupports`, support segment offsets, retrieval status, or a raw grounding artifact.
- `to_prompt_block()` passes only a short source-name list into script generation. Reviewers cannot reconstruct which sentence was supported by which URI.

### 2) Shorts Maker Script Review Checks Against Research Text, Not Source Artifacts

`script_review.py` compares the generated scenes against `research_context.to_prompt_block()` and asks an LLM reviewer whether claims are supported, exaggerated, or missing. This is a useful self-check, but the verifier sees the reduced research block, not the original grounding metadata.

Operational conclusion: treat this as a script-vs-research consistency check. It is not a citation audit unless the research context carries claim-level source metadata.

### 3) Blind-to-X Keeps Source Post Context And Deterministic Value Framing

`research_context.py` builds a deterministic `research_context` from the source post title/content without network calls. It records source frame, real issue, universal value, killer sentence, closure, conflict risk, anchor, flags, and notes. `generate_review_stage.py` injects this before draft generation and publish-decision repair.

Operational conclusion: Blind-to-X "research_context" is editorial framing, not external research. Its `anchor` and Notion "근거 앵커" help reviewers see what source passage the draft is built around, but they should not be labeled web citations.

### 4) Blind-to-X Fact Check Is Numeric Fabrication Guarding

`fact_checker.py` extracts numeric expressions from the source content and generated draft, normalizes Korean numeric units, and flags draft numbers that do not match the source. `generate_review_stage.py` stores failures in `post_data["fact_check_warnings"]`, and the Notion uploader surfaces warning counts/previews.

Operational conclusion: this is a strong local guard for invented numbers. It does not verify non-numeric claims, source credibility, freshness, or URL attribution.

### 5) Product Source Attribution Lives In Output Surfaces

`persist_stage.py` keeps `post_data["source"]`, source/community image decisions, screenshot/original/AI-image selection, publish decision, and X/Notion metadata. `pipeline/notion/_upload.py` writes source, URL, evidence anchor, fact-check warnings, X upload card, and reviewer guidance into Notion.

Operational conclusion: source attribution is already partly product-facing. The missing layer is a normalized artifact that distinguishes original source URL/post, provider grounding sources, URL/document citations, fact-check warnings, and media provenance.

## Provider Official Boundaries

### OpenAI

OpenAI Web Search returns a search-call output item plus message annotations for cited URLs. The `url_citation` annotation includes URL, title, and response character positions, and user interfaces must make web citations visible and clickable. The `sources` field can expose all URLs consulted, which is broader than only inline citations.

OpenAI File Search returns a `file_search_call` output item and message output with `file_citation` annotations. Raw file search results are not returned by default; the request must explicitly include search-call results when the application needs retrieval evidence beyond visible annotations.

Repo implication: do not collapse "inline citation shown" into "complete retrieval evidence stored." Preserve annotations and, when needed for audit, include the actual search/file results artifact.

### Gemini

Gemini Grounding with Google Search returns `groundingMetadata` when a response is successfully grounded. The metadata contains web search queries, source chunks with URI/title, and grounding supports that connect text segments to source chunk indices. Gemini URL Context separately returns `url_context_metadata` with each retrieved URL and retrieval status. Current Gemini docs also call out tool-combination limits and model/version differences.

Repo implication: Shorts Maker should keep `groundingChunks` and `groundingSupports` when the output claims to be grounded. Keeping only source titles is enough for a prompt hint, not enough for reviewer citation evidence.

### Claude / Anthropic

Claude Web Search uses the server tool `web_search_20250305` and always enables citations for web search. Web search result locations include URL, title, encrypted index, and cited text. Search result blocks can also include page age and encrypted content that must be passed back for multi-turn citation continuity.

Claude Citations for user-provided documents are a different feature. Documents must enable citations, and responses include text blocks with citation objects such as character, page, or content-block locations. Anthropic notes that citations can be incompatible with strict structured output because citations interleave with text.

Repo implication: provider web citations and user-document citations are separate surfaces. Structured JSON workflows may need a two-step pattern: retrieve/cite first, then transform into product JSON while preserving citation metadata outside the strict output body.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Store only final generated text | Simple artifacts | Reviewers cannot audit source support | Reject for grounded claims |
| B. Store source names only | Low privacy/cost | URLs, query, segment support, freshness lost | Current Shorts gap |
| C. Store normalized source-evidence artifact | Reviewable across providers and products | Needs schema and redaction rules | Adopt next |
| D. Store raw full provider responses | Maximum debug detail | Privacy/retention and provider schema churn | Only for classified debug runs |

**Decision:** adopt C. Each grounded or source-sensitive output should carry a small artifact that is independent from the final generated text.

Suggested shape:

```json
{
  "grounding_mode": "none|provider_web_search|url_context|file_search|app_owned_source|deterministic_fact_check",
  "provider": "gemini|openai|anthropic|local",
  "model": "gemini-2.5-flash",
  "query_or_source_hash": "sha256:...",
  "sources": [
    {
      "title": "source title",
      "url": "https://example.com/page",
      "retrieval_status": "success|failed|unknown",
      "page_age": "2026-06-08|unknown",
      "supports": [{"text": "claim span or hash", "source_index": 0}]
    }
  ],
  "fact_check": {
    "type": "number_in_source",
    "passed": true,
    "warnings": []
  }
}
```

## Implementation Checklist

1. Decide whether the task needs freshness, source attribution, or only local source consistency.
2. If using Gemini Search Grounding, preserve `webSearchQueries`, `groundingChunks.web.uri/title`, and `groundingSupports` before reducing the response to script facts.
3. If using URL Context, store retrieved URLs and retrieval statuses separately from model prose.
4. If using OpenAI Web/File Search, keep annotations and include search/file results when reviewer evidence requires source snippets.
5. If using Claude Web Search or Citations, keep citation objects and note whether the source was web search or a user-provided document.
6. Do not put raw source text into usage metrics or Langfuse metadata; use hashes/redacted snippets unless the run is classified for full evidence retention.
7. In Notion/X reviewer surfaces, distinguish original post URL, source image URL, provider grounding URL, and first-reply attribution URL.
8. Add eval cases that fail when grounded claims have no source artifact, not only when generated text looks plausible.
9. Record source artifact schema/version with prompt provenance and retention classification.
10. Recheck provider docs before adding a new search/citation tool because supported models, billing, and tool combinations change.

## Pitfalls

- Citation metadata is not proof that every claim is correct.
- A source title without a URL is weak evidence.
- A URL without retrieved status or timestamp can go stale silently.
- LLM self-review against a summarized research block can miss errors introduced by the summarization.
- Structured JSON can be incompatible with native citation interleaving; keep citations as sidecar artifacts when needed.
- Fact-check warnings are not the same thing as source citations.
- Source attribution can create privacy/licensing obligations. Tie this page to [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md) before storing full snippets.

## 출처 (1차 우선, 2026-06-08 확인)

- Official: OpenAI API Docs, *Web search*: <https://developers.openai.com/api/docs/guides/tools-web-search>
- Official: OpenAI API Docs, *File search*: <https://developers.openai.com/api/docs/guides/tools-file-search>
- Official: Google AI for Developers, *Grounding with Google Search*: <https://ai.google.dev/gemini-api/docs/google-search>
- Official: Google AI for Developers, *URL context*: <https://ai.google.dev/gemini-api/docs/url-context>
- Official: Claude API Docs, *Web search tool*: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool>
- Official: Claude API Docs, *Citations*: <https://platform.claude.com/docs/en/build-with-claude/citations>
- Code evidence: `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/research_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_review.py`, `projects/blind-to-x/pipeline/research_context.py`, `projects/blind-to-x/pipeline/fact_checker.py`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/notion/_upload.py`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
