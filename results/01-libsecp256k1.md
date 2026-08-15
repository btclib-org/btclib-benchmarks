# The libsecp256k1 wrappers

## The packages downloaded from PyPI

The `libsecp256k1 pin` column is the premise of the table below: four
wrappers of one library, not four libraries — four vendored trees of one
project, at different revisions.

None of the four can be asked for its revision at run time: no compiled
artifact exports a version symbol, and each package's version attribute
answers for the package rather than for the library. So each pin below is
recorded rather than read, keyed to the build it was read from, and prints
`unrecorded` for any other — an upgraded comparand says it has outgrown its
pin rather than repeating one that has quietly stopped being true. A wrapper
recording its own vendored revision at build time would end the recording
here.

`btclib-secp256k1` is the one row with a commit where the others have a
date: it resolves from its branch until the release these rows are written
against is published, so what identifies that build is the commit, and that
is what its pin is keyed to. The others are releases, and their version is
what identifies them.

<!-- provenance: begin -->
```text
package           version  released           libsecp256k1 pin      bindings
btclib-secp256k1  0.8.0.3  main@d9933e49e793  v0.8.0                cffi
electrum-ecc      0.0.7    2026-02-25         v0.7.1                ctypes
coincurve         21.0.0   2025-03-08         v0.6.0                cffi
secp256k1         0.14.0   2021-11-06         9526874d, pre-v0.1.0  cffi
```
<!-- provenance: end -->

## This run

3.13 rather than 3.14 is not this page's choice: coincurve and secp256k1
publish no cp314 wheel, and neither builds from source without
`pkg-config`, so the interpreter below is the newest that runs all four
wrappers.

<!-- run: begin -->
```text
when    : 2026-08-16 01:52 CEST (23:52 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The output

Nine tables, sorted fastest first and ratioed against whichever row comes out
quickest. The numbers are an order of magnitude, never a figure to quote.

What a timing contains is one call per iteration and its answer thrown away.
Nothing is compared, verified or asserted anywhere in this benchmark —
whether these packages answer correctly is `tests/vectors_test.py`'s subject,
where the published vectors are.

The inputs are drawn from a seed written into the script: a secret key and a
message per call, and as many of each as every table together has calls, so
each table reads a slice of its own. A round consumes that slice exactly once,
no row measures one input repeated, and no table is quick because the one
before it left the same key in a cache. Every table starts from the same
shapes — the keys as 32-byte scalars, the public keys derived from them, the
signatures made once in the fixtures — and no row is handed an object a
package built: whatever an API makes a caller construct before it can work is
constructed inside the call that needs it.

Random rather than published, because four wrappers of one C library compute
the same arithmetic by construction: a vector proves nothing here that
another input would not, and what this page is read for is the boundary
crossing.

Three of the nine tables are one operation asked twice. Signing and verifying
are measured in DER and in the 64-byte compact form, and a public key is
parsed compressed and uncompressed — each pair differing by an encoding
rather than by any arithmetic, so what the pair prices is the encoding. Both
verification tables are handed the 65-byte uncompressed key, and price the
parse of it per call; BIP340's takes the x-only key where an API asks for one
and the same uncompressed key where it does not.

Only what a package offers is measured. Where its own API has no such call
the row reads `NA` — coincurve signs and verifies ECDSA in DER alone, so it
has no row in either compact table. Reaching into the cffi or ctypes bindings
underneath would produce a number, and the number would be libsecp256k1's
rather than the wrapper's.

<!-- output: begin -->
```text
method  : 10000 calls each round, 30 rounds per row, minimum kept
command : uv run python scripts/01-libsecp256k1.py

1. ECDSA sign (32-byte digest, DER out)
                       μs/call     vs best   spread
  btclib_secp256k1       12.70       1.00x     0.11
  secp256k1              26.67       2.10x     0.38
  coincurve              26.80       2.11x     0.79
  electrum_ecc           48.06       3.79x     0.83

2. ECDSA sign (32-byte digest, 64-byte compact out)
                       μs/call     vs best   spread
  btclib_secp256k1       12.57       1.00x     0.63
  secp256k1              26.74       2.13x    10.12
  electrum_ecc           45.60       3.63x     0.87
  coincurve                 NA

3. BIP340 sign (32-byte message)
                       μs/call     vs best   spread
  btclib_secp256k1       16.09       1.00x     0.32
  secp256k1              22.84       1.42x     0.74
  coincurve              43.54       2.71x     0.96
  electrum_ecc           49.23       3.06x     1.03

4. public key parse (a 33-byte compressed key)
                       μs/call     vs best   spread
  coincurve               2.39       1.00x     0.05
  btclib_secp256k1        2.41       1.01x     0.05
  secp256k1               2.80       1.17x     0.04
  electrum_ecc            3.32       1.39x     0.05

5. public key parse (a 65-byte uncompressed key)
                       μs/call     vs best   spread
  coincurve               0.24       1.00x     0.04
  btclib_secp256k1        0.28       1.19x     0.01
  secp256k1               0.66       2.77x     0.04
  electrum_ecc            1.18       4.99x     0.05

6. ECDSA verify (DER signature, the 65-byte key parsed per call)
                       μs/call     vs best   spread
  coincurve              13.23       1.00x     0.20
  secp256k1              13.77       1.04x     5.72
  btclib_secp256k1       13.93       1.05x     7.27
  electrum_ecc           17.53       1.33x     6.59

7. ECDSA verify (64-byte signature, the 65-byte key parsed per call)
                       μs/call     vs best   spread
  secp256k1              13.76       1.00x     9.93
  btclib_secp256k1       13.87       1.01x     0.44
  electrum_ecc           15.16       1.10x     0.51
  coincurve                 NA

8. BIP340 verify (32-byte message, the public key parsed per call)
                       μs/call     vs best   spread
  secp256k1              13.73       1.00x     0.49
  coincurve              15.41       1.12x     4.85
  btclib_secp256k1       15.93       1.16x     1.21
  electrum_ecc           17.31       1.26x     0.10

9. public key tweak by a scalar, which is BIP32's step
                       μs/call     vs best   spread
  coincurve              10.29       1.00x     0.23
  btclib_secp256k1       11.49       1.12x     0.14
  secp256k1              13.81       1.34x     0.26
  electrum_ecc           22.83       2.22x     2.13
```
<!-- output: end -->

## What it shows

The verification tables land close together, which is what a table of one C
library should look like: the arithmetic is the same code, and what is left
to measure is the boundary crossing. What separates rows anywhere on this
page is what a wrapper makes a caller do before, after or around that call.

The signing tables are where a wrapper's own habits cost the most, and none
of it is arithmetic. Two of the four sign only through a key object of their
own — coincurve's `PrivateKey` and secp256k1-py's — and building one derives
the public key, work a signature does not need and a caller cannot decline.
Two others verify the signature they just made before handing it back —
coincurve's `sign_schnorr`, electrum-ecc's `schnorr_sign` and its
`ecdsa_sign` — which is a verification's worth of time inside a signature's
row, and again no caller can decline it. btclib-secp256k1 leads all three
signing tables because it does neither.

The parse pair says the same thing about a public key. The uncompressed
parse is the cheapest row on the page — the encoding carries y, so there is
nothing to solve — and the compressed parse of the same key costs many times
it, that being a square root modulo p. Every verification and every tweak
repeats one of those parses per call, so the two tables are the subtraction
to read the others against. electrum-ecc pays the most for it in both, its
`ECPubkey` holding x and y as Python integers rather than the object
libsecp256k1 read, and parsing again on every use.

BIP340 signing is the one operation where a keypair has to be built no
matter what: ECDSA takes the secret key as it is, and Schnorr does not, so
that table spreads where table 1's four rows are the same C with four
argument conventions around it.

The tweak table is BIP32's step rather than BIP32: none of these four
packages implements derivation, and all four expose the primitive it is
built from. `electrum-ecc` has no tweak-add on `ECPubkey`, so its row
multiplies the generator by the scalar and adds the two points — two calls
into the C library where the others make one, and its row is last by about
what a second crossing costs. BIP32 proper is in [the libraries table][libs],
where the comparands are python libraries rather than secp256k1 wrappers.

Where two rows are close enough that a round or two could reorder them, the
`spread` column is how to see it without waiting for another run: a gap
smaller than the scatter behind either row is not a gap this run settled, and
which of the two prints first is then a property of the run rather than of
the packages.

## What the rows leave out

Nothing is measured that a package does not offer. A row is either its own
API's call or `NA`, and no gap is filled from the C underneath: a wrapper
that leaves an encoding to its caller is a wrapper that leaves an encoding to
its caller, and a table that hid it would be a table about libsecp256k1.

`electrum-ecc` is the only one of the four offering low-r grinding, and its
rows do not grind: a row that signs until r fits in 32 bytes is a multiple of
a row that signs once, and every other row here signs once.

Nothing here says whether any of the four is correct. That is deliberate and
it is not a gap: `tests/vectors_test.py` runs BIP340's vectors, Wycheproof's
and BIP32's against every implementation this project measures, in the
configuration it measures it in, negative cases included. A benchmark that
re-checked them would be a slower copy of a test that already exists, over
inputs nobody published — and four wrappers of one library agreeing with
each other is the weakest evidence available in any case.

## More benchmarks

Four other sets of benchmarks are published in `results/`, each with its own
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
