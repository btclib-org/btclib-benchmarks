# btclib against the other bitcoin libraries, one run

What `scripts/bitcoin_libraries.py` printed on the machine named below:
btclib with its bindings enabled, beside `ecdsa`, `pycoin`, `buidl`,
`embit` and `python-bitcoinlib`, over ECDSA, BIP340 and one BIP32
derivation, and then base58check, bech32 and bech32m in both directions.
Microseconds per call, fastest row first, and a ratio against whichever row
came out quickest.

One run, kept whole — including the setup block, which is the half of the
output that says what each comparand resolved to. Read
[README.md][readme] on what these numbers are before carrying any of them
anywhere: an order of magnitude, never a figure to quote.

The inputs are every BIP340 signing vector and every BIP32 chain the vendored
files publish, cycled one per call. Every implementation's public key, BIP340
signature and BIP32 child key is checked against what those specifications
publish before anything is timed. The address rows are the exception: one
witness-v0 and one witness-v1 address are what is vendored here, so those call
one input.

## What produced it

```text
when    : 2026-08-14 20:31 CEST (18:31 UTC)
python  : 3.13.14
command : uv run python scripts/bitcoin_libraries.py
machine : Apple M5, macOS 26.6 (build 25G72), arm64
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9
ecdsa               : 0.19.2
pycoin              : 0.92718.20260405
buidl               : 0.2.36
embit               : 0.8.0
python-bitcoinlib   : 0.12.2

arithmetic under each row
  btclib              bundled libsecp256k1 v0.8.0 cffi bindings, _btclib_secp256k1.cpython-313-darwin.so
  ecdsa               pure Python; no bindings of any kind, bundled or built
  pycoin              ctypes bindings to a libsecp256k1 it neither bundles nor builds: btclib_secp256k1's, already in this process, which a PyPI install does not give
  buidl               pure Python; buidl.cecc cffi bindings need libsec_build.py, unrun
  embit               bundled secp256k1-zkp d9560e0a ctypes bindings, libsecp256k1_darwin_arm64.dylib
  python-bitcoinlib   OpenSSL's libcrypto ctypes bindings, libssl.35.dylib; no libsecp256k1 bundled, built or found

ECDSA sign (32-byte digest, secp256k1)
                               μs/call     vs best
  dsa_sign_pycoin                12.37        1.0x   (50000 calls)
  dsa_sign_embit                 14.24        1.2x   (50000 calls)
  dsa_sign_btclib                19.20        1.6x   (50000 calls)
  dsa_sign_embit_grind           50.19        4.1x   (20000 calls)
  dsa_sign_btclib_grind          65.21        5.3x   (20000 calls)
  dsa_sign_bitcoinlib           195.19       15.8x   (8000 calls)
  dsa_sign_ecdsa                292.46       23.6x   (5000 calls)
  dsa_sign_buidl              29687.51     2399.2x   (50 calls)

ECDSA verify (32-byte digest, secp256k1)
                               μs/call     vs best
  dsa_verify_pycoin              13.00        1.0x   (50000 calls)
  dsa_verify_btclib              23.08        1.8x   (50000 calls)
  dsa_verify_embit               23.18        1.8x   (50000 calls)
  dsa_verify_bitcoinlib         220.09       16.9x   (7000 calls)
  dsa_verify_ecdsa             1123.59       86.4x   (3000 calls)
  dsa_verify_buidl            61170.11     4704.2x   (25 calls)

BIP340 sign (32-byte message)
                               μs/call     vs best
  ssa_sign_embit                 21.35        1.0x   (50000 calls)
  ssa_sign_btclib                22.71        1.1x   (50000 calls)
  ssa_sign_buidl             107967.08     5057.5x   (20 calls)

BIP340 verify (32-byte message)
                               μs/call     vs best
  ssa_verify_embit               24.68        1.0x   (50000 calls)
  ssa_verify_btclib              34.78        1.4x   (50000 calls)
  ssa_verify_buidl            69374.86     2811.4x   (25 calls)

base58check encode, a P2PKH address from a hash160
                               μs/call     vs best
  base58_encode_embit             2.16        1.0x   (200000 calls)
  base58_encode_buidl             2.31        1.1x   (200000 calls)
  base58_encode_btclib            2.46        1.1x   (200000 calls)
  base58_encode_bitcoinlib        2.54        1.2x   (100000 calls)
  base58_encode_pycoin            3.68        1.7x   (200000 calls)

base58check decode, a hash160 from a P2PKH address
                               μs/call     vs best
  base58_decode_btclib            2.53        1.0x   (200000 calls)
  base58_decode_embit             2.58        1.0x   (200000 calls)
  base58_decode_buidl             3.02        1.2x   (200000 calls)
  base58_decode_pycoin            3.74        1.5x   (200000 calls)
  base58_decode_bitcoinlib        4.36        1.7x   (100000 calls)

bech32 encode, a witness-v0 address from a 20-byte program
                               μs/call     vs best
  bech32_encode_btclib            8.07        1.0x   (200000 calls)
  bech32_encode_buidl            11.31        1.4x   (100000 calls)
  bech32_encode_bitcoinlib       26.52        3.3x   (200000 calls)
  bech32_encode_embit            26.68        3.3x   (200000 calls)

bech32 decode, a 20-byte program from a witness-v0 address
                               μs/call     vs best
  bech32_decode_btclib            7.10        1.0x   (200000 calls)
  bech32_decode_buidl            10.58        1.5x   (100000 calls)
  bech32_decode_bitcoinlib       14.57        2.1x   (200000 calls)
  bech32_decode_embit            14.63        2.1x   (200000 calls)

bech32m encode, a witness-v1 address from a 32-byte program
                               μs/call     vs best
  bech32m_encode_btclib          13.26        1.0x   (200000 calls)
  bech32m_encode_buidl           16.87        1.3x   (100000 calls)
  bech32m_encode_embit           39.93        3.0x   (200000 calls)

bech32m decode, a 32-byte program from a witness-v1 address
                               μs/call     vs best
  bech32m_decode_btclib          11.52        1.0x   (200000 calls)
  bech32m_decode_buidl           15.56        1.4x   (100000 calls)
  bech32m_decode_embit           21.68        1.9x   (200000 calls)

BIP32 derive, seed to child, every chain BIP32 publishes
                               μs/call     vs best
  bip32_derive_pycoin            48.80        1.0x   (30000 calls)
  bip32_derive_btclib            62.53        1.3x   (30000 calls)
  bip32_derive_embit             88.66        1.8x   (15000 calls)
  bip32_derive_buidl         107962.60     2212.3x   (12 calls)
```

## What it shows

The sort separates the rows into the two groups the setup block predicts:
the ones that reach C land within a small factor of one another, and the
pure-Python rows fall an order of magnitude or more behind them —
`buidl.pecc` by a great deal more than that. python-bitcoinlib's OpenSSL
path sits between the two groups. Which row is in which group is not a
property of the packages alone, which is what the setup block is for.

Three things this output says are worth reading twice:

- **pycoin's row is C on this run**, not Python, and it sorts above
  btclib's — through two imports that are the script's rather than pycoin's.
  `bitcoin.core.key` imports `ctypes.util`, which pycoin's loader needs and
  does not import; the name it then asks for resolves to nothing, so the load
  falls through to the symbols `btclib_secp256k1`'s extension has put in the
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
publishes, so it has no bech32m row — the script asserts both halves of that.

The loop counts are per row and print beside their rows, sorting putting rows
orders of magnitude apart next to each other. pycoin's are the only ones
picked at run time, from the backend found: it is the one comparand whose row
can be C on one machine and Python on another, and a count that suits one
measures the clock or takes minutes on the other.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
