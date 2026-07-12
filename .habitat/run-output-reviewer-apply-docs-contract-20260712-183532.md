# Habitat reviewer — apply-docs-contract

_run_id reviewer-apply-docs-contract-20260712-183532 · verdict ok · 2026-07-12T18:36:33Z_

---

I've reviewed the situation. Here's my finding as the **reviewer** agent.

## Verdict: ⛔ Cannot review — no builder diff exists

The branch `habitat/reviewer/apply-docs-contract` is **byte-identical to `main`**:

- `git rev-list --count main..HEAD` → `0` (no commits)
- `git status` → clean (no staged/unstaged changes)
- `git diff main HEAD` → identical

There is no diff to judge. The builder has not yet implemented the change, so `docs/` is still the original Hugo site (`docs/content/docs/*.md`, `hugo.yaml`, `go.mod`, `go.sum`), not the Diátaxis-light contract structure.

## Why I'm not making changes

My role (`.claude/agents/reviewer.md`) is **read-only**: "You do not fix; you issue **PASS or FAIL**." My toolset is Read/Bash/Grep/Glob — no Edit/Write. Applying the docs-contract migration is the **builder's** job (task 2.1–2.4). Doing it here would violate the role separation this habitat is built around, so I'm deliberately not touching `docs/` or `.mcp.json`.

## What a review *would* check (for when the builder's diff lands)

Against the reviewer checklist, noting the current repo state:

1. **Scope** — diff must implement tasks 2.1–3.1 and nothing else.
2. **Contract** — ⚠️ *currently failing*: only `index.md` + `how-to/` + `reference/` + `explanation/` may carry markdown; today `docs/content/docs/` and `docs/pipeline/` still hold markdown. Every page needs front matter with `status` + `last_reviewed`, **no `owner`**, Dutch only.
3. **Cage** — ✅ intact right now: no changes to `CLAUDE.md` (none exists in repo), `.claude/agents/`, or CI. This is a HARD FAIL trigger to watch on the real diff.
4. **Secrets** — ✅ nothing in scope; `.mcp.json` correctly holds the `TODO-change-3` placeholder, not a real URL.

## Recommendation

Hand this change to the **builder** agent to perform the migration and open the PR (`docs: apply handbook docs contract`). Once that diff exists, re-invoke me and I'll issue a real PASS/FAIL tied to file and line.

Want me to re-run the review against a specific builder branch/PR, or is the intent that a builder produces the diff first?
