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

The inputs are BIP340's first test vector and BIP32's first. Every
implementation's public key, BIP340 signature and BIP32 child key is checked
against what those specifications publish before anything is timed.

## What produced it

```text
when    : 2026-08-14 18:48 CEST (16:48 UTC)
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
  dsa_sign_pycoin                12.34        1.0x   (50000 calls)
  dsa_sign_embit                 14.33        1.2x   (50000 calls)
  dsa_sign_btclib                17.33        1.4x   (50000 calls)
  dsa_sign_embit_grind          119.69        9.7x   (20000 calls)
  dsa_sign_btclib_grind         133.98       10.9x   (20000 calls)
  dsa_sign_bitcoinlib           194.54       15.8x   (8000 calls)
  dsa_sign_ecdsa                302.50       24.5x   (5000 calls)
  dsa_sign_buidl              29936.51     2426.6x   (50 calls)

ECDSA verify (32-byte digest, secp256k1)
                               μs/call     vs best
  dsa_verify_pycoin              12.75        1.0x   (50000 calls)
  dsa_verify_btclib              22.67        1.8x   (50000 calls)
  dsa_verify_embit               22.84        1.8x   (50000 calls)
  dsa_verify_bitcoinlib         215.47       16.9x   (7000 calls)
  dsa_verify_ecdsa             1054.74       82.7x   (3000 calls)
  dsa_verify_buidl            60959.80     4781.1x   (25 calls)

BIP340 sign (32-byte message)
                               μs/call     vs best
  ssa_sign_btclib                20.10        1.0x   (50000 calls)
  ssa_sign_embit                 21.30        1.1x   (50000 calls)
  ssa_sign_buidl              91325.50     4542.5x   (20 calls)

BIP340 verify (32-byte message)
                               μs/call     vs best
  ssa_verify_btclib              23.12        1.0x   (50000 calls)
  ssa_verify_embit               23.43        1.0x   (50000 calls)
  ssa_verify_buidl            60667.67     2623.6x   (25 calls)

base58check encode, a P2PKH address from a hash160
                               μs/call     vs best
  base58_encode_embit             2.13        1.0x   (200000 calls)
  base58_encode_buidl             2.30        1.1x   (200000 calls)
  base58_encode_btclib            2.41        1.1x   (200000 calls)
  base58_encode_bitcoinlib        2.53        1.2x   (100000 calls)
  base58_encode_pycoin            3.67        1.7x   (200000 calls)

base58check decode, a hash160 from a P2PKH address
                               μs/call     vs best
  base58_decode_btclib            2.51        1.0x   (200000 calls)
  base58_decode_embit             2.52        1.0x   (200000 calls)
  base58_decode_buidl             3.04        1.2x   (200000 calls)
  base58_decode_pycoin            3.77        1.5x   (200000 calls)
  base58_decode_bitcoinlib        4.22        1.7x   (100000 calls)

bech32 encode, a witness-v0 address from a 20-byte program
                               μs/call     vs best
  bech32_encode_btclib            8.00        1.0x   (200000 calls)
  bech32_encode_buidl            11.29        1.4x   (100000 calls)
  bech32_encode_bitcoinlib       26.41        3.3x   (200000 calls)
  bech32_encode_embit            26.63        3.3x   (200000 calls)

bech32 decode, a 20-byte program from a witness-v0 address
                               μs/call     vs best
  bech32_decode_btclib            7.18        1.0x   (200000 calls)
  bech32_decode_buidl            10.40        1.4x   (100000 calls)
  bech32_decode_bitcoinlib       14.52        2.0x   (200000 calls)
  bech32_decode_embit            14.52        2.0x   (200000 calls)

bech32m encode, a witness-v1 address from a 32-byte program
                               μs/call     vs best
  bech32m_encode_btclib          13.21        1.0x   (200000 calls)
  bech32m_encode_buidl           16.94        1.3x   (100000 calls)
  bech32m_encode_embit           40.02        3.0x   (200000 calls)

bech32m decode, a 32-byte program from a witness-v1 address
                               μs/call     vs best
  bech32m_decode_btclib          11.46        1.0x   (200000 calls)
  bech32m_decode_buidl           15.53        1.4x   (100000 calls)
  bech32m_decode_embit           21.71        1.9x   (200000 calls)

BIP32 derive, seed to m/0h/1 (16-byte seed)
                               μs/call     vs best
  bip32_derive_pycoin            39.58        1.0x   (30000 calls)
  bip32_derive_btclib            58.54        1.5x   (30000 calls)
  bip32_derive_embit             71.61        1.8x   (15000 calls)
  bip32_derive_buidl          88961.01     2247.8x   (12 calls)
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
  btclib's. Its loader asks `ctypes.util.find_library` for a name that
  resolves to nothing here, so it falls through to the symbols already in
  the process — which `btclib_secp256k1`'s extension has put there — and it
  only gets as far as asking because `bitcoin.core.key`, imported above it,
  has already imported `ctypes.util`, which pycoin's own module does not.
  So its rows call the same build btclib's rows call, through ctypes
  instead of cffi, and dropping either import from the script would turn
  the same rows back into Python. What that same package costs when it is
  held to Python is the pycoin row of [the pure-Python table][pure].
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

The encoding tables are the only ones here that are not curve work, and
they are where these libraries differ most: pure Python in all five, so what
separates them is the code and nothing else. They also hold the one wrong
answer in this benchmark. `python-bitcoinlib` encodes a witness-v1 program
with bech32's checksum constant where BIP350 requires bech32m's, and rejects
the address BIP350 publishes, so it has no bech32m row — the script asserts
both halves of that rather than leaving the absence unexplained.

The loop counts are per row and print beside their rows, because sorting
puts rows whose counts differ by orders of magnitude next to each other.
pycoin's are the only ones the script picks at run time, from the backend
it found: it is the one comparand here whose row can be C on one machine
and Python on another, and a count that suits one of those measures the
clock or takes minutes on the other. Every other row's count is written,
buidl's small ones included — it is pure Python wherever its separate
build step has not been run, which is everywhere this installs from PyPI.

[readme]: https://github.com/btclib-org/btclib-benchmarks/blob/main/README.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md

<!-- The output above is a script's, whose columns are the script's to
     choose; rewrapping it to 80 would make it something else. The
     configuration comment below has to open with its own keyword, so the
     reason for it is here rather than inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
