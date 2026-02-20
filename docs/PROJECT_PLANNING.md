# DBT Miner – Project Planning (GitHub)

This doc defines how we’ll use GitHub **Projects + Issues** to run a high‑throughput build of our dbt‑cloud replacement. Architecture notes live in `docs/planning/`.

## GitHub Project (single source of truth)

Use **one** GitHub Project (v2) for the workstream, and create multiple **views** (instead of multiple Projects).
The active project for this effort is **“Miner 1.0”** (org-level v2 project linked to `aegroup-io/dbt-miner`).

### Recommended Project fields
- `Status`: `Triage` → `Ready` → `In Progress` → `In Review` → `Blocked` → `Done`
- `Component`: `api` | `worker` | `web` | `infra` | `docs`
- `Epic`: link to an Epic issue (or a single-select if you prefer, but links age better)
- `Iteration`: the active 2‑week iteration
- `Dependencies`: `None` | `Upstream` | `Decision` | `External` (keep it lightweight)

We intentionally **do not** track `Priority`, `Effort`, or `Risk` in the Project.

### Suggested Project views
- **Board (by Status)**: the default view
- **By Epic**: group by `Epic`, filtered to non‑Done
- **By Component**: group by `Component`
- **Blocked**: filter `Status = Blocked`
- **Triage**: filter `Status = Triage`

## Work item types

### Epic (issue)
An Epic is a normal GitHub Issue that:
- States the **Outcome**
- Lists **child issues** as a checklist (and/or uses issue relationships)
- Links to any key docs in `docs/planning/`

### Issue (work item)
Issues are the unit of execution (implemented via one or more PRs).

### Pull request
PRs should link to their Issue(s). If a PR is large, split it and keep the Issue as the stable requirements source.

## Labels (minimal set)

Prefer Project fields over labels. Keep labels crisp:
- `type:feature`
- `type:bug`
- `type:spike`
- `type:chore`
- `blocked` (optional)
- `needs-decision` (optional)
- `needs-design` (optional)

## Issue standard (“no fluff” contract)

Every non-trivial issue must be reviewable and executable without tribal knowledge. Use the issue forms in `.github/ISSUE_TEMPLATE/`.

### Required content
- **Outcome**: 1–2 sentences describing what changes when shipped.
- **Requirements**: short, testable bullets (avoid implementation narration).
- **Acceptance criteria**: Given/When/Then bullets, or an equivalent verifiable checklist.
- **Demo/Test plan**: exact steps/commands and expected results.

### Strongly recommended content
- **Non-goals**: what is explicitly out of scope for this Issue.
- **Dependencies / open questions**: anything that can block or change requirements.
- **Agent brief (optional)**: if delegating to agents, include:
  - Target area(s): `api/`, `web/`, `mcp/`, `infra/`
  - Constraints (“do not touch…”, “must not change schema…”, etc.)
  - What success looks like (screens/API responses/log output)

## Definition of Ready
An issue is “Ready” when it has Outcome + Requirements + Acceptance criteria + Demo/Test plan, and any dependencies/open questions are explicit.

## Definition of Done
Done means a human merges the PR.

## Feature → Issue (Miner 1.0)

• Plan (features → epics → issues in “Miner 1.0”)

  1. Project prep (1x)

  - Verify GH auth + project scope (gh auth status, if needed gh auth refresh -s project)
  - Verify “Miner 1.0” exists + fields match PROJECT_PLANNING.md (gh project list, gh project field-list, confirm Status/Component/Epic/Iteration/Dependencies)

  2. Create the Epic issues first (delivery phases)

  - Create 5 epics: [Epic] P0 Foundations, [Epic] P1 Execution MVP, [Epic] P2 IDE-grade, [Epic] P3 Super-DAG + automation, [Epic] P4 Hardening
  - Use template: Feature (Vertical Slice) (.github/ISSUE_TEMPLATE/feature.yml)
  - Each epic includes: Outcome + links to docs/planning/dbtminer-delivery-epics.md and the 3 feature lists + a checklist placeholder for child issues
  - Add each epic to the “Miner 1.0” project at creation time (gh issue create --project "Miner 1.0" …)

  3. Pre-review: “issue-ready” check for every feature
     For each feature file in docs/planning/features_{web,api,worker}/:

  - Decide split strategy: usually 1 feature ⇒ API issue + Worker issue (and UX issue if applicable)
  - Validate we can fill required fields from the target template:
      - All issues: Outcome, Requirements, Acceptance Criteria, Demo/Test plan (per PROJECT_PLANNING.md)
      - API template additionally needs endpoints + contract + errors (.github/ISSUE_TEMPLATE/api.yml)
      - Worker template additionally needs trigger/payload + idempotency + retries/timeouts + failure surfacing (.github/ISSUE_TEMPLATE/worker.yml)
      - If we can’t fill these without guessing → create a Spike issue first (.github/ISSUE_TEMPLATE/spike.yml)

  4. Draft the child issues locally (human pre-review before GH)

  - Generate “issue drafts” (markdown files) for each planned issue, aligned to the chosen template sections
  - Build a mapping table: feature file → (issue titles) → template → Component → Epic(P0–P4) → Dependencies
  - Checkpoint with you: you review scope/splitting + any spikes before I create anything in GitHub

  5. Create GH issues + wire into the Project

  - Create issues from drafts via gh issue create --template "<Template Name>" --body-file <draft> --project "Miner 1.0"
  - Set Project fields for each item:
      - Status=Triage initially
      - Component = api|worker|web|infra|docs
      - Epic = link to the correct phase epic (P0–P4)
      - Dependencies/Iteration where known

  6. Definition-of-Ready gate

  - Only promote to Status=Ready once the issue meets the “no fluff” contract + has an executable demo/test plan; otherwise keep in Triage/Blocked with explicit open questions.

  Template alignment (rules of thumb)

  - Epics: Feature (Vertical Slice)
  - API work: API Change
  - Worker work: Background Worker / Service
  - Web work: UX / Web
  - Unknowns/decisions: Spike (Timeboxed)
