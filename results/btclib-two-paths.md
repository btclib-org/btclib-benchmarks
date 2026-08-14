# btclib's two paths, one run

What `scripts/btclib_two_paths.py` printed on the machine named below:
every operation btclib dispatches to the libsecp256k1 bindings, timed
again through its own pure-Python arithmetic. Seconds per ten thousand
calls to five significant digits, sorted on the ratio, and that ratio
against the quicker of the two paths for that operation — every row here
is btclib, so that pairing is the only comparison in this table that means
anything: the fastest row of the whole table would divide a signature by a
point parse.

Sorted on the ratio and not on the seconds because the ratio is what the
table is read for. What an operation costs is a fact about the operation;
what its fallback costs is the fact about the two paths, and that is the
column that ranks them.

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
when    : 2026-08-14 17:43 CEST (15:43 UTC)
python  : 3.13.14
command : uv run python scripts/btclib_two_paths.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9
btclib-secp256k1    : 0.8.0.1

                                us/call       vs best
point_parse_bindings             3.4934          1.0x
pubkey_bindings                  8.2504          1.0x
mult_bindings                    8.2853          1.0x
ellswift_decode_bindings         9.3068          1.0x
dh_bindings                      15.753          1.0x
taproot_tweak_bindings           17.274          1.0x
dsa_sign_bindings                17.404          1.0x
ssa_sign_bindings                20.756          1.0x
dsa_verify_bindings              22.711          1.0x
ssa_verify_bindings              23.001          1.0x
bms_verify_bindings              23.834          1.0x
bms_sign_bindings                31.071          1.0x
dsa_recover_bindings             43.381          1.0x
dsa_sign_pure_python             172.28          9.9x
bms_sign_pure_python             345.23         11.1x
ssa_sign_pure_python             304.65         14.7x
ellswift_decode_pure_python      152.50         16.4x
mult_pure_python                 140.90         17.0x
taproot_tweak_pure_python        312.23         18.1x
pubkey_pure_python               155.92         18.9x
point_parse_pure_python          74.642         21.4x
ssa_verify_pure_python           686.44         29.8x
dsa_verify_pure_python           698.72         30.8x
dh_pure_python                   560.55         35.6x
bms_verify_pure_python           1350.0         56.6x
dsa_recover_pure_python          2787.3         64.3x
```

## What it shows

Every bindings row is faster than its pure-Python counterpart, and the
sort puts all thirteen of them above all thirteen of the others — on this
machine the two paths do not interleave at all.

The spread within that is the part worth reading. Verification separates
the paths further than signing does, in both schemes; public-key recovery,
which is verification and then some, separates them furthest and is the
widest pair in the table. Bitcoin-message verification is second widest for
the same reason, being a recovery with hashing around it. At the narrow end
sit signing and ElligatorSwift decoding, where a single multiplication is
surrounded by work the bindings never do.

The Python side is not a path nobody reaches. It answers for every curve
that is not secp256k1, for a zero scalar, for the point at infinity, and
for everything else the bindings decline — so what this table says about it
is what a caller outside the fast case actually gets, and why the
delegation is a delegation rather than a rewrite.

## Why BIP32 derivation is not a row, and how that is enforced

btclib's BIP32 has no pure-Python path. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
reason beside the call — BIP32 is defined for secp256k1 and nothing else,
so there is no other curve for a fallback to serve. Throwing the switch
leaves the derivation in C and moves only the public key derived for the
fingerprint, one multiplication out of a whole derivation, so a pair of
rows for it would compare C against C with a Python step added.

That a row belongs here is therefore something to prove.
`tests/pure_python_path_test.py` proves it: it replaces every bindings entry
point with a function that raises, throws the switch, and calls every
operation once. A row that has kept a foot in C raises instead of
answering, and the failure names the call. BIP32 derivation is timed in
[the bitcoin-libraries table][libs] instead, against three other libraries,
where being C is the premise rather than the question.

Two properties of the script are visible in the shape of the output. The
labels say `_pure_python` and not `_python` because every row of every one
of these tables is invoked from Python and the distinction being drawn is
about the arithmetic underneath. And the bindings rows all stand above the
Python rows because `python_arithmetic_only()` cannot be undone inside a
process: each operation is timed through the bindings, the switch is
thrown once, and the sort happens afterwards out of numbers already in
hand.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
