# Completion Audit

Use this reference before claiming a launch or self-improvement goal is done.

## Required Evidence

Every explicit requirement needs:

- A concrete artifact: file, commit, PR, workflow, screenshot, command, deployed route, or issue.
- Real evidence: current command output, CI status, browser-click result, source inspection, or verified blocker.
- `verified: true` only after the evidence was inspected in the current cycle.
- `coverage: complete` only when the evidence covers the exact requirement, not just a proxy.

## Manifest Shape

```json
{
  "objective": "Ship the product",
  "success_criteria": ["Each requirement has current evidence"],
  "items": [
    {
      "requirement": "Inventory GitHub projects",
      "artifacts": ["projects/hanwoo-dashboard", ".github/workflows/root-quality-gate.yml"],
      "evidence": ["github_project_inventory.py --include-prs returned open_prs.count=0"],
      "verified": true,
      "coverage": "complete",
      "blockers": []
    }
  ]
}
```

Run:

```bash
python .agents/skills/auto-research/scripts/completion_audit.py .tmp/completion-audit.json --json
```

An incomplete result means the goal is not done. Continue the next experiment or record the blocker.
