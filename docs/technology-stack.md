# Technology Stack Policy

> Workspace-level stack inventory and adoption guide. This file separates
> what is already in use from what is approved as a future option.

## Current Production Stack

| Area | Current standard | Where used |
|---|---|---|
| Frontend web | React, Next.js, JavaScript/TypeScript, TailwindCSS | `projects/hanwoo-dashboard`, `projects/knowledge-dashboard`, `projects/word-chain` |
| Server/BFF | Next.js route handlers/server actions, Python deterministic scripts | `projects/hanwoo-dashboard`, `workspace/`, `projects/blind-to-x`, `projects/shorts-maker-v2` |
| Database | PostgreSQL through Prisma and `@prisma/adapter-pg`; Supabase-compatible URLs | `projects/hanwoo-dashboard` |
| Auth/data platform | Supabase is the preferred managed Postgres/Auth direction for SaaS-style products | `projects/hanwoo-dashboard`, `projects/shorts-maker-v2/docs/v3_saas_design.md` |
| Cache/queue | Redis via `ioredis`, BullMQ for internal async jobs | `projects/hanwoo-dashboard/src/lib/redis.js`, `src/lib/queue.js` |
| Client data loading | Native Fetch API wrapped by local helpers such as `fetchWithTimeout` | `projects/hanwoo-dashboard/src/lib/fetchWithTimeout.js` |

## Approved Candidate Stack

These technologies are acceptable for new work, but only when the project has
an explicit design note and verification path.

| Area | Candidate | Adoption rule |
|---|---|---|
| Frontend web | Svelte/SvelteKit | New standalone app only. Do not mix into existing Next/React apps without a migration plan. |
| Frontend web | TanStack Query | Use only for interactive client lists, mutation invalidation, and cursor pagination. Do not replace simple server-rendered reads. |
| Backend services | Go | Candidate for small high-throughput workers or network services. Keep Python/Next paths for current products unless a bottleneck is proven. |
| Backend services | Rust | Candidate for CPU-bound media/data workers or safety-critical tooling. Requires separate build/test/deploy plan. |
| Mobile | Flutter | Preferred cross-platform mobile option when one shared app is enough. |
| Mobile | Native iOS/Android | Use when platform APIs, performance, or store-specific UX justify separate apps. |
| Messaging | RabbitMQ | Candidate for multi-service routing, delayed delivery, or broker semantics that BullMQ cannot cover. |

## Not Current Defaults

- Java is not part of the current workspace stack.
- Svelte, Go, Rust, Flutter, native mobile, RabbitMQ, and TanStack Query are not installed in active product code today.
- RabbitMQ should not replace Redis/BullMQ while jobs remain internal to `hanwoo-dashboard`.
- TanStack Query should not be added just for ordinary `fetch()` calls; use it when cache invalidation and interactive list state are the actual problem.

## Practical Guidance

1. Existing React/Next projects stay React/Next unless there is a written migration plan.
2. Existing Python pipelines stay Python unless Go/Rust removes a measured bottleneck.
3. PostgreSQL/Supabase remains the default SaaS database path.
4. Redis/BullMQ remains the first queue choice for single-app internal jobs.
5. Fetch API plus local wrappers remains the default request primitive; add TanStack Query only at complex client state boundaries.
