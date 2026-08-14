# every pure-Python implementation, one run

What `scripts/pure_python.py` printed on the machine named below: btclib's
own Python arithmetic, `secp256k1lab`, `python-ecdsa`, `pycoin` and
`buidl.pecc`, each doing the same operation, with btclib's bindings as the
reference line. Microseconds per call, fastest row first, a ratio against
the quickest row of each table — the bindings, here — and one against the
quickest *Python* row, which is how the fallbacks compare with each other.
Neither column is against a row named in advance.

One run, kept whole — the setup block above the tables is where each row
says it really is Python, which is the claim the whole file rests on. Read
[README.md][readme] on what these numbers are: an order of magnitude,
never a figure to quote.

The input is BIP340's first test vector, so both implementations that sign
BIP340 here are held to the signature the specification publishes rather
than to btclib's. ECDSA is not: RFC6979's nonce is btclib's own, and no
vendored vector publishes a signature over this message, so those rows stay
checked against each other.

## What produced it

```text
machine : Apple M5, macOS 26.6 (build 25G72), arm64
when    : 2026-08-14 16:42 CEST (14:42 UTC)
command : uv run python scripts/pure_python.py
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9                   (btclib-org/btclib main@30ed0263b116)
btclib-secp256k1    : 0.8.0.1                  (released)
python              : 3.13.14

btclib                2026.9, bindings the reference
btclib_secp256k1      0.8.0.1
secp256k1lab          1.0.0, pure Python
buidl                 0.2.36, through buidl.pecc
ecdsa                 0.19.2, pure Python
pycoin                0.92718.20260405, backend: pure Python


public key from a private key: a multiplication of the generator
                                            vs best   vs best Python
  btclib, the bindings           8.97 us        1.0x               --
  btclib, Python               193.54 us       21.6x             1.0x
  python-ecdsa                 298.96 us       33.3x             1.5x
  secp256k1lab                1326.80 us      147.9x             6.9x
  pycoin                      5948.77 us      663.1x            30.7x
  buidl.pecc                 30353.37 us     3383.6x           156.8x

ECDSA sign, over a 32-byte digest
                                            vs best   vs best Python
  btclib, the bindings          17.44 us        1.0x               --
  btclib, Python               176.45 us       10.1x             1.0x
  python-ecdsa                 313.34 us       18.0x             1.8x
  pycoin                      5961.78 us      341.8x            33.8x
  buidl.pecc                 30555.89 us     1751.9x           173.2x

ECDSA verify, over a 32-byte digest
                                            vs best   vs best Python
  btclib, the bindings          23.12 us        1.0x               --
  btclib, Python               770.52 us       33.3x             1.0x
  python-ecdsa                1098.71 us       47.5x             1.4x
  pycoin                     18556.35 us      802.5x            24.1x
  buidl.pecc                 61993.66 us     2681.1x            80.5x

BIP340 sign, over a 32-byte message
                                            vs best   vs best Python
  btclib, the bindings          20.10 us        1.0x               --
  btclib, Python               313.85 us       15.6x             1.0x
  secp256k1lab                7869.44 us      391.4x            25.1x
  buidl.pecc                 90878.48 us     4520.3x           289.6x

BIP340 verify, over a 32-byte message
                                            vs best   vs best Python
  btclib, the bindings          23.13 us        1.0x               --
  btclib, Python               714.32 us       30.9x             1.0x
  secp256k1lab                5181.58 us      224.1x             7.3x
  buidl.pecc                 60954.70 us     2635.7x            85.3x
```

## What it shows

The bindings row is first in every table, which is the point of the
exercise: the whole pure-Python family sits orders below it, so everything
under that first line is a ranking of fallbacks.

Among those fallbacks btclib's own Python path leads every table here,
`python-ecdsa` is second in each one it has a row in, and `buidl.pecc` is
last in all five by a distance nothing on this machine would reorder. The
top two are within a small factor of each other in the public key table,
and under an earlier fixture they changed places between runs — which is
the reason to read the ratio column and not the order alone.

`secp256k1lab` is a teaching implementation and reads like one — it is on
no index at all, and it is here because BIP340 is where btclib has fewer
pure-Python comparands than it has for ECDSA, not because anybody would
choose it for speed.

pycoin is a Python row here and a C row in [the bitcoin-libraries
table][libs], the same version of the same package in both. Nothing was
patched to arrange that: this script sets `PYCOIN_NATIVE` before importing
it, where the other script imports it after something else has already put
libsecp256k1 symbols in the process. Both files print which one they got,
which is why the pair can be read at all.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
