# The libsecp256k1 wrappers

## The packages downloaded from PyPI

The `libsecp256k1 pin` column is the premise of the table below: four
wrappers of one library, not four libraries — four vendored trees of one
project, at different revisions. `btclib-secp256k1`'s is the newest upstream
tag of the four; `secp256k1-py`'s predates upstream's first tagged release.

None of the four can be asked for its revision at run time: no compiled
artifact exports a version symbol, and each package's version attribute
answers for the package rather than for the library. So each pin below is
recorded rather than read, keyed to the release it was read from, and prints
`unrecorded` for any other — an upgraded comparand says it has outgrown its
pin rather than repeating one that has quietly stopped being true. A wrapper
recording its own vendored revision at build time would end the recording
here.

<!-- provenance: begin -->
```text
package           version  released    libsecp256k1 pin      bindings  binary
btclib-secp256k1  0.8.0.2  2026-08-14  v0.8.0                cffi      _btclib_secp256k1.cpython-313-darwin.so
electrum-ecc      0.0.7    2026-02-25  v0.7.1                ctypes    libsecp256k1.6.dylib
coincurve         21.0.0   2025-03-08  v0.6.0                cffi      _libsecp256k1.cpython-313-darwin.so
secp256k1         0.14.0   2021-11-06  9526874d, pre-v0.1.0  cffi      _libsecp256k1.cpython-313-darwin.so
```
<!-- provenance: end -->

## This run

<!-- run: begin -->
```text
when    : 2026-08-15 07:52 CEST (05:52 UTC)
python  : 3.13.14
method  : 30 rounds per row, minimum kept; nothing else repeated
command : uv run python scripts/01-libsecp256k1.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
```
<!-- run: end -->

## The output

Five tables, sorted fastest first and ratioed against whichever row comes out
quickest. The numbers are an order of magnitude, never a figure to quote.

What a timing contains is one call per iteration, its answer discarded: no
row checks itself, and no comparison sits inside a measured loop. The
answers are checked in `tests/vectors_test.py`, and where this script builds
its fixtures, which is before any clock starts.

Every call cycles a published input. Tables 1–2 take a key and a message from
the vector file, but not a signature — none is published for that scheme, so
the four sign with RFC6979 and are compared with each other. Tables 3–4 take
the signature too, which is what makes agreement a check against an outside
answer rather than the four agreeing among themselves. Table 5's tweak
takes the next vector's secret key as the scalar.

<!-- output: begin -->
```text
1. ECDSA sign (32-byte digest), 30x20000 calls each row
                       μs/call        sd     vs best
  secp256k1              11.22    ± 0.16       1.00x
  coincurve              11.30    ± 0.07       1.01x
  btclib_secp256k1       11.99    ± 0.01       1.07x
  electrum_ecc           27.26    ± 0.53       2.43x

2. ECDSA verify (32-byte digest, the public key parsed per call), 30x20000 calls each row
                       μs/call        sd     vs best
  secp256k1              11.73    ± 0.05       1.00x
  coincurve              14.06    ± 0.07       1.20x
  btclib_secp256k1       14.08    ± 0.01       1.20x
  electrum_ecc           15.96    ± 0.05       1.36x

3. BIP340 sign (32-byte message), 30x20000 calls each row
                       μs/call        sd     vs best
  secp256k1               7.80    ± 0.18       1.00x
  btclib_secp256k1       15.85    ± 0.03       2.03x
  coincurve              27.31    ± 0.08       3.50x
  electrum_ecc           31.42    ± 0.41       4.03x

4. BIP340 verify (32-byte message, the public key parsed per call), 30x20000 calls each row
                       μs/call        sd     vs best
  coincurve              14.58    ± 0.03       1.00x
  btclib_secp256k1       14.58    ± 0.03       1.00x
  secp256k1              15.06    ± 0.01       1.03x
  electrum_ecc           18.53    ± 0.50       1.27x

5. public key tweak by a scalar, which is BIP32's step, 30x20000 calls each row
                       μs/call        sd     vs best
  coincurve              10.37    ± 0.02       1.00x
  btclib_secp256k1       10.56    ± 0.03       1.02x
  secp256k1              13.83    ± 0.26       1.33x
  electrum_ecc           22.34    ± 0.21       2.16x
```
<!-- output: end -->

## What it shows

The four land close together, which is what a table of one C library
should look like: the arithmetic is the same code, and what is left to
measure is the boundary crossing.

The ctypes row is last in both verification tables, 2 and 4. The three cffi
rows are close enough that their order among themselves is not settled by one
run on a machine like this — which of them reads fastest moves between runs,
and the `sd` column is how to see that without waiting for another: where two
rows are a few hundredths apart and each round of each scattered by as much,
neither is ahead of the other in any durable sense. Table 4 has such a pair,
and its two are separated by less than either's own scatter.

Read that column as the spread of the rounds rather than as an interval
around the number beside it. The value is the *quickest* round, deliberately
— interference only ever adds time, so the fastest of thirty is the one that
ran with least taken from it — and it therefore sits at the low edge of the
distribution the deviation describes.

## What the rows leave out

A timed call does nothing with what it gets back. Whether the answers are
right is the test suite's subject, `tests/vectors_test.py` running these
vectors against every package measured here, in the configuration it is
measured in; the comparisons the script itself makes are built with the
fixtures, before the clock starts. No number above contains a check.

Three of the four produce the same signature bytes for a key and a message,
libsecp256k1's default nonce being RFC6979. `secp256k1-py` does on x86-64 and
does not on aarch64, so its build disagrees about the nonce or about what it
was handed, which is why what all four are held to is the portable claim:
that the signature verifies.

The last table is BIP32's step rather than BIP32: none of these four packages
implements derivation, and all four expose the primitive it is built from, a
public key tweaked by a scalar. Three of them do it in one call.
`electrum-ecc` has no tweak-add on `ECPubkey`, so its row multiplies the
generator by the scalar and adds the two points: two calls into the C library
where the others make one. BIP32 proper is in [the libraries table][libs],
where the comparands are python libraries rather than secp256k1 wrappers.

## More benchmarks

Four other questions are published in `results/`, each with its own
comparands:

- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
