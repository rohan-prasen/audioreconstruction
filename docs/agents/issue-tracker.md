# Issue tracker: GitHub + Linear (dual)

This repo tracks work across **two** surfaces. Route by intent:

| Kind of work | Where it lives | Tooling |
| --- | --- | --- |
| Features, planned work, live/in-flight issues, internal tasks | **Linear** — project `audioreconstruction`, team **Tinkerers** (`ENGG`) | Linear MCP tools (`mcp__linear-server__*`) |
| Public/community bug reports, external PRs, security reports | **GitHub** — `rohan-prasen/audioreconstruction` | `gh` CLI |

**Default for the skills:** `to-tickets`, `to-spec`, `triage`, and `wayfinder` write feature/live work to **Linear**. Only fall back to GitHub when the item is explicitly a public/community issue or an external PR (see the GitHub section).

When a request is ambiguous, prefer Linear (it's the source of truth for planned work) and cross-link the GitHub issue if one exists.

---

## Linear (primary — features & live work)

- **Workspace**: `genesislabb`
- **Team**: `Tinkerers` — key `ENGG`, id `2d4405b8-55a1-4b92-b07d-94d20f0440d5`
- **Project**: `audioreconstruction` — id `6f63c4ce-bd0a-4b5b-96b1-7c760b0b19f4`

Always scope new issues to the `audioreconstruction` project and the `Tinkerers` team.

### Conventions (Linear MCP)

- **Create / update an issue**: `mcp__linear-server__save_issue` with `team: "Tinkerers"`, `project: "audioreconstruction"`, a `title`, and markdown `description`. Pass an `id` to update instead of create.
- **Read an issue**: `mcp__linear-server__get_issue`.
- **List / search issues**: `mcp__linear-server__list_issues` filtered by `project: "audioreconstruction"` (add `state`, `label`, `assignee`, `query` as needed).
- **Comment**: `mcp__linear-server__save_comment` (read with `list_comments`).
- **Statuses**: `mcp__linear-server__list_issue_statuses --team Tinkerers` for the workflow states.
- **Labels**: `mcp__linear-server__list_issue_labels --team Tinkerers`. Existing type labels: `Feature`, `Bug`, `Improvement`, `Update`, `Test`. Create new ones with `mcp__linear-server__save_issue_label`.

### Triage on Linear

The five canonical triage roles map onto Linear **statuses** (with two labels where a single status can't express the split) — full table in `triage-labels.md`:

- `needs-triage` → status **Backlog**
- `needs-info` → status **Backlog** + label `needs-info`
- `ready-for-agent` → status **Todo** + label `ready-for-agent`
- `ready-for-human` → status **Todo** + label `ready-for-human`
- `wontfix` → status **Canceled**

Set the status via `mcp__linear-server__save_issue` (`state`); `triage` creates the two labels via `save_issue_label` if missing. Keep those labels distinct from the type labels above (`Feature`/`Bug`/…), which describe *what* the work is, not its triage state. `In Progress`/`In Review`/`Done`/`Duplicate` are downstream execution states — don't set them during triage.

### When a skill says "publish to the issue tracker"

Create a Linear issue in the `audioreconstruction` project (`save_issue`).

### When a skill says "fetch the relevant ticket"

Run `mcp__linear-server__get_issue` (or `list_issues` scoped to the project to find it).

---

## GitHub (public/community issues & external PRs)

Public issues and pull requests for this open-source repo live on GitHub. Use the `gh` CLI.

### Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

### Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

### Cross-linking

When a GitHub community issue becomes planned work, mirror it into Linear (`save_issue`) and drop the Linear URL in a GitHub comment; put the GitHub URL in the Linear issue description. Keep the Linear issue as the source of truth from that point.

## Wayfinding operations

Used by `/wayfinder`. Run wayfinding on **Linear** (the planned-work surface): the **map** is a parent issue in the `audioreconstruction` project holding the Notes / Decisions-so-far / Fog body, with **child** issues as tickets linked via Linear sub-issues / parent relations. Use Linear labels `wayfinder:map` and `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`), Linear blocking relations for dependencies, assignment for claims, and comments + status changes for resolution.
