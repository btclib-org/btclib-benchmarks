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
when    : 2026-08-14 18:22 CEST (16:22 UTC)
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

                                μs/call       vs best
point_parse_bindings             3.7098          1.0x
pubkey_bindings                  8.5492          1.0x
ellswift_decode_bindings         9.6431          1.0x
mult_bindings                    9.6837          1.0x
dh_bindings                      16.049          1.0x
dsa_sign_bindings                17.606          1.0x
taproot_tweak_bindings           17.744          1.0x
ssa_sign_bindings                20.373          1.0x
dsa_verify_bindings              23.392          1.0x
ssa_verify_bindings              23.422          1.0x
bms_verify_bindings              24.429          1.0x
bms_sign_bindings                28.772          1.0x
dsa_recover_bindings             44.164          1.0x
dsa_sign_pure_python             185.45         10.5x
bms_sign_pure_python             359.29         12.5x
mult_pure_python                 148.56         15.3x
ssa_sign_pure_python             314.81         15.5x
ellswift_decode_pure_python      160.38         16.6x
pubkey_pure_python               156.34         18.3x
taproot_tweak_pure_python        336.34         19.0x
point_parse_pure_python          76.410         20.6x
ssa_verify_pure_python           691.47         29.5x
dsa_verify_pure_python           732.69         31.3x
dh_pure_python                   567.18         35.3x
bms_verify_pure_python           1397.0         57.2x
dsa_recover_pure_python          2897.3         65.6x
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
