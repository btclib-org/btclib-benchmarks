# Changelog

Every change of a release, in full: what changed, why, and what it cost.
The release notes, which say what a user has to act on, are in
[HISTORY.md][notes]; this file is the record behind them.

[notes]: https://github.com/btclib-org/btclib-benchmarks/blob/main/HISTORY.md

## v2026.9 (work in progress, not released yet)

### The benchmarks

- **The four benchmarks of btclib and btclib_secp256k1 live here**, and
  the comparands with them: `ecdsa`, `pycoin`, `buidl`, `embit`,
  `python-bitcoinlib`, `coincurve`, `secp256k1`, `electrum-ecc`,
  `secp256k1lab`.
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

- **`scripts/libsecp256k1_wrappers.py` is wrapper against wrapper, and
  nothing else.** Its released ancestor, btclib_secp256k1's
  `scripts/benchmark.py` up to v0.8.0.1, timed btclib's pure-Python
  arithmetic beside three bindings of libsecp256k1 — two questions in one
  table, and neither of them answered well. The two pure-Python rows are
  not here: `scripts/pure_python.py` asks what staying in Python costs
  and asks it better, with one reference column, a ratio against btclib's
  own Python path beside it, and every backend forced off rather than one
  switch flipped. What is left is the question the wrapper table is for,
  the boundary crossing, every row of it calling the same C.

  That takes btclib out of the script altogether: the fixtures come from
  `btclib_secp256k1` and `hashlib`, so nothing there reaches into
  btclib's private dispatch, and importing it leaves the bindings on for
  the rest of the process. It also carries the check the other three do,
  in both directions — every row is called at import, and every row is
  called against a message its signature was not made for, a positive
  check alone being unable to tell a correct row from one that answers
  true to whatever it is handed.

- **`electrum-ecc` is a fourth wrapper row**, and the closest comparand
  `btclib_secp256k1` has: it wraps the same library, and wraps it the
  other way, ctypes where the other three use cffi. That is the whole of
  what separates them once the C underneath is the same, which is why
  the row belongs in this table and not in `bitcoin_libraries.py` —
  `electrum-ecc` is not a bitcoin library, and timing it there would
  answer "which binding is faster" in a table about libraries.

- **Every wrapper row says which libsecp256k1 is underneath it**, and
  how the row reaches it. "The same C library" is a claim about the API:
  the four vendor different revisions, and a current build timed against
  a stale one is not the comparison the table looks like. Three of them
  link the library into a cffi extension at build time, where the
  revision cannot be recovered at run time, so each pin is recorded in
  the script against the release it was read from and reported as
  unrecorded for any other — a pin outliving its release would be the
  one figure in that output nothing re-derives.

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

  `electrum-ecc` was checked against that ceiling before being added and
  holds no part of it: it has no wheel on PyPI at all, and what it
  compiles at install time is tagged `py3-none`, the C being reached
  through ctypes rather than linked into an extension. It does ask for
  more of the toolchain than the other two — it runs libsecp256k1's
  `autogen.sh`, so `autoconf`, `automake` and `libtool` — which
  `test.yml` now installs beside `pkg-config`.

- **`pysecp256k1` was looked at as a fifth wrapper and is not one.** The
  name on PyPI belongs to a pure-Python implementation of the curve, not
  to a binding; the cffi wrapper of that name is on GitHub only, and has
  not been touched since 2017. Nothing installable answers to it, so
  there is no row to write.

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
