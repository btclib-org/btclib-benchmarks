# One key, every signature under it

## This run

<!-- run: begin -->
```text
when    : 2026-08-15 22:11 CEST (20:11 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

What `scripts/05-key-reuse.py` printed on the machine named above: the same
ECDSA verification, with the public key handed in raw and with it
prepared, on both of btclib's paths and against `python-ecdsa`. The other
four benchmarks time one verification with a fresh key; a verifier never
does one, so this is the question they leave out.

Two tables and one point between them. The first is what a verification
costs in the steady state, once the key is whatever it is going to be.
The second is what getting it there costs and after how many
verifications that has paid for itself — which is the number a caller
actually decides on, and it is against the same implementation's own
unprepared row rather than against the fastest of the table. Getting it
there and nothing else: building the key is work the caller who does not
prepare pays as well, so a column of differences must not carry it.

One run, kept whole. The numbers are an order of magnitude, never a figure
to quote.

## The output

<!-- output: begin -->
```text
btclib              : 2026.9
btclib-secp256k1    : 0.8.0.3
ecdsa               : 0.19.2

method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/05-key-reuse.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

ECDSA verify, one key, every signature under it
                                         μs/call     vs best
  btclib, libsecp256k1, parsed point       18.60        1.0x
  btclib, libsecp256k1, octets             20.97        1.1x
  python-ecdsa, precomputed               547.77       29.5x
  btclib, Python, parsed point            590.53       31.8x
  btclib, Python, octets                  683.05       36.7x
  python-ecdsa                           1111.93       59.8x

what preparing the key costs, and after how many verifications it pays
                                         prepare   saves/call   break-even
  btclib, libsecp256k1, parse once          4.19         2.37          1.8
  btclib, Python, parse once               75.69        92.52          0.8
  python-ecdsa, precompute()             3270.14       564.16          5.8
```
<!-- output: end -->

## What it shows

**Reuse is not where Python catches the C library, and it is worth
saying first.** The best prepared Python row is still an order of
magnitude and more behind the worst unprepared libsecp256k1 row. Preparing a
key moves each group by a small factor and moves neither into the other:
the gap is the arithmetic underneath, and no amount of reuse is an
amount of C. The reason to prepare a key is that it is nearly free, not
that it changes which implementation is fastest.

**Parsing once is the saving btclib already offers, and it pays back
almost immediately.** `assert_as_valid_` takes the public key as a parsed
point wherever it takes sec octets, and on the Python path a caller who
does that gets the decompression back before the first verification is
over — the break-even is under one call, because the square root the
parse pays is the same square root the verification would have paid.
On the libsecp256k1 path it is a smaller saving on a smaller number and pays
back inside two. Neither is a new API and neither is documented anywhere
a caller looks, which is the only reason this table is interesting.

**Past that, btclib has nothing to prepare and `python-ecdsa` does.**
Its precomputed row is the fastest pure-Python verification in any of
these files, and it beats the best btclib Python row here. What it buys
is what btclib drops on every call: the multiplication tables built from
the key, rebuilt per verification because the set of points btclib
memoizes is the generator's and nothing else. That is
[btclib-org/btclib#893][issue], where the same measurement is made from
the other side — with the key memoized through btclib's own existing
cache, the Python row lands level with `python-ecdsa`'s precomputed one.
There is no row for it here, because a benchmark row should be something
a caller can have.

**The caller who most needs `precompute()` cannot call it.** On `ecdsa`
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

[issue]: https://github.com/btclib-org/btclib/issues/893

## More benchmarks

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
