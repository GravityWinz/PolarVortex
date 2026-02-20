# GitHub CLI Workflow Context

This repo uses the GitHub CLI (`gh`) for issue, branch, commit, and PR workflows. When working on a new request, follow this flow end-to-end.

## Workflow

1. **Create or use the issue**
   - If there is no existing issue, create one with `gh issue create`.
   - If the issue already exists, use its number in all branch/commit/PR references.

2. **Create a feature branch**
   - Base the branch on the default branch (currently `dev`).
   - Use a clear, issue-linked name: `issue/<number>-<short-title>`.

3. **Implement the changes**
   - Work locally as usual.
   - Keep changes scoped to the issue requirements.
   - Post issue comments with progress updates while working.

### Recommended comment cadence
- Post an initial "starting work" comment.
- Post updates at meaningful milestones or if blocked.
- Post a final summary when ready for review.
- Typical cadence is 2-4 comments per issue.

### Comment template
Starting work:
- Status: Starting
- Plan: <short plan in 1-3 bullets>
- ETA: <rough estimate if known>

Progress update:
- Status: In progress
- Completed: <what changed or was finished>
- Next: <next step>
- Blocked: <yes/no + details if yes>

Ready for review:
- Status: Ready for review
- Summary: <what was done>
- Tests: <what you ran or "not run">
- Notes: <risks, follow-ups, or links>

4. **Commit the changes**
   - Commit only completed work for the issue.
   - Use a message that references the issue number (e.g., `#123`).

5. **Create a PR**
   - Push the feature branch.
   - Open a PR with `gh pr create` targeting the default branch.
   - Include a short summary and testing notes.
   - If `gh` requires automation auth, set `GH_TOKEN` in the environment.

6. **Review and testing**
   - The user will review and perform manual testing.
   - If issues are found, the user will update the issue or PR and request fixes.
   - Iterate until the PR is accepted, then close the issue.

## Command Examples

Create issue:
- `gh issue create --title "..." --body "..."`

Comment on issue:
- `gh issue comment <number> --body "..."`

Create branch:
- `git checkout -b issue/123-short-title`

Commit:
- `git add .`
- `git commit -m "Fix: ... (#123)"`

Create PR:
- `git push -u origin issue/123-short-title`
- `gh pr create --title "..." --body "..."`
