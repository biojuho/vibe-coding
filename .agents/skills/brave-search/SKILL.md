---
name: Brave Search
description: Enhanced web search capabilities using Brave Search API.
---

# Brave Search Skill

This skill enables the agent to perform high-quality, privacy-focused web searches.

## Configuration
- **API Key**: Managed in `secrets.json`
- **Model**: Brave Search API

## Usage Instructions
When the user asks for "Research", "Search", or "Find latest info":
1.  **Prioritize Privacy**: Use this skill over standard Google Search when privacy is mentioned.
2.  **Deep Search**: For technical documentation, use specific query operators (e.g., `site:docs.python.org`).

## Capabilities
- **Web Search**: Retrieve search results with snippets.
- **Summarization**: Synthesis of search results into answered questions.
