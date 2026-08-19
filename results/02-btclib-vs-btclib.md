# btclib vs btclib

## This run

<!-- run: begin -->
```text
when    : 2026-08-16 23:22 CEST (21:22 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

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

**The three signing rows below were measured before btclib's signing had a
check**, and they are the only rows here that predate one. btclib verifies
the signature it has just made before answering with it, by default and on
both arms, `verify=False` being a caller declining it, and the lock carries
that btclib.

The script now declines it wherever a row can, and the two rows that can say
so in their names: `dsa_sign_nogrind_noverify` and `ssa_sign_noverify`. That
is what this table's ratio requires rather than a preference — the check is
not the same work on the two arms, a fraction of a signature where
libsecp256k1 answers against a full verification where the Python does, so a
row taking the default would divide one checked signing by another and move a
long way with neither arithmetic having changed. What the default costs is
priced where it is performed: [the wrappers table][wrappers] for the crossing,
and the verification rows below for the Python. Those two rows are therefore
the ones whose next run has least to correct — what they publish is a
signature alone, and a signature alone is what they will publish again.

`bms_sign` is the row with no such choice, and it is the one that will move.
Recoverable signing takes no argument that declines, and what its fast path
performs is not a verification: it recovers the key from the signature and
refuses one that is not the signer's, which reads the recovery id — the one
value the call is made for that nothing downstream re-derives. The
pure-Python arm performs no such check. So the check is paid on the
libsecp256k1 side only, no flag in a name shared by two columns could say so,
and part of what this row prints after the next run is a default of the
bindings rather than the price of the crossing. That row is [ISS 28][i28],
and the run all three wait for is [ISS 23][i23]'s.

**`ssa_sign_held_noverify` is a new row, and its two columns do not save the
same thing.** It signs under an `ssa.Signer`, which holds across calls the
keypair `ssa.sign_` builds and wipes inside each one — and there is a keypair
to hold only where libsecp256k1 answers. With the dispatch off a `Signer`
holds a scalar and every signature is `sign_`'s again, so its pure-Python
column is the pure-Python column of the row above and its ratio is the
crossing multiplied by a saving one side has and the other has not. Read it
against the fresh signing row rather than against the rest of the table.

The row is here because that asymmetry is the answer. What btclib's fallback
cannot offer is as much this page's subject as what it costs, and no page in
this project timed a held signer on either of btclib's arms: [ISS 42][i42].
It is also the one fixture the switch cannot reach — a signer decides which
arm it is on when it is built and keeps the answer, so the held objects are
built once per pass, off the clock both times, by the same call that throws
the switch. Every other fixture here is octets or a point, and is read by
whichever arithmetic is on when the row runs. Written the obvious way, that
row's pure-Python column printed a libsecp256k1 number, silently and
convincingly, and the suite's own pure-Python probe is what said so.

<!-- output: begin -->
```text
btclib 2026.9 (wrapper 0.8.0.3), measured as μs/call, sorted on the ratio

method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/02-btclib-vs-btclib.py

                      libsecp256k1   pure python     ratio
dsa_sign                      15.2           161     10.5x
bms_sign                      27.8           331     11.9x
ssa_sign                      25.7           322     12.5x
pubkey_from_prvkey            10.4           149     14.4x
taproot_tweak                 15.6           234     15.0x
generator_mult                8.23           141     17.1x
pubkey_parse_33               3.50          74.6     21.4x
ellswift_decode               5.51           132     24.0x
bms_verify                    24.7           700     28.3x
ssa_verify                    21.3           659     31.0x
dsa_verify                    20.0           676     33.8x
dsa_recover                   36.0          1300     36.1x
dh_shared_secret              14.4           548     38.1x
```
<!-- output: end -->

## Results

No ratio is under 1.0x: libsecp256k1 wins every operation. What the column
spreads over is the part worth reading, and it sorts the table into two
groups, divided by what the Python side has to multiply.

### The narrow group: multiplying the generator

Every operation whose Python side multiplies the
generator: all three signatures — ECDSA, BIP340 and the bitcoin-message
one, which signs recoverably — the public key from a secret key, the bare
generator multiplication, and the taproot tweak, which adds one such
multiplication to a point. With them sit the two operations that are field
arithmetic rather than a scalar multiplication — parsing a compressed
public key, which is a square root, and ElligatorSwift decoding. btclib
memoizes the generator's multiples, so the Python side of that group
starts from a table it did not have to build.

### The wide group: multiplying an arbitrary point

Every operation that multiplies a point which is *not* the
generator: verification in both schemes, public-key recovery,
bitcoin-message verification — which is a recovery — and Diffie-Hellman.
There is no table for an arbitrary point and btclib builds none, so
Python walks a full-width ladder where the C library walks its own. That
is the same gap [one key, every signature under it][reuse] measures from
the other side, by asking what the second verification under one key
costs.

Inside this group the ratio is widest where the least other work
surrounds the multiplication, and Diffie-Hellman is the end of that: one
such multiplication and nothing else. The pair to read against it is
public-key recovery and bitcoin-message verification, which is that
recovery with signature parsing and hashing around it: the one with more
work in it is the narrower of the two, because that work is in both halves
of the ratio and pulls it towards one.

### What the table cannot be read for

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
[i23]: https://github.com/btclib-org/btclib-benchmarks/issues/23
[i28]: https://github.com/btclib-org/btclib-benchmarks/issues/28
[i42]: https://github.com/btclib-org/btclib-benchmarks/issues/42

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
