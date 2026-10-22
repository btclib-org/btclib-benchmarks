# Working in this repository

Read `CONTRIBUTING.md` for contribution rules and local gates,
`REVIEWING.md` before opening or reviewing a pull request,
`REPOSITORY.md` before changing repository settings, and
`ARCHITECTURE.md` before changing benchmark structure.

Use a separate worktree for each task. Keep the primary checkout clean and
on `main`; do not switch branches or stash there. See `CONTRIBUTING.md`'s
*Worktrees* section for setup and cleanup.

Choose the least capable model that can reliably complete the task: use
a fast model for straightforward execution, a reasoning-focused model
for multi-step work, and the most capable available model for difficult
or ambiguous problems. Increase capability if progress stalls.
