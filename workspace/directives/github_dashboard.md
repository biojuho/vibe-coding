# GitHub Dashboard Directive

## Goal

Collect GitHub profile, repository, commit, PR, and language metrics for the workspace dashboard.

## Tools

- `workspace/execution/github_stats.py`
- `workspace/execution/pages/github_dashboard.py`

## Requirements

- `GITHUB_PERSONAL_ACCESS_TOKEN` available in environment

## CLI

```bash
python workspace/execution/github_stats.py user
python workspace/execution/github_stats.py repos
python workspace/execution/github_stats.py commits --days 30
python workspace/execution/github_stats.py prs
python workspace/execution/github_stats.py languages
```
