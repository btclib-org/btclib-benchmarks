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

- **`bitcoin_libraries.py` no longer times four signatures against one.**
  btclib and embit both grind for a low-r signature by default — sign
  repeatedly until r fits in 32 bytes — where python-ecdsa, pycoin, buidl
  and python-bitcoinlib sign once. Each of the two now has a `grind=False`
  row, which is the comparable one, and a row of its default beside it.

  The fixture change is what surfaced it. Grinding costs a fixed number of
  signatures for a fixed key and message, and the key this project used to
  carry wanted two, the expected value; BIP340's vector key wants four, so
  the row that had looked like ordinary overhead turned into a row timing
  four signatures against rows timing one. Both numbers were right and only
  one of them was a comparison.

- **Every fixture is a published test vector**, BIP340's first and BIP32's
  first, transcribed from btclib's vendored copies (`tests/**/_data/`,
  whose own README pins each file to a commit of bitcoin/bips and compares
  the bytes) — the values rather than the files, each script timing one
  input per row.

  The timings do not move for it, which was measured before the change:
  three different valid keys through the bindings land within the noise of
  the machine. The assertions move. Every row used to be checked against
  btclib's answer, so a comparand could only ever disagree with btclib;
  now the public key, the BIP340 signature and the BIP32 child key are
  checked against what the specification publishes, and btclib and a
  comparand being wrong together is a failure instead of a table. Signing
  BIP340 over the vector's aux_rand rather than a random one is what makes
  that possible, and `buidl` and `secp256k1lab` are held to the same
  signature byte for byte. ECDSA keeps only the cross-comparand check:
  RFC6979's nonce is btclib's own and no vendored vector publishes a
  signature over this message.

  The key this project signed with until now was 1, and it flattered a
  published row. Its public key is the generator, and python-ecdsa returns
  the generator *object* for it — precomputed table and all, 259 entries —
  so every row verifying against that key verified with a table no real
  key gets and came out at about half its true cost. python-ecdsa's ECDSA
  verification row is therefore twice what it was, in this benchmark and in
  the pure-Python one, and the number that changed is the one that was
  wrong. The same key would also have made any pure-Python public-key
  derivation row a single ladder step instead of 256 — hundreds of times
  less, measured — which is the row nobody had added yet.

  `.secrets.baseline` carries the new fixtures as reviewed findings: a
  private key published in a BIP is exactly what a scanner cannot tell from
  a credential, and CONTRIBUTING.md now has the command that records one.

- **`btclib_two_paths.py` covers every operation that has two paths**,
  fourteen of them where it had five. `_libsecp256k1_serves` is the
  predicate every dispatch site asks, so which operations qualify is a
  list to read rather than a judgement: public key derivation, point
  parsing, generator multiplication, ECDSA sign/verify/recover, BIP340
  sign/verify, ECDH, bitcoin-message sign/verify, taproot tweaking and
  ElligatorSwift decoding — plus BIP32 derivation, which asks for no
  dispatch of its own and gets one anyway through `curves.sec_point`, and
  is exactly the sort of row that made naming modules by hand untenable.
  `commit_nonce` and `pedersen` are dispatched too and have no row:
  anti-exfil signing and Pedersen commitments are protocol machinery
  rather than operations an application performs.

  The pure-Python rows are labelled `_pure_python` now, not `_python`:
  every row in every one of these tables is invoked from Python, and the
  distinction the label is drawing is about the arithmetic underneath.

  Each operation is also one function rather than two with the same body.
  `python_arithmetic_only` is process-wide, so which path a call takes is
  a property of when it runs and not of which function was called; the
  table's two labels are made from the operation's name, and a pair can no
  longer drift apart in the edit that adds a row.

- **pycoin's rows in `bitcoin_libraries.py` are sized by the backend they
  resolved to.** Their counts were picked when that script's pycoin was
  pure Python, and nobody re-picked them when it turned out to be C: three
  rows ran a couple of hundred calls or fewer beside neighbours running
  tens of thousands, which is a row measuring the clock rather than the
  library. `pycoin_calls` now carries both counts and takes the one the
  probe's answer calls for. One written count cannot be right for both:
  the same call is a few microseconds through libsecp256k1 and several
  milliseconds in Python, and which of the two a machine gets is decided
  by the imports rather than by this project. buidl's counts are small for
  the ordinary reason and stay written — it is pure Python on every machine
  that has not run its separate build step.

- **Every table is sorted fastest row first, with a ratio against its
  fastest row.** Both were previously the reader's job: rows printed in
  the order they were written, and only `pure_python.py` divided anything,
  so a table of six packages left the comparison it exists for to be done
  by hand — and an order written by hand is an opinion about a result
  rather than the result.

  The reference is the quickest row of the run and not btclib's, which is
  the one row in these tables that cannot be it: a column against btclib
  prints fractions under one for everything faster, which reads as
  btclib's score rather than as the table's answer, and where btclib
  stands is its own place in the order. So `pure_python.py`'s two columns
  are against the fastest row and the fastest *Python* row, and
  `btclib_two_paths.py` divides each row by the quicker of its own pair,
  its rows being one operation through two paths — the fastest row of that
  whole table would divide a signature by a multiplication.
  `libsecp256k1_wrappers.py` prints two decimals where the others print
  one, its rows all calling the same C and landing within a few percent
  where one decimal would read 1.0x down the whole column.

  It costs the thing that made a row printable as it was timed: each
  `benchmark` returns microseconds now, and the printing happens once the
  table's numbers are all in hand. In the two scripts that throw
  btclib's dispatch off mid-run that separates two orders that used to be
  one — the bindings rows are still timed before the switch, and the sort
  happens after it.

- **`results/` publishes one run of each benchmark**, linked from
  README.md, each file carrying the header its script printed above the
  numbers and naming the machine and what else was running on it. A
  benchmark whose output lives only in a terminal is one nobody can
  compare against, and the alternative — numbers quoted in prose — is the
  thing this project forbids everywhere else. They are a record of one
  run, not a claim about anyone's hardware: nothing there was repeated and
  no outlier was discarded, exactly as the scripts do not.

- **`bitcoin_libraries.py` was calling pycoin's row pure Python while it
  ran C.** `_pycoin_backend()` looked for `LibSECP256K1` among the base
  class names of the generator pycoin built, and that name is an alias
  pycoin binds to a class called `Optimizations` — as its OpenSSL module
  also calls its own. So both positive branches were unreachable and every
  run reported the fallback. It reads each base's module now, which is
  what distinguishes them, and the same blind check is repaired in
  `pure_python.py`, where `PYCOIN_NATIVE` made the answer right by
  construction and the safety net that was to catch it failing was dead
  code.

  What the fixed probe reports on this machine is C, for two reasons that
  are neither pycoin's nor deliberate: pycoin calls
  `ctypes.util.find_library` having imported only `ctypes`, so unless
  another package imported `ctypes.util` first the lookup raises and
  pycoin's own `except AttributeError` reports it as no library found —
  `bitcoin.core.key`, above it in the same script, imports it — and the
  library name it then asks for resolves to nothing, so the load falls
  through to the symbols `btclib_secp256k1`'s extension has already put in
  the process. Both are properties of the import list, and the script's
  docstring now says so.

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
