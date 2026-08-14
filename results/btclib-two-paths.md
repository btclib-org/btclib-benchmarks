# btclib's two paths, one run

What `scripts/btclib_two_paths.py` printed on the machine named below:
every operation btclib dispatches to the libsecp256k1 bindings, timed
again through its own pure-Python arithmetic. Seconds per thousand calls,
fastest row first, and a ratio against the quicker of the two paths for
that operation — every row here is btclib, so that pairing is the only
comparison in this table that means anything: the fastest row of the whole
table would divide a signature by a point parse.

Fourteen operations, which is not a selection. `_libsecp256k1_serves` is
the predicate every dispatch site in btclib asks, and the rows below are
the operations holding one that a caller would call — with BIP32
derivation added for the opposite reason, asking for no dispatch of its own
and getting one anyway through `curves.sec_point`.

One run, kept whole — the header the script printed above its numbers is
part of it, because a table that does not say which build of btclib it
timed cannot be checked. Nothing was repeated and no outlier was
discarded, so what [README.md][readme] says about reading these applies
here first: an order of magnitude, never a figure to quote.

## What produced it

```text
machine : Apple M5, macOS 26.6 (build 25G72), arm64
when    : 2026-08-14 16:42 CEST (14:42 UTC)
command : uv run python scripts/btclib_two_paths.py
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9                   (btclib-org/btclib main@30ed0263b116)
btclib-secp256k1    : 0.8.0.1                  (released)
python              : 3.13.14

                                s/1000       vs best
point_parse_bindings          0.003531          1.0x
mult_bindings                 0.008191          1.0x
pubkey_bindings               0.008272          1.0x
ellswift_decode_bindings      0.009194          1.0x
dh_bindings                   0.015720          1.0x
dsa_sign_bindings             0.017184          1.0x
taproot_tweak_bindings        0.017229          1.0x
ssa_sign_bindings             0.020200          1.0x
dsa_verify_bindings           0.022869          1.0x
ssa_verify_bindings           0.023121          1.0x
bms_verify_bindings           0.023811          1.0x
bms_sign_bindings             0.031176          1.0x
bip32_derive_bindings         0.033767          1.0x
dsa_recover_bindings          0.043434          1.0x
point_parse_pure_python       0.074923         21.2x
ellswift_decode_pure_python   0.122476         13.3x
mult_pure_python              0.140246         17.1x
pubkey_pure_python            0.147887         17.9x
bip32_derive_pure_python      0.168742          5.0x
dsa_sign_pure_python          0.172511         10.0x
ssa_sign_pure_python          0.302488         15.0x
taproot_tweak_pure_python     0.315211         18.3x
bms_sign_pure_python          0.357373         11.5x
dh_pure_python                0.573763         36.5x
ssa_verify_pure_python        0.677775         29.3x
dsa_verify_pure_python        0.693829         30.3x
bms_verify_pure_python        1.350389         56.7x
dsa_recover_pure_python       2.767919         63.7x
```

## What it shows

Every bindings row is faster than its pure-Python counterpart, and the
sort puts all fourteen of them above all fourteen of the others — on this
machine the two paths do not interleave at all, the slowest thing the
bindings do still beating the quickest thing Python does.

The spread within that is the part worth reading. Verification separates
the paths further than signing does, in both schemes; public-key recovery,
which is verification twice over, separates them further still and is the
widest pair in the table. At the other end sits BIP32 derivation, the
narrowest pair in the table: the difference between its two rows is about
one pure-Python generator multiplication, and everything else a derivation
does — HMAC-SHA512 per step, base58 at the end — is identical on both
paths. The pair says less about the arithmetic than about how little of a
derivation is arithmetic.

The Python side is not a path nobody reaches. It answers for every curve
that is not secp256k1, for a zero scalar, for the point at infinity, and
for everything else the bindings decline — so what this table says about it
is what a caller outside the fast case actually gets, and why the
delegation is a delegation rather than a rewrite.

Two properties of the script are visible in the shape of the output. The
labels say `_pure_python` and not `_python` because every row of every one
of these tables is invoked from Python and the distinction being drawn is
about the arithmetic underneath. And the bindings rows all stand above the
Python rows because `python_arithmetic_only()` cannot be undone inside a
process: each operation is timed through the bindings, the switch is
thrown once, and the sort happens afterwards out of numbers already in
hand.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
