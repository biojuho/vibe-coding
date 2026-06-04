# Karpathy Autoresearch Concepts

Use this reference when adapting Andrej Karpathy's autoresearch idea to product, GitHub, or app-quality work.

## Primary Sources

- Karpathy autoresearch repository: https://github.com/karpathy/autoresearch
- GitHub Copilot cloud agent docs: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent
- GitHub Dependabot automation docs: https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/automating-dependabot-with-github-actions

## Concept Mapping

| Autoresearch concept | Product-improvement equivalent |
| --- | --- |
| Small real training setup | One real project or one production-like user flow |
| Mutable `train.py` | Narrow editable surface: one feature, module, PR, or dependency family |
| Frozen `prepare.py` and constants | Stable fixtures, baseline data, test commands, screenshots, or benchmark inputs |
| `program.md` as agent instructions | Skill, task note, or experiment brief that tells agents how to run the loop |
| Fixed 5-minute training budget | Fixed evaluation budget such as one test suite, one browser flow, or one timed benchmark |
| Scalar `val_bpb` metric | Numeric product metric: pass count, latency, error count, conversion proxy, a11y violations, bundle size |
| Keep/discard loop | Adopt candidate only after gates pass and metrics improve; otherwise revert |

## Design Lessons

Keep the experiment boundary narrow. The point is not "AI changes everything"; the point is a loop where every candidate is compared against the same evaluation harness.

Prefer metrics that are hard to game:

- Real tests over source-string checks
- Browser console/network results over visual guesses
- Latency or error count over subjective "better"
- User-flow completion over screenshot-only evidence

Avoid Goodhart failures. If a candidate improves one metric by deleting functionality, failing hidden workflows, weakening auth, suppressing errors, or reducing coverage, reject it.

Treat platform-specific results as local. A variant that wins on one machine, browser, dependency tree, or data sample may not transfer without broader verification.

## Product Adaptation

For SaaS dashboards, pipelines, and web apps:

1. Select a single workflow, such as login, export, payment, upload, scrape, or dashboard refresh.
2. Record baseline: command output, screenshot, console/network status, and a numeric score.
3. Research current docs for any library or service touched.
4. Implement the candidate.
5. Rerun the exact baseline protocol.
6. Adopt only if gates pass and the candidate improves the weighted score.

For GitHub PR/dependency work:

1. Inventory open PRs and merge states.
2. Prefer patch/minor updates with passing CI and low blast radius.
3. Treat major updates, security-sensitive changes, and blocked PRs as separate experiments.
4. Never mass-merge or auto-approve without branch protection and passing required checks.
