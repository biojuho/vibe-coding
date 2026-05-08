# Directives ↔ Execution 매핑 인덱스

> 각 SOP(지침)가 어떤 실행 스크립트를 호출하는지, 역으로 스크립트가 어떤 SOP에 종속되는지 명시합니다.
> 고아 파일 방지 및 유지보수 추적용.

> Active execution priority comes from `.ai/TASKS.md` and `.ai/HANDOFF.md`; roadmap-style directives are reference context unless they are tied to a live task.

---

## SOP → Execution 매핑

| Directive | Execution Script(s) | 비고 |
|-----------|---------------------|------|
| api_monitoring.md | api_usage_tracker.py, health_check.py | API 사용량 추적 + 헬스체크 |
| code_improvement.md | `code_improver.py`, `_ci_models.py`, `_ci_utils.py`, `_ci_analyzers.py`, `_ci_report.py` | AI 코드 개선 (slim orchestrator + 4 submodules) |
| community_trends.md | community_trend_scraper.py | 커뮤니티 트렌드 스크래핑 |
| daily_report.md | daily_report.py | 일일 보고서 생성 |
| debugging_process.md | error_analyzer.py, debug_history_db.py | 에러 분석 + 디버그 이력 |
| deepseek_ko_bridge.md | language_bridge.py, llm_client.py | 한국어 LLM 브릿지 |
| enhancement_plan_v2.md | *(계획 문서, 직접 매핑 없음)* | 고도화 계획 참조용 |
| finance_tracker.md | finance_db.py | 가계부 DB |
| github_dashboard.md | github_stats.py | GitHub 통계 |
| llm_fallback.md | llm_client.py | 9단계 LLM 폴백 체인 |
| llm_observability_langfuse.md | llm_client.py, llm_metrics.py, projects/blind-to-x/pipeline/draft_providers.py | LLM 호출 셀프호스트 트레이싱 (T-253) |
| llm_eval_promptfoo.md | blind_to_x_eval_extract.py, run_eval_blind_to_x.py | blind-to-x 드래프트 회귀 평가 (T-254) |
| anthropic_prompt_caching.md | llm_client.py, api_usage_tracker.py | Claude prompt caching 비용 절감 (T-255) |
| local_inference.md | local_inference.py, smart_router.py, reasoning_chain.py, reasoning_engine.py, thought_decomposer.py, confidence_verifier.py, benchmark_local.py, graph_engine.py, workers.py, code_evaluator.py, repo_map.py, context_selector.py | 로컬 추론 + 추론/평가 오케스트레이션 |
| mcp_skill_expansion_plan.md | *(계획 문서, 직접 매핑 없음)* | MCP 확장 계획 참조용 |
| notebooklm_ops.md | notebooklm_integration.py, content_writer.py | NotebookLM 운영 |
| notion_integration.md | notion_client.py, notion_shorts_sync.py, notion_article_uploader.py | Notion API 연동 |
| operator_workflow.md | scripts/doctor.py, health_check.py, scripts/quality_gate.py, qaqc_runner.py | Canonical fast/standard/deep operator ladder for the shared control plane |
| process_management.md | process_manager.py, scheduler_engine.py, scheduler_worker.py | 프로세스/스케줄러 관리 |
| pr_triage_orchestrator.md | pr_triage_orchestrator.py, pr_triage_worktree.py | Read-only PR triage orchestration with repo-specific validation |
| pr_triage_worktree.md | pr_triage_worktree.py | Isolated git worktree prep for PR-style validation |
| qa_qc_workflow.md | qaqc_runner.py, qaqc_history_db.py, governance_checks.py | QA/QC 자동화 + control-plane governance |
| vibe_debt_audit.md | vibe_debt_auditor.py, debt_history_db.py | 기술 부채 정량화 + TDR 추이 추적 |
| roadmap_v3.md | *(계획 문서, 직접 매핑 없음)* | v3.0 로드맵 참조용 |
| scheduler.md | scheduler_engine.py, scheduler_worker.py | Windows Task Scheduler 연동 |
| session_workflow.md | *(워크플로우, 직접 매핑 없음)* | AI 세션 워크플로우 |
| security_rotation.md | *(SOP 문서)* → scripts/key_rotation_checker.py | 키 로테이션 절차 |
| system_audit_action_plan.md | *(계획 문서, 직접 매핑 없음)* | 감사 액션 플랜 |
| telegram_notifications.md | telegram_notifier.py | Telegram 알림 |
| local_first_saas_design.md | *(설계 문서, 직접 매핑 없음)* | Local-First SaaS (ADR-013) |
| mcp_resource_profile.md | *(분석 문서, 직접 매핑 없음)* | MCP 서버 리소스 프로파일 |
| project_operations_grade.md | *(정책 문서, 직접 매핑 없음)* | 프로젝트 등급화 정책 |
| watchdog_backup.md | pipeline_watchdog.py, backup_to_onedrive.py, backup_restore_test.py | 감시 + 백업 |
| yt_analytics_to_notion.md | yt_analytics_to_notion.py, youtube_analytics_collector.py | YT→Notion 연동 |

---

## 매핑 없는 Execution 스크립트 (유틸리티/인프라)

| Script | 분류 | 용도 |
|--------|------|------|
| _env_loader.py | utility | 중앙 환경변수 로더 |
| _logging.py | utility | loguru 중앙 로깅 설정 |
| bgm_downloader.py | utility | Pixabay BGM 다운로더 |
| brand_asset_generator.py | utility | 브랜드 에셋 생성 |
| channel_growth_tracker.py | utility | YouTube 채널 성장 추적 |
| content_db.py | utility | 콘텐츠 DB (SQLite) |
| gdrive_pdf_extractor.py | utility | Google Drive PDF 추출 |
| harness_context.py | infrastructure | Context window compaction + oversized tool-output offloading |
| harness_eval.py | infrastructure | Generator-evaluator quality loop for LLM output validation |
| harness_middleware.py | infrastructure | HarnessSession observability + loop detection + budget enforcement |
| harness_sandbox.py | infrastructure | Agent sandbox profiles with Docker/subprocess isolation |
| harness_security_checklist.py | infrastructure | Pre-flight/runtime security validation with secret and path guards |
| harness_tool_registry.py | infrastructure | Agent harness tool allowlist + HITL permission registry |
| joolife_hub.py | entrypoint | Streamlit 메인 허브 |
| lyria_bgm_generator.py | utility | Lyria BGM 생성 |
| pr_self_review.py | utility | AI 기반 PR 셀프 리뷰 |
| result_tracker_db.py | utility | 결과 추적 DB |
| roi_calculator.py | utility | ROI 계산기 |
| selector_validator.py | utility | CSS 셀렉터 검증 |
| shorts_daily_runner.py | entrypoint | Shorts 일일 실행기 |
| topic_auto_generator.py | utility | 토픽 자동 생성 |
| youtube_uploader.py | utility | YouTube 업로드 |

---

*마지막 업데이트: 2026-05-08*
