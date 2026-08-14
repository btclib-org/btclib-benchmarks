# Bitcoin Python libraries

## The packages downloaded from PyPI

Three of the six reach for a C library when they are imported and fall back
to Python without saying so, and a seventh column would not tell them apart:
what a row measures is the arithmetic it resolved to on the machine that ran
it, which is why the table below states it rather than the reader assuming
it. btclib resolves from its branch until 2026.9 is published, so its cell
carries the commit where the others carry a release date.

```text
package             version           released                  arithmetic
btclib              2026.9            main@a6988751392b         bundled libsecp256k1 v0.8.0 cffi bindings, _btclib_secp256k1.cpython-313-darwin.so
pycoin              0.92718.20260405  2026-04-05                ctypes bindings to a libsecp256k1 it neither bundles nor builds: btclib-secp256k1's, already in this process, which a PyPI install does not give
ecdsa               0.19.2            2026-03-26                pure Python; no bindings of any kind, bundled or built
embit               0.8.0             2024-05-30                bundled secp256k1-zkp d9560e0a ctypes bindings, libsecp256k1_darwin_arm64.dylib
python-bitcoinlib   0.12.2            2023-06-03                OpenSSL's libcrypto ctypes bindings, libssl.35.dylib; no libsecp256k1 bundled, built or found
buidl               0.2.36            2022-02-28                pure Python; buidl.cecc cffi bindings need libsec_build.py, unrun
```

## This run

```text
when    : 2026-08-14 23:47 CEST (21:47 UTC)
python  : 3.13.14
method  : one run, kept whole — nothing repeated, no outlier discarded
command : uv run python scripts/bitcoin_libraries.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

ECDSA, BIP340 and BIP32 derivation, then base58check, bech32 and bech32m in
both directions. Microseconds per call, fastest row first, and a ratio
against whichever row came out quickest.

The inputs are every BIP340 signing vector and every BIP32 chain the vendored
files publish, cycled one per call; the address rows are the exception, one
witness-v0 and one witness-v1 address being what is vendored, so they call one
input.

```text
what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

ECDSA sign (32-byte digest, secp256k1)
                               μs/call     vs best
  dsa_sign_pycoin                12.51        1.0x   (50000 calls)
  dsa_sign_embit                 14.54        1.2x   (50000 calls)
  dsa_sign_btclib                19.02        1.5x   (50000 calls)
  dsa_sign_embit_grind           50.70        4.1x   (20000 calls)
  dsa_sign_btclib_grind          63.24        5.1x   (20000 calls)
  dsa_sign_bitcoinlib           206.65       16.5x   (8000 calls)
  dsa_sign_ecdsa                312.10       24.9x   (5000 calls)
  dsa_sign_buidl              30761.15     2458.8x   (50 calls)

ECDSA verify (32-byte digest, secp256k1)
                               μs/call     vs best
  dsa_verify_pycoin              13.45        1.0x   (50000 calls)
  dsa_verify_btclib              22.45        1.7x   (50000 calls)
  dsa_verify_embit               23.18        1.7x   (50000 calls)
  dsa_verify_bitcoinlib         220.16       16.4x   (7000 calls)
  dsa_verify_ecdsa             1202.36       89.4x   (3000 calls)
  dsa_verify_buidl            62655.86     4659.5x   (25 calls)

BIP340 sign (32-byte message)
                               μs/call     vs best
  ssa_sign_embit                 21.50        1.0x   (50000 calls)
  ssa_sign_btclib                22.59        1.1x   (50000 calls)
  ssa_sign_buidl             110672.87     5148.0x   (20 calls)

BIP340 verify (32-byte message)
                               μs/call     vs best
  ssa_verify_embit               25.86        1.0x   (50000 calls)
  ssa_verify_btclib              32.19        1.2x   (50000 calls)
  ssa_verify_buidl            70489.36     2726.0x   (25 calls)

base58check encode, a P2PKH address from a hash160
                               μs/call     vs best
  base58_encode_embit             2.21        1.0x   (200000 calls)
  base58_encode_buidl             2.48        1.1x   (200000 calls)
  base58_encode_btclib            2.50        1.1x   (200000 calls)
  base58_encode_bitcoinlib        2.62        1.2x   (100000 calls)
  base58_encode_pycoin            3.82        1.7x   (200000 calls)

base58check decode, a hash160 from a P2PKH address
                               μs/call     vs best
  base58_decode_embit             2.55        1.0x   (200000 calls)
  base58_decode_btclib            2.64        1.0x   (200000 calls)
  base58_decode_buidl             3.10        1.2x   (200000 calls)
  base58_decode_pycoin            3.79        1.5x   (200000 calls)
  base58_decode_bitcoinlib        4.23        1.7x   (100000 calls)

bech32 encode, a witness-v0 address from a 20-byte program
                               μs/call     vs best
  bech32_encode_btclib            8.44        1.0x   (200000 calls)
  bech32_encode_buidl            12.03        1.4x   (100000 calls)
  bech32_encode_embit            27.59        3.3x   (200000 calls)
  bech32_encode_bitcoinlib       27.65        3.3x   (200000 calls)

bech32 decode, a 20-byte program from a witness-v0 address
                               μs/call     vs best
  bech32_decode_btclib            7.36        1.0x   (200000 calls)
  bech32_decode_buidl            10.61        1.4x   (100000 calls)
  bech32_decode_bitcoinlib       15.04        2.0x   (200000 calls)
  bech32_decode_embit            15.48        2.1x   (200000 calls)

bech32m encode, a witness-v1 address from a 32-byte program
                               μs/call     vs best
  bech32m_encode_btclib          13.91        1.0x   (200000 calls)
  bech32m_encode_buidl           17.66        1.3x   (100000 calls)
  bech32m_encode_embit           41.83        3.0x   (200000 calls)

bech32m decode, a 32-byte program from a witness-v1 address
                               μs/call     vs best
  bech32m_decode_btclib          11.87        1.0x   (200000 calls)
  bech32m_decode_buidl           16.11        1.4x   (100000 calls)
  bech32m_decode_embit           22.74        1.9x   (200000 calls)

BIP32 derive, seed to child, every chain BIP32 publishes
                               μs/call     vs best
  bip32_derive_pycoin            49.59        1.0x   (30000 calls)
  bip32_derive_btclib            66.34        1.3x   (30000 calls)
  bip32_derive_embit             88.50        1.8x   (15000 calls)
  bip32_derive_buidl         109149.13     2201.2x   (12 calls)
```

## What it shows

The sort separates the rows into the two groups the packages table predicts:
the ones that reach C land within a small factor of one another, and the
pure-Python rows fall an order of magnitude or more behind them —
`buidl.pecc` by a great deal more than that. python-bitcoinlib's OpenSSL
path sits between the two groups. Which row is in which group is not a
property of the packages alone, which is what that table's last column is
for.

Three things this output says are worth reading twice:

- **pycoin's row is C on this run**, not Python, and it sorts above
  btclib's — through two imports that are the script's rather than pycoin's.
  `bitcoin.core.key` imports `ctypes.util`, which pycoin's loader needs and
  does not import; the name it then asks for resolves to nothing, so the load
  falls through to the symbols `btclib-secp256k1`'s extension has put in the
  process. Its rows therefore call the same build btclib's rows call, through
  ctypes instead of cffi. What the same package costs held to Python is the
  pycoin row of [the pure-Python table][pure].
- **two libraries here sign more than once by default.** btclib and embit
  both grind for a low-r signature — they sign repeatedly until r fits in
  32 bytes — so their default is not comparable per signature with the
  four rows that sign once. Each therefore has two rows: one signature,
  which is the comparable one, and the default beside it, whose cost is
  that signature times however many draws it took before r fit. Half of
  all draws fit already, so two signatures is the expectation and this
  pair asks several times that — the ratio between a library's two rows is
  where to read what it actually was. That multiple is a property of the
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
orders of magnitude apart next to each other. pycoin's are the only ones
picked at run time, from the backend found: it is the one comparand whose row
can be C on one machine and Python on another, and a count that suits one
measures the clock or takes minutes on the other.

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
