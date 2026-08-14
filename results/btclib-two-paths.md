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
machine : Apple M5, macOS 26.6 (build 25G72), arm64
when    : 2026-08-14 17:12 CEST (15:12 UTC)
command : uv run python scripts/btclib_two_paths.py
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9                   (btclib-org/btclib main@30ed0263b116)
btclib-secp256k1    : 0.8.0.1                  (released)
python              : 3.13.14

                                s/10000       vs best
point_parse_bindings           0.035234          1.0x
mult_bindings                  0.081920          1.0x
pubkey_bindings                0.088896          1.0x
ellswift_decode_bindings       0.093277          1.0x
dh_bindings                     0.15643          1.0x
dsa_sign_bindings               0.17107          1.0x
taproot_tweak_bindings          0.17331          1.0x
ssa_sign_bindings               0.20572          1.0x
dsa_verify_bindings             0.22911          1.0x
ssa_verify_bindings             0.23144          1.0x
bms_verify_bindings             0.24952          1.0x
bms_sign_bindings               0.28405          1.0x
dsa_recover_bindings            0.43376          1.0x
dsa_sign_pure_python             1.7330         10.1x
bms_sign_pure_python             3.4287         12.1x
ellswift_decode_pure_python      1.3643         14.6x
ssa_sign_pure_python             3.0427         14.8x
pubkey_pure_python               1.4829         16.7x
mult_pure_python                 1.4005         17.1x
taproot_tweak_pure_python        3.1108         17.9x
point_parse_pure_python         0.74953         21.3x
ssa_verify_pure_python           6.7898         29.3x
dsa_verify_pure_python           6.9310         30.3x
dh_pure_python                   5.5176         35.3x
bms_verify_pure_python           13.649         54.7x
dsa_recover_pure_python          27.936         64.4x
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

## The row that had to be removed, and the check that removed it

BIP32 derivation was a row here. It read about five times slower in Python
where every other row read ten to sixty, which is what a row measuring
something other than what it claims looks like — and it was: btclib's BIP32
has no pure-Python path. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
reason beside the call — BIP32 is defined for secp256k1 and nothing else,
so there is no other curve for a fallback to serve. Throwing the switch
left the derivation in C and moved only the public key derived for the
fingerprint.

Arithmetic on a published table is a poor way to find that, so
`tests/pure_python_path_test.py` now finds it: it replaces every bindings
entry point with a function that raises, throws the switch, and calls every
operation once. A row that has kept a foot in C raises instead of
answering. BIP32 derivation is still timed in [the bitcoin-libraries
table][libs], against three other libraries, where being C is the premise
rather than the question.

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
