# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working
with code in this repository.

What this project publishes is measurements: `scripts/` holds the
benchmarks, `results/` the run each one saved and the page rendered from
it, and `README.md` is what a reader arrives at. `src/btclib_benchmarks/`
is the one importable package here, installed into this project's own
venv so the suite and the scripts can import it, and released to no
index.

How to work here — what the issue tracker takes, the prose style, and
how a pull request is opened and landed — is `CONTRIBUTING.md`, which is
the same file in every repository of the organization up to its last
section, which is this tree's and holds the environment, the commands
and the gates. Repository configuration is `REPOSITORY.md`: read it
before changing a workflow, a branch rule or a setting. Reviewing is
`REVIEWING.md`, and `/review` is that file as a command; read it before
reviewing a pull request and before opening one, since it is what the
pull request will be answered against.

## Architecture

The benchmarks, one question each:

- `scripts/02-btclib-vs-btclib.py` — btclib's libsecp256k1 path against its own
  pure-Python arithmetic
- `scripts/03-libraries.py` — btclib, libsecp256k1 on, against other
  Python bitcoin libraries
- `scripts/04-pure-python.py` — every pure-Python implementation of one
  operation, libsecp256k1 as the reference line
- `scripts/01-libsecp256k1.py` — btclib_secp256k1 against the other
  wrappers of the same C library, and which revision of it each vendors
- `scripts/05-key-reuse.py` — what a verifier pays per signature under a key
  it already has, raw against prepared, on both paths and against
  python-ecdsa's `precompute()`
- `scripts/06-silentpayments.py` — BIP352, which only `btclib_secp256k1`
  implements of every comparand here

`src/btclib_benchmarks/_provenance.py`, `src/btclib_benchmarks/_inputs.py`,
`src/btclib_benchmarks/_vectors.py` and `scripts/artifacts.py` are what
the suite covers.
`src/btclib_benchmarks/_results.py` and `scripts/render.py` are the
non-benchmarks besides those, and they are outside the gate on purpose —
see below.

Measuring and publishing are two commands, which `CONTRIBUTING.md`
carries. A benchmark writes `results/<name>.json`: the numbers as
measured, the packages block, and what the run block states.
`scripts/render.py` writes `results/<name>.md` from that file, replacing
only what lies between the `<!-- run: begin -->`-style markers and
leaving every word of prose alone. So a heading is reworded and
re-published without a machine, where otherwise it costs either a fresh
run — different numbers — or an edited block, whose numbers no run ever
printed.

Three rules follow, and breaking any of them puts the coupling back:

- **`render.py` and `_results.py` import no benchmark.** Importing one
  builds its fixtures and runs its cross-comparand assertions.
- **Nothing derived is stored.** Ratios, savings, break-evens and the
  sort are computed at render time from the microseconds beside them, and
  the column widths from the labels. A number in the JSON is a number a
  clock produced.
- **Neither module is covered**, and that is the same decision: a page is
  written by a command a person runs, and putting the rewording of a
  heading behind the suite is the coupling this split removes. The
  `render-check` hook is what says a page still matches its run.

`results/machine.toml` overrides the one line a process may get wrong,
which machine ran it.

## The primary checkout is the maintainer's

**Never work in it.** No edit, no `git add`, no commit, no branch switch,
no rebase, no `git stash`, no `pre-commit run` — the hooks fix files in
place. It is the maintainer's window on the tree: whatever is open in
their editor, whatever they have half-staged, and the branch they are
looking at are theirs, and one working tree has one index and one HEAD to
lose. Reading it is fine — `git log`, `git show`, `git diff`, `gh`, and a
`git fetch`, which writes refs and leaves the work tree alone.

**But `git fetch` moves `refs/remotes/origin/main` without moving the work
tree**, so a `grep` or a `Read` against the checkout's files answers for
whenever it was last brought forward, not for now. The read that cannot go
stale is `git show origin/main:<path>`: it answers from the ref `git
fetch` just moved, never from the tree. Where the checkout has to be
current rather than merely readable, a fast-forward of a clean `main`
brings it up:

```shell
git fetch origin && git merge --ff-only origin/main
```

That writes no commit, switches no branch and runs no hook, so it is on
the permitted side of *never work in it*, not an exception to it. Stop if
the checkout is not on `main` or is not clean: that is no longer bringing
it forward.

**Every session works in a worktree**, its own, from the first edit,
named `wt-<tracker>-<issue>-<repo>-<role>` rather than after the issue
alone. `tracker` is the repository whose issue tracker holds the issue:
an issue number is unique only within one tracker, so
`btclib-org/.github#45` and `btclib-org/btclib#45` are different issues
that would otherwise name the same worktree. `issue` is what prevents
the collision that has actually happened — two worktrees of different
work sharing a generic basename in one repository's own `.git`, keyed on
its path's basename. `repo` prevents a different collision, a *path*
one rather than a `.git` one: two repositories each keep their own
`.git/worktrees/<basename>` and cannot collide there, but the workers of
one session share one scratchpad directory, so a session carrying one
issue into several repositories computes the same target path for each
of them, and `git worktree add` refuses a directory that already
exists — or worse, a second worker reads the first one's tree; naming it
this way also sorts every worktree of one issue together. `role` covers
the narrower case of a coder and its reviewer holding a worktree at
once, which the ordinary sequence avoids by each removing its own.

An issue of `btclib-org/.github`'s tracker worked in `btclib` by a coder
names its worktree `wt-github-255-btclib-coder`. `cd "$WT"` is followed
by `uv sync --locked`, a second venv that takes about a minute, and the
editing, the gates and the commits all happen in the worktree before the
push.

```shell
WT=<scratchpad>/wt-<tracker>-<issue>-<repo>-<role>
git worktree add "$WT" origin/main -b <branch>
cd "$WT" && uv sync --locked
# edit, gate and commit here, then
git push origin HEAD:refs/heads/<branch>
```

`-b <branch>` sits after the path and the commit-ish so that the
placeholder ends the command, which is section 9 of the standard's rule.
With the placeholder ahead of `"$WT"` the `>` closing it takes that path
as its target, and a path with no directory at it is a file the paste
creates.

Removing the worktree is part of finishing, and it stands in a block of
its own: the block above ends in a placeholder, and a shell that
discards that line as a parse error reads the next as a fresh command —
which, in one block, is this line against whatever `$WT` already held.

```shell
git worktree remove --force "$WT"
```

The venv is the whole of the cost, and it buys the thing that matters: a
commit cannot contain work that was never in it. Expect `origin/main` to
move while you work, so `git fetch && git rebase origin/main` before
pushing, resolving in favour of *both* sides (their change and yours,
both CHANGELOG.md bullets).

**Never `git stash` in a worktree either: `refs/stash` is shared.** A
worktree isolates files, not refs. The stash is a single ref in the
common `.git`, so `git stash push` pushes onto the same stack every other
session pops from — and on a clean tree it creates nothing, so the `git
stash pop` that follows applies and *drops* whatever another session
shelved. Commit to your own branch instead: a branch is per-worktree in
the way the stash only looks to be. What is already lost is still in the
object store — `git fsck --unreachable` names the commit and `git stash
store <sha>` puts the ref back.

**Do not rewrite `refs/heads/main`, or advance it with work that is not
yours.** `git update-ref`, or a push carrying another session's commits,
leaves every working tree's files alone and moves the base under them, so
their next commit — built on the older copy — reverts what just landed.
Your own branch is what you push, and the pull request is what moves
`main`: CONTRIBUTING.md's *Pull requests* has how a branch under review is
corrected and how it is merged.

## Model

The default model for this repository is Sonnet. Switch to Opus only
for architectural decisions with conflicting constraints -- design
choices with non-obvious trade-offs, refactors with unclear
dependencies, diagnosis where the symptom does not point to the
cause. Use `/model opus` for the session, then switch back to Sonnet.

Do not use Fable unless explicitly instructed.

## Non-obvious facts that will otherwise waste a session

- **The comparands are `dependencies`, not a `bench` group**, and that
  inversion is why this repository exists. In btclib and
  btclib_secp256k1 they were third-party packages in the lock of a
  library that never imports them, so an advisory against a comparand
  was an advisory against btclib. Do not "tidy" them into a group.
- **Both ends of the interpreter range are set by a comparand**, not
  chosen. 3.13 is the ceiling: `coincurve` and `secp256k1` publish no
  cp314 wheel and neither builds without `pkg-config`. 3.11 is the
  floor: `secp256k1lab` declares it and `scripts/04-pure-python.py` imports
  it unguarded. Raising either means checking a package index first.
  `coincurve` and `secp256k1` and no others hold the ceiling: `electrum-ecc`
  compiles from an sdist on every platform and what it builds is
  `py3-none`, so it installs on any interpreter.
- **`os-macos.yml`'s matrix carries one macOS image, not two.** An Intel
  cell is a comparand's build limit, not a choice — that workflow's own
  header is the full explanation.
- **Every timing lives behind `main()`.** Importing a script must run
  its fixtures and its cross-comparand assertions and time nothing —
  that is what makes the suite possible. `02-btclib-vs-btclib.py` and
  `04-pure-python.py` also call `python_arithmetic_only()`, which turns
  btclib's dispatch off process-wide and cannot be undone: it belongs
  inside `main()`, after every row that is meant to reach libsecp256k1.
  At module level it would leave every later test in the process
  measuring Python. `01-libsecp256k1.py` does not import btclib at
  all any more, and that is deliberate — a table of wrappers has no
  pure-Python row to switch for.
- **The wrapper rows carry the libsecp256k1 revision each package
  vendors**, `LIBSECP256K1_PINS` in `01-libsecp256k1.py` holding
  it: most of the wrapper rows link the library into a cffi extension
  (`electrum-ecc` reaches it through ctypes instead), where
  nothing at run time can say which revision that was. Each pin is keyed
  by the build it was read from, so an upgraded comparand prints
  `unrecorded` instead of a pin that has quietly stopped being true. Go
  read the new build and put the pin back.
- **A build is not always a version.** `secp256k1` serves an sdist and
  wheels under one version carrying libsecp256k1 revisions years apart,
  so the version fires no guard when the library moves under it: for that
  row the key is the version and the artifact, `INDEX_WHEELS` recording
  the tags the index serves and `_provenance.built_here` answering the
  other side. A tag in neither set is `unrecorded` rather than a guess.
  Do not key a pin on a version again without checking that the version
  has one artifact.
- **`scripts/` is eight files, and two of them have their `main()`
  run by something other than a manual invocation** — `pyproject.toml`'s
  `[tool.mypy]` comment names all eight. The suite calls
  `artifacts.main()` (`tests/artifacts_test.py`), and the `render-check`
  hook runs `scripts/render.py --check` on every `pre-commit` run, so
  "only a manual run exercises what is under `scripts/`" is false of
  both.
- **Coverage measures `src/btclib_benchmarks/` — `_results.py`
  excepted — and the suite, and omits the benchmark scripts** —
  covering a timing function means running it, and a measurement inside
  CI is a number that means nothing.
- **pytest is strict**: a warning is an error, an unregistered marker is
  an error, and an xfail that passes is a failure. A comparand's release
  that fixes a recorded defect therefore turns the suite red, which is
  what keeps the record current rather than a note nobody re-reads.

## Conventions to match

Section 9 of the standard is the prose style, section 10 is what a
workflow here has to carry, and neither is re-listed in this file, that
section's own *One fact in one place* being the reason.
`CONTRIBUTING.md`'s last section has the environment, the gates and what
a merge waits for; its *Writing a row* has what a benchmark row owes,
including that no number is ever stated in prose; and its *What the
suite can and cannot check* is why no workflow here runs a benchmark.

What is left to this file is what those cannot say, because it is about
a session rather than about the tree: the worktree rule, the model, the
failure modes in the section that names them, and what this tree is.

## Verifying

Check exit codes, not filtered output. Run the command as documented
before claiming it works — every claim in this file was checked against
the tree, and the tree changes.
