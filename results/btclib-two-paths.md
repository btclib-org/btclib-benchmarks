# btclib against btclib, one run

What `scripts/btclib_two_paths.py` printed on the machine named below.
Both rows of every pair are btclib, called the same way; what differs
underneath is which arithmetic answers — the libsecp256k1 that
`btclib_secp256k1` bundles and compiles into a cffi extension, or the
Python of `curves/curve_group.py`. Not btclib against btclib_secp256k1:
`pip install btclib` installs both.

Microseconds per call to five significant digits, sorted on the ratio, and
that ratio against the quicker of the pair. The fastest row of the whole
table would divide a signature by a point parse, and the ratio is what the
table is read for: what an operation costs is a fact about the operation,
what its fallback costs is the fact about the two arithmetics.

Thirteen operations, which is not a selection. `_libsecp256k1_serves` is
the predicate every dispatch site in btclib asks, and these are the
operations holding one that a caller would call.

One run, kept whole — the header the script printed above its numbers is
part of it, because a table that does not say which build of btclib it
timed cannot be checked. Nothing was repeated and no outlier was
discarded, so what [README.md][readme] says about reading these applies
here first: an order of magnitude, never a figure to quote.

## What produced it

```text
when    : 2026-08-14 18:49 CEST (16:49 UTC)
python  : 3.13.14
command : uv run python scripts/btclib_two_paths.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9

the two arithmetics under each pair
  libsecp256k1        bundled and compiled into btclib_secp256k1 0.8.0.1, through cffi bindings, _btclib_secp256k1.cpython-313-darwin.so
  pure python         btclib's own curves/curve_group.py, the dispatch off

                                μs/call       vs best
point_parse_libsecp256k1         3.6592          1.0x
ellswift_decode_libsecp256k1     8.1837          1.0x
mult_libsecp256k1                8.3207          1.0x
pubkey_libsecp256k1              8.4351          1.0x
dh_libsecp256k1                  15.825          1.0x
dsa_sign_libsecp256k1            17.373          1.0x
taproot_tweak_libsecp256k1       17.399          1.0x
dsa_verify_libsecp256k1          23.184          1.0x
ssa_verify_libsecp256k1          23.274          1.0x
ssa_sign_libsecp256k1            23.763          1.0x
bms_verify_libsecp256k1          23.991          1.0x
bms_sign_libsecp256k1            28.589          1.0x
dsa_recover_libsecp256k1         43.986          1.0x
dsa_sign_pure_python             175.13         10.1x
bms_sign_pure_python             344.11         12.0x
ssa_sign_pure_python             324.19         13.6x
ellswift_decode_pure_python      123.85         15.1x
mult_pure_python                 145.02         17.4x
taproot_tweak_pure_python        315.34         18.1x
pubkey_pure_python               153.73         18.2x
point_parse_pure_python          76.568         20.9x
ssa_verify_pure_python           688.01         29.6x
dsa_verify_pure_python           700.90         30.2x
dh_pure_python                   554.09         35.0x
bms_verify_pure_python           1352.0         56.4x
dsa_recover_pure_python          2972.1         67.6x
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

The Python side is not a path nobody reaches. It answers for every curve
that is not secp256k1, for a zero scalar, for the point at infinity, and
for everything else the bindings decline — so what this table says about it
is what a caller outside the fast case actually gets, and why the
delegation is a delegation rather than a rewrite.

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

That a row belongs here is therefore something to prove.
`tests/pure_python_path_test.py` proves it: it replaces every bindings entry
point with a function that raises, throws the switch, and calls every
operation once. A row that has kept a foot in C raises instead of
answering, and the failure names the call. BIP32 derivation is timed in
[the bitcoin-libraries table][libs] instead, against three other libraries,
where being C is the premise rather than the question.

The labels name the two arithmetics rather than a package and a language:
every row here is btclib, and every row here is invoked from Python. The
libsecp256k1 rows are all timed before the Python ones because
`python_arithmetic_only()` cannot be undone inside a process — the switch is
thrown once, between the halves, and the sort happens afterwards.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
