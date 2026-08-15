# Bitcoin Python libraries

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package            version           released           arithmetic
btclib             2026.9            main@a6988751392b  libsecp256k1 enhanced
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
  bundles is in [the bindings table][wrappers].
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
when    : 2026-08-15 06:24 CEST (04:24 UTC)
python  : 3.13.14
method  : 3 rounds per row, minimum kept; nothing else repeated
command : uv run python scripts/bitcoin_libraries.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```
<!-- run: end -->

## The output

Eleven tables: the curve operations, BIP32 derivation, and the three
address encodings in both directions. Fastest row first, ratioed against
whichever row came out quickest, with the spread of a row's own three
rounds beside it — a row within a percent of the one above it, whose
spread is the same size, is not behind it in any durable sense.

The inputs are every BIP340 signing vector and every BIP32 chain the
vendored files publish, cycled one per call; the address rows are the
exception, one witness-v0 and one witness-v1 address being what is
vendored, so they call one input.

<!-- output: begin -->
```text
what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

1. ECDSA sign (32-byte digest)
                   μs/call     vs best   spread
  pycoin             12.33        1.0x    0.1%   (3x50000 calls)
  embit              14.14        1.1x    1.0%   (3x50000 calls)
  btclib             16.42        1.3x    0.4%   (3x50000 calls)
  embit_grind        49.88        4.0x    3.7%   (3x20000 calls)
  btclib_grind       54.21        4.4x    0.3%   (3x20000 calls)
  bitcoinlib        192.27       15.6x    0.6%   (3x8000 calls)
  ecdsa             282.77       22.9x    0.5%   (3x5000 calls)
  buidl           29531.26     2395.8x    0.1%   (3x50 calls)

2. ECDSA verify (32-byte digest)
                   μs/call     vs best   spread
  pycoin             12.92        1.0x    0.0%   (3x50000 calls)
  btclib             20.10        1.6x    0.7%   (3x50000 calls)
  embit              23.11        1.8x    0.0%   (3x50000 calls)
  bitcoinlib        218.30       16.9x    0.2%   (3x7000 calls)
  ecdsa            1109.32       85.9x    0.1%   (3x3000 calls)
  buidl           60691.99     4699.0x    0.2%   (3x25 calls)

3. BIP340 sign (32-byte message)
                   μs/call     vs best   spread
  embit              21.25        1.0x    0.1%   (3x50000 calls)
  btclib             22.33        1.1x    0.1%   (3x50000 calls)
  buidl          106922.54     5030.8x    0.2%   (3x20 calls)

4. BIP340 verify (32-byte message)
                   μs/call     vs best   spread
  embit              24.28        1.0x    2.1%   (3x50000 calls)
  btclib             31.84        1.3x    0.2%   (3x50000 calls)
  buidl           68884.12     2837.1x    0.6%   (3x25 calls)

5. BIP32 derive, seed to child, every chain BIP32 publishes
                   μs/call     vs best   spread
  pycoin             48.56        1.0x    0.4%   (3x30000 calls)
  btclib             63.39        1.3x    0.7%   (3x30000 calls)
  embit              87.19        1.8x    0.2%   (3x15000 calls)
  buidl          104267.76     2147.3x    7.1%   (3x12 calls)

6. base58check encode, a P2PKH address from a hash160
                   μs/call     vs best   spread
  embit               2.15        1.0x    0.2%   (3x200000 calls)
  buidl               2.31        1.1x    0.2%   (3x200000 calls)
  btclib              2.38        1.1x    0.5%   (3x200000 calls)
  bitcoinlib          2.55        1.2x    0.4%   (3x100000 calls)
  pycoin              3.70        1.7x    0.2%   (3x200000 calls)

7. base58check decode, a hash160 from a P2PKH address
                   μs/call     vs best   spread
  btclib              2.43        1.0x    0.3%   (3x200000 calls)
  embit               2.50        1.0x    0.4%   (3x200000 calls)
  buidl               3.02        1.2x    0.6%   (3x200000 calls)
  pycoin              3.75        1.5x    1.1%   (3x200000 calls)
  bitcoinlib          4.23        1.7x    0.6%   (3x100000 calls)

8. bech32 encode, a witness-v0 address from a 20-byte program
                   μs/call     vs best   spread
  btclib              8.05        1.0x    1.0%   (3x200000 calls)
  buidl              11.39        1.4x    1.1%   (3x100000 calls)
  bitcoinlib         26.64        3.3x    0.2%   (3x200000 calls)
  embit              26.67        3.3x    0.1%   (3x200000 calls)

9. bech32 decode, a 20-byte program from a witness-v0 address
                   μs/call     vs best   spread
  btclib              7.06        1.0x    0.3%   (3x200000 calls)
  buidl              10.30        1.5x    0.2%   (3x100000 calls)
  bitcoinlib         14.62        2.1x    0.9%   (3x200000 calls)
  embit              14.63        2.1x    0.0%   (3x200000 calls)

10. bech32m encode, a witness-v1 address from a 32-byte program
                   μs/call     vs best   spread
  btclib             13.80        1.0x    1.3%   (3x200000 calls)
  buidl              17.14        1.2x    0.1%   (3x100000 calls)
  embit              40.23        2.9x    0.7%   (3x200000 calls)

11. bech32m decode, a 32-byte program from a witness-v1 address
                   μs/call     vs best   spread
  btclib             11.72        1.0x    0.6%   (3x200000 calls)
  buidl              15.43        1.3x    0.2%   (3x100000 calls)
  embit              22.02        1.9x    0.1%   (3x200000 calls)
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
  verification costs. It is the sharpest reason in these four files for
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

Four other questions are published in `results/`, each with its own
comparands:

- [the libsecp256k1 bindings][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the bindings measured here
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/libsecp256k1-wrappers.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/key-reuse.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
