# One key, every signature under it

## This run

<!-- run: begin -->
```text
when    : 2026-10-15 09:44 CEST (07:44 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

What `scripts/05-key-reuse.py` printed on the machine named above: the same
ECDSA verification, with the public key handed in raw and with it
prepared, on both of btclib's paths and against `python-ecdsa`. The other
benchmarks time one verification with a fresh key; a verifier never
does one, so this is the question they leave out.

Two tables and one point between them. The first is what a verification
costs in the steady state, once the key is whatever it is going to be.
The second is what getting it there costs and after how many
verifications that has paid for itself — which is the number a caller
actually decides on, and it is against the same implementation's own
unprepared row rather than against the fastest of the table. Getting it
there and nothing else: building the key is work the caller who does not
prepare pays as well, so a column of differences must not carry it.

Each row is timed in rounds and the quickest is kept. Rows that a
difference is taken between take their rounds in turn, so that a machine
drifting during the run drifts under both. The numbers are an order of
magnitude, never a figure to quote.

**`halves`** is in microseconds, like the number beside it. The rounds are
split in half, and the column is how far the quickest round of one half sat
from the quickest of the other: this run's agreement with itself. In the
first table it is the row's own. In the second it is the distance for the
saving, `saves/call`, which is the same implementation's unprepared row less
its prepared row, and a break-even divides by that saving. A saving no
larger than its `halves` is not settled by the run, and one larger can still
move on the next. **`vs best`** is a row's time over the fastest row of its table.
**`break-even`** is `prepare` over `saves/call`, and `never` is printed
where the saving is nothing or less. Beside a `halves` as wide as the
saving, it says the run could not tell the saving from nothing, and not
that preparing loses. **`prepare`** is the cost of
getting the key to the prepared state and nothing else.

The rows named `few keys` are the parsed point over the same few keys the
`PreparedPoint` rows cycle through. They are what a prepared point is
answered against: a row cycling through few keys is not a row cycling
through many, and the difference between the two is not what preparing
saves.

## The benchmarks

<!-- output: begin -->
```text
btclib              : 2026.10.9
btclib-secp256k1    : 0.8.0.11
ecdsa               : 0.19.2

method  : 10 rounds per row, pairs in turn, minimum kept; calls per row
command : uv run python scripts/05-key-reuse.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/, not by a script
  (CONTRIBUTING.md's Writing a row names where)

ECDSA verify, one key, every signature under it
                                                   μs/call     vs best   halves
  btclib, libsecp256k1, parsed point, few keys       17.06        1.0x     0.02   (10x20,000 calls)
  btclib, libsecp256k1, PreparedPoint                17.12        1.0x     0.02   (10x20,000 calls)
  btclib, libsecp256k1, parsed point                 17.96        1.1x     0.00   (10x20,000 calls)
  btclib, libsecp256k1, octets                       19.27        1.1x     0.01   (10x20,000 calls)
  btclib, Python, PreparedPoint                     435.84       25.5x    12.57   (10x500 calls)
  python-ecdsa, precomputed                         567.86       33.3x     0.24   (10x500 calls)
  btclib, Python, parsed point                      575.59       33.7x    12.43   (10x500 calls)
  btclib, Python, parsed point, few keys            583.17       34.2x     5.15   (10x500 calls)
  btclib, Python, octets                            646.18       37.9x     9.66   (10x500 calls)
  python-ecdsa                                     1110.47       65.1x     5.36   (10x500 calls)

what preparing the key costs, and after how many verifications it pays
                                                   prepare   saves/call   halves   break-even
  btclib, libsecp256k1, parse once                    4.76         1.30     0.01          3.6
  btclib, libsecp256k1, PreparedPoint                 1.50        -0.06     0.01        never
  btclib, Python, parse once                         67.99        70.59     2.77          1.0
  btclib, Python, PreparedPoint                    3116.81       147.33     7.42         21.2
  python-ecdsa, precompute()                       3299.82       542.62     5.12          6.1
```
<!-- output: end -->

## Results

### Reuse is not where Python catches the C library

The best prepared Python row is still an order of
magnitude and more behind the worst unprepared libsecp256k1 row. Preparing a
key moves each group by a small factor and moves neither into the other:
the gap is the arithmetic underneath, and no amount of reuse is an
amount of C. The reason to prepare a key is what it saves a verifier that
sees the key again, not that it changes which implementation is fastest.
It is nearly free where the key is only parsed once, and costs a table's
worth of work where the Python path builds one.

### Parsing once is a saving btclib already offers

It pays back almost immediately. `assert_as_valid_` takes the public key as a parsed
point wherever it takes sec octets, and on the Python path a caller who
does that gets the decompression back by the first verification, because
the square root the parse pays is the same square root the verification
would have paid. On the libsecp256k1 path it is a smaller saving on a
smaller number and takes a few verifications to pay back. Neither is a new
API and neither is documented anywhere a caller looks, which is the only
reason this table is interesting.

### `PreparedPoint` pays on the Python path and not on the C one

btclib has a prepared key, `curve.PreparedPoint`, which keeps the
multiplication tables of the key in a cache under the point a caller wraps
in it. On the Python path it is the fastest btclib row here, and quicker
than `python-ecdsa`'s precomputed key. The price is the tables, built by
the first verification under the point, and its break-even is the longest of
the break-evens that pay: it is a saving for a verifier that sees the same keys
again, and a loss for one that sees each key only a few times. The cache is
bounded, so the rows keep few prepared keys.

On the libsecp256k1 path the same wrapper is accepted and its tables go
unused, the bindings holding tables of their own. On this path the prepared
point is no quicker than the parsed point over the same few keys, and in
this run slightly slower, by more than the `halves` beside it. The
break-even prints `never`.

### `python-ecdsa` has a prepared key too

`VerifyingKey.precompute()` builds tables from the key as well. Its
precomputed row is its fastest and is behind btclib's prepared row.

### The caller who most needs `precompute()` cannot call it

On `ecdsa`
0.19.2 the method raises `AssertionError` on a key built by
`from_string` — it hands the point to `PointJacobi.from_affine`, which
does not carry the curve order over, and the precomputation asserts on
it. A key built from the secret exponent works. So a verifier, who has
the public key as bytes and nothing else, is exactly the caller it fails
for. The row above uses the construction that works, so that it measures
the method rather than the defect; a real verifier on this version gets
the unprepared row instead, which is the slowest in the table.

## Why the state being reused is not a secret

The usual objection to keeping key-derived state alive is that key
material outlives its use, and in Python it outlives it whatever anyone
intends: there is no way to zero a buffer that the interpreter is free to
copy, so a secret held once is a secret held until the process ends. That
argument does not apply here at all, and it is worth being precise about
why rather than leaning on it. Everything prepared in this table is
derived from the *public* key — a decompressed point, a table of its odd
multiples. An observer of any signature already has it. There is no
secret being cached, so the question is only whether the memory is worth
the calls, which is what the second table answers.

The private key has no counterpart. The one table a signature leans on is
the generator's, which every key shares and which btclib already
memoizes; none of these implementations builds per-private-key state. So
there is no signing half of this benchmark, and that absence is a result
rather than an omission.

## More benchmarks

Five other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [Silent Payments][sp] — what only `btclib_secp256k1` offers of BIP352,
  which no other comparand here implements at all

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
