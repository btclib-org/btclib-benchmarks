# Bitcoin Python libraries

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package            version           released           arithmetic
btclib             2026.9            main@0abf2fa2bb2c  libsecp256k1 enhanced
pycoin             0.92718.20260405  2026-04-05         libsecp256k1 enhanced
ecdsa              0.19.2            2026-03-26         pure Python
embit              0.8.0             2024-05-30         libsecp256k1 enhanced
python-bitcoinlib  0.12.2            2023-06-03         OpenSSL's libcrypto
buidl              0.2.36            2022-02-28         pure Python
```
<!-- provenance: end -->

The last column says which arithmetic answered on the machine that ran
this, and nothing about how the package got there. That part is one
paragraph each, and none of the six is the same story:

- **btclib** requires `btclib-secp256k1`, which bundles libsecp256k1 and
  compiles it into a cffi extension at install time, so a wheel from PyPI
  is enhanced without anything further being done to it. Which revision it
  bundles is in [the wrappers table][wrappers].
- **pycoin** bundles nothing and builds nothing. `pycoin.ecdsa.native` is a
  ctypes loader that asks the machine for a library by name, and a PyPI
  install therefore gets pure Python unless one is already there. Here one
  is: btclib-secp256k1's extension has put its symbols in this process, and
  pycoin's loader finds them — through an import this script makes rather
  than anything pycoin does. On a machine where nothing else has loaded
  libsecp256k1, this row is Python, which is where the count it uses comes
  from as well. What that costs is the pycoin row of [the pure-Python
  table][pure].
- **embit** ships its own shared library in the wheel and reaches it
  through ctypes, and what it ships is secp256k1-zkp — ElementsProject's
  fork — rather than bitcoin-core/secp256k1. It is not a package anyone can
  install on its own, and the revision it carries is recorded here against
  the release it was read from.
- **buidl** has cffi bindings in `buidl.cecc`, and `pip install buidl` does
  not build them: `libsec_build.py` compiles them against a system library
  and has to be run by hand. So its rows are `buidl.pecc`, pure Python,
  unless somebody did that.
- **python-bitcoinlib** reaches C that is not libsecp256k1 at all —
  OpenSSL's libcrypto, through ctypes. It can detect a libsecp256k1 and
  does not use it for these operations.
- **ecdsa** has no bindings of any kind, bundled, built or found.

## This run

<!-- run: begin -->
```text
when    : 2026-08-16 16:40 CEST (14:40 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The output

Eleven tables: the curve operations, BIP32 derivation, and the three
address encodings in both directions. Fastest row first, ratioed against
whichever row came out quickest, with the spread of a row's own three
rounds beside it — how far its slowest round ran from its quickest, in the
same microseconds as the value it sits beside. A row whose distance from
the one above it is no larger than that is not behind it in any durable
sense.

The inputs are every BIP340 signing vector and every BIP32 chain the
vendored files publish, cycled one per call; the address rows are the
exception, one witness-v0 and one witness-v1 address being what is
vendored, so they call one input.

<!-- output: begin -->
```text
method  : 3 rounds per row, minimum kept; nothing else repeated
command : uv run python scripts/03-libraries.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

1. ECDSA sign (32-byte digest)
                   μs/call     vs best   spread
  pycoin             12.38        1.0x     0.02   (3x50000 calls)
  embit              14.13        1.1x     0.01   (3x50000 calls)
  btclib             15.48        1.3x     0.01   (3x50000 calls)
  btclib_grind       28.52        2.3x     0.07   (3x20000 calls)
  embit_grind        29.54        2.4x     0.00   (3x20000 calls)
  bitcoinlib        191.28       15.4x     0.73   (3x8000 calls)
  ecdsa             299.05       24.2x     0.35   (3x5000 calls)
  buidl           30157.06     2435.8x    25.09   (3x50 calls)

2. ECDSA verify (32-byte digest)
                   μs/call     vs best   spread
  pycoin             13.95        1.0x     0.09   (3x50000 calls)
  btclib             20.74        1.5x     0.16   (3x50000 calls)
  embit              24.19        1.7x     0.57   (3x50000 calls)
  bitcoinlib        223.62       16.0x     1.51   (3x7000 calls)
  ecdsa            1103.84       79.1x     5.41   (3x3000 calls)
  buidl           59979.52     4298.8x   290.06   (3x25 calls)

3. BIP340 sign (32-byte message)
                   μs/call     vs best   spread
  embit              21.26        1.0x     0.04   (3x50000 calls)
  btclib             22.39        1.1x     0.02   (3x50000 calls)
  buidl          111088.44     5226.4x  4725.47   (3x20 calls)

4. BIP340 verify (32-byte message)
                   μs/call     vs best   spread
  btclib             21.86        1.0x     0.10   (3x50000 calls)
  embit              25.08        1.1x     0.40   (3x50000 calls)
  buidl           68895.33     3151.5x   482.65   (3x25 calls)

5. BIP32 derive, seed to child, every chain BIP32 publishes
                   μs/call     vs best   spread
  pycoin             48.61        1.0x     0.51   (3x30000 calls)
  btclib             64.62        1.3x     0.44   (3x30000 calls)
  embit              86.81        1.8x     0.18   (3x15000 calls)
  buidl          103834.21     2136.0x  4861.53   (3x12 calls)

6. base58check encode, a P2PKH address from a hash160
                   μs/call     vs best   spread
  embit               2.14        1.0x     0.02   (3x200000 calls)
  buidl               2.30        1.1x     0.00   (3x200000 calls)
  btclib              2.40        1.1x     0.01   (3x200000 calls)
  bitcoinlib          2.53        1.2x     0.00   (3x100000 calls)
  pycoin              3.72        1.7x     0.01   (3x200000 calls)

7. base58check decode, a hash160 from a P2PKH address
                   μs/call     vs best   spread
  embit               2.46        1.0x     0.00   (3x200000 calls)
  btclib              2.49        1.0x     0.01   (3x200000 calls)
  buidl               2.84        1.2x     0.06   (3x200000 calls)
  pycoin              3.67        1.5x     0.07   (3x200000 calls)
  bitcoinlib          4.20        1.7x     0.09   (3x100000 calls)

8. bech32 encode, a witness-v0 address from a 20-byte program
                   μs/call     vs best   spread
  btclib              7.99        1.0x     0.02   (3x200000 calls)
  buidl              11.70        1.5x     0.11   (3x100000 calls)
  bitcoinlib         26.34        3.3x     0.10   (3x200000 calls)
  embit              26.41        3.3x     0.46   (3x200000 calls)

9. bech32 decode, a 20-byte program from a witness-v0 address
                   μs/call     vs best   spread
  btclib              6.94        1.0x     0.01   (3x200000 calls)
  buidl              10.16        1.5x     0.02   (3x100000 calls)
  bitcoinlib         14.44        2.1x     0.14   (3x200000 calls)
  embit              14.51        2.1x     0.08   (3x200000 calls)

10. bech32m encode, a witness-v1 address from a 32-byte program
                   μs/call     vs best   spread
  btclib             13.10        1.0x     0.07   (3x200000 calls)
  buidl              17.32        1.3x     0.40   (3x100000 calls)
  embit              39.47        3.0x     0.63   (3x200000 calls)

11. bech32m decode, a 32-byte program from a witness-v1 address
                   μs/call     vs best   spread
  btclib             11.58        1.0x     0.05   (3x200000 calls)
  buidl              15.30        1.3x     0.06   (3x100000 calls)
  embit              21.79        1.9x     0.15   (3x200000 calls)
```
<!-- output: end -->

## What it shows

The sort separates the rows into the two groups the packages table predicts:
the ones that reach C land within a small factor of one another, and the
pure-Python rows fall an order of magnitude or more behind them —
`buidl.pecc` by a great deal more than that. python-bitcoinlib's OpenSSL
path sits between the two groups. Which row is in which group is not a
property of the packages alone, which is what that table's last column is
for.

Two things this output says are worth reading twice:

- **two libraries here sign more than once by default.** btclib and embit
  both grind for a low-r signature — they sign repeatedly until r fits in
  32 bytes — so their default is not comparable per signature with the
  rows that sign once. Each therefore has two rows: one signature,
  which is the comparable one, and the default beside it, whose cost is
  that signature times however many draws it took before r fit. Half of
  all draws fit already, so two signatures is the expectation over random
  messages, and the ratio between a library's two rows is where to read
  what this run's messages actually cost it. That multiple is a property
  of the draw rather than of either library — it is the one number on this
  page that moves when the inputs do, and it is why the grinding rows sit
  where they do in the order rather than beside their own one-signature
  rows.
- **python-ecdsa's verification row is worth reading against its key.**
  Handed the private key 1, python-ecdsa returns the generator *object* as
  the public key — precomputed table and all — and a row verifying against
  it verifies with a table no real key gets, at about half the cost. The
  keys here are drawn from the shared pool, and a drawn key is not the
  generator, so the row costs what verification costs. It is the sharpest
  reason in these five files for drawing the input rather than choosing
  it: a chosen key can be special in ways a table of timings cannot show.

The encoding tables are the only ones that are not curve work, and they are
where these libraries differ most: pure Python in all five, so what separates
them is the code.

## What these packages get wrong

A row here is a timing and not a verdict, so where a comparand answers a
published case wrongly this page says so. None of it makes a row
meaningless — every package times the operation it is asked for, over
inputs it handles — but a reader comparing them is owed the fact that some
of them are lax about what they accept.

`python-bitcoinlib` is the one that cannot be timed at all in a table it
would otherwise appear in. It encodes a witness-v1 program with bech32's
checksum constant where BIP350 requires bech32m's, and refuses to decode
the address BIP350 publishes, so it has no bech32m row in either
direction. `tests/round_trip_test.py` holds it to both halves of that,
which is also what will fail when a release fixes it.

`pycoin` and `buidl` are lax where a DER decoder should be strict. Run
against Wycheproof, whose whole subject is adversarial encodings, both
accept signatures the file rejects: pycoin reads BER long-form lengths
where DER admits one form, lengths that are wrong or that overflow a
uint64, and signatures with bytes appended or taken away that still parse;
buidl reads the same family, plus zeros prepended to r and to s, a
truncated r, and an r larger than any verification should admit. The one
that goes the other way is buidl's, which *rejects* a valid signature
where `k*G` has a large x coordinate.

`buidl` also cannot encode the empty payload that Bitcoin Core publishes
as the first base58 case: its encoder goes through `int(s.hex(), 16)`,
which raises on the empty string rather than answering with it.

Every one of these is recorded in `tests/vectors_test.py` as an expected
failure rather than skipped, so a release that fixes one turns the suite
red and brings somebody back to this list. What none of them changes is
the timings above: the signatures and addresses these rows carry are the
ones a specification publishes, and every package answers those correctly.

The loop counts are per row and print beside their rows, sorting putting rows
orders of magnitude apart next to each other. pycoin's are picked at run time,
from the backend found, for the reason its paragraph above gives.

## More benchmarks

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
