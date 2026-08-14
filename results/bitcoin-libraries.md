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
when    : 2026-08-14 17:44 CEST (15:44 UTC)
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
  btclib              libsecp256k1 v0.8.0 compiled into btclib_secp256k1 0.8.0.1, _btclib_secp256k1.cpython-313-darwin.so, through cffi bindings
  ecdsa               pure Python; it has no bindings of any kind
  pycoin              the same libsecp256k1 btclib's row calls, which it neither bundles nor compiles, through ctypes bindings
  buidl               pure Python; the cffi bindings of buidl.cecc are not built
  embit               the prebuilt libsecp256k1 it bundles, libsecp256k1_darwin_arm64.dylib, through ctypes bindings
  python-bitcoinlib   OpenSSL's libcrypto, through ctypes bindings, no libsecp256k1 of its own to opt into

ECDSA sign (32-byte digest, secp256k1)
                           us/call     vs best
  dsa_sign_pycoin            12.30        1.0x   (50000 calls)
  dsa_sign_embit             14.15        1.2x   (50000 calls)
  dsa_sign_btclib            17.04        1.4x   (50000 calls)
  dsa_sign_embit_grind      120.34        9.8x   (20000 calls)
  dsa_sign_btclib_grind     135.24       11.0x   (20000 calls)
  dsa_sign_bitcoinlib       193.05       15.7x   (8000 calls)
  dsa_sign_ecdsa            297.40       24.2x   (5000 calls)
  dsa_sign_buidl          30069.80     2445.1x   (50 calls)

ECDSA verify (32-byte digest, secp256k1)
                           us/call     vs best
  dsa_verify_pycoin          12.94        1.0x   (50000 calls)
  dsa_verify_btclib          22.72        1.8x   (50000 calls)
  dsa_verify_embit           24.04        1.9x   (50000 calls)
  dsa_verify_bitcoinlib     221.85       17.1x   (7000 calls)
  dsa_verify_ecdsa         1076.48       83.2x   (3000 calls)
  dsa_verify_buidl        63663.85     4918.6x   (25 calls)

BIP340 sign (32-byte message)
                           us/call     vs best
  ssa_sign_btclib            21.28        1.0x   (50000 calls)
  ssa_sign_embit             21.71        1.0x   (50000 calls)
  ssa_sign_buidl          93099.54     4374.9x   (20 calls)

BIP340 verify (32-byte message)
                           us/call     vs best
  ssa_verify_embit           23.48        1.0x   (50000 calls)
  ssa_verify_btclib          23.53        1.0x   (50000 calls)
  ssa_verify_buidl        61083.50     2601.6x   (25 calls)

BIP32 derive, seed to m/0h/1 (16-byte seed)
                           us/call     vs best
  bip32_derive_pycoin        39.19        1.0x   (30000 calls)
  bip32_derive_btclib        59.39        1.5x   (30000 calls)
  bip32_derive_embit         71.07        1.8x   (15000 calls)
  bip32_derive_buidl      90320.02     2304.9x   (12 calls)
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
  multiple is a property of the pair rather than of either library, and it
  is why the grinding rows sit where they do in the order rather than
  beside their own one-signature rows.
- **python-ecdsa's verification row is worth reading against its key.**
  Handed the private key 1, python-ecdsa returns the generator *object* as
  the public key — precomputed table and all — and a row verifying against
  it verifies with a table no real key gets, at about half the cost. The
  key here is BIP340's, which has no such table, so the row costs what
  verification costs. It is the sharpest reason in these four files for
  taking the input from a specification rather than choosing one.

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
