# Contributing to Vibe Coding

First off, thank you for considering contributing to Vibe Coding! 🎵

This document provides guidelines and instructions for contributing. Following these helps maintain quality across the workspace.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style & Linting](#code-style--linting)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Architecture Decisions](#architecture-decisions)
- [Project-Specific Guides](#project-specific-guides)

---

## Code of Conduct

Be respectful, constructive, and inclusive. We're all here to build great products together.

---

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your feature or bugfix
4. **Make changes** following our conventions
5. **Test** your changes thoroughly
6. **Submit a PR** against `main`

---

## Development Setup

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | [python.org](https://python.org) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| uv | Latest | [astral.sh/uv](https://astral.sh/uv) |
| pnpm | 10+ | `npm install -g pnpm` |

### Environment Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/<your-fork>/vibe-coding.git
cd vibe-coding

# 2. Create root venv and install uv
py -3 -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip uv

# 3. Sync all environments
cd workspace && ..\venv\Scripts\uv.exe sync && cd ..
cd projects\blind-to-x && ..\..\venv\Scripts\uv.exe sync && cd ..\..
cd projects\shorts-maker-v2 && ..\..\venv\Scripts\uv.exe sync && cd ..\..

# 4. Install Node dependencies
cd projects\hanwoo-dashboard && pnpm install && cd ..\..

# 5. Copy environment variables
copy .env.example .env
# Edit .env with your API keys
```

### Verify Your Setup

```bash
cd workspace
..\venv\Scripts\uv.exe run scripts\doctor.py
```

---

## Code Style & Linting

We enforce consistent code style across the workspace:

### Python (Ruff)

All Python code is linted and formatted with [Ruff](https://docs.astral.sh/ruff/).

```bash
# Check linting
ruff check .

# Auto-fix
ruff check --fix .

# Format
ruff format .
```

Configuration: [`ruff.toml`](ruff.toml)

### JavaScript / TypeScript (ESLint + Biome)

- **ESLint** for JS/TS linting rules
- **Biome** for formatting (replaces Prettier)

```bash
# Lint
pnpm lint

# Format with Biome
pnpm biome check --write .
```

Configuration: [`biome.json`](biome.json)

### General Rules

- **No `any` types** in TypeScript — use proper typing
- **No unused imports** — Ruff and ESLint will catch these
- **Descriptive variable names** — no single-letter variables except loop indices
- **Docstrings** on all public Python functions
- **Comments** explaining *why*, not *what*

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code refactoring (no feature or fix) |
| `test` | Adding or updating tests |
| `chore` | Build, CI, tooling changes |
| `perf` | Performance improvement |

### Scopes

Use the project name as scope when the change is project-specific:

```
feat(joolife): add cattle weight tracking chart
fix(shorts-maker): handle TTS timeout in edge cases
test(blind-to-x): add coverage for scoring engine
docs(workspace): update architecture diagram
```

### AI Context Commits

When updating shared AI context files:

```
[ai-context] session log update
[ai-context] update HANDOFF for next session
```

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest -q` for Python, `pnpm test` for Node)
- [ ] Linting passes (`ruff check .` / `pnpm lint`)
- [ ] New features include tests
- [ ] Documentation is updated if needed
- [ ] No secrets or API keys in the code

### PR Template

```markdown
## What

Brief description of what this PR does.

## Why

Motivation or issue link.

## How

Key implementation details or design decisions.

## Testing

How you tested the changes.

## Checklist

- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated
- [ ] No breaking changes (or migration documented)
```

### Review Process

1. Create a PR with a clear title following commit conventions
2. Fill out the PR template
3. Automated checks must pass (tests, lint)
4. At least one maintainer review is required
5. Squash and merge to keep history clean

---

## Testing Requirements

### Minimum Standards

- **All new features** must include tests
- **All bug fixes** must include a regression test
- **All tests must pass** before a PR can be merged

### Running Tests

```bash
# Workspace
cd workspace
..\venv\Scripts\uv.exe run pytest -q tests

# Blind-to-X (1,622+ tests)
cd projects\blind-to-x
..\..\venv\Scripts\uv.exe run pytest -q

# Shorts Maker V2 (602+ tests)
cd projects\shorts-maker-v2
..\..\venv\Scripts\uv.exe run pytest -q

# Joolife (282+ tests)
cd projects\hanwoo-dashboard
pnpm test
```

### Test Guidelines

- Use `pytest` for all Python projects
- Use descriptive test names: `test_scoring_engine_returns_zero_for_empty_input`
- Mock external API calls — never hit real APIs in tests
- Keep tests fast — mock I/O-heavy operations
- Group tests logically in `tests/` directories

---

## Architecture Decisions

Significant architecture decisions are tracked in [`.ai/DECISIONS.md`](.ai/DECISIONS.md).

### When to Create a Decision Record

- Adopting a new technology or library
- Changing data models or database schema
- Modifying the 3-layer architecture
- Adding a new project to the workspace
- Changing CI/CD or deployment processes

### Decision Record Format

```markdown
## Decision: [Title]

- **Date:** YYYY-MM-DD
- **Status:** Proposed / Accepted / Deprecated
- **Context:** Why this decision was needed
- **Decision:** What was decided
- **Consequences:** Trade-offs and implications
```

> ⚠️ **Never change existing architecture decisions without discussion.** Propose changes via a PR that updates `.ai/DECISIONS.md`.

---

## Project-Specific Guides

Each project may have additional contributing guidelines:

| Project | README | Notes |
|---------|--------|-------|
| Joolife | [`projects/hanwoo-dashboard/README.md`](projects/hanwoo-dashboard/README.md) | Next.js conventions |
| Shorts Maker V2 | [`projects/shorts-maker-v2/`](projects/shorts-maker-v2/) | Pipeline step patterns |
| Blind-to-X | [`projects/blind-to-x/README.md`](projects/blind-to-x/README.md) | Scraper & scoring engine |

---

## 💬 Communication

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **AI Context**: Check `.ai/HANDOFF.md` for current project status

---

<p align="center">
  <sub>Thank you for helping make Vibe Coding better! 🎵</sub>
</p>
