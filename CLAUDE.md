# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

Repository configuration — branch protection, required checks, token
permissions — is in `REPOSITORY.md`. Read that before changing a workflow
or a repository setting. Writing a benchmark row does not need it.

## Commands

```shell
uv sync --locked                            # installs the comparands, and
                                            # compiles two of them
uv run pytest                               # the suite, gated at 100%
uv run pre-commit run --all-files           # every lint hook, what CI runs
uv run python scripts/bitcoin_libraries.py  # a benchmark, by hand
```

`CONTRIBUTING.md` carries each of these with its reasoning.

## What this repository is

Four benchmarks, one question each:

- `scripts/btclib_two_paths.py` — btclib's bindings path against its own
  pure-Python arithmetic
- `scripts/bitcoin_libraries.py` — btclib, bindings on, against other
  Python bitcoin libraries
- `scripts/pure_python.py` — every pure-Python implementation of one
  operation, bindings as the reference line
- `scripts/libsecp256k1_wrappers.py` — btclib_secp256k1 against the other
  wrappers of the same C library

`scripts/_provenance.py` is the only module the suite covers, and the
only one that is not a benchmark.

## Non-obvious facts that will otherwise waste a session

- **The comparands are `dependencies`, not a `bench` group**, and that
  inversion is why this repository exists. In btclib and
  btclib_secp256k1 they were third-party packages in the lock of a
  library that never imports them, so an advisory against a comparand
  was an advisory against btclib. Do not "tidy" them into a group.
- **Both ends of the interpreter range are set by a comparand**, not
  chosen. 3.13 is the ceiling: `coincurve` and `secp256k1` publish no
  cp314 wheel and neither builds without `pkg-config`. 3.11 is the
  floor: `secp256k1lab` declares it and `scripts/pure_python.py` imports
  it unguarded. Raising either means checking a package index first.
- **`btclib` resolves from `main`, not PyPI**, through
  `[tool.uv.sources]`, and that entry is temporary. These scripts reach
  into btclib's *dispatch*, which is private and moves between releases.
  The floor already names `>=2026.9`; deleting the source entry the day
  that release lands is the whole of the change.
- **Every timing lives behind `main()`.** Importing a script must run
  its fixtures and its cross-comparand assertions and time nothing —
  that is what makes the suite possible. Two of the scripts also call
  `python_arithmetic_only()`, which turns btclib's dispatch off
  process-wide and cannot be undone: it belongs inside `main()`, after
  every row that is meant to reach the bindings. At module level it
  would leave every later test in the process measuring Python.
- **Coverage measures `_provenance.py` and the suite, and omits the four
  benchmarks** — covering a timing function means running it, and a
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

## Verifying

Check exit codes, not filtered output. Run the command as documented
before claiming it works — every claim in this file was checked against
the tree, and the tree changes.
