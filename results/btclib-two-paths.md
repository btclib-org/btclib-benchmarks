# btclib vs btclib

## This run

```text
when    : 2026-08-14 23:39 CEST (21:39 UTC)
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
dsa_sign                    16.546        160.62      9.7x
bms_sign                    28.170        324.95     11.5x
ssa_sign                    25.416        323.07     12.7x
taproot_tweak               17.789        236.33     13.3x
pubkey_from_prvkey          10.275        149.94     14.6x
ellswift_decode             9.3297        145.37     15.6x
generator_mult              8.2929        141.65     17.1x
pubkey_parse                3.5835        74.935     20.9x
bms_verify                  24.035        714.60     29.7x
dsa_recover                 41.546        1325.2     31.9x
ssa_verify                  20.939        681.12     32.5x
dsa_verify                  19.907        678.35     34.1x
dh_shared_secret            14.045        548.47     39.1x
```

## What it shows

No ratio is under 1.0x: the bindings win every operation.
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

BIP32 derivation is timed in [the libraries table][libs] instead, where being
C is the premise.

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
