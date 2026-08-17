# Changelog

Every change of a release, in full: what changed, why, and what it cost.
The release notes, which say what a user has to act on, are in
[HISTORY.md][notes]; this file is the record behind them.

[notes]: https://github.com/btclib-org/btclib-benchmarks/blob/main/HISTORY.md

## v2026.9 (work in progress, not released yet)

### The benchmarks

- **The four benchmarks of btclib and btclib-secp256k1 live here**, and
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

- **btclib-secp256k1's benchmark is `scripts/01-libsecp256k1.py`
  now**, that repository having shipped one up to v0.8.0.1: it is the
  one of the four with a released ancestor, and the one HISTORY.md tells
  a reader what to do about. The other three have none.

- **`scripts/01-libsecp256k1.py` is wrapper against wrapper, and
  nothing else.** Its released ancestor, btclib-secp256k1's
  `scripts/benchmark.py` up to v0.8.0.1, timed btclib's pure-Python
  arithmetic beside three bindings of libsecp256k1 — two questions in one
  table, and neither of them answered well. The two pure-Python rows are
  not here: `scripts/04-pure-python.py` asks what staying in Python costs
  and asks it better, with one reference column, a ratio against btclib's
  own Python path beside it, and every backend forced off rather than one
  switch flipped. What is left is the question the wrapper table is for,
  the boundary crossing, every row of it calling the same C.

  That takes btclib out of the script altogether: the fixtures come from
  `btclib-secp256k1` and `hashlib`, so nothing there reaches into
  btclib's private dispatch, and importing it leaves the bindings on for
  the rest of the process. It also carries the check the other three do,
  in both directions — every row is called at import, and every row is
  called against a message its signature was not made for, a positive
  check alone being unable to tell a correct row from one that answers
  true to whatever it is handed.

- **`electrum-ecc` is a fourth wrapper row**, and the closest comparand
  `btclib-secp256k1` has: it wraps the same library, and wraps it the
  other way, ctypes where the other three use cffi. That is the whole of
  what separates them once the C underneath is the same, which is why
  the row belongs in this table and not in `03-libraries.py` —
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

- **Every measured package answers the vendored vectors, in the
  configuration it is measured in.** `tests/_data/` carries BIP340's own
  vector file and BIP32's, copied from btclib's vendored copies at a pinned
  commit with the digests published beside them and checked on every run, and
  `tests/vectors_test.py` runs them against every implementation this project
  times — btclib, btclib-secp256k1, coincurve, secp256k1-py, electrum-ecc,
  embit, buidl and secp256k1lab, each in the spelling its API offers.

  The negative cases are why it is worth having. Eight of BIP340's nineteen
  rows are signatures to reproduce and the rest are verifications, the ones
  expecting FALSE being a public key off the curve, an s past the order, an r
  that is not a field element: an implementation that answers true to all of
  them passes a round-trip check and fails this one. A raise counts as a
  rejection, refusing to parse an unusable key being a correct answer
  differently spelled.

  btclib is held to them too, which duplicates its own suite on purpose: it
  is the one package these tables exist to publish, and a benchmark that
  checked every comparand but not its subject would be an odd thing to have
  built. The pure-Python configuration is a subprocess -- `PYCOIN_NATIVE` is
  read when pycoin is imported and btclib's dispatch flag cannot be restored
  -- so the same file runs twice, once per arithmetic. BIP340's four
  variable-length vectors from 2022 divide the packages by API rather than by
  correctness, and which ones can be asked is written down: none of the
  wrappers exposes `schnorrsig_sign_custom`, three of them pass a length
  through to verification.

  Nothing failed. The one wrong answer this project has found stays the one
  the benchmark itself asserts: `python-bitcoinlib`'s bech32m.

- **No timed function checks its own answer.** Rows across all five scripts
  compared what they had just computed against an expected value, inside the
  loop being timed: an equality on bytes, a `verify` whose result was
  asserted, a membership test over a list of recovered keys. Each
  of those is time charged to the comparand that did not spend it, and the
  cost is not even across rows -- comparing DER against DER is not comparing
  two Python integers, and a row whose API returns an object pays for
  serializing it before the comparison can be written at all.

  The checks did not move to nowhere. `tests/vectors_test.py` is where the
  answers are checked, against what the specifications publish rather than
  against a sibling row, and the cross-comparand assertions each script
  still makes now sit where its fixtures are built -- at import, which is
  what the suite runs when it loads the module. What a benchmark measures and
  what a suite asserts had been one thing, and they are two.

  Every published table was re-run, the verification rows moving most.

- **Grinding is represented the same way everywhere, including where that
  means no row.** btclib and embit grind by default and `electrum-ecc`
  offers it, so each has a `grind=False` row beside a row of its default in
  the three benchmarks that compare packages. `02-btclib-vs-btclib.py` has
  none, by the same rule rather than in spite of it: grinding multiplies both
  paths by the same number of attempts, so the ratio the table is read for
  does not move, as measuring it confirmed, and the rows would restate the
  pair above them.

- **The unit is μs, not us.** Four tables printing `us/call` were four
  tables asking a reader to know that `u` was standing in for a character
  the terminal has had for decades. U+03BC and not U+00B5, which is the
  micro sign and would be the obvious pick: ruff calls it ambiguous against
  the Greek letter, NFKC maps one to the other, and this project holds ruff
  to zero findings.

- **The interpreter is not in a script's output.** It belongs to the run
  rather than to the packages, as the machine and the time do, and no script
  can state those either -- so `results/` names all three in the block above
  the output, and printing one of them twice per published file was the only
  thing that came of having it in both.

- **`03-libraries.py` says which libsecp256k1 btclib's row calls**,
  where it used to print `btclib-secp256k1`'s own version number and leave
  the library underneath unnamed. The revision is recorded against the
  release it was read from and printed as unrecorded for any other, the
  library being compiled into a cffi extension where nothing at run time can
  recover it; the extension's file name goes beside it, and so does the
  prebuilt library embit loaded, which is a file name because embit's
  bundled libraries carry no version a caller can read.

  Dropping `btclib-secp256k1` from that block turned pycoin's rows back into
  Python rows, which is the fragility the docstring describes made concrete:
  the import was load-bearing, its side effect being the symbols pycoin's
  ctypes probe finds. It is back, with the reason written beside it.

- **The wrapper table signs as well as verifying, and tweaks a public
  key.** Verification was the whole of it, which left out the operation the
  four APIs differ over most. `electrum-ecc` signs with
  `grind_r_value=False`, it being the only one of the four offering low-r
  grinding: a row that grinds is a multiple of a row that signs once, and
  three of these rows sign once. Three of the four also agree on one
  signature exactly -- libsecp256k1's default nonce is RFC6979, so one key
  and one message give one signature through three APIs, and the fixtures
  check that. `secp256k1-py`'s build agrees on x86-64 and not on aarch64, so
  what every wrapper is held to is the portable claim, that the signature
  verifies; BIP340 is checked against the vector for the three whose API
  takes an aux_rand.

  The last table is BIP32's step and not BIP32: none of the four implements
  derivation, and all four expose the primitive it is built from, a public
  key tweaked by a scalar. `electrum-ecc` has no tweak-add on `ECPubkey`, so
  it reaches the same point as a scalar times the generator plus an
  addition -- two crossings where the others make one.

- **Every table prints microseconds per call.** `02-btclib-vs-btclib.py` had
  been printing seconds per thousand: a unit that changes between
  benchmarks is a unit a reader converts before comparing two of them. Five
  significant digits there, where the quickest row is a few microseconds
  and the slowest four orders above it.

- **`04-pure-python.py` has no reference line and no second ratio.** It was a
  table of Python rows against the bindings, which asked two questions at
  once: what Python costs, which `02-btclib-vs-btclib.py` answers over
  btclib's own two paths, and which Python implementation is quicker, which
  is the one this script is for. So the bindings row is gone, with the
  `btclib-secp256k1` line beside it, and what is left is one ratio against
  whichever row came out fastest. "Pure Python" is said once, in the block
  above the tables, rather than per row -- and the block says what holds
  each row to Python, which is different for each of them and is the part a
  reader could doubt. btclib signs ECDSA in two rows there too, one
  signature and its grinding default.

- **Version numbers appear once per run.** `report_provenance` prints every
  package in the table, comparands included, and the setup block beneath it
  is left with the one thing a version cannot say: which arithmetic the row
  reached, in one vocabulary across every line -- the code that does the
  arithmetic, then the mechanism the row calls it through. A provenance
  line is the version alone unless the origin is one a reader has to act
  on: an index install and the revision `[tool.uv.sources]` pins are what
  the declaration asks for, where `editable:`, `local:` and `sys.path:` say
  the run is measuring something else.

- **`03-libraries.py` no longer times four signatures against one.**
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
  the generator *object* for it, precomputed table and all, so a row
  verifying against that key verified with a table no real key gets and came
  out well under its true cost. python-ecdsa's ECDSA verification row moved
  when the fixture did, and the new number is the correct one. The same key
  would also have made any pure-Python public-key derivation row one ladder
  step rather than a full-width scalar's worth, which is the row nobody had
  added yet.

  `.secrets.baseline` carries the new fixtures as reviewed findings: a
  private key published in a BIP is exactly what a scanner cannot tell from
  a credential, and CONTRIBUTING.md now has the command that records one.

- **`02-btclib-vs-btclib.py` covers every operation that has two paths**,
  where it covered five. `_libsecp256k1_serves` is the
  predicate every dispatch site asks, so which operations qualify is a
  list to read rather than a judgement: public key derivation, point
  parsing, generator multiplication, ECDSA sign/verify/recover, BIP340
  sign/verify, ECDH, bitcoin-message sign/verify, taproot tweaking and
  ElligatorSwift decoding. `commit_nonce` and `pedersen` are dispatched
  too and have no row: anti-exfil signing and Pedersen commitments are
  protocol machinery rather than operations an application performs.

  Its table is sorted on the ratio now rather than on the seconds, that
  being the column it is read for: what an operation costs is a fact about
  the operation, and what its fallback costs is the fact about the two
  paths. Seconds break the tie, so the bindings rows still read fastest
  first among themselves. They are seconds per ten thousand calls to five
  significant digits, where per thousand the quickest row was a run of
  zeros and two digits.

- **BIP32 derivation was a fourteenth row and is not one**, because
  btclib's BIP32 has no pure-Python path: `_prv_key_derivation` calls
  `btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
  `PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
  reason beside the call — BIP32 is defined for secp256k1 and nothing else,
  so no other curve needs a fallback. Throwing the switch left the
  derivation in C and moved only the public key derived for the
  fingerprint, which is why that pair read far narrower than every other. It
  is still timed in
  `03-libraries.py`, where being C is the premise rather than the
  question.

  Reading a ratio off a published table is a poor way to catch that, so
  `tests/pure_python_path_test.py` catches it instead: in a subprocess, it
  replaces every bindings entry point with a function that raises, throws
  the switch, and calls every operation once. A row that has kept a foot in
  C raises instead of answering, and the suite says which call it was. The
  dispatch predicate is deliberately left alone — it is the question rather
  than an answer, and patching it fails every row while proving nothing
  about any of them.

  The pure-Python rows are labelled `_pure_python` now, not `_python`:
  every row in every one of these tables is invoked from Python, and the
  distinction the label is drawing is about the arithmetic underneath.

  Each operation is also one function rather than two with the same body.
  `python_arithmetic_only` is process-wide, so which path a call takes is
  a property of when it runs and not of which function was called; the
  table's two labels are made from the operation's name, and a pair can no
  longer drift apart in the edit that adds a row.

- **pycoin's rows in `03-libraries.py` are sized by the backend they
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
  the order they were written, and only `04-pure-python.py` divided anything,
  so a table of six packages left the comparison it exists for to be done
  by hand — and an order written by hand is an opinion about a result
  rather than the result.

  The reference is the quickest row of the run and not btclib's, which is
  the one row in these tables that cannot be it: a column against btclib
  prints fractions under one for everything faster, which reads as
  btclib's score rather than as the table's answer, and where btclib
  stands is its own place in the order. So `04-pure-python.py`'s two columns
  are against the fastest row and the fastest *Python* row, and
  `02-btclib-vs-btclib.py` divides each row by the quicker of its own pair,
  its rows being one operation through two paths — the fastest row of that
  whole table would divide a signature by a multiplication.
  `01-libsecp256k1.py` prints two decimals where the others print
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
  numbers and naming the machine it ran on. A
  benchmark whose output lives only in a terminal is one nobody can
  compare against, and the alternative — numbers quoted in prose — is the
  thing this project forbids everywhere else. They are a record of one
  run, not a claim about anyone's hardware: nothing there was repeated and
  no outlier was discarded, exactly as the scripts do not.

- **`03-libraries.py` was calling pycoin's row pure Python while it
  ran C.** `_pycoin_backend()` looked for `LibSECP256K1` among the base
  class names of the generator pycoin built, and that name is an alias
  pycoin binds to a class called `Optimizations` — as its OpenSSL module
  also calls its own. So both positive branches were unreachable and every
  run reported the fallback. It reads each base's module now, which is
  what distinguishes them, and the same blind check is repaired in
  `04-pure-python.py`, where `PYCOIN_NATIVE` made the answer right by
  construction and the safety net that was to catch it failing was dead
  code.

  What the fixed probe reports on this machine is C, for two reasons that
  are neither pycoin's nor deliberate: pycoin calls
  `ctypes.util.find_library` having imported only `ctypes`, so unless
  another package imported `ctypes.util` first the lookup raises and
  pycoin's own `except AttributeError` reports it as no library found —
  `bitcoin.core.key`, above it in the same script, imports it — and the
  library name it then asks for resolves to nothing, so the load falls
  through to the symbols `btclib-secp256k1`'s extension has already put in
  the process. Both are properties of the import list, and the script's
  docstring now says so.

- **Wycheproof's ECDSA file and Bitcoin Core's base58 pairs are vendored**,
  beside BIP340's vectors and BIP32's, and every implementation this project
  times is held to both. `vectors/README.md` publishes a digest per file and
  the suite checks it on every run, so a copy that drifts fails a test
  rather than quietly becoming the new question — which is not
  hypothetical: `codespell` and `typos` both corrected `empyt` inside the
  Wycheproof file on the first run, and the digest is what caught it. Both
  now skip `vectors/` for that reason.

  What the two files found is the reason to have them. Wycheproof's is
  adversarial where BIP340's is a specification's own list: pycoin accepts
  a run of signatures it should refuse and buidl a few, all of them a DER
  decoder reading BER long forms, wrong lengths or trailing bytes, plus two
  in buidl where the arithmetic admits an r it should not and rejects a
  valid signature. Core's base58 file catches buidl again, on the empty
  payload its encoder raises for. Every one of those is recorded as an
  expected failure with `xfail_strict` on, so the day a release fixes one
  the suite fails and somebody comes back to the table.

  The low-s cases are *not* recorded as failures, and the distinction
  matters: that file is `EcdsaBitcoinVerify`, and refusing the high s of a
  malleable pair is bitcoin's policy rather than ECDSA's. libsecp256k1
  applies it inside `secp256k1_ecdsa_verify`, so the packages reaching that
  C inherit it and the ones implementing ECDSA themselves answer true —
  both right to a different question, and each asserted as its own.

  RFC6979's file was considered and left out. It publishes NIST curves and
  no secp256k1, that pair being absent from its appendix A.2, so nothing
  this project times could be held to it; the secp256k1 vectors btclib uses
  are five tuples in its test source rather than a file to vendor.

- **A run is saved as data, and the page is rendered from it.** Each
  benchmark writes `results/<name>.json` as it finishes — every number as
  measured, the packages block, and what the run block states — and
  `scripts/render.py` writes `results/<name>.md` from that file, between
  the markers the page carries and touching no word of the prose around
  them. Before this, publishing a run meant a person copying what
  scrolled past into a page and typing the clock and the machine in
  beside it, which made the two things one: rewording a heading cost
  either a fresh measurement, whose numbers are different, or a
  hand-edited block, whose numbers no run ever printed. It is now two
  commands, and the second needs no machine.

  Nothing derived is stored. Ratios, savings, break-evens, the sort and
  the column widths are all computed at render time from the microseconds
  beside them, so a number in the file is a number a clock produced, and
  a mistake in a derived column is fixed without measuring again. The
  widths in particular were hand-set per script and are now taken from
  the labels, one width per page: a comparand with a longer name widens
  the column instead of overflowing a number somebody chose.

  `render.py` imports no benchmark, which is the property that makes it
  cheap — importing one builds every fixture and runs every
  cross-comparand assertion. Neither it nor `scripts/_results.py` is
  under the coverage gate, deliberately: a page is written by a command a
  person runs, and putting the rewording of a heading behind the suite is
  the coupling this split removes. `render.py --check` is what says a
  page still matches the run it publishes.

  `results/machine.toml` overrides the one line a run may get wrong,
  which machine it was taken on. The rest of the run block is taken where
  the run is: the clock, the interpreter, the command, and the chip and
  OS build read from the machine itself.

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

- **REPOSITORY.md documented a merge that could not carry the
  maintainer's signature.** It said the maintainer merges their own pull
  request with `gh pr merge --squash --admin`, which asks GitHub to write
  the commit and sign it with its own web-flow key — the very thing the
  next section but one warns about. What lands is a local squash,
  fast-forwarded onto `main`, and the file now says so beside what
  `enforce_admins: false` actually costs: that push bypasses the required
  checks, the required review and the resolution of review threads, so all
  three are honoured by the procedure rather than by the forge, and the
  procedure is written down instead of remembered. `required_signatures`
  is named with them, as the one whose bypass was not tested and will not
  be: the test is pushing an unsigned commit to `main`, so what holds the
  signature is reading the commit before the push.

  What lands is the branch's *tip*, and a branch of more than one commit is
  squashed and force-pushed before it: GitHub closes a pull request as
  merged when its head ref becomes reachable from the base, not when some
  commit with the same tree does. A squash left behind locally would land
  the change and leave the pull request open.

  Two smaller claims went with it. `delete_branch_on_merge` does not fire
  for a fast-forward push, so a branch left standing is evidence of
  nothing and deleting it is a step someone takes. And issues have a
  second use worth stating: parking a finding noticed while writing or
  reviewing a pull request, so that the pull request stays one subject.

- **CONTRIBUTING.md said everything lands through a pull request and
  nothing about how.** The cadence was unwritten — one subject per pull
  request, opened the moment it is written rather than batched with the
  next or held for the previous one — and so was the review it goes
  through: given promptly on local evidence, anchored to a sha because a
  branch moves under a review, ended by an ack and by nothing else. The
  landing was unwritten too, and it is the half where a mistake is
  expensive: the checks read after the rebase rather than before, the
  squash performed locally, the branch deleted by hand, and the checkouts
  sitting on `main` brought up to date, a stale one being where the next
  branch gets built on a base that has moved.

  Two rules that only look like details went in with it. A finding noticed
  beside the subject becomes an issue instead of riding along in the diff,
  because a diff answering two questions cannot be accepted for either. And
  an issue or a pull request is written `ISS 123` or `PR 45`, as a link,
  disambiguated by `owner/repo` once a second repository is in play: a bare
  `#123` resolves only inside the repository it was written in, and
  resolves to nothing anywhere else.

  The rule carries its one mechanical exemption — a pull request's closing
  keyword is read by the forge, so it takes the forge's own reference — and
  says which side is current where an older page has not caught up.
  [Two such pages][iss68] are named in an issue rather than reworded here,
  a rule and the pages behind it being two subjects.

[iss68]: https://github.com/btclib-org/btclib-benchmarks/issues/68
