# T-1460 Output Quality Loop: Best-of-N Publishability Selection

## Target

`blind-to-x` should not stop at "a draft exists." The selected X/Threads draft should be copy-ready: platform-valid, specific, non-repetitive, source-faithful, and strong enough that the reviewer is unlikely to rewrite it from scratch.

## External Output Bar

Current social-writing tools compete on final-output quality, not just generation:

- X official docs make publishability a hard constraint: weighted character count, URL handling, emoji/CJK weights, and Unicode normalization must be respected before posting.
- Buffer AI Assistant emphasizes channel-aware generation, shortening/expanding, tone adjustment, prompt context, and human review for factuality.
- Typefully Writing Assistant positions itself as an in-editor editor that improves hooks, endings, structure, platform fit, voice continuity, and confusing weak points.
- Hypefury exposes quality signals like hooks used, story/CTA structure, engagement words, and virality scoring.

Applied standard: the selector must prefer a less flashy but directly usable and distinct draft over a high-scoring near-duplicate.

## Good vs Bad Output

Good output:

- Fits the target platform constraints before the user copies it.
- Has a concrete hook, scene, or claim instead of generic "what do you think?" endings.
- Preserves the source point without copying source phrasing.
- Avoids recent-draft repetition and template-feeling cadence.
- Carries selection metadata so reviewers can understand why it was chosen.

Bad output:

- Wins because it sounds exciting, then fails length/originality/similarity gates later.
- Repeats a recent draft with only cosmetic changes.
- Needs the user to manually check publishability, novelty, or platform fit.
- Hides why it was selected.

## Baseline

Before T-1460, Best-of-N selection blended only editorial reviewer score and comment-trigger score. That caught "better writing" but not "ready to post." A high editorial score could win even when the candidate duplicated recent output and would later require reroll/review effort.

## Candidate

T-1460 blends deterministic `QualityGate` results into Best-of-N selection with a configurable `llm.best_of_n_quality_weight` default of `0.35`.

The publishability score checks every requested publishable draft via `QualityGate.check()` and penalizes:

- hard failures
- warnings
- recent-draft semantic similarity
- source-copying/originality problems
- platform validity problems already covered by the gate

The selected draft now records:

- `_quality_gate_score`
- `_quality_gate_failures`
- `_quality_gate_warnings`
- `_max_semantic_similarity`
- `_best_of_n_selection_score`

## A/B Decision

Baseline metrics:

- selects publishable distinct candidate: `0`
- records quality selection metadata: `0`
- quality weight config guard: `0`

Candidate metrics:

- selects publishable distinct candidate: `1`
- records quality selection metadata: `1`
- quality weight config guard: `1`

Required gates:

- focused Best-of-N regression tests
- related output-quality regression tests
- Ruff check
- `git diff --check`

Decision: adopt candidate.

## Verification

- `.venv\Scripts\python.exe -m pytest tests\unit\test_draft_generator_best_of_n.py -q --tb=short --maxfail=1 -o addopts='' --basetemp=.pytest-tmp-t1460-focused` -> `17 passed`
- `.venv\Scripts\python.exe -m pytest tests\unit\test_output_quality_uplift.py tests\unit\test_draft_generator_best_of_n.py -q --tb=short --maxfail=1 -o addopts='' --basetemp=.pytest-tmp-t1460-related` -> `58 passed`
- `.venv\Scripts\python.exe -m ruff check pipeline\draft_generator.py tests\unit\test_draft_generator_best_of_n.py` -> pass
- `python execution\project_qc_runner.py --project blind-to-x --json --artifact .tmp\project_qc_runner_blind_t1460.json` -> pass (`1836 passed`, `9 skipped`, lint pass)
- `py -3.13 execution\code_review_gate.py --base HEAD~1 --json` -> advisory warn (`risk_score=0.40`), covered by focused, related, and project QC gates
- `git diff --check` -> pass

## Next Loop

The next highest-output-quality step is to add an operator-facing selection summary to Notion review rows, so reviewers see why the candidate won: editorial score, publishability score, warning count, and similarity score. That turns hidden selector quality into visible trust.
