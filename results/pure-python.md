# Every pure-Python implementation

## What produced it

```text
when    : 2026-08-14 22:10 CEST (20:10 UTC)
python  : 3.13.14
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/pure_python.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

What `scripts/pure_python.py` printed on the machine named above: btclib's
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

The inputs are every BIP340 vector the file publishes, cycled: each call takes
the next, so a row is an average over inputs nobody here chose. Both
implementations that sign BIP340 are held to the signatures the specification
publishes; ECDSA is not, RFC6979's nonce being btclib's own, so those rows
stay checked against each other. btclib signs ECDSA twice, once per row: one
signature, which is what the other implementations produce, and its own
default beside it, which grinds until r fits in 32 bytes.

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
  btclib                         188.82 μs        1.0x
  python-ecdsa                   217.45 μs        1.2x
  secp256k1lab                   932.66 μs        4.9x
  pycoin                        5879.73 μs       31.1x
  buidl.pecc                   20996.51 μs      111.2x

ECDSA sign, over a 32-byte digest
                                              vs best
  btclib, one signature          178.92 μs        1.0x
  python-ecdsa                   292.47 μs        1.6x
  btclib, grinding (default)     674.43 μs        3.8x
  pycoin                        5993.50 μs       33.5x
  buidl.pecc                   29866.54 μs      166.9x

ECDSA verify, over a 32-byte digest
                                              vs best
  btclib                         875.48 μs        1.0x
  python-ecdsa                  1137.51 μs        1.3x
  pycoin                       19720.62 μs       22.5x
  buidl.pecc                   82892.72 μs       94.7x

BIP340 sign, over a 32-byte message
                                              vs best
  btclib                         341.63 μs        1.0x
  secp256k1lab                  7429.75 μs       21.7x
  buidl.pecc                  111175.15 μs      325.4x

BIP340 verify, over a 32-byte message
                                              vs best
  btclib                         700.80 μs        1.0x
  secp256k1lab                  5190.46 μs        7.4x
  buidl.pecc                   68318.46 μs       97.5x
```

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

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[two]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
