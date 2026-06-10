## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2051 | `[llm-wiki/current-head-actions-evidence-playbook]` Added ignored post-push Actions evidence playbook artifacts for the LLM Wiki autonomous-loop boundary, defining exact-head run discovery, watch/view/log/artifact commands, required workflow acceptance criteria, 5 status classes, and 8 proxy-stop rules. Verification passed live exact-head `gh run list` returning no runs, JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, rollup `git apply --check`, strict LLM Wiki audit pass, and ignore checks. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2055 | `[llm-wiki/actions-rerun-cancel-boundary]` Added ignored rerun/cancel authority boundary artifacts for the LLM Wiki autonomous-loop current-head Actions path, defining read-only commands, side-effect commands requiring explicit authorization, 8 status/failure classes, preferred rerun order, job `databaseId` guard, and 10 proxy-stop rules. Verification passed live exact-head `gh run list` returning no runs, JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, rollup `git apply --check`, strict LLM Wiki audit pass, and ignore checks. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2056 | `[llm-wiki/actions-manual-approval-boundary]` Added ignored manual approval/deployment protection boundary artifacts for the LLM Wiki autonomous-loop current-head Actions path, defining pending deployment evidence fields, read-only commands, side-effect commands requiring explicit authorization, 12 manual approval/protection classes, and 11 proxy-stop rules. Verification passed live exact-head `gh run list` returning no runs, JSON parse, A/B `adopt_candidate`, bounded completion audit `5/5`, strict LLM Wiki audit pass, ignore checks, and refreshed dirty handoff plan. Long-running objective remains blocked until explicit authorization/user-owned external events occur. | Codex | 2026-06-09 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2057 | `[claude-goal/help-extra-topic-recovery]` Added context-correct next-step recovery for slash/direct help calls with too many topic tokens, preserving exit `2` while suggesting the exact one-topic help command plus command-list fallback for known topics. Verification passed manual before/after probes, A/B `adopt_candidate`, focused regression (`3 passed`), full `claude-goal` tests (`379 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2059 | `[claude-goal/direct-unknown-command-recovery]` Added direct unknown-command typo suggestions and help fallback before DB-open, so `statuz`/`stats` suggest `status` and generic unknown commands point to direct help without argparse usage noise. Verification passed manual before/after probes, A/B `adopt_candidate`, focused regression (`2 passed`), full `claude-goal` tests (`379 passed`), Ruff, py_compile, diff-check, and graph risk `0.00`. | Codex | 2026-06-09 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2112 | `[auto-research/debug-inventory-evidence-section-lines]` Extracted `_markdown_evidence_freshness_section_lines(...)` from `_append_markdown_evidence_freshness(...)`, naming the evidence freshness Markdown section assembly while preserving empty-section omission, header, rows, and trailing blank line. Verification passed focused debug inventory pytest (`24 passed`), broad auto-research/code-review pytest (`194 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.555556`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2113 | `[auto-research/debug-inventory-completion-blocker-section-lines]` Extracted `_markdown_completion_blocker_section_lines(...)` from `_append_markdown_completion_blockers(...)`, naming the completion blockers Markdown section assembly while preserving empty-section omission, header, rows, and trailing blank line. Verification passed focused debug inventory pytest (`24 passed`), broad auto-research/code-review pytest (`195 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.556128`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2114 | `[auto-research/debug-inventory-expected-gate-section-lines]` Extracted `_markdown_expected_failure_gate_section_lines(...)` from `_append_markdown_expected_failure_gates(...)`, naming the expected nonzero gates Markdown section assembly while preserving empty-section omission, header, rows, and trailing blank line. Verification passed focused debug inventory pytest (`25 passed`), broad auto-research/code-review pytest (`195 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.555556`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2113b | `[auto-research/debug-inventory-json-stdout-emitter]` Extracted `_emit_inventory_json(...)` from `_emit_inventory_output(...)`, naming the JSON stdout branch while preserving ASCII escaping, pretty indenting, and trailing newline behavior. Verification passed focused debug inventory pytest (`25 passed`), broad auto-research/code-review pytest (`195 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.560758`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2115 | `[auto-research/debug-inventory-blocked-notice-lines]` Extracted `_markdown_blocked_notice_lines(...)` from `_append_markdown_blocked_notice(...)`, naming the blocked-debug-loop callout line assembly while preserving zero-blocker omission and existing important-note/highest-priority Markdown output. Verification passed focused debug inventory pytest (`25 passed`), broad auto-research/code-review pytest (`195 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.555556`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2116 | `[auto-research/debug-inventory-markdown-list-lines]` Extracted `_markdown_list_lines(...)` from `_append_markdown_list(...)`, naming the common Markdown list header/row assembly used by Blockers/Reproduction/Expected/Actual while preserving empty-list behavior and displayed value formatting. Verification passed focused debug inventory pytest (`25 passed`), broad auto-research/code-review pytest (`195 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.555556`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2117 | `[auto-research/debug-inventory-markdown-blocker-lines]` Extracted `_markdown_blocker_lines(...)` from `_append_markdown_blockers(...)`, naming the blocker-list versus no-blocker Markdown branch while preserving populated blocker rows and exact `- Blockers: none` output. Verification passed focused debug inventory pytest (`26 passed`), broad auto-research/code-review pytest (`196 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.556125`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2116b | `[auto-research/debug-inventory-markdown-writer-helper]` Extracted `_write_inventory_markdown(...)` from `_write_inventory_outputs(...)`, naming the Markdown parent-directory creation and UTF-8 rendered Markdown write boundary while preserving JSON output behavior. Verification passed focused debug inventory pytest (`26 passed`), broad auto-research/code-review pytest (`196 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, A/B `adopt_candidate` (`score_delta=0.560570`), explicit launch audit, completion audit incomplete (`15` items, `7` complete, `13` issues, `8` blocked), and debug inventory expected exit `1`. | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2118 | `[auto-research/debug-inventory-markdown-action-sections]` Extracted `_markdown_inventory_item_action_sections(...)` from `_markdown_inventory_item_action_lines(...)`, naming the `Root cause` / `Next action` section contract and routing those rows through `_markdown_list_lines(...)` while preserving exact Markdown output. Verification passed focused debug inventory pytest (`26 passed`), broad auto-research/code-review pytest (`196 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.600000`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2119 | `[auto-research/debug-inventory-markdown-item-lines]` Extracted `_markdown_inventory_item_lines(...)` from `_append_markdown_inventory_item(...)`, naming the complete single-inventory-item Markdown assembly while preserving header, blocker, reproduction/expected/actual, root-cause, next-action, and trailing blank-line output. Verification passed focused debug inventory pytest (`26 passed`), broad auto-research/code-review pytest (`196 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.500000`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2120b | `[auto-research/debug-inventory-markdown-summary-details]` Extracted `_markdown_summary_detail_lines(...)` and `_append_markdown_summary_details(...)` from `render_markdown(...)`, naming the blocked notice, completion blockers, expected failure gates, and evidence freshness section assembly while preserving exact Markdown output. Verification passed focused debug inventory pytest (`27 passed`), broad auto-research/code-review pytest (`197 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.714286`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2121 | `[auto-research/debug-inventory-markdown-item-list-lines]` Extracted `_markdown_inventory_item_list_lines(...)` from `_append_markdown_inventory_item_lists(...)`, naming the Reproduction/Expected/Actual line assembly as a pure helper while preserving exact inventory item Markdown output. Verification passed focused debug inventory pytest (`27 passed`), broad auto-research/code-review pytest (`197 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.857143`). | Codex | 2026-06-10 |

## Rotation 2026-06-10 (archived DONE rows beyond the newest 5)

| T-2122b | `[auto-research/debug-inventory-markdown-inventory-items-lines]` Extracted `_markdown_inventory_items_lines(...)` from `_append_markdown_inventory_items(...)`, naming the full inventory-items Markdown assembly as a pure helper while preserving exact item/body Markdown output. Verification passed focused debug inventory pytest (`27 passed`), broad auto-research/code-review pytest (`197 passed`), Ruff check/format, py_compile, diff-check with LF/CRLF warnings only, graph risk `0.00`, and A/B `adopt_candidate` (`score_delta=0.857143`). | Codex | 2026-06-10 |
