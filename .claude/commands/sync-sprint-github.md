Sync the sprint-status.yaml file to GitHub Issues.

This creates/updates GitHub labels, milestones, and issues to mirror the sprint tracking state. Run this after `/bmad-bmm-sprint-planning` or anytime to reconcile state between the YAML file and GitHub.

**Required context:**
- Sprint status file: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Epic source file: `_bmad-output/planning-artifacts/epic-all.md` (or sharded epics)

**Instructions:**
1. Read the custom sync task at `_bmad/_config/custom/sync-github-issues.md`
2. Read the sprint-status.yaml and epic files
3. Follow the task steps exactly to sync state to GitHub Issues
4. Use `gh` CLI for all GitHub operations
5. Report the sync summary when complete

ARGUMENTS: $ARGUMENTS
