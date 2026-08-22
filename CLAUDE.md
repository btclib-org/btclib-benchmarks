# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

Repository configuration — branch protection, required checks, token
permissions — is in `REPOSITORY.md`. Read that before changing a workflow
or a repository setting. Writing a benchmark row does not need it.

How a change gets from an issue to `main` — one subject per pull request,
opened as soon as it is written, the review it goes through and the
landing, which only needs a valid signature on the commit rather than
the maintainer's own key — is `CONTRIBUTING.md`'s *Pull requests*. Read
it before opening one, and before reviewing one. What a review itself
has to establish, what a finding must contain, and why everything it
notices that the diff is not about becomes an issue rather than a
comment, is `REVIEWING.md` — and `/review` is that file as a command.

## Commands

```shell
uv sync --locked                            # installs the comparands,
                                            # compiling those that need it
uv run pytest                               # the suite, gated at 100%
uv run pre-commit run --all-files           # every lint hook, what CI runs
uv run python scripts/03-libraries.py  # a benchmark, by hand
uv run python scripts/render.py             # the pages, from the saved runs
uv run python scripts/artifacts.py          # which artifact each comparand
                                            # install resolved to
```

`CONTRIBUTING.md` carries each of these with its reasoning.

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

`scripts/_provenance.py`, `scripts/_inputs.py` and `scripts/artifacts.py`
are what the suite covers. `scripts/_results.py` and `scripts/render.py`
are the non-benchmarks besides those, and they are outside the gate on purpose
— see below.

## Measuring and publishing are two commands

A benchmark writes `results/<name>.json`: the numbers as measured, the
packages block, and what the run block states. `scripts/render.py` writes
`results/<name>.md` from that file, replacing only what lies between the
`<!-- run: begin -->`-style markers and leaving every word of prose
alone. So a heading is reworded and re-published without a machine, where
otherwise it costs either a fresh run — different numbers — or an edited
block, whose numbers no run ever printed.

Three rules follow, and breaking any of them puts the coupling back:

- **`render.py` and `_results.py` import no benchmark.** Importing one
  builds its fixtures and runs its cross-comparand assertions.
- **Nothing derived is stored.** Ratios, savings, break-evens and the
  sort are computed at render time from the microseconds beside them, and
  the column widths from the labels. A number in the JSON is a number a
  clock produced.
- **Neither module is covered**, and that is the same decision: a page is
  written by a command a person runs, and putting the rewording of a
  heading behind the suite is the coupling this split removes.
  `render.py --check` is what says a page still matches its run.

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

**Every session works in a worktree**, its own, from the first edit:

```shell
WT=<scratchpad>/wt<issue>
git worktree add -b <branch> "$WT" origin/main
cd "$WT" && uv sync --locked          # a second venv, about a minute
# edit, gate and commit here, then
git push origin HEAD:refs/heads/<branch>
git worktree remove --force "$WT"     # removing it is part of finishing
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

- **The suite, the lint gate and the documentation build are the
  required checks on a pull request**, named by the rule `REPOSITORY.md`
  reads back from the endpoint. So code does not reach a review without
  having passed them or passing them beside it on the same sha, and a
  reviewer may rely on that rather than establishing it again;
  `REVIEWING.md` has what the reliance takes.
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
- **Coverage measures `_provenance.py` and the suite, and omits the
  benchmark scripts** — covering a timing function means running it, and a
  measurement inside CI is a number that means nothing.

## Conventions to match

- **Workflows**: every action pinned to a commit SHA with the tag in a
  trailing comment; `permissions: contents: read` and `timeout-minutes`
  declared; concurrency groups named literally; `persist-credentials:
  false` on checkout; uv commands pass `--locked`, never `--frozen`.
  `actionlint` and `zizmor` stay at zero findings.
- **No workflow runs a benchmark.** CI lints and type-checks. Measuring
  is done by a person on a machine whose state they know.
- **Never state a number in prose** — not a timing, not a ratio, not a
  count of anything. The tables come from running the scripts; a figure
  written anywhere else is a claim nothing re-derives.
- **Prose style is CONTRIBUTING.md's "Documentation and comments"**: why,
  not how it got here, negative results included. Markdown at 80 columns.
- pytest is strict: a warning is an error, an unregistered marker is an
  error, an xfail that passes is a failure.

## What a review of this tree checks that a generic one would not

Each of these is a question, and the document that answers it is named
because that document, and not this one, is where the rule lives.

- Does the diff **restate a measured number** anywhere but where the
  benchmark wrote it? Measuring and rendering are two commands on
  purpose: a benchmark writes the data and `scripts/render.py` writes
  the page from it, so a figure typed into prose is one no rerun
  corrects. `README.md` states the split and `CONTRIBUTING.md` both
  commands.
- Does a change to a benchmark keep it **comparable to what it is
  compared against**? A number is only a result beside the run it is
  read against, and a benchmark edited without its comparands rerun
  produces a table whose rows no longer answer the same question.
- Does the diff **state a count** of anything? `CONTRIBUTING.md` says why
  it must not.
- If the branch was rebased: do `CHANGELOG.md` and `RELEASE_NOTES.md`
  say what the branch meant them to say? They are `merge=union`, so
  they never conflict and a rebase can put back a line the branch had
  removed.
- A new or changed workflow: the conventions in `CLAUDE.md`, and
  `REPOSITORY.md` before any rule or setting is touched. A job added to
  a workflow without a matching entry in branch protection is a check
  the branch rule does not know about.

## Verifying

Check exit codes, not filtered output. Run the command as documented
before claiming it works — every claim in this file was checked against
the tree, and the tree changes.
