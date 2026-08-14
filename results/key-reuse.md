# one key, every signature under it, one run

What `scripts/key_reuse.py` printed on the machine named below: the same
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

One run, kept whole. Read [README.md][readme] on what these are: an order
of magnitude, never a figure to quote.

## What produced it

```text
when    : 2026-08-14 22:11 CEST (20:11 UTC)
python  : 3.13.14
command : uv run python scripts/key_reuse.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9
btclib-secp256k1    : 0.8.0.2
ecdsa               : 0.19.2


ECDSA verify, one key, every signature under it
                                                  vs best
  btclib, bindings, parsed point      20.38 μs        1.0x
  btclib, bindings, octets            23.15 μs        1.1x
  python-ecdsa, precomputed          538.45 μs       26.4x
  btclib, Python, octets             700.21 μs       34.4x
  btclib, Python, parsed point       724.69 μs       35.6x
  python-ecdsa                      1087.38 μs       53.3x

what preparing the key costs, and after how many verifications it pays
                                    prepare  saves/call  break-even
  btclib, bindings, parse once        3.61 μs      2.77 μs       1.3
  btclib, Python, parse once        109.56 μs    -24.48 μs      -4.5
  python-ecdsa, precompute()       3228.44 μs    548.93 μs       5.9
```

## What it shows

**Reuse is not where Python catches the C library, and it is worth
saying first.** The best prepared Python row is still an order of
magnitude and more behind the worst unprepared bindings row. Preparing a
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
On the bindings path it is a smaller saving on a smaller number and pays
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

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[issue]: https://github.com/btclib-org/btclib/issues/893

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
