# btclib vs btclib

## This run

<!-- run: begin -->
```text
when    : 2026-08-16 09:17 CEST (07:17 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The output

Not btclib against btclib-secp256k1: `pip install btclib` installs both, and
every row is btclib called the same way. What differs is which arithmetic
answers — the libsecp256k1 that btclib-secp256k1 compiles into a cffi
extension, or the Python of `curves/curve_group.py` with the dispatch off.

The inputs are drawn from a seed written into the script, as [the wrappers
table][wrappers] draws its own: a secret key and a message per call, and
each operation reads a slice of that stream long enough for its longest
column, so no row measures one input repeated. Random rather than
published, because both columns of a row are btclib computing the same
answer two ways — a vector proves nothing about either that another input
would not, and correctness is `tests/vectors_test.py`'s subject, where the
vectors are run against both paths.

No row checks what it computed, and nothing in this benchmark asserts: a
comparison inside a timed loop would be time charged to an arithmetic that
did not spend it. The operations are not a selection —
`_libsecp256k1_serves` is the predicate every dispatch site in btclib asks,
and every operation holding one that a caller would call is below.

`pubkey_parse_33` carries its size in its name because the size is what it
is timing: a compressed key is x alone, so parsing one is a modular square
root, and that root is the only part of a parse btclib delegates. There is
no 65-byte row because there would be nothing to compare — the
uncompressed form hands both coordinates over and is read in Python either
way, one code path with no dispatch in it.

<!-- output: begin -->
```text
btclib 2026.9 (wrapper 0.8.0.3), measured as μs/call, sorted on the ratio

method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/02-btclib-vs-btclib.py

                      libsecp256k1   pure python     ratio
dsa_sign                      23.0           184      8.0x
bms_sign                      32.7           362     11.1x
pubkey_from_prvkey            14.7           166     11.3x
ssa_sign                      29.2           363     12.4x
generator_mult                11.7           156     13.3x
taproot_tweak                 19.4           264     13.6x
pubkey_parse_33               5.57          83.7     15.0x
ellswift_decode               6.87           150     21.9x
bms_verify                    29.2           775     26.5x
dsa_verify                    28.7           772     26.9x
ssa_verify                    24.9           746     30.0x
dsa_recover                   44.3          1480     33.5x
dh_shared_secret              17.1           616     36.1x
```
<!-- output: end -->

## What it shows

No ratio is under 1.0x: libsecp256k1 wins every operation. What the column
spreads over is the part worth reading, and it sorts the table into two
groups, divided by what the Python side has to multiply.

The narrow group is every operation whose Python side multiplies the
generator: both signatures, the public key from a secret key, the bare
generator multiplication, and the taproot tweak, which adds one such
multiplication to a point. With them sit the two operations that are field
arithmetic rather than a scalar multiplication — parsing a compressed
public key, which is a square root, and ElligatorSwift decoding. btclib
memoizes the generator's multiples, so the Python side of that group
starts from a table it did not have to build.

The wide group is every operation that multiplies a point which is *not*
the generator: verification in both schemes, public-key recovery,
bitcoin-message verification — which is a recovery — and Diffie-Hellman.
There is no table for an arbitrary point and btclib builds none, so
Python walks a full-width ladder where the C library walks its own. That
is the same gap [one key, every signature under it][reuse] measures from
the other side, by asking what the second verification under one key
costs.

Inside the wide group the ratio is widest where the least other work
surrounds the multiplication, and Diffie-Hellman is the end of that: one
such multiplication and nothing else. The pair to read against it is
public-key recovery and bitcoin-message verification, which is that
recovery with signature parsing and hashing around it: the one with more
work in it is the narrower of the two, because that work is in both halves
of the ratio and pulls it towards one.

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

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
