# Notion Integration Directive

## Goal

Manage Notion-backed tasks and metadata directly from the workspace hub.

## Tools

- `workspace/execution/notion_client.py`
- `workspace/execution/pages/notion_tasks.py`

## Required Environment

```env
NOTION_API_KEY=ntn_your_integration_token
NOTION_TASK_DATABASE_ID=your_database_id
```

## Optional Overrides

```env
NOTION_TASK_TITLE_PROPERTY=Name
NOTION_TASK_STATUS_PROPERTY=Status
NOTION_TASK_DUE_PROPERTY=Due Date
```
