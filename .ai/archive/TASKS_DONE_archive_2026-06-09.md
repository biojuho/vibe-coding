## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1706 | `[claude-goal/install-health-command-hints-verifier]` Reproduced and fixed a verifier bypass where `--verify-json` accepted tampered `doctor_command`/`schema_command` and argv hints. The verifier now recomputes expected command hints from artifact `script_path`. Verification passed focused pytest (`4 passed, 85 deselected`), final full pytest (`132 passed`), Ruff check/format, py_compile, diff-check, and graph detect. No stage, commit, push, revert, `update_goal`, root product edit, or T-251 retry. | Codex | 2026-06-08 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1708 | `[claude-goal/install-health-script-path-verifier]` Reproduced and fixed a verifier bypass where `--verify-json` accepted a tampered `script_path` plus matching command hints. The verifier now requires artifact `script_path` to resolve to the currently executing verifier script. Verification passed focused pytest (`3 passed, 89 deselected`), full pytest (`133 passed`), Ruff check/format, py_compile, diff-check, and graph detect. No stage, commit, push, revert, `update_goal`, root product edit, or T-251 retry. | Codex | 2026-06-08 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1710 | `[claude-goal/install-health-env-path-verifier]` Reproduced and fixed a verifier bypass where `--verify-json` accepted a tampered `settings_path`. The verifier now checks environment-derived path provenance against `SETTINGS_PATH`, `SKILL_PATH`, `COMMANDS_PATH`, and `DB_PATH`. Verification passed focused pytest (`3 passed, 90 deselected`), full pytest (`134 passed`), Ruff check/format, py_compile, diff-check, and graph detect. No stage, commit, push, revert, `update_goal`, root product edit, or T-251 retry. | Codex | 2026-06-08 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1711 | `[claude-goal/install-health-runtime-provenance-verifier]` Reproduced and fixed a verifier bypass where `--verify-json` accepted tampered install-health runtime provenance metadata. The verifier now requires artifact runtime metadata to exactly match the current verifier process metadata. Verification passed focused runtime pytest (`1 passed, 93 deselected`), focused install-health verifier pytest (`14 passed, 80 deselected`), full pytest (`135 passed`), Ruff check/format, py_compile, diff-check, and graph detect. No stage, commit, push, revert, `update_goal`, root product edit, or T-251 retry. | Codex | 2026-06-08 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1712 | `[llm-wiki/credentials-secrets-api-key-boundary]` Added page 39 separating provider keys, CI/runtime secrets, OAuth/PAT/user token files, Supabase/Postgres URLs, browser-public keys, observability secrets, redacted readiness artifacts, and live side-effect authorization. Verification passed LLM Wiki write/no-write audits, strict manifest audit, strict release evidence, focused pytest (`31 passed`), objective audit expected blocked, completion audit expected incomplete, diff-check, whitespace scan, and graph detect risk `0.00`. No stage, commit, push, revert, `update_goal`, product code edit, or T-251 retry. | Codex | 2026-06-08 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1875 | `[llm-wiki/full-queue-rollup-authorization-unit]` Generated ignored full queue rollup `.tmp\llm-wiki-full-queue-rollup.patch` from runtime modernization plus release-evidence one-shot patches and added gate/adoption artifacts. Verification passed main `git apply --check`, detached apply, Wiki/workflow focused pytest (`33 passed`), Blind-to-X focused pytest (`109 passed`), diff-check, LLM Wiki audit, code-review gate risk `0.00`, and graph detect risk `0.00`. No tracked patch was applied to main; scoped authorization is still required for adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1876 | `[llm-wiki/full-queue-review-matrix]` Added ignored file-by-file review matrix and audit artifacts for the verified full queue rollup. Matrix covers all 19 patch files with purpose, risk, and gate focus; A/B selected the matrix over patch-only authorization; completion audit passed (`4/4`). No tracked patch was applied to main; scoped authorization is still required for adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1878 | `[llm-wiki/full-queue-rollback-rehearsal]` Proved the rollback path for `.tmp\llm-wiki-full-queue-rollup.patch` in a detached worktree: forward apply, `git apply -R --check`, reverse apply, clean status/diff, reapply check, and worktree removal all passed. A/B selected detached rehearsal over prose-only rollback; completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required for adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1879 | `[llm-wiki/full-queue-adoption-preflight-bundle]` Added ignored deterministic preflight bundle artifacts for `.tmp\llm-wiki-full-queue-rollup.patch`, separating side-effect-free pre-authorization checks, the explicit authorized apply command, post-apply gates, and abort-before-staging rollback. Validation passed JSON/path/CLI/apply-check preflight; A/B selected the bundle (`score_delta=3.7212643678160915`); completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required for adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1880 | `[claude-goal/verifier-recovery-slash-copy]` Fixed slash verifier recovery copy for operating-contract and install-health missing-artifact flows so `/goal invoke ...` recovery stays in `/goal` syntax while direct Python helper execution keeps direct recovery commands. Verification passed manual before/after probes, focused recovery regression (`3 passed`), verifier cluster (`34 passed`), full `claude-goal` tests (`368 passed`), py_compile, Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1881 | `[llm-wiki/full-queue-integrity-lock]` Added ignored SHA256 integrity lock artifacts for the LLM Wiki full queue adoption evidence set. Locked 23 existing full-queue `.tmp` artifacts, verified the rollup patch SHA and `git apply --check`, confirmed `git apply --numstat` scope, and proved gates/adoption/review/rollback/preflight artifacts agree on patch SHA and 19-file count. A/B selected the lock (`score_delta=7.712643678160919`); completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required for adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1882 | `[claude-goal/markdown-slash-automation-hints]` Fixed slash Markdown success output so `/goal invoke contract --markdown` and `/goal invoke doctor --install --markdown` show `/goal` Automation Hints while direct Markdown controls and canonical artifact contracts keep Python helper hints. Verification passed manual before/after probes, focused Markdown regression (`4 passed`), broader Markdown cluster (`6 passed`), full `claude-goal` tests (`369 passed`), py_compile, Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1883 | `[llm-wiki/objective-coverage-refresh]` Added ignored current objective coverage artifacts after the full-queue integrity lock. Coverage now maps the autonomous-loop prompt to current LLM Wiki audit, selector, readiness, release packet, debug inventory, and full-queue integrity evidence. A/B selected the refresh (`score_delta=0.7032967032967034`); long-running objective audit remains intentionally incomplete; cycle completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required for rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1884 | `[claude-goal/json-top-help-discoverability]` Fixed top-level slash help so the working read-only `/goal json` command is discoverable in both usage and Commands. Verification passed manual before/after probes, focused help regression (`2 passed`), broader help/json cluster (`85 passed`), full `claude-goal` tests (`370 passed`), py_compile, Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1885 | `[llm-wiki/full-queue-post-apply-gate-provenance]` Added ignored gate-provenance artifacts for the LLM Wiki full queue adoption path. Relabeled from local T-1884 because shared context assigned T-1884 to `claude-goal/json-top-help-discoverability`. The matrix maps all `7/7` post-apply gates to objective requirements, what each gate proves, what it does not prove, failure signatures, and repair actions. A/B selected the provenance matrix (`score_delta=0.5`); completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required before rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1886 | `[claude-goal/existing-goal-recovery-copy]` Fixed duplicate-goal recovery so direct `set` keeps direct Python helper clear guidance while slash `invoke` duplicate set uses `/goal clear` and leaves the first objective intact. Verification passed manual before/after probes, focused duplicate regression (`2 passed`), full `tests/test_claude_goal.py` (`198 passed`), full `claude-goal` tests (`370 passed`), py_compile/compileall, Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1887 | `[llm-wiki/full-queue-post-apply-evidence-capture]` Added ignored evidence-capture manifest artifacts for the LLM Wiki full queue adoption path. Relabeled from local T-1886 because shared context assigned T-1886 to `claude-goal/existing-goal-recovery-copy`. All `7/7` post-apply gates now have planned stdout/stderr/result JSON/summary/visible artifact paths, required fields/markers, and stop-before-staging policy. A/B selected structured capture (`score_delta=0.5`); completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required before rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1889 | `[llm-wiki/full-queue-post-apply-evidence-acceptance]` Added ignored evidence-acceptance verifier artifacts for the LLM Wiki full queue adoption path. Relabeled from local T-1888 because shared context assigned T-1888 to `claude-goal/operating-contract-json-command-surface`. All `7/7` post-apply gates now have acceptance/rejection controls, `10` acceptance rules, `7` synthetic cases, embedded result JSON Schema, stdout/stderr SHA-256 checks, HEAD/dirty-signature currentness, visible release-evidence artifact requirements, no-proxy acceptance, and stop-before-staging policy. A/B selected the structured verifier (`score_delta=0.5`); completion audit passed (`6/6`). No tracked patch was applied to main; scoped authorization is still required before rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1888 | `[claude-goal/contract-json-command-surface]` Fixed operating-contract drift so the real slash `/goal json` command is included in contract JSON, schema `commandSurface`, Markdown, and regression tests. Verification passed manual before/after probes, focused contract pytest (`31 passed`), artifact verifier, py_compile, Ruff, diff-check, graph risk `0.00`, failed-test rerun, and full `claude-goal` tests (`371 passed`). | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1890 | `[claude-goal/status-json-recovery]` Fixed `status --json` recovery so direct CLI points to `python3 goal/scripts/claude_goal.py json` while slash `status`/`show`/`get`/`menu --json` points to `/goal json` without mutating the active goal. Verification passed manual before/after probes, focused status-json regression (`2 passed`), full `tests/test_claude_goal.py` (`199 passed`), full `claude-goal` tests (`371 passed`), py_compile/compileall, Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1900 | `[claude-goal/pause-stale-contract-command-surface]` Fixed operating-contract drift so the real top-level slash `/goal pause-stale` command is included in contract JSON as `pause_stale`, schema `commandSurface`, Markdown, and regression tests. Verification passed manual before/after probes, focused contract pytest (`31 passed`), artifact verifier, py_compile, Ruff, diff-check, graph risk `0.00`, and full `claude-goal` tests (`371 passed`). | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1901 | `[llm-wiki/full-queue-post-apply-acceptance-fixtures]` Added ignored fixture dry-run artifacts for the LLM Wiki full queue acceptance path. Relabeled to T-1901 using `execution/next_task_id.py` after live shared context advanced through T-1900. Materialized all T-1889 synthetic cases and dry-ran deterministic checks for complete pass, missing result JSON, pytest exit-code mismatch, stdout hash mismatch, proxy-only pass, stale HEAD, and unexpected dirty-scope expansion. Dry-run matched `7/7` expected outcomes/reject rules; A/B selected fixture dry-run (`score_delta=0.45`); completion audit passed (`5/5`). No tracked patch was applied to main; scoped authorization is still required before rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-1902 | `[claude-goal/contract-json-recovery]` Fixed exact `contract --json` misuse recovery so direct CLI points to `python3 goal/scripts/claude_goal.py contract` / `--json-output <path>` while slash canonical/raw/alias forms point to `/goal contract` / `/goal contract --json-output <path>`. Verification passed manual before/after probes, focused regression (`3 passed`), full `tests/test_claude_goal.py` (`200 passed`), full `claude-goal` tests (`372 passed`), py_compile/compileall, Ruff, diff-check, graph risk `0.00`, and nested root check. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2010 | `[claude-goal/status-update-json-recovery]` Fixed exact `pause`/`resume`/`clear --json` misuse recovery so direct CLI points to `python3 goal/scripts/claude_goal.py <command>` then `json`, while slash forms point to `/goal <command>` then `/goal json` without mutating the active goal. Verification passed manual before/after probes, focused regression (`3 passed`), full `claude-goal` tests (`373 passed`), Ruff, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2011 | `[llm-wiki/autonomous-loop-completion-boundary]` Added ignored prompt-to-artifact completion-boundary audit artifacts for the LLM Wiki autonomous loop while preserving the current `dirty_worktree_handoff_current` guardrail. The audit maps the user's explicit loop prompt to `9` requirements: `8` complete and `1` intentionally blocked by the active-loop/no-stop condition plus dirty handoff/T-251 boundaries. A/B rejected tracked wiki/code edits under the dirty boundary and adopted handoff-only evidence (`score_delta=0.62`). Verification passed strict LLM Wiki audit (`pass`, `41` pages, `212` sources, unexpected `0`), objective audit, completion audit expected incomplete (`8/9`, blocked `1`), and debug inventory expected-fail gate. No tracked patch was applied to main; scoped authorization is still required before rollup adoption. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2012 | `[claude-goal/json-json-recovery]` Fixed exact `json --json` redundant-flag recovery so direct CLI points to `python3 goal/scripts/claude_goal.py json` while slash canonical/raw forms point to `/goal json`. Verification passed manual before/after probes, focused regression (`3 passed`), full `tests/test_claude_goal.py` (`202 passed`), full `claude-goal` tests (`374 passed`), py_compile/compileall, Ruff, diff-check, graph risk `0.00`, and nested root check. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2020 | `[claude-goal/complete-json-recovery]` Fixed exact `complete --json` misuse recovery so direct CLI points to `python3 goal/scripts/claude_goal.py complete --schema` then `complete --audit-json`, while slash forms point to `/goal complete --schema` then `/goal complete --audit-json` without mutating the active goal. Verification passed manual before/after probes, focused regression (`3 passed`), full `claude-goal` tests (`375 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2013 | `[llm-wiki/current-authorization-menu]` Added ignored current-signature authorization menu artifacts for the LLM Wiki rollup adoption boundary. A/B rejected stale authorization reuse and adopted the current signature menu (`score_delta=0.5467619047619047`); bounded completion audit passed (`5/5`); rollup `git apply --check` still passes at SHA256 `5881090AC6356D8BEE6909173ED2753FB92047FC364A8B52E28AAE1B3F00F21D`; strict LLM Wiki audit passed (`41` pages, `212` sources, unexpected `0`). Long-running objective remains blocked until explicit scoped rollup authorization, explicit push/user push for Actions, and user-owned T-251 reset. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2021 | `[llm-wiki/authorization-artifact-index]` Added ignored current-vs-stale artifact index for the LLM Wiki rollup authorization boundary. It marks `.tmp\llm-wiki-release-evidence-authorization-request.md` and `.tmp\llm-wiki-gap-registry-current.md` as superseded because they record stale signature `90348c64...` / dirty count `19`, while current state is signature `6c721755...` / dirty count `20`. A/B adopted the index (`score_delta=1.8571428571428572`); bounded completion audit passed (`5/5`); rollup `git apply --check` and strict LLM Wiki audit passed. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2030 | `[claude-goal/command-word-objective-recovery]` Fixed command-word objective ambiguity so user-facing slash command unexpected-positional errors now show `Next: ... /goal -- <objective>` for objectives beginning with `complete`, `status`, `contract`, and similar command words, while preserving strict option errors and internal `stop-hook` behavior. Verification passed manual probes, focused regression (`6 passed`), full `claude-goal` tests (`377 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2022 | `[llm-wiki/autonomous-loop-prompt-evidence-map]` Added ignored prompt-to-artifact evidence map artifacts for the LLM Wiki autonomous-loop objective, mapping 0-step orientation, gap selection, external research, A/B comparison, latest reflection, self-verification, cycle report, autonomy, and duplicate/drift prevention to current evidence and blockers. Verification passed JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, strict LLM Wiki audit pass, expected incomplete launch audit, expected-fail debug inventory, and ignore checks. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2031b | `[llm-wiki/unblock-trigger-matrix]` Added ignored trigger-matrix artifacts for the LLM Wiki autonomous-loop boundary, mapping dirty-handoff-only work, explicit scoped rollup authorization, explicit push/user push, reported Supabase T-251 reset, and completion-claim attempts to first commands, required gates, and stop conditions. Verification passed JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, rollup `git apply --check`, strict LLM Wiki audit pass, and ignore checks. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2032 | `[llm-wiki/evidence-freshness-matrix]` Added ignored freshness matrix artifacts for the LLM Wiki autonomous-loop boundary, mapping session orientation, dirty handoff, selector, strict audit, rollup precheck, post-apply gates, release packet, current-head Actions, Hanwoo T-251, and completion audit evidence to invalidation keys and refresh commands. Verification passed JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, rollup `git apply --check`, strict LLM Wiki audit pass, and ignore checks. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2040 | `[claude-goal/option-terminator-help]` Added `/goal -- complete production launch checklist` to top-level slash help and slash set help so command-word objective escape is discoverable before a runtime error. Verification passed manual probes, focused regression (`4 passed`), full `claude-goal` tests (`378 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2042 | `[llm-wiki/evidence-lineage-graph]` Added ignored evidence lineage graph artifacts for the LLM Wiki autonomous-loop boundary, mapping 10 evidence nodes, 20 dependency edges, and 8 anti-proxy stop rules across worktree state, graph state, strict audit, rollup precheck, release packet, current-head Actions, Hanwoo T-251, debug inventory, and bounded completion audits. Verification passed JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, rollup `git apply --check`, and strict LLM Wiki audit pass. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-09 (archived DONE rows beyond the newest 5)

| T-2050 | `[claude-goal/doctor-strict-verifier-help]` Added a `Verifier workflow:` section to direct and slash doctor help so install-health strict JSON artifact generation and `--verify-json` are discoverable before verifier failure. Verification passed manual probes, focused regression (`3 passed`), full `claude-goal` tests (`378 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |
