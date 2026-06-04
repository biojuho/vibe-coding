# Auto Research Loop Contract

Use this as the minimum contract for one self-improvement cycle.

## Experiment Brief

```text
Project:
Hypothesis:
Editable surface:
Frozen inputs:
Baseline command(s):
Candidate command(s):
Browser/app-click flow:
Primary metric:
Secondary metrics:
Required gates:
Stop condition:
Commit/push policy:
```

## Evidence Manifest

Record evidence before deciding:

```json
{
  "project": "projects/example",
  "hypothesis": "Candidate reduces dashboard load errors",
  "baseline": {
    "label": "main-before-cycle",
    "commands": ["npm test", "npm run build"],
    "metrics": {
      "tests_passed": 100,
      "console_errors": 3,
      "load_ms": 1250
    }
  },
  "candidate": {
    "label": "auto-research-cycle-1",
    "commands": ["npm test", "npm run build"],
    "metrics": {
      "tests_passed": 100,
      "console_errors": 0,
      "load_ms": 1180
    }
  },
  "directions": {
    "tests_passed": "higher",
    "console_errors": "lower",
    "load_ms": "lower"
  },
  "weights": {
    "tests_passed": 1,
    "console_errors": 3,
    "load_ms": 1
  },
  "required_gates": ["tests", "build", "browser_smoke"],
  "gates": {
    "candidate": {
      "tests": true,
      "build": true,
      "browser_smoke": true
    }
  },
  "min_delta": 0.01
}
```

## Adoption Gate

Adopt only when all are true:

- Candidate required gates are true.
- Candidate score beats baseline by `min_delta`.
- No critical regression is observed in logs, screenshots, auth, privacy, or data integrity.
- The diff is scoped to the experiment.
- Any live cost, credential, deployment, or push action is authorized.

Reject or open a follow-up when evidence is incomplete, inconclusive, or externally blocked.

## Browser/App-Click QA

For a web UI, verify at least:

- First viewport renders without blank areas.
- Primary navigation works.
- Main create/edit/delete or submit flow is exercised when safe.
- Console has no new errors.
- Network failures are expected or documented.
- Mobile and desktop layout do not overlap or hide controls.

Use screenshots as evidence, not as the only gate.

## GitHub PR Triage

Classify PRs before acting:

| Class | Action |
| --- | --- |
| Patch/minor dependency with green CI | Candidate for auto-merge experiment |
| Major dependency | Separate upgrade experiment with focused tests and changelog review |
| Blocked merge state | Inspect required checks, branch protection, or conflicts first |
| Security-sensitive dependency | Prefer official advisory/changelog and broad tests |
| Stale PR | Rebase/update only after checking worktree and branch ownership |

Never merge, approve, or push unrelated work just because it appears in the same backlog.
