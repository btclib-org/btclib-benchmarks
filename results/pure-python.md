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

The inputs are every BIP340 vector the file publishes, cycled: each call takes
the next, so a row is an average over inputs nobody here chose. Both
implementations that sign BIP340 are held to the signatures the specification
publishes; ECDSA is not, RFC6979's nonce being btclib's own, so those rows
stay checked against each other. btclib signs ECDSA twice, once per row: one
signature, which is what the other implementations produce, and its own
default beside it, which grinds until r fits in 32 bytes.

## What produced it

```text
when    : 2026-08-14 19:38 CEST (17:38 UTC)
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
  btclib                         195.38 μs        1.0x
  python-ecdsa                   223.14 μs        1.1x
  secp256k1lab                   934.07 μs        4.8x
  pycoin                        6054.36 μs       31.0x
  buidl.pecc                   21076.56 μs      107.9x

ECDSA sign, over a 32-byte digest
                                              vs best
  btclib, one signature          187.77 μs        1.0x
  python-ecdsa                   285.82 μs        1.5x
  btclib, grinding (default)     696.34 μs        3.7x
  pycoin                        6014.97 μs       32.0x
  buidl.pecc                   29784.45 μs      158.6x

ECDSA verify, over a 32-byte digest
                                              vs best
  btclib                         839.58 μs        1.0x
  python-ecdsa                  1128.47 μs        1.3x
  pycoin                       18972.79 μs       22.6x
  buidl.pecc                   61094.47 μs       72.8x

BIP340 sign, over a 32-byte message
                                              vs best
  btclib                         346.25 μs        1.0x
  secp256k1lab                  7355.73 μs       21.2x
  buidl.pecc                  110478.22 μs      319.1x

BIP340 verify, over a 32-byte message
                                              vs best
  btclib                         704.51 μs        1.0x
  secp256k1lab                  5170.71 μs        7.3x
  buidl.pecc                   68141.55 μs       96.7x
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
