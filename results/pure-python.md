# Every pure-Python implementation

## This run

```text
when    : 2026-08-14 23:39 CEST (21:39 UTC)
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
The numbers are an order of magnitude, never a figure to quote.

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

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock


public key from a private key: a multiplication of the generator
                                              vs best
  btclib                         188.98 μs        1.0x
  python-ecdsa                   216.76 μs        1.1x
  secp256k1lab                   924.96 μs        4.9x
  pycoin                        5923.47 μs       31.3x
  buidl.pecc                   20893.75 μs      110.6x

ECDSA sign, over a 32-byte digest
                                              vs best
  btclib, one signature          167.46 μs        1.0x
  python-ecdsa                   287.04 μs        1.7x
  btclib, grinding (default)     623.43 μs        3.7x
  pycoin                        6001.68 μs       35.8x
  buidl.pecc                   29862.88 μs      178.3x

ECDSA verify, over a 32-byte digest
                                              vs best
  btclib                         822.95 μs        1.0x
  python-ecdsa                  1090.69 μs        1.3x
  pycoin                       18958.38 μs       23.0x
  buidl.pecc                   60908.78 μs       74.0x

BIP340 sign, over a 32-byte message
                                              vs best
  btclib                         336.68 μs        1.0x
  secp256k1lab                  7376.37 μs       21.9x
  buidl.pecc                  110144.09 μs      327.1x

BIP340 verify, over a 32-byte message
                                              vs best
  btclib                         686.32 μs        1.0x
  secp256k1lab                  5128.88 μs        7.5x
  buidl.pecc                   67834.38 μs       98.8x
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

[two]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md

## More benchmarks

Four other questions are published in `results/`, each with its own
comparands:

- [the libsecp256k1 bindings][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the bindings measured here
- [python libraries][libs] — where bindings (if available) are just one
  component of a python library
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/libsecp256k1-wrappers.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/key-reuse.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
