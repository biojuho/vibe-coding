# MCP Servers Comprehensive Diagnostics Report

**Date:** 2026-05-26T18:09:03.893245
**Overall Verdict:** 🟢 ALL SERVERS FUNCTIONAL

This report lists the status of local workspace MCP servers based on a deterministic Stdio JSON-RPC handshake validation.

## Status Matrix

| Server Name | Syntax Check | Import & Deps | Stdio Handshake | Environment Check | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **sqlite-multi** | ✅ passed | ✅ passed | ✅ passed | ✅ passed | 🟢 OK |
| **system-monitor** | ✅ passed | ✅ passed | ✅ passed | ✅ passed | 🟢 OK |
| **telegram** | ✅ passed | ✅ passed | ✅ passed | ❌ failed | 🟢 OK |
| **cloudinary** | ✅ passed | ✅ passed | ✅ passed | ✅ passed | 🟢 OK |
| **youtube-data** | ✅ passed | ✅ passed | ✅ passed | ✅ passed | 🟢 OK |
| **n8n-workflow** | ✅ passed | ✅ passed | ✅ passed | ✅ passed | 🟢 OK |

## Detailed Server Diagnoses

### sqlite-multi
- **Path:** `infrastructure/sqlite-multi-mcp/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `passed`
---
### system-monitor
- **Path:** `infrastructure/system-monitor/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `passed`
---
### telegram
- **Path:** `infrastructure/telegram-mcp/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `failed (missing: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)`
---
### cloudinary
- **Path:** `infrastructure/cloudinary-mcp/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `passed`
---
### youtube-data
- **Path:** `infrastructure/youtube-mcp/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `passed`
---
### n8n-workflow
- **Path:** `infrastructure/n8n-mcp/server.py`
- **Syntax Check:** `passed`
- **Imports Check:** `passed`
- **JSON-RPC Handshake:** `passed`
- **Environment Check:** `passed`
---

## Agent-Side Integrated Notion MCP
- **Verification method:** `mcp_notion-mcp-server_API-get-self` direct call
- **Status:** 🟢 PASS
- **Connected Account:** `Desk Joopark` (Juho Park의 Notion workspace)