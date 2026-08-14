# btclib against btclib

## This run

```text
when    : 2026-08-14 23:16 CEST (21:16 UTC)
python  : 3.13.14
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/btclib_two_paths.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

What `scripts/btclib_two_paths.py` printed on the machine named above.
Both rows of every pair are btclib, called the same way; what differs
underneath is which arithmetic answers — the libsecp256k1 that
`btclib_secp256k1` bundles and compiles into a cffi extension, or the
Python of `curves/curve_group.py`. Not btclib against btclib_secp256k1:
`pip install btclib` installs both.

Microseconds per call to five significant digits, sorted on the ratio, and
that ratio against the quicker of the pair. Every row cycles the published
vectors, taking the next input per call. The fastest row of the whole
table would divide a signature by a point parse, and the ratio is what the
table is read for: what an operation costs is a fact about the operation,
what its fallback costs is the fact about the two arithmetics.

Thirteen operations, which is not a selection. `_libsecp256k1_serves` is
the predicate every dispatch site in btclib asks, and these are the
operations holding one that a caller would call.

One run, kept whole — the header the script printed above its numbers is
part of it, because a table that does not say which build of btclib it
timed cannot be checked. Nothing was repeated and no outlier was
discarded. The numbers are an order of magnitude, never a figure to quote.

## The output

```text
btclib              : 2026.9

the two arithmetics under each pair
  libsecp256k1        bundled and compiled into btclib_secp256k1 0.8.0.2, through cffi bindings, _btclib_secp256k1.cpython-313-darwin.so
  pure python         btclib's own curves/curve_group.py, the dispatch off

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

                                μs/call       vs best
point_parse_libsecp256k1         3.6229          1.0x
mult_libsecp256k1                8.3438          1.0x
ellswift_decode_libsecp256k1     8.6076          1.0x
pubkey_libsecp256k1              10.388          1.0x
dh_libsecp256k1                  13.748          1.0x
taproot_tweak_libsecp256k1       17.453          1.0x
dsa_sign_libsecp256k1            19.447          1.0x
dsa_verify_libsecp256k1          23.298          1.0x
ssa_verify_libsecp256k1          23.888          1.0x
bms_verify_libsecp256k1          24.138          1.0x
ssa_sign_libsecp256k1            25.338          1.0x
bms_sign_libsecp256k1            30.642          1.0x
dsa_recover_libsecp256k1         43.301          1.0x
dsa_sign_pure_python             175.65          9.0x
bms_sign_pure_python             341.97         11.2x
ssa_sign_pure_python             329.98         13.0x
pubkey_pure_python               149.54         14.4x
ellswift_decode_pure_python      137.08         15.9x
mult_pure_python                 139.77         16.8x
taproot_tweak_pure_python        312.06         17.9x
point_parse_pure_python          74.908         20.7x
ssa_verify_pure_python           688.17         28.8x
dsa_verify_pure_python           676.55         29.0x
dh_pure_python                   551.54         40.1x
bms_verify_pure_python           1329.8         55.1x
dsa_recover_pure_python          3251.9         75.1x
```

## What it shows

Every libsecp256k1 row is faster than its pure-Python counterpart, and the
sort puts all of them above all of the others: on this machine the two
arithmetics do not interleave.

The spread within that is the part worth reading. Verification separates the
two further than signing does, in both schemes; public-key recovery, which is
verification and then some, separates them furthest, and bitcoin-message
verification next, being a recovery with hashing around it. At the narrow end
sit signing and ElligatorSwift decoding, where one multiplication is
surrounded by work the C never does.

The Python side is not a path nobody reaches: it answers for every curve
that is not secp256k1, for a zero scalar, for the point at infinity, and for
anything else outside libsecp256k1's entry points. What this table says about
it is what a caller outside the fast case gets.

## Why BIP32 derivation is not a row, and how that is enforced

btclib's BIP32 has no pure-Python path. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
reason beside the call — BIP32 is defined for secp256k1 and nothing else, so
there is no other curve for a fallback to serve. Throwing the switch leaves
the derivation in C and moves only the public key derived for the
fingerprint, so a pair of rows for it would compare C against C with a Python
step added. Its pair was far narrower than every other, which is what that
looks like from the outside.

That a row belongs here is therefore a property to prove.
`tests/pure_python_path_test.py` replaces every bindings entry point with a
function that raises, throws the switch, and calls every operation: a row that
has kept a foot in C raises instead of answering. BIP32 derivation is timed in
[the bitcoin-libraries table][libs] instead, where being C is the premise.

The labels name the two arithmetics rather than a package and a language:
every row here is btclib, and every row is invoked from Python. The
libsecp256k1 rows are timed first because `python_arithmetic_only()` cannot be
undone inside a process; the sort happens afterwards.

## More benchmarks

Four other questions are published in `results/`, each with its own
comparands:

- [python libraries][libs] — where bindings (if available) are just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [the libsecp256k1 wrappers][wrappers] — four packages wrapping one C
  library, and which revision of it each vendors
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md
[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/libsecp256k1-wrappers.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/key-reuse.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
