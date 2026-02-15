# Sync Sprint Status to GitHub Issues

> Custom BMAD task — syncs `sprint-status.yaml` to GitHub Issues using `gh` CLI.
> Designed to run after `/bmad-bmm-sprint-planning` or on-demand to reconcile state.

## Prerequisites

- `gh` CLI authenticated
- Repository has Issues enabled
- `sprint-status.yaml` exists at `{status_file}`

## Task Instructions

<task>

<step n="1" goal="Load sprint-status.yaml and parse current state">
<action>Read the sprint-status.yaml file from the implementation-artifacts directory</action>
<action>Extract all entries from `development_status` section</action>
<action>Categorize each entry as: epic (matches `epic-N`), story (matches `N-N-*`), or retrospective (matches `*-retrospective`)</action>
<action>Store the full inventory with current statuses</action>
</step>

<step n="2" goal="Discover existing GitHub state">
<action>Run `gh label list` to find existing epic labels</action>
<action>Run `gh api repos/{owner}/{repo}/milestones` to find existing milestones</action>
<action>Run `gh issue list --state all --label story --limit 200 --json number,title,state,labels,milestone` to find existing story issues</action>
<action>Build a map of what already exists on GitHub</action>
</step>

<step n="3" goal="Create missing labels">
<action>For each epic in sprint-status.yaml, check if label `epic-N` exists</action>
<action>If missing, create it with `gh label create "epic-N" --color {color} --description "{epic title}"`</action>
<action>Ensure `story` label exists</action>

**Color palette for epic labels:**
- epic-1: `1d76db` (blue)
- epic-2: `0e8a16` (green)
- epic-3: `e99695` (rose)
- epic-4: `f9d0c4` (peach)
- epic-5: `c5def5` (light blue)
- epic-6: `bfdadc` (teal)
- epic-7: `d4c5f9` (lavender)
- epic-8: `fef2c0` (cream)
- epic-9+: `ededed` (gray)
</step>

<step n="4" goal="Create missing milestones">
<action>For each epic, check if a milestone named "Epic N: {title}" exists</action>
<action>If missing, create with `gh api repos/{owner}/{repo}/milestones -f title="Epic N: {title}" -f state="open"`</action>
<action>Map milestone numbers for issue creation</action>
</step>

<step n="5" goal="Create missing issues and sync status">
<action>For each story in sprint-status.yaml:</action>

1. **Check if issue already exists** — match by sprint key in title or body
2. **If missing** — create issue with:
   - Title: `{epic}.{story} {Story Title}` (e.g., "1.1 Build BaseConnector")
   - Labels: `epic-N`, `story`
   - Milestone: "Epic N: {title}"
   - Body: acceptance criteria from epic file if available, plus sprint key
3. **If exists** — sync status:
   - If sprint-status says `done` and issue is open → close the issue
   - If issue is closed and sprint-status says less than `done` → report mismatch (don't reopen automatically)
   - If sprint-status says `backlog` and issue is open → no change needed

**Status mapping (sprint-status.yaml → GitHub Issue):**
| Sprint Status | GitHub State |
|---|---|
| backlog | open |
| ready-for-dev | open |
| in-progress | open |
| review | open |
| done | closed |
</step>

<step n="6" goal="Reverse sync — GitHub → sprint-status.yaml">
<action>For each closed GitHub Issue that has a matching story in sprint-status.yaml:</action>
<action>If the sprint-status entry is NOT `done`, update it to `done`</action>
<action>For each epic where ALL stories are `done`, update epic status to `done`</action>
<action>Save updated sprint-status.yaml if any changes were made</action>
</step>

<step n="7" goal="Report summary">
<action>Display sync results:</action>

```
GitHub Issues Sync Summary
==========================
Labels created:    {n}
Milestones created: {n}
Issues created:    {n}
Issues closed:     {n} (status → done)
Status mismatches: {n} (investigate manually)
YAML updated:      {yes/no}
```
</step>

</task>
