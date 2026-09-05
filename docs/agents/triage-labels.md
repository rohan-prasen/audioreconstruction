# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual state used in each of this repo's issue trackers (see `issue-tracker.md` for routing).

| Canonical role    | GitHub label      | Linear (project `audioreconstruction`)                    | Meaning                                  |
| ----------------- | ----------------- | --------------------------------------------------------- | ---------------------------------------- |
| `needs-triage`    | `needs-triage`    | status **Backlog** (no label — untouched Backlog = untriaged) | Maintainer needs to evaluate this issue  |
| `needs-info`      | `needs-info`      | status **Backlog** + label `needs-info`                   | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | status **Todo** + label `ready-for-agent`                 | Fully specified, ready for an AFK agent  |
| `ready-for-human` | `ready-for-human` | status **Todo** + label `ready-for-human`                 | Requires human implementation            |
| `wontfix`         | `wontfix`         | status **Canceled**                                       | Will not be actioned                     |

## How to apply on Linear

- **Status** carries the coarse axis: `Backlog` = not actionable, `Todo` = ready to pick up, `Canceled` = dead. Set it via `mcp__linear-server__save_issue` (`state`).
- **Labels** only disambiguate what a single status field can't: `ready-for-agent` vs `ready-for-human` (both live in `Todo`), and `needs-info` (a waiting flavour of `Backlog`). `triage` creates these labels via `save_issue_label` if missing; keep them distinct from the type labels `Feature`/`Bug`/`Improvement`/`Update`/`Test`.
- `In Progress` / `In Review` / `Done` / `Duplicate` are **downstream execution states**, not triage roles — leave them to normal workflow, don't set them during triage.

> Corner cut: Linear's single status field can't express `ready-for-agent` vs `ready-for-human` on its own, so those two ride a label on top of the `Todo` status. If you'd rather split them by two distinct statuses (e.g. add an "Agent Ready" workflow state), add the state in Linear and update the right-hand column.

On GitHub, use the label strings in the second column as-is. Edit either column to match whatever vocabulary you actually use.
