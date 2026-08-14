# the libsecp256k1 wrappers, one run

What `scripts/libsecp256k1_wrappers.py` printed on the machine named
below: `btclib_secp256k1`, `coincurve`, `secp256k1-py` and `electrum-ecc`
signing and verifying the same ECDSA and BIP340 signatures and tweaking the
same public key, every row calling `bitcoin-core/secp256k1`. Microseconds
per call, fastest row first, a ratio against whichever row came out
quickest, and one loop count for every row — a table whose rows are all C
needs no count of its own per row.

One run, kept whole — the block naming which revision of libsecp256k1 sits
under each row is not decoration here, it is the premise of the table.
Read [README.md][readme] on what these numbers are: an order of magnitude,
never a figure to quote.

The signatures being verified are BIP340's own, every vector the file
publishes, cycled one per call: where every row wraps the same library, "they
agree with each other" is the check that proves least, and agreeing with the
specification is one with an outside answer.

Which packages are here is the set of wrappers of that library, and it is
worth saying what is not: `ecdsa`, the PyPI package, wraps nothing. It has
no compiled backend at all, so it belongs to [the pure-Python
table][pure] and to [the libraries table][libs], never to this one.

## What produced it

```text
when    : 2026-08-14 22:11 CEST (20:11 UTC)
python  : 3.13.14
command : uv run python scripts/libsecp256k1_wrappers.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib-secp256k1    : 0.8.0.2
coincurve           : 21.0.0
secp256k1           : 0.14.0
electrum-ecc        : 0.0.7

libsecp256k1 under each row
  btclib-secp256k1  0.8.0.2   v0.8.0                  cffi bindings, _btclib_secp256k1.cpython-313-darwin.so
  coincurve         21.0.0    v0.6.0                  cffi bindings, _libsecp256k1.cpython-313-darwin.so
  secp256k1         0.14.0    9526874d, pre-v0.1.0    cffi bindings, _libsecp256k1.cpython-313-darwin.so
  electrum-ecc      0.0.7     v0.7.1                  ctypes bindings, libsecp256k1.6.dylib

ECDSA verify (32-byte digest, the public key parsed per call)
                                   μs/call     vs best
  dsa_secp256k1                      11.82       1.00x   (100000 calls)
  dsa_btclib_secp256k1               14.13       1.20x   (100000 calls)
  dsa_coincurve                      14.23       1.20x   (100000 calls)
  dsa_electrum_ecc                   16.08       1.36x   (100000 calls)

BIP340 verify (32-byte message, the public key parsed per call)
                                   μs/call     vs best
  ssa_coincurve                      14.67       1.00x   (100000 calls)
  ssa_btclib_secp256k1               14.85       1.01x   (100000 calls)
  ssa_secp256k1                      15.12       1.03x   (100000 calls)
  ssa_electrum_ecc                   18.68       1.27x   (100000 calls)

ECDSA sign (32-byte digest)
                                   μs/call     vs best
  dsa_sign_secp256k1                 11.43       1.00x   (100000 calls)
  dsa_sign_coincurve                 11.71       1.03x   (100000 calls)
  dsa_sign_btclib_secp256k1          12.69       1.11x   (100000 calls)
  dsa_sign_electrum_ecc              27.46       2.40x   (100000 calls)
  dsa_sign_electrum_ecc_grind        61.61       5.39x   (100000 calls)

BIP340 sign (32-byte message)
                                   μs/call     vs best
  ssa_sign_secp256k1                  7.81       1.00x   (100000 calls)
  ssa_sign_btclib_secp256k1          16.05       2.05x   (100000 calls)
  ssa_sign_coincurve                 27.42       3.51x   (100000 calls)
  ssa_sign_electrum_ecc              31.50       4.03x   (100000 calls)

public key tweak by a scalar, which is BIP32's step
                                   μs/call     vs best
  tweak_coincurve                    10.45       1.00x   (100000 calls)
  tweak_btclib_secp256k1             10.62       1.02x   (100000 calls)
  tweak_secp256k1                    13.89       1.33x   (100000 calls)
  tweak_electrum_ecc                 22.47       2.15x   (100000 calls)
```

## What it shows

The four land close together, which is what a table of one C library
should look like: the arithmetic is the same code, and what is left to
measure is the boundary crossing. The ratio column prints two decimals
where the other benchmarks print one, because at one decimal most of this
column would read 1.0x and say nothing.

The ctypes row is last in both verification tables. The three cffi rows are close
enough that their order among themselves is not something one run on a
machine like this settles: which of them the ratio column calls the fastest
is not stable across runs. That is the column's other use — a row a few
percent off the best is not behind it in any durable sense, and being able
to see how few percent is the point.

The revisions are why the closeness is worth stating rather than assuming.
These are four vendored trees of one project, and the pins above the timings
say so: `btclib_secp256k1`'s is the newest upstream tag of the four, and
`secp256k1-py`'s predates upstream's first tagged release. Part of any
difference is which library a row was built against.

Those pins are recorded rather than read because none of the four can be
asked: no compiled artifact exports a version symbol, and each package's
version attribute answers for the wrapper. A wrapper recording its vendored
revision at build time would end the recording here.

Each pin is keyed to the release it was read from and prints `unrecorded`
for any other, so an upgraded comparand says that it has outgrown its pin
rather than repeating one that has quietly stopped being true.

## What the signing and tweak tables add

Signing separates these APIs more than verifying does, and one row
separates itself: `electrum-ecc` grinds for a low-r signature unless told
not to, the only one of the four that offers grinding at all, so it has two
rows — one signature, and its default. Grinding is a loop around a wrapper
rather than anything the C library does, which is why the tables about
libraries carry the same distinction for btclib and embit.

Three of the four produce the same ECDSA bytes for a key and a message,
libsecp256k1's default nonce being RFC6979. `secp256k1-py` does on x86-64 and
does not on aarch64, so its build disagrees about the nonce or about what it
was handed, and what the script asserts of every wrapper is the portable
thing: that the signature verifies. BIP340 is checked against the vector for
three of them; `secp256k1-py`'s `schnorr_sign` takes no aux_rand, so there
too the check its API leaves is that its signature verifies.

The last table is BIP32's step rather than BIP32: none of these four
packages implements derivation, and all four expose the primitive it is
built from, a public key tweaked by a scalar. `electrum-ecc` has no
tweak-add on `ECPubkey`, so the same result is reached as a scalar times
the generator plus a point addition — two crossings where the other three
make one, which is the sort of difference this table exists to show. BIP32
proper is in [the libraries table][libs], where the comparands are
libraries.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
