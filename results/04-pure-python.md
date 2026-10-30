# Every pure-Python implementation

## The packages

<!-- provenance: begin -->
```text
package          version           released    held to Python by
btclib           2026.10.30        2026-10-30  its delegation to btclib-secp256k1's cffi bindings switched off
ecc              2026.10.30        2026-10-29  its delegation to btclib-secp256k1's cffi bindings switched off
starkbank-ecdsa  2.3.1             2026-04-23  having no compiled backend at all
pycoin           0.92718.20260405  2026-04-05  PYCOIN_NATIVE=none before its import, resolving to pure Python
ecdsa            0.19.2            2026-03-26  having no compiled backend at all
secp256k1lab     1.0.0             2025-03-26  having no compiled backend at all
buidl            0.2.36            2022-02-28  being imported as buidl.pecc, not buidl.ecc
```
<!-- provenance: end -->

Every row here is Python, so the word belongs in the heading rather than in
every cell; the last column carries what makes it true, which is different for
each of them and is the only part of the claim a reader could doubt. pycoin's
cell is read back after the fact rather than written down: a benchmark that
says Python on a row that loaded a shared object is worse than no benchmark.
`secp256k1lab` is on no index and comes from its git tag, which is still a
release somebody cut on a day.

## This run

<!-- run: begin -->
```text
when    : 2026-10-30 19:41 +07 (12:41 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
commit  : 090c60363adc1833453098ce2061d77d85e842a2
uv.lock : b4fdc6f0fe4ab496c148f7c13430bf4f1c6035704a40258237f28ae753b2e344
```
<!-- run: end -->

## The benchmarks

Microseconds per call, fastest row first, and a ratio against whichever row
came out quickest — no row here is C, so none of them is a reference line and
none is named in advance.

**The `halves` column is what an ordering on this page is checked by.** Each
row is timed in rounds; the rounds are halved, the quickest is what is
published, and the column is how far the two halves' minima sat apart, in the
same microseconds as the value beside it. So it says whether a row agreed with
itself when measured twice, seconds apart — which is what a reader checks an
ordering by before believing it.

What it answers here is not only the ordering. This is the page whose tables
are read by *subtracting*: an unchecked signing row taken from its checked one
is what btclib's own verification costs, and a difference keeps an error that
a ratio would divide away. Without the column, the two subtractions that must
agree could disagree with nothing on the page to say so — which is what [ISS
111][i111] found them doing, the two checked rows having priced one check at
two sizes a factor of two apart. The counts each row is averaged over are
beside it for the same reason.

Read it as this run's agreement with itself and not as an error bar. Two
halves seconds apart say nothing about two runs a day apart; [the wrappers
page][wrappers] pays for a second pass and states that size, and this page
does not.

The inputs are the seeded pool of `_inputs`, cycled: each call takes the
next, so a row is an average over inputs nobody here chose. btclib signs
ECDSA twice, once per row: one signature, which is what the other
implementations produce, and its own default beside it, which grinds until r
fits in 32 bytes.

**btclib's four ECDSA signing rows and its BIP340 pair state both flags of
the check in their name:** `grind` or `nogrind`, then `verify` or
`noverify`, in the order the call performs them. btclib verifies the
signature it has just made before answering with it, by default, on this
arm as much as on the one the switch turns off — a fallback answering a
different question from the arm it stands in for would be two libraries
wearing one name. So the ECDSA verify row below is what the two unchecked
ECDSA signing rows are missing, and the BIP340 verify row what the unchecked
BIP340 row is.

Nowhere else in this project is that check so large a share of what it
protects, and the tables below say why between them: verifying multiplies an
arbitrary point as well as the generator, where signing multiplies the
generator alone and starts from a table `ecc` has already built. Which makes
this the page where one row cannot carry the default: in the ECDSA table
nothing else checks, so a single btclib row would fall behind implementations
that sign and stop and read as arithmetic that had grown slower, when what
changed is that the row had become a different operation from the ones beside
it. [The wrappers table][wrappers] met that with a pair, and this page carries
the same one: an unchecked row for the comparison with the implementations
that check nothing, and a checked row beside it for what the guarantee costs —
[ISS 55][i55] is that decision. The check runs once on the signature the
grinding loop settled on, so the two flags add rather than multiply, and
btclib's ECDSA rows are four rather than two.

Which rows check was read out of each implementation rather than assumed, and
the answer is not the same in the two schemes. **Both BIP340 comparands check
what they signed, and neither can decline**: secp256k1lab ends `schnorr_sign`
on `assert schnorr_verify(...)`, which is how BIP340's own reference code
writes its last step, and buidl verifies under the point its key holds and
raises on a failure. So in that table it is btclib's *checked* row that has
comparands and its unchecked row that stands alone — the same pair read the
other way round, and the reason it has to be a pair rather than a choice
between two rows.

**A third flag joins the ECDSA table alone**: `deterministic` where the nonce
is reproducible from the key and the message, and `hedged` where the call
mixes fresh entropy into it. starkbank-ecdsa is the row that hedges.
`scripts/04-pure-python.py`'s docstring says how each row derives its nonce.

The rows labelled btclib call `btclib.key` for the public key, and the
`ecc.ecc.dsa` and `ecc.ecc.ssa` modules for the signatures and the
verifications, all of them on the curve arithmetic of `ecc.curves`. The
packages block names both releases.

<!-- output: begin -->
```text
method  : 4 rounds per row in two halves, minimum kept; calls per row
command : uv run python scripts/04-pure-python.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/, not by a script
  (CONTRIBUTING.md's Writing a row names where)

public key from a private key: a multiplication of the generator
                                                     μs/call     vs best   halves
  btclib                                              119.09        1.0x     4.00   (4x2,700 calls)
  python-ecdsa                                        279.88        2.4x     1.08   (4x1,800 calls)
  secp256k1lab                                       1260.48       10.6x    18.34   (4x400 calls)
  pycoin                                             5852.42       49.1x    83.97   (4x90 calls)
  buidl.pecc                                        29809.15      250.3x    22.65   (4x17 calls)

ECDSA sign, over a 32-byte digest
                                                     μs/call     vs best   halves
  btclib, nogrind, noverify, deterministic            141.21        1.0x     1.06   (4x3,000 calls)
  starkbank-ecdsa, nogrind, noverify, hedged          286.01        2.0x     1.10   (4x350 calls)
  btclib, grind, noverify, deterministic              290.32        2.1x     1.74   (4x1,300 calls)
  python-ecdsa, nogrind, noverify, deterministic      292.48        2.1x     1.12   (4x1,700 calls)
  btclib, nogrind, verify, deterministic              813.57        5.8x     2.37   (4x500 calls)
  btclib, grind, verify, deterministic                966.15        6.8x    36.90   (4x500 calls)
  pycoin, nogrind, noverify, deterministic           5907.36       41.8x    93.15   (4x88 calls)
  buidl.pecc, nogrind, noverify, deterministic      29990.59      212.4x    32.42   (4x17 calls)

ECDSA verify, over a 32-byte digest
                                                     μs/call     vs best   halves
  btclib                                              643.45        1.0x     3.78   (4x750 calls)
  starkbank-ecdsa                                     794.45        1.2x     0.33   (4x100 calls)
  python-ecdsa                                       1124.02        1.7x     9.76   (4x450 calls)
  pycoin                                            18111.19       28.1x   659.14   (4x28 calls)
  buidl.pecc                                        59769.91       92.9x   630.80   (4x8 calls)

BIP340 sign, over a 32-byte message
                                                     μs/call     vs best   halves
  btclib, noverify                                    283.76        1.0x     0.49   (4x1,500 calls)
  btclib, verify                                      912.37        3.2x     0.28   (4x500 calls)
  secp256k1lab, verify                               7593.78       26.8x    16.45   (4x65 calls)
  buidl.pecc, verify                               103242.06      363.8x    59.56   (4x5 calls)

BIP340 verify, over a 32-byte message
                                                     μs/call     vs best   halves
  btclib                                              636.08        1.0x     2.82   (4x740 calls)
  secp256k1lab                                       5029.56        7.9x    38.86   (4x100 calls)
  buidl.pecc                                        70123.36      110.2x   818.47   (4x7 calls)
```
<!-- output: end -->

## Results

btclib's Python arithmetic leads every table here, `starkbank-ecdsa` is second
in each table it has a row in, ahead of `python-ecdsa`, which is second in the
public-key table, and `buidl.pecc` is last in every table by a distance
nothing on this machine would reorder. In every table they share, btclib and
python-ecdsa are within a factor of each other rather than an order of
magnitude, and the verification table is the closest of the three. That last
is something this run settles rather than suggests, and it is what the
`halves` column buys: the distance printed beside each of those rows is far
smaller than the distance between them, so the ordering is the packages and
not the afternoon.

### Signing: btclib's default is the last row, not the first

btclib is the only implementation in that table which grinds, and the only
one which checks what it signed, so its rows are those two switches thrown
every way and nothing beside them is either. The row a caller gets from
`dsa.sign_(msg, key)` has both on and comes last; the row that compares
with what every other implementation here produces has both off, and it
leads.

Neither is the other made slower. Grinding is more than one signature — it
signs until r fits in 32 bytes — and the check is a verification the rows
beside it never perform, so what separates btclib's rows from each other is
work the comparands do not do rather than arithmetic they do worse. That is
why python-ecdsa comes out ahead of btclib's checked rows while sitting
behind its unchecked one, and why this table is read by subtracting one
btclib row from another rather than by its ranking. Read alone, the
grinding row answers a question nobody asked it: it is not this signature
made slower, it is more than one of them.

### BIP340: why a teaching implementation is a comparand

`secp256k1lab` is a teaching implementation, on no index at all, and it is
here because BIP340 is where btclib has fewer pure-Python comparands than for
ECDSA.

### Verification: two comparands accept more than they should

Two of the comparands verify more than they should, and the verification
rows are where that matters. Run against Wycheproof, whose subject is
adversarial encodings, `pycoin` accepts BER long-form lengths, lengths
that are wrong or that overflow a uint64, and signatures with bytes
appended or taken away; `buidl.pecc` accepts zeros prepended to r and to
s, a truncated r, and an r larger than any verification should admit, and
rejects one valid signature where `k*G` has a large x coordinate. The rows
above are still the cost of verifying a signature a specification
publishes, which both answer correctly — but a verification row is read as
a verification, and theirs admits more than the arithmetic does.
[The libraries table][libs] lists this and the rest of what these packages
get wrong, `tests/vectors_test.py` records every case as an expected
failure, and a release that fixes one turns the suite red.

### What is measured elsewhere

What all of this costs against C is not in this table: that is
[the two-paths table][two], over btclib's own arithmetic, and [the
bitcoin-libraries table][libs], over what `pip install` gives.

pycoin is a Python row here and a C row in that libraries table, the same
version of the same package in both. Nothing was
patched to arrange that: this script sets `PYCOIN_NATIVE` before importing
it, where the other script imports it after something else has already put
libsecp256k1 symbols in the process. Both files print which one they got,
which is why the pair can be read at all.

[two]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md

## More benchmarks

The other sets of benchmarks published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show
- [Silent Payments][sp] — what only `btclib_secp256k1` offers of BIP352,
  which no other comparand here implements at all
- [mnemonics][mnemonics] — BIP39 and SLIP-0039, `bip39-slip39` against
  Trezor's packages and `embit`

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md
[mnemonics]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/07-mnemonics.md
[i55]: https://github.com/btclib-org/btclib-benchmarks/issues/55
[i111]: https://github.com/btclib-org/btclib-benchmarks/issues/111

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
