# Changelog

Every change of a release, in full: what changed, why, and what it cost.
The release notes, which say what a user has to act on, are in
[RELEASE_NOTES.md][notes]; this file is the record behind them.

[notes]: https://github.com/btclib-org/btclib-benchmarks/blob/main/RELEASE_NOTES.md

## v2026.9 (work in progress, not released yet)

### A tag-integrity ruleset enforces signed tags org-wide

- **`tag-integrity`, `target: tag`, `refs/tags/v*`: `required_signatures`,
  no bypass actor.** This repository has no release to gate — RELEASING.md
  says as much, "there is no release" — so unlike the sibling
  repositories that publish to PyPI on a tag push, there was no
  publish-authorizing artifact at stake. What was at stake is
  consistency: RELEASING.md's tagging step already says "Signed, as
  every tag in this org is", and the ruleset now enforces that uniformly
  rather than leaving it to be remembered by hand. No `deletion` or
  `non_fast_forward` rule, matching the sibling repositories. Created
  directly by the maintainer, a live repository-infrastructure change
  rather than a pull-request review — this entry documents it. Sibling
  repository btclib filed the same question as issue
  [btclib#1022](https://github.com/btclib-org/btclib/issues/1022).

### Claude reads a pull request against REVIEWING.md

- **`claude-review.yml`**, two jobs: one on every non-draft pull request,
  whose prompt names `REVIEWING.md` rather than restating it, so the
  standard moves without the workflow being edited; one answering
  `@claude` in a comment, carrying no prompt of ours on purpose — the
  action reads the comment that triggered it. It gates nothing and must
  not: `main`'s required contexts are named outside the repository, and
  a review that held a merge would make a model's judgement a branch
  rule. It does not re-run the gates, `test.yml` and `lint.yml` running
  them beside it on the same sha — the two workflows this repository
  has, which is why the prompt names those two and not the three btclib
  names.

  Three things it refuses to do silently, each measured in btclib before
  being asked not to. Without `CLAUDE_CODE_OAUTH_TOKEN` the action
  reviews nothing and reports **success**. Without `id-token: write` it
  dies before authentication, the action minting a GitHub OIDC token at
  startup whatever the Anthropic credential is. And it refuses to run at
  all when the workflow file differs from the copy on the default
  branch — a pull request must not be able to edit the workflow holding
  the credential — reporting that refusal by skipping, green. It fails
  on an empty secret and on an empty `execution_file`, which is exactly
  when no review was written. On a pull request that adds or edits this
  file the job is therefore red until the change is on `main`.

  The automatic job skips a pull request from a fork, which is not a
  policy but what secrets do: none but `GITHUB_TOKEN` reaches a runner a
  fork triggered. `@claude` in a comment still answers there, and is
  also how a pull request that needs no push asks for a review:
  `issue_comment` is a base-repository event and fires on its own.

### Landing and review

- **The pull request is the only way into `main`, and the button is the
  landing.** `CONTRIBUTING.md` had "a local squash fast-forwarded onto
  `main`, never a button on the forge", and `REPOSITORY.md` the push
  that went with it, the branch left standing because a fast-forward is
  not a merge the forge cleans up after, and auto-merge "allowed and
  unused". The `main-self-merge` bypass is in `pull_request` mode across
  the organization, so it excuses the approving review one maintainer
  cannot produce and excuses nothing else: a direct push is refused for
  everyone, the holder included. The ruleset also names `squash` as the
  only merge method it accepts. `REPOSITORY.md` documented neither
  ruleset before and documents both now, the bypass mode being the fact
  the rest hangs on.

- **`REVIEWING.md` is the standard a review is written against**, the
  reviewer's half of `CONTRIBUTING.md`: what a review establishes before
  it gives an ack, what a finding must contain and how it labels its
  severity, and what becomes of everything a reviewer notices that the
  diff is not about — every collateral finding is filed as an issue
  rather than asked for in a comment. Named from `CONTRIBUTING.md`, the
  README and `CLAUDE.md`, a page of the documentation beside
  `contributing`, and `.claude/commands/review.md` as the `/review`
  command. The body is deliberately the text btclib carries, one section
  excepted: the questions a review of *this* tree asks, which are about
  a measured number restated where no rerun corrects it.

### The benchmarks

- **Pages 02, 03 and 04 stop describing their own checked/noverify rows as
  a future run's work.** [ISS 23][iss23], [ISS 28][iss28], [ISS 53][iss53]
  and [ISS 55][iss55] each ended in a run, and that run is in the refresh
  above — the rows already state both flags of the check. The prose beside
  them did not catch up: "the next run will", "the run all three wait
  for", "measured before ... had a check" all stayed true in wording after
  they had stopped being true in fact, because `render.py` replaces only
  the marked blocks and a run cannot rewrite the words around them.
  Rewritten to match what is already published; no numbers moved.

  Page 01's own aside about page 03 still printing `spread` goes with it —
  page 03 prints `halves` now, like every other page that has moved to the
  statistic the wrappers page introduced.

- **The wrappers page's three exclusive tables and all of Silent
  Payments are published.** Both were prose with no numbers below them:
  `results/01-libsecp256k1.md`'s "What only one of the four offers" and
  the whole of `results/06-silentpayments.md` each said so explicitly,
  a rendered region being filled from a saved run and neither having had
  one yet. This is that run — `render.py` fills the regions the pull
  requests that wrote the prose already opened for them, so nothing
  below either heading is worded differently, only no longer empty.

  `LIBSECP256K1_PINS` moves to the `btclib-secp256k1` commit this run
  measured. The pin is keyed to the build it was read from and prints
  `unrecorded` for any other rather than repeat one that has quietly
  stopped being true, and the run that found `unrecorded` is what read
  the new build and put the pin back — the library underneath it is
  unchanged, still v0.8.0.

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

- **Signing is asked twice in each scheme, the second time under a key the
  caller is already holding.** Every signing row priced a first signature
  under a fresh key, and that is the one shape a signing service never runs:
  it signs again under a key it kept. So each scheme carries a pair, the
  held table handed the object its own package offers a caller who will sign
  again -- coincurve's and secp256k1-py's `PrivateKey`, electrum-ecc's
  `ECPrivkey`, btclib-secp256k1's `ssa.Signer` -- built in the fixtures from
  the keys the fresh table signs with once, in that table's order. Which is
  the one place a row is handed anything, and it is a measurement rather than
  a shortcut: the question is asked of every package at once.

  The two pairs answer different things, which is why the script times both.
  What a held object stands in for in BIP340 is a keypair, and an API's shape
  does not say whether a caller got one: two of the four keep a keypair
  across calls, and two build one inside every call however long the object
  they were reached through has been alive. ECDSA takes the secret key as it
  is, so there is no keypair to keep and what the pair prices is a
  constructor with nothing in it the signature reads -- a public key, an
  x-only key, a keypair, each derived because the object exists rather than
  because a signature needs it. btclib-secp256k1 is `NA` in the ECDSA half,
  its signing call taking the 32 octets a caller already has, and the `NA` is
  the finding rather than a gap.

  `tests/wrappers_test.py` holds both pairs to the same equality, each
  package against itself and signed twice through one object: the two tables
  are a subtraction only while the held call answers the octets the fresh one
  answers, and an object accumulating state across calls would price
  something other than a signature from its second call on.

  Both pairs are on the published page, the ECDSA one from the run after its
  rows landed: a table reaches a page from a run, and a run is a person's on a
  machine whose state they know. What that pair prices is read out beside it
  there — more of a fresh-key row is the construction than is the signature,
  and what is left once the construction goes is one cost three of the four
  wrappers share, which is the page's own premise measured rather than
  asserted.

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

- **The dispersion column is headed by the statistic under it.** Two
  keys were already two statistics — `01-libsecp256k1.py` saves
  `halves_apart`, the distance between the minima of two halves of a
  row's rounds, and `03-libraries.py` saves `spread`, the slowest round
  less the quickest — and both printed under one word. Each page defines
  its own column in the prose beside its tables, so no reader of one page
  was misled; a reader comparing the two met the heading before either
  paragraph. `_results.py` now takes the word from the field the rows
  carry, which is row knowledge and leaves that module still unable to
  tell one page from another. `halves` and not `halves_apart`, the column
  being sized by the values under it and the key being wider than they
  are.

  The wrappers page regenerated from the run already saved, no
  measurement taken, which is what the split between measuring and
  publishing is for. The paragraph that explains how to read the column
  moved with the heading, and it is the larger half of the change.

- **`render.py --check` says what the script produces and the run does
  not.** It answers one question, whether a page matches the run saved
  beside it, and was read as answering a second, whether the page
  describes the benchmark that exists — the same question only while the
  saved run is as new as the script. Both drifts are ordinary states here
  and neither had a name: a person coming back to a page could not tell
  one measured before a table existed from one whose script has moved on.
  The check now names the tables each side has and the other has not, in
  both directions, as lines of its output.

  Not a failure, and not a gate on a measurement, which is the coupling
  this repository split apart on purpose. The titles are read out of the
  script's `TABLES` with `ast` and never by importing it — importing a
  benchmark builds its fixtures and runs its cross-comparand assertions,
  which is the price this module exists not to pay. Two of the five build
  their tables inside `main()`, where no literal says what the titles are,
  and those two get no comparison rather than a wrong one.

- **Two published pages spell a reference the way the guide asks.**
  `results/05-key-reuse.md` carried `btclib-org/btclib#893` and
  `results/01-libsecp256k1.md` a bare `#23`, both predating the rule that
  an issue is `ISS 123`, disambiguated by `owner/repo` once a second
  repository is in play. Both lines are prose outside the `run:` markers,
  so no measurement was involved and `render.py --check` stayed green
  throughout.

- **Every signing row of the wrappers page says what its call did**, where a
  bare package name used to mean whichever flag some other row in the same
  table had thought worth mentioning. `grind` names the low-r loop, `verify`
  the check made before a signature is handed back, in the order a call
  performs them, and a bare name is a call that does neither — so the name is
  a statement either way. The suffixes are the arguments the call spells, not
  a package's peculiarity spelled out on its behalf: electrum-ecc's rows carry
  `verify` though its `ecdsa_sign` takes no such argument, because that is
  what it does, and coincurve's are bare because its signing does neither.

  The first pass at this named both flags on every row, `nogrind_noverify`
  included. It was correct and it read as a column of one word repeated,
  which is the same objection this project makes to a call count printed on
  every line: what a table says once belongs above it, not down it.

  Each table now carries every combination its packages admit, which is four
  rows for btclib-secp256k1 — the fourth, `grind` with `verify`, being the
  one the page argued about while it lacked it. The check runs once, on the
  signature the loop settled on, so grinding a checked signature was said to
  cost what grinding an unchecked one costs; measured, the two differences
  agree to a percent. A claim about two rows is better measured than argued.

- **The wrappers page is ordered so that what a later table contains is read
  before it**, and the derivation is a pair. Signing came last and the
  derivation after it, on the argument that a derivation is the scale the
  signing constructors are read against — which is a reason to put it before
  them rather than after. So the order is the parse pair, the derivation
  every key object performs as it is built, the tweak, verification, and
  signing last because it parses no public key at all and what its tables
  carry instead is a constructor.

  The derivation answers both serializations now, as every other operation
  here that touches a public key does, and the pair prices a negative
  result: each package's two rows land inside the run's own agreement with
  itself, so the octets of y cost less than the column can separate. That is
  the whole asymmetry of the compressed form in one place — paid for on the
  way in, once per parse, and never on the way out.

  Three things were found while moving the tables. The derivation rows were
  missing from the loop that calls every row once at import, having been
  added to the page without being added to it. `tests/wrappers_test.py` had
  no derivation case at all, and has one now against `secp256k1lab`'s own
  generator multiplication, over both encodings. And the per-table call
  counts were keyed by the table's number, which is an index into a page and
  moves when the page is reordered: nothing at run time would have said so,
  the count being printed beside the row it was used for, so a count that
  followed the position would read as one that had been chosen. They are
  keyed by the rows they belong to now.

- **A row of the wrappers page ends where its own call ends, and says which
  end that is.** The tweak tables timed every row to the compressed key
  BIP32 stores, on the argument that timing each API's own answer would put
  a tweak-and-serialize beside a tweak. True, and it left the other half
  unmeasurable: three of the four answer with a key object, so the page was
  charging them work no caller does in the middle of a chain, which
  serializes the key it arrives at and not the ones it passed through. Both
  are rows now, `octets` and `object`, and what the serialization costs is a
  subtraction inside one table instead of a sentence. btclib-secp256k1 has
  one row there because octets are what its key is rather than a
  serialization it performed — and that row stands ahead of the other three
  even where they stop at their own object.

  The same suffix reaches the one other row whose answer is not what its
  table's title says: secp256k1-py's `ecdsa_sign` returns a parsed signature
  and no bytes, alone of the four, so its serialization is now priced in the
  table that prints the encoding it serializes to. The two `object` rows are
  one call over two slices of the pool, and they agree, which makes their
  agreement a check on the pool rather than a second finding.

  The held ECDSA table gains btclib-secp256k1, which read `NA` on the
  argument that `dsa.sign` takes the 32 octets a caller already holds. True
  of a plain signature and false of a checked one: the check verifies under a
  public key, `sign` derives one per call when nobody hands it over, and
  `pubkey=` is where a caller who has it puts it. So what the other three
  keep inside a key object, this package keeps as the octets that are its
  key, and what the row saves is that derivation less the parse of the
  octets handed in — which the derivation table at the top of the page
  measures on its own, by a different route, and agrees with. The bare row
  stays `NA`, and the two together are one finding said twice: a signature
  nobody checks needs no public key.

  Every title now says which end of a call a key is at and which encoding it
  is in, no width appearing without the word for it. The four ECDSA
  verification tables are ordered by the key, the 64-byte signature first, so
  a package's two signature encodings are adjacent tables and the same
  signature under the two key encodings is one table apart.

- **Two rows of the wrappers page were comparing unlike things, and both now
  say so by measuring it.** The derivation table timed coincurve's
  `from_valid_secret`, an entry point whose own docstring says it avoids
  input checks, beside a btclib-secp256k1 call that makes them — so the
  difference between them was printed as though it were the derivation. The
  row is `from_secret` now, which validates, and the unchecked spelling
  stays beside it under a name that says what it skips.

  What it skips is not the scalar's range: libsecp256k1 answers that from the
  value and every row here leaves it to the library. It is the length. The C
  call takes a bare pointer and reads 32 octets from it whatever the caller
  passed, so a secret of 20 octets derives a public key from twelve octets of
  whatever sat beside it in memory — and a different key as its neighbours
  change, which is what checking the length buys. Read in order the three
  rows say what the page could not say before: btclib-secp256k1 sits between
  coincurve's two, its own check costing it less than coincurve's costs
  coincurve.

  The BIP340 signing tables had the mirror of that. Three of the four are
  handed the auxiliary randomness BIP340's *Default Signing* mixes into the
  nonce; secp256k1-py's `schnorr_sign` passes `NULL` and its own source
  carries a note that the randomness is recommended. That was in the prose as
  an API's shape and nowhere as a cost. Its rows say `_noaux` now, and
  coincurve — the one package that spells both — carries a row of each in the
  fresh table, so the recommendation is priced where a reader meets it. Once,
  not twice: the difference is the same either side of a keypair.

  A cost stated in prose is a number no run re-derives, which is why both of
  these are rows.

  The held ECDSA table carries btclib-secp256k1 twice, where it used to
  carry it once and print `NA` beside it. The unchecked row is the one the
  other packages' unchecked rows compare with, and it is the same call the
  fresh table makes — `dsa.sign` takes the 32 octets, so a caller who will
  sign again holds what a caller signing once holds. Reading it out of the
  fresh table left a comparison spanning two titles; here the two rows
  landing together is what says the holding bought nothing, in the table
  whose subject that is.

  Three `NA` rows were carrying signing flags they had no business with —
  the two compact ECDSA verifications and BIP340 from a full public key,
  each of which prints coincurve as `NA`. A verification neither grinds nor
  declines a check, so those rows name the package and nothing else. For the
  same reason the held table's secp256k1-py row drops `octets`: with no
  `object` row beside it there is nothing for the suffix to tell apart.

  Both flags are on every row of the signing tables again, `nogrind` and
  `noverify` included, and the BIP340 tables carry `aux` beside `verify` for
  the same reason: a reader comparing two rows should read the same two
  questions answered on both, rather than one row's suffix against another's
  silence. Where a package's answer is a choice as well — secp256k1-py's
  parsed signature — the answer's flag closes the name, so a label reads as
  what the call did and then what it handed back.

  The ECDSA signing titles say which end of the call each key is at, in the
  order the call meets them: the digest, the key handed in or held already,
  and what comes out.

- **A sixth benchmark, `06-silentpayments.py`, for BIP352.** [ISS 83][iss83]'s
  census found two whole modules `btclib_secp256k1` exports that no other
  wrapper on the wrappers page does, `ellswift` and `silentpayments`, and
  the pull request that answered the rest of that census left both for a
  page of their own. `ellswift`'s two deterministic calls turned out to
  have a real second arithmetic after all — btclib's own pure-Python
  `ecc/ellswift.py` dispatches through the same switch `02-btclib-vs-btclib.py`
  already reads every row through, so `decode` and `xdh` are timed there
  now instead, against Python rather than against a same-package ratio.
  `silentpayments` has no such split anywhere in btclib, so this new page
  is the whole of where it is priced.

  Two tables, each keeping the rule the wrappers page's own exclusives
  kept — a ratio between two things that answer one question, never
  between two unrelated operations. `create_outputs` and `scan_outputs`
  are the sender's and the recipient's sides of one payment, verifying the
  claim against making it: the fixture for the second row is the first
  row's own output, scanned for and found before either is timed.
  `prevouts_summary`, `label` and `labeled_spend_pubkey` are the three
  calls a recipient makes that are not themselves a scan, read as three
  prices beside each other rather than a fresh-versus-prepared pair.
  `keys.pubkey_sum` and its aggregation siblings are exclusives from the
  same census and are not here: they have no part in BIP352, and would
  have been the same "ratio of nothing" the wrappers page already refused.

  The fixtures are three disjoint slices of `_inputs`' shared pool, read
  from the top rather than shared with a stated reason the way the
  wrappers page's own ten are: that pool is read by every script here
  independently, and this page does not compete with the wrappers page
  for the same slices. Module-level assertions round-trip both tables
  before anything is timed — what `create_outputs` makes, `scan_outputs`
  finds, labeled and unlabeled — which nothing else in this project's
  suite exercises, no BIP352 vector file being vendored here.

  Six benchmarks now, not five: `README.md`, `CLAUDE.md`,
  `tests/scripts_import_test.py`'s `BENCHMARKS` and the coverage omit
  list all said five in one place or another, and every other page's
  own `More benchmarks` footer named four other sets rather than five.
  Found and fixed together rather than left for the next reader to
  notice one was stale and wonder about the rest.

  Not measured here. `render.py` puts a page's three blocks between the
  markers it carries, and this page carries none yet — adding them is
  part of publishing the first run rather than something to leave behind
  an empty fence.

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

- **CI records which artifact each comparand's install resolved to**,
  `scripts/artifacts.py` printing one line per declared dependency before
  the suite runs. PEP 610 says where a distribution came from and stops
  there, and for a comparand vendoring libsecp256k1 that is half the
  answer: an index serves a wheel and an sdist under one version, and the
  two need not carry the same library. `secp256k1` is the case that
  proves it, and it is not hypothetical — `uv.lock` carries no aarch64
  wheel for it, so on `ubuntu-24.04-arm`, three of the six cells, its
  library is compiled on the runner from an sdist whose pin is four years
  older than the one its wheels carry. Those three jobs were asserting
  the pages' claims against a different binary from the one the pages are
  measured on, and nothing said which.

  What can say is the wheel each install came from: every install goes
  through one, an sdist being built into a wheel first, and its `WHEEL`
  metadata states the tag. A bare `linux_*` platform is one no index
  accepts, so a wheel carrying it was built where it is installed. The
  test on that is against the start of the platform field and not the
  whole tag, `manylinux_2_17_x86_64` ending in the same word — a
  substring test called every downloaded Linux wheel a local build, and
  the suite caught it. On macOS and Windows the two are spelled alike, so
  there the tag is reported and nothing is concluded from it.

  Recorded and not asserted. What an install resolved to is a fact about a
  machine and a lock rather than a claim this repository is entitled to
  make: an index gaining a wheel changes every line and breaks nothing.
  The step reads installed metadata and times nothing, so it is no more a
  benchmark than the linters are. What it still cannot say is the revision
  a local build downloaded — nothing in an installed tree records it, and
  `LIBSECP256K1_PINS` is where that is written down by hand.

- **The wrappers page prices a public key derivation**, which is what its
  own constructors have to be read against. Two of the four sign only
  through a private-key object, and building one derives a public key — so
  a reader met a constructor costing more than a signature with nothing on
  the page to say how much of it was the curve. Most of it is not: a
  constructor costs close to twice a derivation, and the rest is Python
  objects and a crossing. That decomposition was measured outside the
  benchmark and recorded in an issue; the table is what puts it where a
  reader of the constructors finds it.

  Whether it belonged here was the question, and the answer is the reason
  it is last on the page. A generator multiplication is the one operation
  on this page where the C library is most of the cost, which is either the
  argument for the row or against it: it prices libsecp256k1 rather than a
  wrapper, and it is the scale everything else is read against. It is
  ordered as the second of those — after the tables whose constructors it
  explains, rather than among the operations it is not one of.

  Two of the four rows are a constructor themselves, `PrivateKey` and
  `ECPrivkey` each deriving as they are built and neither package offering a
  spelling that skips the object. That is not a flaw in those rows: it is
  why those two are the ones that gain least from a key they already hold.

- **The lock moves btclib to the tip that answers ISS 23.**
  `btclib-secp256k1` was already there, so this is one revision: btclib's
  `dsa.sign_`, `ssa.sign_` and `ssa.Signer.sign` now take a `verify`
  keyword, and `dsa.sign_` a `pub_key` beside it, so a caller can decline
  the check or hand over the key the check would otherwise derive. What
  the fast path does with it is the other half of
  [btclib#982](https://github.com/btclib-org/btclib/issues/982): the
  grind and the check both cross into the bindings now, so the check
  happens once on the signature the grind kept rather than once per
  attempt discarded, and the arm has no verification of its own to write.

  Nothing here is measured against it yet, and that is the point of
  recording the move on its own. Every page that times btclib's signing
  was measured before the check existed on that path, so what those pages
  publish is the shape btclib had; the pages are the run that follows,
  one script at a time on a machine given time to cool.

  One published sentence went stale with the keyword and is corrected
  here rather than left for the run: `results/01-libsecp256k1.md` said
  btclib exposed no way to decline the check, which was the reason its
  held pair had no counterpart on the btclib pages. It has one now, and
  the paragraph says so — prose outside the `run:` markers, so the
  numbers beside it are untouched.

- **A libsecp256k1 pin is keyed on the build, and a build is not always a
  version.** `secp256k1` 0.14.0 serves two artifacts carrying libsecp256k1
  revisions years apart: the sdist ships a library tree among its own files
  whose `configure.ac` still calls itself 0.1, and the wheels — re-published
  under that unchanged version long afterwards — come from a source that had
  moved `LIB_TARBALL_URL` on to the v0.6.0 tag. The installed extension is
  what settles it rather than the upstream claim: it exports the `musig`
  entry points that release added, where the tree in the sdist has neither
  that module nor `ellswift`.

  So the guard on that column could not fire. It compared the recorded key
  with what identifies the build, and for a release that was the version —
  which stood still while the library moved under it, leaving a pin that
  went on printing after it had stopped being true. `_build_of` is the key
  now: a commit for a branch install, a version for a release, and the
  version with the artifact for a release whose index serves two.
  `INDEX_WHEELS` records the tags the index is known to serve, because that
  is the half a tag cannot answer alone — `_provenance.built_here` says when
  a wheel was made where it sits, which on Linux is the sdist, and on macOS
  and Windows a published wheel and a local build are spelled alike. A tag
  in neither set is `unrecorded` for both columns rather than a guess
  between two libraries.

  The `released` column had the same defect one column earlier and is fixed
  by the same key, which also reorders the table: that build is one of the
  newest here rather than the oldest, and only the library it carries is
  old. `built_here` is public for this, and `artifact_of` now says the sdist
  *carries* its revision rather than downloading it — it ships the tree.

  Two places said the old rule as fact and no longer do. The aarch64 CI
  job's `xfail` reason named the compiler, and names the library it builds:
  that job is the only one of the six running the older revision, which is
  a candidate for the nonce difference recorded there that the pin could
  not confirm before and can now. And `results/01-libsecp256k1.md` is wrong
  on that row, measured under the old key — provenance is measured data, so
  re-publishing cannot correct it and the next run of that page will. The
  prose says so meanwhile, outside the markers, naming [ISS 67][iss67];
  ISS 27's third candidate is narrowed by it but not closed, that one
  splitting macOS from Linux where both install wheels of one revision.

- **The three pages that time btclib's signing say that they predate its
  check.** The lock move above records it in this file, and a reader of one of
  those pages had no way to know it from the page in front of them: btclib
  verifies the signature it has just made before answering with it, the lock
  carries that btclib, and those rows were measured before that path had a check
  at all. Saying which rows are the stale ones is prose and lands now;
  correcting them is a run, and a run here is one script at a time on a machine
  given time to cool. Every other row on all three pages is current,
  verification included, and each page says so — a page that warned about itself
  in general would have put its whole table in doubt to correct three rows.

  Each page also says what its next run has to print, that being a decision
  rather than a measurement and separable from one.
  `results/02-btclib-vs-btclib.md` declines the check on both arms, its subject
  being the crossing: the two checks are not the same size — a verification on
  the Python arm against a fraction of a signature on the other — so a row that
  took the default would move the ratio a long way with neither arithmetic
  having changed. Its recoverable row has no such choice, recoverable signing
  taking no argument that declines, and what is paid there is a recovery and a
  comparison rather than a verification, on the libsecp256k1 side alone: [ISS 28
  — the recoverable row][iss28].

  `results/03-libraries.md` and `results/04-pure-python.md` each want a pair,
  which is the shape `results/01-libsecp256k1.md` took for the same question:
  btclib is the only comparand on either page that takes the argument, so one
  row is what compares with the implementations that verify nothing and a second
  is what the guarantee costs. The pure-Python page is the sharper of the two,
  the check there being a verification in Python — the largest share of a
  signature it comes to anywhere in this project, and that page's own verify
  rows are what say so.

  No number is settled here, and four issues stay open for the runs: [ISS 23 —
  the three pages][iss23], [ISS 53 — page 03 measured and discarded][iss53],
  [ISS 55 — page 04's shape][iss55], and [ISS 47 — the spread estimator][iss47],
  which rides with page 03's run rather than costing a second one.

- **The wrappers page states how far two of its own passes disagreed**, which is
  the one thing every dispersion column on these pages cannot say. A column of
  within-pass agreement answers whether a gap between two adjacent rows is a gap
  the run settled; what a reader comparing this page against the version
  published before it relies on is between-run agreement, and the page warned
  that a row could move by more than any distance printed beside it without
  giving the size.

  So the page is timed twice in one invocation, idle in between, and the run
  block carries a generated line naming how far apart the two passes began, how
  many rows came out quicker the second time, and by how much — the worst row
  and the median beside it. What a published number is does not change: it is
  the first pass, and the same minimum of two halves it was before.

  The count of rows is in that line because a magnitude without it means two
  different things, and both were measured. The first run taken this way came
  out quicker on the second pass for 78 of its 85 rows, which is a difference
  between the passes rather than noise between them and would be an argument for
  publishing the later one. Two more runs within the hour split 45 of 85 and 45
  of 86, with median differences of three hundredths of a per cent, so there is
  nothing systematic to correct for: the rule stays what ISS 35 set — the first
  pass is published, fixed rather than chosen once both are in hand — and the
  line prints the count, three runs having shown that the median alone means
  either thing.

  The one-directional run is not what is published and it is not discarded
  either. What is published is a later run, taken on this page as it stands
  after the rows were renamed; what the earlier ones are kept for is the count
  above, which is evidence about the method rather than about the packages. One
  of them earned discarding on its own: its halves put a row at seven per cent
  of its value, and by the standard this page has always been kept to that is
  interference rather than a measurement.

  A claim the page already made was checked against the run rather than assumed
  to survive it. The derivation pair states that serializing y is free, on the
  argument that a package's two rows land inside the run's own agreement with
  itself: it holds for all five packages here, and it did not in the run of an
  hour earlier, where two of the five sat further apart than their halves
  distance and every one of them inside its own drift. Which is what the drift
  line is for, and why the sentence stands rather than being widened to a claim
  no single run supports.

  Both halves of a second pass are refused unless the file carries both: a run
  naming the instant the second pass began with no row measured twice, or rows
  measured twice under a run naming one instant, raises where it is built.
  Either half alone renders as silence, and silence there means a page that
  never took a second pass — which is what the other four pages are, and what
  they stay until one of them is worth two passes rather than one.

  Nothing derived is stored, as everywhere here: the second pass is kept per row
  under `us_per_call_again` and the second instant beside `when` under
  `when_again`, and the count, the median and the worst are computed at render
  time where the ratios and the sort already are. Two optional keys and a shape
  addition, so `SCHEMA` does not move and a run file written before this renders
  exactly as it did.

  Against publishing the row-wise minimum of both passes, which was the other
  shape considered: a page whose rows come from two occasions has no run to
  name. The run block states one instant, one machine, one method, and the saved
  file is what one clock produced. That it would also double the four expensive
  pages is the second objection rather than the first. [ISS 35 — between-run
  agreement][iss35] is where the shape was argued, and it waited for this page's
  rows to settle: a run taken while what a table contains is still moving is a
  run thrown away.

- **Every btclib signing row on the three pages that carry one now states the
  policy it was measured under**, and passes it rather than taking whatever
  btclib's default happens to be. btclib verifies the signature it has just
  made before answering with it, on both arms, and exposes `verify` for a
  caller who declines — so a row that named nothing was a row whose reader
  could not tell what it had done, and the three pages' decisions, written
  down in the entry above, are now what their scripts perform.

  `scripts/02-btclib-vs-btclib.py` declines on both arms and says so in two
  row names, `dsa_sign_nogrind_noverify` and `ssa_sign_noverify`. That is
  what the ratio requires rather than a preference: the check is a fraction
  of a signature where libsecp256k1 answers and a full verification where the
  Python does, so a row taking the default would divide one checked signing
  by another and move with neither arithmetic having changed. `bms_sign` is
  the row that still names no verify flag, and the name is silent because its
  two columns do not share one — recoverable signing takes no argument that
  declines, and what it performs is a recovery and a comparison on the
  libsecp256k1 side alone. Its docstring and the page say so where a label
  cannot.

  `scripts/03-libraries.py` and `scripts/04-pure-python.py` each carry the
  pair the wrappers page took, btclib being the only comparand on either that
  takes the argument: an unchecked row for the comparison with libraries that
  check nothing, and a checked row for what the guarantee costs. Both grind
  as well, so btclib's ECDSA rows are four and not two — the check runs once
  on the signature the loop settled on, so the flags add rather than multiply.
  Every other signing row on both pages is renamed to state its own two flags,
  which is `results/01-libsecp256k1.md`'s rule arriving where the same silence
  was: what a row did is a property of the row, not a favour its API granted,
  and python-ecdsa having no way to ask for a check is why its row says
  `noverify` rather than why it should say nothing.

  Reading each library to name its flag turned up something neither page
  said, and it changes which rows are comparable with which. **Both BIP340
  comparands on the pure-Python page check what they signed, and buidl checks
  on the libraries page too**, none of the three offering a way to decline:
  secp256k1lab ends `schnorr_sign` on `assert schnorr_verify(...)`, which is
  how BIP340's own reference code writes the specification's last step, and
  buidl verifies under the point its key holds and raises on a failure. So in
  those tables it is btclib's *checked* row that has comparands and its
  unchecked row that stands alone — the same pair read the other way round,
  and the reason the pair has to be a pair rather than a choice between two
  rows. The BIP340 signing rows published today put btclib ahead of both, and
  part of that lead is a step those two take and that row did not. No
  comparand checks an ECDSA signature it has just made, on either page.

  No page moves until it is run, one script at a time on a machine given time
  to cool, and each of the three still carries the paragraph naming the rows
  that predate the check. What changes on page 02 is the shape of that
  warning: its two declining rows have least to correct, what they publish
  being a signature alone and a signature alone being what they will publish
  again, and `bms_sign` is the row that will move. [ISS 23][iss23],
  [ISS 28][iss28], [ISS 53][iss53] and [ISS 55][iss55] end in those runs.
- **The wrappers page prices three calls only one of its four comparands
  offers**, each beside its own nearest sibling inside the same package. Every
  other table there is four wrappers answering one question and a ratio saying
  what choosing one instead of another costs; these have one wrapper, and the
  ratio is between two calls of it. The nonce derivations both schemes expose,
  where the other three wrappers derive theirs inside the signing call and
  hand back a signature. BIP341's tweak check, which is what a taproot spend
  has to establish and which all four wrappers can tweak toward and none of
  the other three can ask about. And re-encoding a public key's octets in one
  call, against the parse and serialize the other three leave to a caller.

  The shape is the one [ISS 83][iss83] arrived at, and it is what its census
  argued for: a table of unlike exclusives would have had a ratio column
  dividing an ElligatorSwift encode by a silent-payment scan, which is a ratio
  of nothing. So what is here is the exclusives that have a sibling to be read
  against, and the two whole modules the census names — `ellswift` and
  `silentpayments` — are what it still holds open, having no sibling and no
  fixtures in this pool.

  No eleventh slice: the pool holds ten and all ten were taken, so each of the
  three shares one with a reason of its own, which is what the tweak and
  derivation pairs already do. The nonce rows read the slices their own scheme
  signs on, so each is that scheme's first step over the inputs its table
  used. That sharing found something on the way in: an x-only key names the
  even-y point of its pair, so where a pool key's public key has odd y the
  x-only form names that key's negation, and a negated point tweaked by the
  scalar it came from is the point at infinity — which libsecp256k1 refuses.
  Written each-key's-own it raised on the keys of that parity and on no
  others. The tweak is the next key's scalar instead, and the comment beside
  it says why.

  Each of the three is pinned in `tests/wrappers_test.py`, which is where
  correctness for this page lives — the benchmark asserts nothing, by design.
  The tweak check is held to answering no as well as yes, a positive case
  alone being unable to tell a check from a function that returns True: a
  wrong tweak, a wrong parity and a wrong internal key are each refused. The
  BIP340 nonce is held to the published vector, R being the nonce times the
  generator and x(R) the first half of the signature. The RFC6979 nonce is
  held to the r of the signature the same package makes, no file publishing
  one, and the test says that this is agreement rather than a specification.
  Re-encoding is held to the key derived from the secret rather than only to
  the parse and serialize it replaces.

  The page carries the prose and not the tables: a rendered region is filled
  from a saved run, and the run beside it was taken before these rows existed.
  Adding the region is part of publishing the next run, and `render.py`
  refuses a run whose groups the page has no region for, so that run cannot
  quietly drop them.

- **The libraries page measures the dispersion the wrappers page measures**,
  four rounds in two halves with the distance between the halves' minima
  beside each row, where it took three rounds and printed the slowest less
  the quickest. The two answer different questions and only one of them is
  the question the column is read for: a maximum less a minimum is an
  extreme-value statistic over a handful of samples, so it has enormous
  variance by construction, grows as rounds are added, and reports the worst
  interruption a row happened to catch. A distance between two halves' minima
  says whether the row agreed with itself, and shrinks as rounds are added.
  The page stopped telling its reader to use the first as a separation test
  two entries ago; it now stops printing it.

  Four and not more. Each half's minimum is the better for having rounds
  behind it, and this page's pure-Python rows are orders of magnitude slower
  than the wrappers page's — which is why its loop count is per row rather
  than per table, and why a fifth round costs more here than a fifth round
  costs there. Three would not halve: half a round is the minimum of nothing.

  The key moves with the statistic, `halves_apart` rather than `spread`, which
  is the discipline `SCHEMA` states — a value whose definition changes is
  written under a new name, so a number in a saved run means what its key
  says and a run saved before the change keeps the statistic it was taken
  under. Nothing re-saves and nothing re-renders: the block on the page still
  carries three rounds under `spread` until the page is next run, and the
  prose beside it says which column is which. [ISS 47][iss47] is the change,
  and the run it waits for is the one [ISS 23][iss23] orders — one run that
  prints the new rows and the new column together rather than paying for this
  page twice.

- **Two pages time a held signer, which nothing here did.** `05-key-reuse.py`
  asks what a verifier pays per signature under a key it already has, and its
  own argument for asking — that a verifier does not verify one signature — is
  every bit as true of a signer. `grep -rn Signer scripts/*.py` was empty on
  btclib's side: neither `btclib.ecc.ssa.Signer` nor the one it delegates to
  was timed on either arm. [ISS 42][iss42].

  `scripts/02-btclib-vs-btclib.py` gains one row, and its two columns do not
  save the same thing. `ssa.Signer` holds across calls the keypair `ssa.sign_`
  builds and wipes inside each one, and there is a keypair to hold only where
  libsecp256k1 answers: with the dispatch off a signer holds a scalar and every
  signature is `sign_`'s again. The row is there because that asymmetry is the
  answer — what the fallback cannot offer is as much that page's subject as
  what it costs — and it is read against the fresh signing row rather than
  against the rest of the table.

  `scripts/03-libraries.py` splits BIP340 signing into two tables, a fresh key
  and a key held already, and the split corrects a comparison as much as it
  adds one: buidl and embit were already being called through an object built
  outside the clock, where btclib's row was handed 32 octets and built
  everything per call. What each library holds differs, and it was read out of
  the source rather than off the shape of its API — btclib's `ssa.Signer`
  holds the keypair, buidl's `PrivateKey` holds `secret * G`, embit's holds
  the secret octets and hands them to a library that builds the keypair inside
  every call. A held key object is not a held keypair.

  **A held object is the one fixture `python_arithmetic_only` cannot reach**,
  and finding that out is what the page 02 row cost. `ssa.Signer.__init__`
  asks the dispatch once and keeps the answer, zeroing its own scalar where it
  built the bindings' signer, so an object built before the switch stays on
  libsecp256k1 for life and could not sign in Python if asked. Written the
  obvious way, that row's pure-Python column printed a libsecp256k1 number,
  silently and convincingly, and `tests/pure_python_path_test.py` — which
  blocks every binding and throws the same switch — is what said so. The
  rebuild is therefore inside `python_arithmetic_only` rather than beside its
  callers: an invariant a caller has to remember is one that gets forgotten,
  and what forgetting this one produces is not an error but a wrong number.

  Neither page moves until it is run. [ISS 42][iss42] ends in those two runs.

- **`docs.yml` builds the documentation, and nothing gated a merge on it
  before.** `.readthedocs.yaml` runs `sphinx-build -W`, which turns a
  docstring or a markdown link sphinx cannot resolve into a build
  failure — but the only two workflows this repository had were
  `lint.yml`, which never invokes sphinx, and `test.yml`, which tests
  helpers rather than prose. [ISS 95][iss95] hit that hole twice by hand,
  the second time on a pair of relative links between `CONTRIBUTING.md`
  and `REVIEWING.md` that this repository's `{include}`-based pages
  cannot resolve — a shape with no local gate to catch it, failing only
  on Read the Docs, after the merge, on a page nobody was watching.

  The new job runs the same `sphinx-build -W --keep-going` command on the
  same interpreter `.readthedocs.yaml` pins, 3.14 rather than this
  repository's own 3.13 floor — that floor being set by two wrapper
  comparands the documentation build never installs, and one interpreter
  is what keeps "does the build pass" one question between the two
  places it now runs rather than two. It is a job for a maintainer to add
  to `main`'s required status checks, `Build the documentation` named on
  its own the way btclib and btclib-secp256k1 both name theirs;
  `REPOSITORY.md`'s *Required checks on main* section is what to update
  once it is.
- **`02-btclib-vs-btclib.py` gains `ellswift_xdh`.** `ecc/ellswift.py`
  gates four public functions on the same dispatch every other row on this
  page reads through, and only `decode_var` was timed: `create_var` and
  `encode_var` draw a random field element on every call, which is why an
  encoded form is built once, off the clock, as the fixture that feeds
  `decode_var` rather than as a row of its own. `xdh` is deterministic
  like `decode_var` — no field element is drawn inside it, only hashed —
  so it is timed the same way, over a fixture key paired with the next
  key's own encoding, the construction `dh_shared_secret` already uses for
  its counterparty. Found while sizing [ISS 83][iss83]'s remaining
  exclusives for a page of their own: `ellswift`'s split arithmetic is
  this page's subject already, which is a better home for its
  deterministic calls than a same-package ratio would have been. The page
  is not re-measured here, and the new row carries no number until it is.
- **`test.yml` no longer asks apt for a toolchain the runner already
  carries.** [ISS 96][iss96] traced three cancelled jobs in one evening to
  the same cause: `apt-get update` stalled on an upstream mirror and took
  the step's whole thirty minutes with it, before any comparand was
  installed and before the checkout did anything for the job. The step
  existed for `pkg-config`, `autoconf`, `automake` and `libtool`, which
  three of the wrapper comparands want to compile a libsecp256k1 of their
  own. Both `ubuntu-latest` and `ubuntu-24.04-arm` — the whole matrix —
  ship all four already, `actions/runner-images`' own manifests for
  Ubuntu 24.04 and its arm64 image listing each among the preinstalled
  software, so the step was asking apt for what the image had every time
  it ran. It is gone rather than retried: a request for nothing has
  nothing a retry improves on.
- **A closed pull request's run no longer lands in its merge's own push
  run's concurrency group.** `test.yml`, `lint.yml` and `docs.yml`
  grouped by `github.ref` alone, and github.ref for a closed, merged
  pull request's run resolves to the base branch's ref rather than
  `refs/pull/N/merge`, landing it in the same group as the push the
  merge itself triggers. The two events fire about a second apart on
  every merge, and after [PR 99][pr99] landed, its own `test`, `lint`
  and `docs` push runs for the merge commit were all cancelled within
  one to two seconds of being created, before any job started --
  required checks reading `cancelled` for a commit the run that got to
  run never tested. The group is now
  `github.event.pull_request.number || github.ref`: a pull_request run
  of any action, closed included, groups by the pull request's own
  number instead, which still cancels that same pull request's own
  earlier run exactly as `closed` was added for, and cannot equal any
  push's `github.ref`.

- **`HISTORY.md` is `RELEASE_NOTES.md` now.** Its own heading has always
  read "Release notes"; the filename did not, and where a project splits
  a changelog from its history the convention runs the other way --
  [Keep a Changelog](https://keepachangelog.com/) names CHANGELOG.md as
  the curated, human-facing list, which is what this file already was.
  `CHANGELOG.md` keeps naming the old file in its own past entries, that
  being what was true then; every live reference moved with the file --
  `.gitattributes`' merge driver, the docs toctree, `pyproject.toml`'s
  codespell glob, and the cross-file prose in `CONTRIBUTING.md`,
  `RELEASING.md` and `REVIEWING.md`. Mirrors btclib-org/btclib
  [ISS 1011](https://github.com/btclib-org/btclib/issues/1011) and its
  fix, [PR 1039](https://github.com/btclib-org/btclib/pull/1039).

[iss23]: https://github.com/btclib-org/btclib-benchmarks/issues/23
[iss28]: https://github.com/btclib-org/btclib-benchmarks/issues/28
[iss35]: https://github.com/btclib-org/btclib-benchmarks/issues/35
[iss42]: https://github.com/btclib-org/btclib-benchmarks/issues/42
[iss47]: https://github.com/btclib-org/btclib-benchmarks/issues/47
[iss53]: https://github.com/btclib-org/btclib-benchmarks/issues/53
[iss55]: https://github.com/btclib-org/btclib-benchmarks/issues/55
[iss67]: https://github.com/btclib-org/btclib-benchmarks/issues/67
[iss68]: https://github.com/btclib-org/btclib-benchmarks/issues/68
[iss83]: https://github.com/btclib-org/btclib-benchmarks/issues/83
[iss95]: https://github.com/btclib-org/btclib-benchmarks/issues/95
[iss96]: https://github.com/btclib-org/btclib-benchmarks/issues/96
[pr99]: https://github.com/btclib-org/btclib-benchmarks/pull/99
