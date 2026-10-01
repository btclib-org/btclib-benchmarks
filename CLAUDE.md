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

[ARCHITECTURE.md](./ARCHITECTURE.md) is the design: what each script
measures, the shared modules under `src/btclib_benchmarks/`, and why
`render.py` and `_results.py` import no benchmark and are outside the
suite's 100% floor on purpose. Read it before adding a script or touching
the split between measuring and publishing, where breaking any of the
rules it states puts the coupling back.

## The primary checkout is the maintainer's

Never work in it: no edit, no `git add`, no commit, no branch switch, no
rebase, no `git stash` — the hooks fix files in place. The one write
allowed there brings it forward, and only while it is on `main` and
`git status --porcelain` prints nothing; where it is not, stop:

```shell
checkout=<checkout>
```

```shell
git -C "${checkout:?}" pull --ff-only
```

Read it only after that, once this prints one sha twice:

```shell
git -C "${checkout:?}" rev-parse HEAD origin/main
```

A measurement that has to hold at a named revision reads
`git -C "${checkout:?}" show <sha>:<path>` instead.

Every session works in a worktree of its own, from its first edit, named
`wt-<tracker>-<issue>-<repo>-<role>` — `wt-github-255-btclib-writer` for
issue 255 of `btclib-org/.github`'s tracker, worked in `btclib` by a
writer. The environment is created there, with the command `CONTRIBUTING.md`
names under *The environment and the gates*. Every path is written out in
full, `<scratchpad>` being the session's scratch directory:

```shell
git worktree add \
  <scratchpad>/wt-<tracker>-<issue>-<repo>-<role> origin/main -b <branch>
```

Removing it is part of finishing:

```shell
git worktree remove --force <scratchpad>/wt-<tracker>-<issue>-<repo>-<role>
```

`refs/stash` and the local `main` are shared by every worktree: never
`git stash`, and move `main` only by the `git pull --ff-only` above.

## Model

Default model: Sonnet; Opus for design decisions with conflicting constraints.
Do not use Fable unless instructed.

## Non-obvious facts that will otherwise waste a session

- **The comparands are `dependencies`, not a `bench` group**, and that
  inversion is why this repository exists. In btclib and
  btclib_secp256k1 they were third-party packages in the lock of a
  library that never imports them, so an advisory against a comparand
  was an advisory against btclib. Do not "tidy" them into a group.
- **Both ends of the interpreter range are set by a comparand**, not
  chosen. 3.13 is the ceiling: `coincurve` and `secp256k1` publish no
  cp314 wheel, `secp256k1`'s sdist wants `pkg-config`, and `coincurve`'s
  does not build at all, `.python-version`'s comment saying why. 3.11 is the
  floor: `secp256k1lab` declares it and `scripts/04-pure-python.py` imports
  it unguarded. Raising either means checking a package index first.
  `coincurve` and `secp256k1` and no others hold the ceiling: `electrum-ecc`
  is built from an sdist rather than resolved to a wheel, and what it
  builds is `py3-none`, so it installs on any interpreter.
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
  measuring Python. `01-libsecp256k1.py` imports no btclib: a table of
  wrappers has no pure-Python row to switch.
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
- **`artifacts.py` and `render.py` have their `main()` run by something
  other than a manual invocation.** The suite calls
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

## Verifying

Check exit codes, not filtered output. Run the command as documented
before claiming it works — every claim in this file was checked against
the tree, and the tree changes.
