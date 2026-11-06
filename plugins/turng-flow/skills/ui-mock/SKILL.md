---
name: ui-mock
description: Make UI mocks on a Design canvas, get the owner's approval before any UI code, and keep approved and pending mocks on separate pages. Use when a task adds or changes screens, tabs, dialogs, or states, and when the owner approves or rejects a mock.
---

# ui-mock

No UI code before the owner approves the mock.

## The canvas
- The project has one Design canvas (Artifact type Design). If it does not exist, create it with the Artifact tool, action `quickstart`, intent `design`.
- It has two pages, named in the owner's language: "Approved" and "Pending".
- Write the canvas link in the task's `TASK_SPEC.md`.

## Layout (both pages)
- Group the mocks by app page, then by feature, then by tab. Each group has one title note above it, on the same page.
- The main screens of a group sit side by side in one horizontal row.
- A variant of a screen (dialog, empty state, error, editing state, confirmation) sits below its main screen, in the same column. Its title starts with "↳".
- States shared by many screens (loading, offline) form their own group.

## Steps
1. Before any UI code, put the new or changed mocks on the Pending page, in the layout above. Do not change the Approved page. Give the owner the link and the names of the artboards that changed, and ask for approval (one item per turn, rule 2).
2. When the owner approves, record the decision with `turng-flow:project-history`. Then move the approved artboards to the Approved page and place each one by the layout above. A changed screen replaces its old artboard. Pending keeps only mocks that are not approved yet.
3. Write a "Mock approved" item in the task's `TASK_SPEC.md`: the canvas link, the artboard names, the decision id. Only then start the code.
4. If the owner approves only part of the mocks, move only that part. The rest stays on Pending with the owner's remarks, and no code is written for it.
5. The code must match the approved mock. If the code needs a screen, state, or message the mock does not show, add it to Pending and get approval first.

## Failure cases
- The canvas cannot be reached or a publish is refused: tell the owner and write no UI code.
- Someone edited the canvas since you read it: read it again before you move or change anything.
- The owner says a task needs no mock: write the owner's words in `TASK_SPEC.md` and continue.
