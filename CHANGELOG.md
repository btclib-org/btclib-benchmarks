# Changelog

Every change of a release, in full: what changed, why, and what it cost.
[HISTORY.md](./HISTORY.md) has the release notes, which say what a user
has to act on; this file is the record behind them.

## v2026.9 (work in progress, not released yet)

### The benchmarks

- **The four benchmarks of btclib and btclib_secp256k1 move here**, from
  the `bench` dependency group of each of those two repositories. The
  comparands — `ecdsa`, `pycoin`, `buidl`, `embit`,
  `python-bitcoinlib`, `coincurve`, `secp256k1`, `secp256k1lab` — were
  third-party packages resolved into the lock of a library that never
  imports them, so an advisory against a comparand was an advisory
  against btclib: all four of the Dependabot alerts open there were a
  benchmark row, three of them transitive through `hwi`. Here the
  comparands are what the project is for, and an alert names the package
  it is about.

- **Every benchmark runs behind a `main()` guard.** They were bare
  module-level statements, so importing one ran every timing loop in it
  — which is why nothing could test them. The guard is what lets
  `tests/scripts_import_test.py` import all four and check the thing a
  test can actually check: that they load, and that the assertions
  comparing every comparand against btclib still hold.

  `scripts/libsecp256k1_wrappers.py` needed one more move for the same
  reason: it called `python_arithmetic_only()` at import, which turns
  btclib's dispatch off process-wide. Importing it in a suite would have
  left every later test measuring the Python path.

- **Each benchmark prints where its packages came from** before any
  number, `scripts/_provenance.py` being what answers it. A released
  wheel, a git checkout and an editable install satisfy the same
  requirement and all land in `site-packages`, so the path a module was
  imported from cannot tell them apart — PEP 610's `direct_url.json`
  can, and does. The first version of that file read the path instead
  and labelled a git build of btclib `released`, which is the failure
  this exists to prevent: not an error, a plausible number for a version
  nobody runs.

### Packaging and CI

- **The interpreter is 3.13, where the rest of btclib-org pins 3.14.**
  `coincurve` and `secp256k1` publish wheels up to `cp313` and neither
  builds from source without `pkg-config` and a toolchain, so on 3.14
  the comparands cannot be installed at all. `.python-version` carries
  the condition for raising it.

- **`btclib` resolves from `main` rather than from PyPI**, through
  `[tool.uv.sources]`, and that entry is temporary. What these scripts
  reach into is btclib's dispatch, which is private and moves between
  releases: `grind=` on `dsa.sign_` and the `_libsecp256k1_available`
  switch are both in main and in no published wheel. The floor already
  names `>=2026.9`, so deleting the source entry is the whole of what
  release day costs.

- **No workflow runs a benchmark.** CI lints and type-checks; the
  measuring is done by a person, on a machine whose state they know. A
  shared runner disagrees with a laptop by more than most of the
  differences being reported.
