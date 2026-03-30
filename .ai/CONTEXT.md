# Vibe Coding Context

> Local-only workspace. Do not push, pull, or deploy from this repo unless the user explicitly changes that policy.

## Workspace Summary

- Name: `Vibe Coding (Joolife)`
- Purpose: shared AI tooling plus multiple product projects
- Root runtime: Python 3.14, `pytest`, `ruff`, `venv`, `.env`
- Canonical path contract:
  - `workspace/...` for root-owned automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for MCP/services

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Canonical Structure

```text
Vibe coding/
├── .ai/
├── .agents/
├── .claude/
├── .github/
├── .tmp/
├── _archive/
├── infrastructure/
├── projects/
│   ├── blind-to-x/
│   ├── hanwoo-dashboard/
│   ├── knowledge-dashboard/
│   ├── shorts-maker-v2/
│   ├── suika-game-v2/
│   └── word-chain/
├── workspace/
│   ├── directives/
│   ├── execution/
│   │   └── pages/
│   ├── scripts/
│   └── tests/
└── venv/
```

## Current State

> ⚠️ [상태 이전 및 분리 알림]
> - 매일 변동되는 작업 상태(진행 중인 이슈, 테스트 커버리지)
> - 일시적인 버그나 회피 패턴(Minefield)
> - 최신 품질 및 배포 로그 (Quality Notes)
> 
> 해당 내용들은 이제 토큰 최적화를 위해 **`.ai/STATUS.md`** 파일에서 관리됩니다.
> (※ 관련결정사항: [ADR-018 in DECISIONS.md])

## Shared Services

- MCP servers are configured via `.mcp.json` and related files at repo root.
- Telegram bot and other external providers use root `.env`.
- `infrastructure/` remains top-level and is not part of `workspace/`.


