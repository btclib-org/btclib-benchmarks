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
uv run python scripts/03-libraries.py  # a benchmark, by hand
uv run python scripts/render.py             # the pages, from the saved runs
```

`CONTRIBUTING.md` carries each of these with its reasoning.

## What this repository is

Five benchmarks, one question each:

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

`scripts/_provenance.py` and `scripts/_inputs.py` are the modules the suite
covers. `scripts/_results.py` and `scripts/render.py` are the other two
non-benchmarks, and they are outside the gate on purpose — see below.

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
  Those two comparands and no others hold the ceiling: `electrum-ecc`
  compiles from an sdist on every platform and what it builds is
  `py3-none`, so it installs on any interpreter.
- **`btclib` resolves from `main`, not PyPI**, through
  `[tool.uv.sources]`, and that entry is temporary. These scripts reach
  into btclib's *dispatch*, which is private and moves between releases.
  The floor already names `>=2026.9`; deleting the source entry the day
  that release lands is the whole of the change.
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
  it: three of the four link the library into a cffi extension, where
  nothing at run time can say which revision that was. Each pin is keyed
  by the release it was read from, so an upgraded comparand prints
  `unrecorded` instead of a pin that has quietly stopped being true. Go
  read the new release and put the pin back.
- **Coverage measures `_provenance.py` and the suite, and omits the five
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
