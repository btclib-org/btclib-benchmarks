# btclib vs btclib

## This run

```text
when    : 2026-08-14 23:34 CEST (21:34 UTC)
python  : 3.13.14
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/btclib_two_paths.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

Not btclib against btclib-secp256k1: `pip install btclib` installs both, and
every row is btclib called the same way. What differs is which arithmetic
answers — the libsecp256k1 that btclib-secp256k1 compiles into a cffi
extension, or the Python of `curves/curve_group.py` with the dispatch off.

Every row cycles the published vectors, taking the next input per call, and no
row checks what it computed: the answers are `tests/vectors_test.py`'s
subject, and a comparison inside a timed loop would be time charged to an
arithmetic that did not spend it. The operations are not a selection —
`_libsecp256k1_serves` is the predicate every dispatch site in btclib asks,
and every operation holding one that a caller would call is below.

```text
btclib 2026.9 (bindings 0.8.0.2), measured as μs/call, sorted on the ratio

                      libsecp256k1   pure python     ratio
dsa_sign                    18.998        173.64      9.1x
bms_sign                    30.229        339.05     11.2x
ssa_sign                    24.679        320.98     13.0x
pubkey                      10.260        148.11     14.4x
ellswift_decode             9.3432        138.89     14.9x
mult                        8.1802        138.17     16.9x
taproot_tweak               17.165        306.25     17.8x
point_parse                 3.8501        76.411     19.8x
ssa_verify                  23.439        678.19     28.9x
dsa_verify                  23.040        667.02     29.0x
dh                          13.871        544.55     39.3x
bms_verify                  23.777        1321.7     55.6x
dsa_recover                 42.763        3210.0     75.1x
```

## What it shows

No ratio is under 1.0x: the bindings win every operation on this machine.
What the column spreads over is the part worth reading. Verification
separates the two arithmetics further than signing does, in both schemes;
public-key recovery, which is verification and then some, separates them
furthest, and bitcoin-message verification next, being a recovery with
hashing around it. At the narrow end sit signing and ElligatorSwift decoding,
where one multiplication is surrounded by work the C never does.

The whole libsecp256k1 column is timed before the whole Python one, because
`python_arithmetic_only()` cannot be undone inside a process. The sort is
applied afterwards, to numbers already in hand.

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
[the libraries table][libs] instead, where being C is the premise.

## More benchmarks

Four other questions are published in `results/`, each with its own
comparands:

- [the libsecp256k1 bindings][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [python libraries][libs] — where bindings (if available) are just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/libsecp256k1-wrappers.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/key-reuse.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
