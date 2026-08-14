# Changelog

Every change of a release, in full: what changed, why, and what it cost.
The release notes, which say what a user has to act on, are in
[HISTORY.md][notes]; this file is the record behind them.

[notes]: https://github.com/btclib-org/btclib-benchmarks/blob/main/HISTORY.md

## v2026.9 (work in progress, not released yet)

### The benchmarks

- **The four benchmarks of btclib and btclib_secp256k1 live here**, and
  the comparands with them: `ecdsa`, `pycoin`, `buidl`, `embit`,
  `python-bitcoinlib`, `coincurve`, `secp256k1`, `secp256k1lab`.
  Measured from inside either library, each of those would be a
  third-party package resolved into the lock of something that never
  imports it, and an advisory against a comparand would be an advisory
  against the library it is compared with — a Dependabot alert whose
  reader has to work out that the package is a benchmark row rather than
  a dependency. Here the comparands are what the project is for, and an
  alert names the package it is about.

- **btclib_secp256k1's benchmark is `scripts/libsecp256k1_wrappers.py`
  now**, that repository having shipped one up to v0.8.0.1: it is the
  one of the four with a released ancestor, and the one HISTORY.md tells
  a reader what to do about. The other three have none.

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
