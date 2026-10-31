# btclib vs btclib

## The packages

<!-- provenance: begin -->
```text
ecc                 : 2026.10.30
btclib              : 2026.10.30
btclib-secp256k1    : 0.8.0.13
```
<!-- provenance: end -->

## This run

<!-- run: begin -->
```text
mode    : release
when    : 2026-10-30 19:25 +07 (12:25 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
commit  : 090c60363adc1833453098ce2061d77d85e842a2
uv.lock : b4fdc6f0fe4ab496c148f7c13430bf4f1c6035704a40258237f28ae753b2e344
```
<!-- run: end -->

## The benchmarks

Not btclib against btclib-secp256k1: `pip install btclib[secp256k1]` installs
both, and every row is btclib called the same way. What differs is which
arithmetic answers — the libsecp256k1 that btclib-secp256k1 compiles into a
cffi extension, or the Python of `ecc/curves/curve_group.py` with the dispatch
off. That file is in the `ecc` release the packages block above names: btclib
takes its curve and its signature schemes from `ecc`, and a row whose
operation is btclib's own, such as `bms_sign` or `taproot_tweak`, reaches that
arithmetic through btclib.

The inputs are drawn from a seed written into the script, as [the wrappers
table][wrappers] draws its own: a secret key and a message per call, and
each operation reads a slice of that stream long enough for its longest
column, so no row measures one input repeated. Random rather than
published, because both columns of a row are btclib computing the same
answer two ways — a vector proves nothing about either that another input
would not, and correctness is `tests/vectors_test.py`'s subject, where the
vectors are run against both paths.

No row checks what it computed, and nothing in this benchmark asserts: a
comparison inside a timed loop would be time charged to an arithmetic that did
not spend it. The dispatch sites ask `ecc.curves.curve._libsecp256k1_serves`
or `ecc.curves.is_libsecp256k1_serving`, and both read the one switch
`python_arithmetic_only` throws. The rows are operations reachable through a
public function; BIP32 and silent payments have a Python arm and no row here.

`pubkey_parse_33` carries its size in its name because the size is what it
is timing: a compressed key is x alone, so parsing one is a modular square
root, and that root is the only part of a parse btclib delegates. There is
no 65-byte row because there would be nothing to compare — the
uncompressed form hands both coordinates over and is read in Python either
way, one code path with no dispatch in it.

**Two of the three signing rows below decline btclib's signing check
explicitly, and say so in their own names.** btclib verifies the signature
it has just made before answering with it, by default and on both arms,
`verify=False` being a caller declining it, and the lock carries that
btclib. `dsa_sign_nogrind_noverify` and `ssa_sign_noverify` pass it, and
that is what this table's ratio requires rather than a preference — the
check is not the same work on the two arms, a fraction of a signature where
libsecp256k1 answers against a full verification where the Python does, so a
row taking the default would divide one checked signing by another and move
a long way with neither arithmetic having changed. What the default costs is
priced where it is performed: [the wrappers table][wrappers] for the
crossing, and the verification rows below for the Python. These two rows
publish a signature alone regardless of what btclib's own default is, which
is the point of naming the flag rather than reading it off btclib's current
behaviour.

`bms_sign` is the row with no such choice. Recoverable signing takes no
argument that declines, and what its fast path performs is not a
verification: it recovers the key from the signature and refuses one that
is not the signer's, which reads the recovery id — the one value the call is
made for that nothing downstream re-derives. The pure-Python arm performs no
such check. So the check is paid on the libsecp256k1 side only, and no flag
in a name shared by two columns could say so: what this row prints is a
default of the bindings folded into the price of the crossing rather than
separable from it, and its ratio is the narrowest on this page for that
reason rather than because the crossing buys least here.

The two rows above decline their check and this one cannot, which is a
decision rather than an omission, and btclib's call site is where it is
argued. What the bindings perform here is not the verification those two
decline: it is a recovery, and what it establishes is the recovery id — the
one value this call is made for that nothing downstream re-derives. A
faulted r or s fails the first verification anybody makes; a wrong id fails
nobody, and is found by whoever relied on it. So the check answers a
question the caller has no other way to ask, which is why no argument
declines it and why this row prices a guarantee rather than choosing
against one. [ISS 28][i28] is where that was settled.

**`ssa_sign_held_noverify`'s two columns do not save the same thing.** It
signs under `ecc.ecc.ssa.Signer`, which holds across calls what `ssa.sign_`
builds inside each one. Where libsecp256k1 answers that is a keypair; with the
dispatch off it is the key's public point, multiplied once when the signer is
built. Each column saves a multiplication of the generator against the fresh
signing row above it, but not the same share of a signature, so this row's
ratio is not the crossing alone. Read it against the fresh signing row rather
than against the rest of the table.

The row is here because a caller who signs again holds a signer, on either
arm: [ISS 42][i42]. It is also the one fixture the switch cannot reach — a
signer built while libsecp256k1 answers holds a keypair and signs on the
bindings for the rest of its life, so the held objects are built once per
pass, off the clock both times, by the same call that throws the switch. Every
other fixture here is octets or a point, and is read by whichever arithmetic
is on when the row runs. Written the obvious way, that row's pure-Python
column printed a libsecp256k1 number, silently and convincingly, and the
suite's own pure-Python probe is what said so.

**`ellswift_xdh` is ElligatorSwift's x-only ECDH, beside the decode above
it.** `ecc/ecc/ellswift.py` gates each of its public functions on the same
dispatch this page reads every other row through. `create` and `encode_var`
draw fresh randomness on every call, which is why an encoded form is built
once as a fixture and never timed, `decode_var` being the deterministic half
of that pair. The row's `xdh` is btclib's, in `btclib.ecc.ellswift`: it
decodes with `ecc`'s `decode_var` and multiplies with `ecc`'s `mult`, and
reaches the dispatch through those two. It is deterministic too — nothing is
drawn inside it, only hashed — so it is timed the same way `decode_var` is,
over a fixture key paired with the next key's encoding in its own slice, the
same construction `dh_shared_secret` already uses for its counterparty. It
multiplies one point that is not the generator, so it joins the wide group
below rather than the narrow one decoding sits in.

<!-- output: begin -->
```text
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/02-btclib-vs-btclib.py

μs/call, sorted on the ratio
                             libsecp256k1   pure python     ratio
bms_sign                             49.9           283      5.7x
dsa_sign_nogrind_noverify            13.5           142     10.5x
ssa_sign_noverify                    23.9           280     11.7x
pubkey_from_prvkey                   9.36           124     13.3x
taproot_tweak                        15.3           203     13.3x
pubkey_parse_33                      4.74          66.1     13.9x
generator_mult                       8.20           126     15.3x
ssa_sign_held_noverify               9.34           158     16.9x
ellswift_decode                      5.68           102     17.9x
bms_verify                           31.1           669     21.5x
ellswift_xdh                         23.8           604     25.4x
dh_shared_secret                     18.5           504     27.2x
dsa_verify                           24.7           708     28.6x
ssa_verify                           20.2           631     31.3x
dsa_recover                          35.8          1250     34.8x
```
<!-- output: end -->

## Results

No ratio is under 1.0x: libsecp256k1 wins every operation. What the column
spreads over is the part worth reading, and it sorts the table into two
groups, divided by what the Python side has to multiply.

### The narrow group: multiplying the generator

Every operation whose Python side multiplies the generator: all three
signatures — ECDSA, BIP340 and the bitcoin-message one, which signs
recoverably — the public key from a secret key, the bare generator
multiplication, and the taproot tweak, which adds one such multiplication to a
point. With them sit the two operations that are field arithmetic rather than
a scalar multiplication — parsing a compressed public key, which is a square
root, and ElligatorSwift decoding. `ecc` memoizes the generator's multiples,
so the Python side of that group starts from a table it did not have to build.

### The wide group: multiplying an arbitrary point

Every operation that multiplies a point which is *not* the generator:
verification in both schemes, public-key recovery, bitcoin-message
verification — which is a recovery — Diffie-Hellman and ElligatorSwift's ECDH.
There is no table for an arbitrary point unless a caller asks `ecc` for one
with `PreparedPoint`, which no row here does, so Python walks a full-width
ladder where the C library walks its own. That is the same gap [one key, every
signature under it][reuse] measures from the other side, by asking what the
second verification under one key costs.

Inside this group the order is not set by how little work surrounds the
multiplication: Diffie-Hellman, one such multiplication and nothing else, sits
below both verifications and the recovery in this run. The pair to read
against each other is public-key recovery and bitcoin-message verification,
which is that recovery with signature parsing and hashing around it: the one
with more work in it is the narrower of the two, because that work is in both
halves of the ratio and pulls it towards one.

### What the table cannot be read for

The whole libsecp256k1 column is timed before the whole Python one, because
the script calls `python_arithmetic_only()` once and never undoes it. The
sort is applied afterwards, to numbers already in hand.

The Python side is not a path nobody reaches: it answers for every curve
that is not secp256k1, for a zero scalar, for the point at infinity, and for
anything else outside libsecp256k1's entry points. What this table says about
it is what a caller outside the fast case gets.

## BIP32 derivation is not a row

BIP32 is `btclib-wallet`'s, and its Python arm is behind `ecc`'s
`is_libsecp256k1_serving`, so `python_arithmetic_only` reaches it. It is no
row here because none was asked for. The dispatch is on the bindings being
there and not on the curve, BIP32 being defined for secp256k1 alone.

BIP32 derivation is timed in [the libraries table][libs] instead, where being
C is the premise.

## More benchmarks

The other sets of benchmarks published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show
- [Silent Payments][sp] — what only `btclib_secp256k1` offers of BIP352,
  which no other comparand here implements at all
- [mnemonics][mnemonics] — BIP39 and SLIP-0039, `bip39-slip39` against
  Trezor's packages and `embit`

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md
[mnemonics]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/07-mnemonics.md
[i28]: https://github.com/btclib-org/btclib-benchmarks/issues/28
[i42]: https://github.com/btclib-org/btclib-benchmarks/issues/42

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
