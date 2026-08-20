# Every pure-Python implementation

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package       version           released           held to Python by
btclib        2026.9            main@5f7ad5422544  its delegation to btclib-secp256k1's cffi bindings switched off
pycoin        0.92718.20260405  2026-04-05         PYCOIN_NATIVE=none before its import, resolving to pure Python
ecdsa         0.19.2            2026-03-26         having no compiled backend at all
secp256k1lab  1.0.0             2025-03-26         having no compiled backend at all
buidl         0.2.36            2022-02-28         being imported as buidl.pecc, not buidl.ecc
```
<!-- provenance: end -->

Every row here is Python, so the word belongs in the heading rather than in
five cells; the last column carries what makes it true, which is different
for each of them and is the only part of the claim a reader could doubt.
pycoin's cell is read back after the fact rather than written down: a
benchmark that says Python on a row that loaded a shared object is worse
than no benchmark. `secp256k1lab` is on no index and comes from its git
tag, which is still a release somebody cut on a day.

## This run

<!-- run: begin -->
```text
when    : 2026-08-20 09:25 CEST (07:25 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

Microseconds per call, fastest row first, and a ratio against whichever row
came out quickest — no row here is C, so none of them is a reference line and
none is named in advance.

The inputs are every BIP340 vector the file publishes, cycled: each call takes
the next, so a row is an average over inputs nobody here chose. btclib signs
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
generator alone and starts from a table btclib has already built. Which
makes this the page where one row cannot carry the default: in the ECDSA
table nothing else checks, so a single btclib row would fall behind
implementations that sign and stop and read as arithmetic that had grown
slower, when what changed is that the row had become a different operation
from the ones beside it. [The wrappers table][wrappers] met that with a
pair, and this page carries the same one: an unchecked row for the
comparison with the three that check nothing, and a checked row beside it
for what the guarantee costs — [ISS 55][i55] is that decision, and [ISS
23][i23] the run that carries it. The check runs once on the signature the
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

<!-- output: begin -->
```text
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/04-pure-python.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

public key from a private key: a multiplication of the generator
                                      μs/call     vs best
  btclib                               183.68        1.0x
  python-ecdsa                         269.28        1.5x
  secp256k1lab                        1270.36        6.9x
  pycoin                              5536.40       30.1x
  buidl.pecc                         29794.67      162.2x

ECDSA sign, over a 32-byte digest
                                      μs/call     vs best
  btclib, nogrind, noverify            161.85        1.0x
  python-ecdsa, nogrind, noverify      292.09        1.8x
  btclib, grind, noverify              380.51        2.4x
  btclib, grind, verify               1013.90        6.3x
  btclib, nogrind, verify             1483.03        9.2x
  pycoin, nogrind, noverify           5703.13       35.2x
  buidl.pecc, nogrind, noverify      29829.55      184.3x

ECDSA verify, over a 32-byte digest
                                      μs/call     vs best
  btclib                               659.41        1.0x
  python-ecdsa                        1089.68        1.7x
  pycoin                             17752.52       26.9x
  buidl.pecc                         59596.86       90.4x

BIP340 sign, over a 32-byte message
                                      μs/call     vs best
  btclib, noverify                     320.80        1.0x
  btclib, verify                       976.72        3.0x
  secp256k1lab, verify                7613.43       23.7x
  buidl.pecc, verify                103897.65      323.9x

BIP340 verify, over a 32-byte message
                                      μs/call     vs best
  btclib                               673.34        1.0x
  secp256k1lab                        5057.73        7.5x
  buidl.pecc                         70935.72      105.3x
```
<!-- output: end -->

## Results

btclib's Python arithmetic leads every table here,
`python-ecdsa` is second in each one it has a row in, and `buidl.pecc` is
last in all five by a distance nothing on this machine would reorder. In
every table they share, btclib and python-ecdsa are within a factor of each
other rather than an order of magnitude, and which of the three tables is the
closest is not a gap this run settles — everywhere else on this page the gaps
are wide enough that the order is not in question, which is why the ratio
column is the one to read and not the ranking.

### Signing: btclib's own default is the row above it

The one place another implementation's number comes out smaller than a
btclib number is the signing table, and what is above btclib there is
btclib's own default. btclib grinds for a low-r signature unless told
not to — it signs until r fits in 32 bytes — so that row is not one
signature but as many as this key and this message take, and nothing
else in this file grinds. The two rows are one switch thrown both ways
and are labelled as such: the comparable row is the other one, which is
what every other implementation here produces, and it leads. Read as a
pair they say what a caller who writes `dsa.sign_(msg, key)` waits for
and what the signature underneath it costs. Read alone, the grinding row
would answer a question nobody asked it — it is not this signature made
slower, it is more than one of them.

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

Five other sets of benchmarks are published in `results/`, each with its own
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

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md
[i23]: https://github.com/btclib-org/btclib-benchmarks/issues/23
[i55]: https://github.com/btclib-org/btclib-benchmarks/issues/55

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
