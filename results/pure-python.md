# every pure-Python implementation, one run

What `scripts/pure_python.py` printed on the machine named below: btclib's
Python arithmetic, `secp256k1lab`, `python-ecdsa`, `pycoin` and
`buidl.pecc`, each doing the same operation. Microseconds per call, fastest
row first, and a ratio against whichever row came out quickest — no row
here is C, so none of them is a reference line and none is named in
advance.

One run, kept whole — the block above the tables says what holds each row
to Python, which is the claim the whole file rests on, and says it once:
with every row Python, a row repeating the word would be a column of it.
Read [README.md][readme] on what these numbers are: an order of magnitude,
never a figure to quote.

The input is BIP340's first test vector, so both implementations that sign
BIP340 here are held to the signature the specification publishes rather
than to btclib's. ECDSA is not: RFC6979's nonce is btclib's own, and no
vendored vector publishes a signature over this message, so those rows stay
checked against each other. btclib signs ECDSA twice, once per row: one
signature, which is what the other implementations produce, and its own
default beside it, which grinds until r fits in 32 bytes.

## What produced it

```text
when    : 2026-08-14 18:24 CEST (16:24 UTC)
python  : 3.13.14
command : uv run python scripts/pure_python.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9
secp256k1lab        : 1.0.0
ecdsa               : 0.19.2
pycoin              : 0.92718.20260405
buidl               : 0.2.36

every row is pure Python arithmetic, held to it by
  btclib              its delegation to btclib_secp256k1's cffi bindings switched off
  pycoin              PYCOIN_NATIVE=none before its import, resolving to pure Python
  buidl               being imported as buidl.pecc, not buidl.ecc
  ecdsa               having no compiled backend at all
  secp256k1lab        having no compiled backend at all


public key from a private key: a multiplication of the generator
                                            vs best
  btclib                       190.26 μs        1.0x
  python-ecdsa                 288.08 μs        1.5x
  secp256k1lab                1335.56 μs        7.0x
  pycoin                      6021.60 μs       31.6x
  buidl.pecc                 30309.05 μs      159.3x

ECDSA sign, over a 32-byte digest
                                            vs best
  btclib                       175.07 μs        1.0x
  python-ecdsa                 301.72 μs        1.7x
  btclib, grinding low-r      1405.69 μs        8.0x
  pycoin                      6234.26 μs       35.6x
  buidl.pecc                 30230.80 μs      172.7x

ECDSA verify, over a 32-byte digest
                                            vs best
  btclib                       762.87 μs        1.0x
  python-ecdsa                1077.19 μs        1.4x
  pycoin                     19419.05 μs       25.5x
  buidl.pecc                 61476.25 μs       80.6x

BIP340 sign, over a 32-byte message
                                            vs best
  btclib                       312.64 μs        1.0x
  secp256k1lab                7904.38 μs       25.3x
  buidl.pecc                 91106.36 μs      291.4x

BIP340 verify, over a 32-byte message
                                            vs best
  btclib                       708.76 μs        1.0x
  secp256k1lab                5201.97 μs        7.3x
  buidl.pecc                 60881.41 μs       85.9x
```

## What it shows

btclib's Python arithmetic leads every table here,
`python-ecdsa` is second in each one it has a row in, and `buidl.pecc` is
last in all five by a distance nothing on this machine would reorder. The
top two are within a small factor of each other in the public key table,
close enough that a busy machine can put either first — which is the reason
to read the ratio column and not the order alone.

`secp256k1lab` is a teaching implementation and reads like one — it is on
no index at all, and it is here because BIP340 is where btclib has fewer
pure-Python comparands than it has for ECDSA, not because anybody would
choose it for speed.

What all of this costs against C is not in this table: that is
[the two-paths table][two], over btclib's own arithmetic, and [the
bitcoin-libraries table][libs], over what `pip install` gives.

pycoin is a Python row here and a C row in that libraries table, the same
version of the same package in both. Nothing was
patched to arrange that: this script sets `PYCOIN_NATIVE` before importing
it, where the other script imports it after something else has already put
libsecp256k1 symbols in the process. Both files print which one they got,
which is why the pair can be read at all.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[two]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
