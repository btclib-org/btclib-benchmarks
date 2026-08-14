# the libsecp256k1 wrappers, one run

What `scripts/libsecp256k1_wrappers.py` printed on the machine named
below: `btclib_secp256k1`, `coincurve`, `secp256k1-py` and `electrum-ecc`
verifying the same ECDSA and BIP340 signatures, every row calling
`bitcoin-core/secp256k1`. Microseconds per call, fastest row first, a
ratio against whichever row came out quickest, and one loop count for all
eight rows.

One run, kept whole — the block naming which revision of libsecp256k1 sits
under each row is not decoration here, it is the premise of the table.
Read [README.md][readme] on what these numbers are: an order of magnitude,
never a figure to quote.

The signature being verified is BIP340's first test vector, not one made by
one of the four packages being compared: where every row wraps the same
library, "they agree with each other" is the check that proves least, and
agreeing with the specification is one with an outside answer.

## What produced it

```text
machine : Apple M5, macOS 26.6 (build 25G72), arm64
when    : 2026-08-14 16:42 CEST (14:42 UTC)
command : uv run python scripts/libsecp256k1_wrappers.py
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib-secp256k1    : 0.8.0.1                  (released)
coincurve           : 21.0.0                   (released)
secp256k1           : 0.14.0                   (released)
electrum-ecc        : 0.0.7                    (released)
python              : 3.13.14

libsecp256k1 under each row
  btclib-secp256k1  0.8.0.1   v0.8.0                  cffi, _btclib_secp256k1.cpython-313-darwin.so
  coincurve         21.0.0    v0.6.0                  cffi, _libsecp256k1.cpython-313-darwin.so
  secp256k1         0.14.0    9526874d, pre-v0.1.0    cffi, _libsecp256k1.cpython-313-darwin.so
  electrum-ecc      0.0.7     v0.7.1                  ctypes, libsecp256k1.6.dylib

ECDSA verify (32-byte digest, the public key parsed per call)
                           us/call     vs best
  dsa_coincurve              14.32       1.00x   (100000 calls)
  dsa_btclib_secp256k1       14.67       1.02x   (100000 calls)
  dsa_secp256k1              16.07       1.12x   (100000 calls)
  dsa_electrum_ecc           16.80       1.17x   (100000 calls)

BIP340 verify (32-byte message, the public key parsed per call)
                           us/call     vs best
  ssa_btclib_secp256k1       14.82       1.00x   (100000 calls)
  ssa_coincurve              15.28       1.03x   (100000 calls)
  ssa_secp256k1              16.01       1.08x   (100000 calls)
  ssa_electrum_ecc           18.70       1.26x   (100000 calls)
```

## What it shows

The four land close together, which is what a table of one C library
should look like: the arithmetic is the same code, and what is left to
measure is the boundary crossing. The ratio column prints two decimals
where the other benchmarks print one, because at one decimal most of this
column would read 1.0x and say nothing.

The ctypes row is last in both tables. The three cffi rows are close
enough that their order among themselves is not something one run on a
machine like this settles — which of them the ratio column calls the
fastest moved between runs while this file was being taken. That is the
column's other use: a row a few percent off the best is not behind it in
any durable sense, and being able to see how few percent is the point.

The revisions are why the closeness is worth stating rather than assuming.
These are four different vendored trees of one project, and the pins above
the timings say so: `btclib_secp256k1`'s is the newest upstream tag of the
four, and `secp256k1-py`'s predates upstream's first tagged release. So a
row is not fast or slow purely as a binding — part of any difference is
which library it was built against, and the output is where that is
visible instead of being a footnote nobody re-derives.

Each pin is keyed to the release it was read from and prints `unrecorded`
for any other, so an upgraded comparand says that it has outgrown its pin
rather than repeating one that has quietly stopped being true.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
