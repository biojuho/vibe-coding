# Infrastructure (인프라구조)

🇬🇧 This directory contains the core infrastructure for the Vibe Coding workspace.
🇰🇷 이 디렉터리는 Vibe Coding 워크스페이스를 위한 핵심 인프라 구성을 포함하고 있습니다.

## 🛠️ Management Tools (관리 도구)

### 🇬🇧 MCP Manager / 🇰🇷 MCP 관리자 (`scripts/mcp-manager.py`)
🇬🇧 Manage Model Context Protocol (MCP) servers.
🇰🇷 Model Context Protocol (MCP) 서버를 관리합니다.

```bash
# 🇬🇧 Create a new Python MCP server / 🇰🇷 새로운 Python MCP 서버 생성
python infrastructure/scripts/mcp-manager.py new my-server --lang python

# 🇬🇧 Create a new TypeScript MCP server / 🇰🇷 새로운 TypeScript MCP 서버 생성
python infrastructure/scripts/mcp-manager.py new my-server --lang ts
```

### 🇬🇧 Skill Manager / 🇰🇷 스킬 관리자 (`scripts/skill-manager.py`)
🇬🇧 Manage Vibe Coding skills.
🇰🇷 Vibe Coding 기반 스킬들을 관리합니다.

```bash
# 🇬🇧 Create a new skill template / 🇰🇷 새로운 스킬 템플릿 생성
python infrastructure/scripts/skill-manager.py new my-skill

# 🇬🇧 Validate a skill structure / 🇰🇷 스킬 구조 검증
python infrastructure/scripts/skill-manager.py validate .agents/skills/my-skill
```

## 📦 Components (구성 요소)

- **github-mcp**: 🇬🇧 MCP server for GitHub integration. / 🇰🇷 GitHub 연동을 위한 MCP 서버.
- **notebooklm-mcp**: 🇬🇧 MCP server for NotebookLM integration. / 🇰🇷 NotebookLM 연동을 위한 MCP 서버.
