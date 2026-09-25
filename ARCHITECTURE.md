# Architecture

btclib-benchmarks is a set of scripts run by hand from a checkout, never
installed to an index and never run in CI. This page is its high-level
design: what each part measures, how the two that are not benchmarks stay
uncoupled from the six that are, and what the project depends on to run.
What a user can expect of it in terms of security is the
[assurance case](./ASSURANCE_CASE.md).

## What each script measures

The benchmarks, one question each:

- `scripts/02-btclib-vs-btclib.py` — btclib's libsecp256k1 path against its
  own pure-Python arithmetic
- `scripts/03-libraries.py` — btclib, libsecp256k1 on, against other
  Python bitcoin libraries
- `scripts/04-pure-python.py` — every pure-Python implementation of one
  operation, libsecp256k1 as the reference line
- `scripts/01-libsecp256k1.py` — btclib_secp256k1 against the other
  wrappers of the same C library, and which revision of it each vendors
- `scripts/05-key-reuse.py` — what a verifier pays per signature under a
  key it already has, raw against prepared, on both paths and against
  python-ecdsa's `precompute()`
- `scripts/06-silentpayments.py` — BIP352, which only `btclib_secp256k1`
  implements of every comparand here

`README.md`'s opening list is the same six for a reader deciding whether to
run one. Five import `btclib` and time it against a comparand;
`scripts/01-libsecp256k1.py` times `btclib_secp256k1` against the other
wrappers of `bitcoin-core/secp256k1` and imports no pure-Python arithmetic
to switch off. Every script keeps its timing loops behind a `main()`
guard: importing one builds its fixtures and runs the cross-comparand
assertions beside them, and times nothing, which is what lets
`tests/scripts_import_test.py` import all six under the suite without
spending the minutes a real run costs. `scripts/artifacts.py` is covered
by `tests/artifacts_test.py`, and `scripts/render.py` by nothing, below.

## The shared modules, and why two of them import no benchmark

`src/btclib_benchmarks/` holds four modules, none of them public
(`__all__` is empty in `__init__.py`, and every module name starts with
an underscore):

- **`_inputs.py`** — one pool of keys and messages, derived by sha256 from
  a fixed seed rather than read from a file, and cached under `.inputs/`
  once derivation is paid for. `POOL_SIZE` and `GENERATION` are the two
  constants the whole pool is re-derivable from, in any language with a
  hash.
- **`_vectors.py`** — the vendored BIP340, BIP32, Wycheproof and base58
  vectors, parsed once for `tests/vectors_test.py` and for the fixtures a
  benchmark checks itself against at import.
- **`_provenance.py`** — `describe`, `origin_of`, `artifact_of`: what a
  distribution's `direct_url.json` and `WHEEL` metadata say about where it
  came from, read before any row is trusted.
- **`_results.py`** — the shape of a saved run (`Measurement`, `Ratios`,
  `Timing`) and what a page's own three marked regions hold, shared by
  every benchmark's writer and by `scripts/render.py`'s reader.

`_results.py` and `scripts/render.py` import no benchmark, and that is a
rule three ways rather than one, stated here and enforced by nothing but
review: importing a benchmark script builds
its fixtures and runs every cross-comparand assertion, which is the right
cost for a measurement and the wrong one for rewording a heading. Nothing
derived — a ratio, a savings figure, a sort order — is stored in
`results/<name>.json`; each is computed at render time from the
microseconds beside it, so a number in the JSON is a number a clock
produced. And neither module is covered by the suite's 100% floor: a page
is written by a command a person runs, and putting that behind the suite
is the coupling this split exists to remove — `render-check`
(`.pre-commit-config.yaml`) is what instead asks whether a page still
matches the run it publishes, on every commit, without importing a
benchmark to answer.

## Provenance: which artifact actually ran

A released wheel, a git checkout and an editable install of the same
distribution all satisfy the same requirement and land in the same
`site-packages`; they do not perform alike. `_provenance.origin_of` reads
the `direct_url.json` PEP 610 has an installer write for anything that did
not come from an index, so its absence is the positive statement that a
release answered. `_provenance.artifact_of` goes one layer further for a
comparand that vendors a C library: the `WHEEL` metadata's tags say
whether the wheel was built where it is installed (a bare `linux_*` tag,
which no index serves) or downloaded, because a wheel and an sdist of the
same version need not carry the same libsecp256k1 revision — `secp256k1`
is the case this was written for. `scripts/artifacts.py` prints one line
per comparand from these functions, and every numbered script prints its
own `describe()` block before any timing, so a table is never read without
knowing what produced it.

## The comparands are dependencies, not a benchmark group

`ecdsa`, `pycoin`, `buidl`, `embit`, `python-bitcoinlib`, `coincurve`,
`secp256k1`, `secp256k1lab`, `electrum-ecc` and `starkbank-ecdsa` are
`pyproject.toml`'s direct `dependencies`, resolved by `uv sync --locked`
into this project's own `.venv` alongside `btclib` and
`btclib_secp256k1`. `README.md`'s *Why this is its own repository* is the
reason: measured from inside btclib these would sit in a lock a library
that never imports them still carries, so a Dependabot alert against one
would misname what it is about. Here the relationship runs the other way,
and an alert against a comparand names the package it is actually about.

## What sits outside the scripts

- **`vectors/`** — vendored, static, read by `tests/vectors_test.py` and
  by every benchmark's own fixtures; `vectors/README.md` says where each
  file came from.
- **`results/`** — one JSON and one Markdown page per benchmark, written
  by a person running a script and `scripts/render.py` in turn, never by
  a workflow: `CONTRIBUTING.md`'s *What the suite can and cannot check* is
  why nothing here times anything on a schedule.
- **`.inputs/`** — the derived key and message pool, gitignored, rebuilt
  from `_inputs.SEED` on a machine that has not run a benchmark yet.
- **`results/machine.toml`** — the one line a process may get wrong about
  itself, the machine it ran on, overridden by hand.

## The public surface

Nothing here is imported by another project: `src/btclib_benchmarks/`
ships in the sdist for `check-sdist`, `pyroma` and `twine` to inspect, but
`project.version` names a *state of the benchmarks* rather than a release,
and `CONTRIBUTING.md`'s *A version, and no release* is where that is
argued in full. A reader arrives at a script by running it, not by
importing the package it depends on.
