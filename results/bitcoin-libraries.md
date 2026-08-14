# btclib against the other bitcoin libraries, one run

What `scripts/bitcoin_libraries.py` printed on the machine named below:
btclib with its bindings enabled, beside `ecdsa`, `pycoin`, `buidl`,
`embit` and `python-bitcoinlib`, over ECDSA, BIP340 and one BIP32
derivation. Microseconds per call, fastest row first, and a ratio against
whichever row came out quickest — not against btclib's, which would print
btclib's score where the table's answer belongs; where btclib stands is
its own place in the order.

One run, kept whole — including the setup block, which is the half of the
output that says what each comparand resolved to. Read
[README.md][readme] on what these numbers are before carrying any of them
anywhere: an order of magnitude, never a figure to quote.

The inputs are BIP340's first test vector and BIP32's first, so the key,
the message and the seed are published values rather than values chosen
here — and every implementation's public key, BIP340 signature and BIP32
child key was checked against what the specification publishes before any
of this was timed, not merely against btclib's answer.

## What produced it

```text
machine : Apple M5, macOS 26.6 (build 25G72), arm64
when    : 2026-08-14 16:47 CEST (14:47 UTC)
command : uv run python scripts/bitcoin_libraries.py
state   : a working desktop, browser and editor open — not a quiesced
          machine, which is the condition README.md says to distrust
```

## The output

```text
btclib              : 2026.9                   (btclib-org/btclib main@30ed0263b116)
btclib-secp256k1    : 0.8.0.1                  (released)
python              : 3.13.14

btclib               : 2026.9 (bindings enabled)
btclib_secp256k1     : 0.8.0.1
ecdsa                : 0.19.2 (pure Python, no native path)
pycoin               : 0.92718.20260405 (libsecp256k1, via ctypes)
buidl                : 0.2.36 (pure Python)
embit                : 0.8.0 (bundled libsecp256k1, via ctypes, always)
python-bitcoinlib    : 0.12.2 (OpenSSL, via ctypes; libsecp256k1 available but unused: False)

ECDSA sign (32-byte digest, secp256k1)
                           us/call     vs best
  dsa_sign_pycoin            13.58        1.0x   (50000 calls)
  dsa_sign_embit             15.64        1.2x   (50000 calls)
  dsa_sign_btclib            17.98        1.3x   (50000 calls)
  dsa_sign_embit_grind      123.68        9.1x   (20000 calls)
  dsa_sign_btclib_grind     147.19       10.8x   (20000 calls)
  dsa_sign_bitcoinlib       222.43       16.4x   (8000 calls)
  dsa_sign_ecdsa            331.64       24.4x   (5000 calls)
  dsa_sign_buidl          33784.65     2487.7x   (50 calls)

ECDSA verify (32-byte digest, secp256k1)
                           us/call     vs best
  dsa_verify_pycoin          12.82        1.0x   (50000 calls)
  dsa_verify_embit           22.85        1.8x   (50000 calls)
  dsa_verify_btclib          22.88        1.8x   (50000 calls)
  dsa_verify_bitcoinlib     214.27       16.7x   (7000 calls)
  dsa_verify_ecdsa         1060.34       82.7x   (3000 calls)
  dsa_verify_buidl        61376.90     4787.9x   (25 calls)

BIP340 sign (32-byte message)
                           us/call     vs best
  ssa_sign_btclib            20.44        1.0x   (50000 calls)
  ssa_sign_embit             21.34        1.0x   (50000 calls)
  ssa_sign_buidl          91804.81     4492.3x   (20 calls)

BIP340 verify (32-byte message)
                           us/call     vs best
  ssa_verify_btclib          23.20        1.0x   (50000 calls)
  ssa_verify_embit           23.57        1.0x   (50000 calls)
  ssa_verify_buidl        60736.88     2618.4x   (25 calls)

BIP32 derive, seed to m/0h/1 (16-byte seed)
                           us/call     vs best
  bip32_derive_pycoin        39.69        1.0x   (30000 calls)
  bip32_derive_btclib        58.99        1.5x   (30000 calls)
  bip32_derive_embit         71.70        1.8x   (15000 calls)
  bip32_derive_buidl      90626.36     2283.5x   (12 calls)
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
  which is the comparable one, and the default beside it, which for this
  key and message costs four signatures where two is the expectation. That
  multiple is a property of the pair, not of either library, and it is why
  the grinding rows sit where they do in the order rather than beside their
  own one-signature rows.

  This was invisible until the fixture became a published vector: the key
  it replaced happened to want two signatures, so grinding cost about what
  a reader would have read as ordinary overhead.
- **python-ecdsa's verification row is twice what it used to be, and the
  new number is the right one.** This table used to sign with the private
  key 1, whose public key is the generator — and python-ecdsa hands back
  the generator *object* for it, precomputed table and all. Every row
  verifying against that key verified with a table no real key gets. The
  published vector's key has no such table, so the row now costs what
  verification costs. Nothing about python-ecdsa changed; what changed is
  that the input is no longer one that flattered it.

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
