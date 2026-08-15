# Every pure-Python implementation

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package       version           released           held to Python by
btclib        2026.9            main@95b03da34a71  its delegation to btclib-secp256k1's cffi bindings switched off
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
when    : 2026-08-15 22:10 CEST (20:10 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The output

Microseconds per call, fastest row first, and a ratio against whichever row
came out quickest — no row here is C, so none of them is a reference line and
none is named in advance.

The inputs are every BIP340 vector the file publishes, cycled: each call takes
the next, so a row is an average over inputs nobody here chose. btclib signs
ECDSA twice, once per row: one signature, which is what the other
implementations produce, and its own default beside it, which grinds until r
fits in 32 bytes.

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
  btclib                          188.43        1.0x
  python-ecdsa                    220.21        1.2x
  secp256k1lab                    919.04        4.9x
  pycoin                         5862.55       31.1x
  buidl.pecc                    20621.20      109.4x

ECDSA sign, over a 32-byte digest
                                 μs/call     vs best
  btclib, one signature           164.82        1.0x
  python-ecdsa                    291.80        1.8x
  btclib, grinding (default)      612.43        3.7x
  pycoin                         6014.59       36.5x
  buidl.pecc                    29485.50      178.9x

ECDSA verify, over a 32-byte digest
                                 μs/call     vs best
  btclib                          800.78        1.0x
  python-ecdsa                   1134.17        1.4x
  pycoin                        18901.23       23.6x
  buidl.pecc                    60552.40       75.6x

BIP340 sign, over a 32-byte message
                                 μs/call     vs best
  btclib                          330.25        1.0x
  secp256k1lab                   7360.47       22.3x
  buidl.pecc                   108874.08      329.7x

BIP340 verify, over a 32-byte message
                                 μs/call     vs best
  btclib                          662.63        1.0x
  secp256k1lab                   5082.25        7.7x
  buidl.pecc                    67038.09      101.2x
```
<!-- output: end -->

## What it shows

btclib's Python arithmetic leads every table here,
`python-ecdsa` is second in each one it has a row in, and `buidl.pecc` is
last in all five by a distance nothing on this machine would reorder. The
top two are within a small factor of each other in the public key table,
close enough that a busy machine can put either first — which is the reason
to read the ratio column and not the order alone.

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

`secp256k1lab` is a teaching implementation, on no index at all, and it is
here because BIP340 is where btclib has fewer pure-Python comparands than for
ECDSA.

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

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
