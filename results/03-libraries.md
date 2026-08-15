# Bitcoin Python libraries

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package            version           released           arithmetic
btclib             2026.9            main@95b03da34a71  libsecp256k1 enhanced
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
when    : 2026-08-15 22:10 CEST (20:10 UTC)
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
  pycoin             12.27        1.0x     0.00   (3x50000 calls)
  embit              14.12        1.2x     0.14   (3x50000 calls)
  btclib             17.08        1.4x     0.08   (3x50000 calls)
  embit_grind        49.84        4.1x     0.01   (3x20000 calls)
  btclib_grind       56.32        4.6x     0.21   (3x20000 calls)
  bitcoinlib        191.11       15.6x     0.38   (3x8000 calls)
  ecdsa             281.68       23.0x     0.49   (3x5000 calls)
  buidl           29459.19     2401.1x    75.51   (3x50 calls)

2. ECDSA verify (32-byte digest)
                   μs/call     vs best   spread
  pycoin             12.93        1.0x     0.20   (3x50000 calls)
  btclib             20.88        1.6x     0.05   (3x50000 calls)
  embit              23.02        1.8x     0.06   (3x50000 calls)
  bitcoinlib        217.82       16.8x     2.25   (3x7000 calls)
  ecdsa            1089.04       84.2x    27.97   (3x3000 calls)
  buidl           60568.13     4682.6x   432.83   (3x25 calls)

3. BIP340 sign (32-byte message)
                   μs/call     vs best   spread
  embit              21.11        1.0x     0.04   (3x50000 calls)
  btclib             22.13        1.0x     0.03   (3x50000 calls)
  buidl          106342.54     5037.8x  1163.91   (3x20 calls)

4. BIP340 verify (32-byte message)
                   μs/call     vs best   spread
  embit              24.14        1.0x     0.11   (3x50000 calls)
  btclib             32.90        1.4x     0.07   (3x50000 calls)
  buidl           68616.94     2842.8x  1498.87   (3x25 calls)

5. BIP32 derive, seed to child, every chain BIP32 publishes
                   μs/call     vs best   spread
  pycoin             48.29        1.0x     0.81   (3x30000 calls)
  btclib             64.89        1.3x     0.33   (3x30000 calls)
  embit              86.08        1.8x     0.12   (3x15000 calls)
  buidl          103547.02     2144.1x  4825.52   (3x12 calls)

6. base58check encode, a P2PKH address from a hash160
                   μs/call     vs best   spread
  embit               2.14        1.0x     0.01   (3x200000 calls)
  buidl               2.34        1.1x     0.01   (3x200000 calls)
  btclib              2.37        1.1x     0.01   (3x200000 calls)
  bitcoinlib          2.55        1.2x     0.08   (3x100000 calls)
  pycoin              3.63        1.7x     0.01   (3x200000 calls)

7. base58check decode, a hash160 from a P2PKH address
                   μs/call     vs best   spread
  embit               2.42        1.0x     0.05   (3x200000 calls)
  btclib              2.45        1.0x     0.01   (3x200000 calls)
  buidl               2.89        1.2x     0.01   (3x200000 calls)
  pycoin              3.71        1.5x     0.18   (3x200000 calls)
  bitcoinlib          4.21        1.7x     0.06   (3x100000 calls)

8. bech32 encode, a witness-v0 address from a 20-byte program
                   μs/call     vs best   spread
  btclib              7.86        1.0x     0.02   (3x200000 calls)
  buidl              11.26        1.4x     0.01   (3x100000 calls)
  embit              26.17        3.3x     0.05   (3x200000 calls)
  bitcoinlib         26.21        3.3x     0.10   (3x200000 calls)

9. bech32 decode, a 20-byte program from a witness-v0 address
                   μs/call     vs best   spread
  btclib              6.85        1.0x     0.11   (3x200000 calls)
  buidl              10.32        1.5x     0.22   (3x100000 calls)
  embit              14.50        2.1x     0.18   (3x200000 calls)
  bitcoinlib         14.51        2.1x     0.24   (3x200000 calls)

10. bech32m encode, a witness-v1 address from a 32-byte program
                   μs/call     vs best   spread
  btclib             13.27        1.0x     0.06   (3x200000 calls)
  buidl              17.19        1.3x     0.09   (3x100000 calls)
  embit              39.53        3.0x     0.26   (3x200000 calls)

11. bech32m decode, a 32-byte program from a witness-v1 address
                   μs/call     vs best   spread
  btclib             11.55        1.0x     0.13   (3x200000 calls)
  buidl              15.18        1.3x     0.03   (3x100000 calls)
  embit              21.67        1.9x     0.51   (3x200000 calls)
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
  four rows that sign once. Each therefore has two rows: one signature,
  which is the comparable one, and the default beside it, whose cost is
  that signature times however many draws it took before r fit. Half of
  all draws fit already, so two signatures is the expectation, and both
  libraries here ask for more than that — the ratio between a library's
  two rows is where to read how many it took. That multiple is a property of the
  pair rather than of either library, and it is why the grinding rows sit
  where they do in the order rather than beside their own one-signature
  rows.
- **python-ecdsa's verification row is worth reading against its key.**
  Handed the private key 1, python-ecdsa returns the generator *object* as
  the public key — precomputed table and all — and a row verifying against
  it verifies with a table no real key gets, at about half the cost. The
  key here is BIP340's, which has no such table, so the row costs what
  verification costs. It is the sharpest reason in these five files for
  taking the input from a specification rather than choosing one.

The encoding tables are the only ones that are not curve work, and they are
where these libraries differ most: pure Python in all five, so what separates
them is the code. They also hold the one wrong answer in this benchmark.
`python-bitcoinlib` encodes a witness-v1 program with bech32's checksum
constant where BIP350 requires bech32m's, and rejects the address BIP350
publishes, so it has no bech32m row — `tests/vectors_test.py` holds it to
both halves of that.

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
