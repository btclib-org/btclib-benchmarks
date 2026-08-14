# Vendored test vectors

Two files, and what they are for: every package this project measures is
held to them, in the configuration it is measured in, before any of its
timings are believed. A benchmark row is a number produced by code nobody
here wrote, and the only thing that makes one worth printing is that the
code answered a published question correctly first.

`tests/vectors_test.py` is what runs them. btclib is held to them too, which
its own suite already does: redundant is the right amount for the one
package whose numbers this project exists to publish.

## Where each file came from

Both are copies of btclib's own vendored copies, taken from
`btclib-org/btclib` at commit `2e5f944697e9d4fd9ec0c47956b7f9643bcae503`,
whose `tests/_data/README.md` pins each of them in turn to a commit of
`bitcoin/bips` and compares the bytes. Copying that copy rather than
fetching upstream again is deliberate: btclib is the package under test
here, its provenance file is maintained, and one chain of custody with two
links that are both checkable beats two chains.

| file | btclib path at that commit | sha256 |
| --- | --- | --- |
| `bip340_test_vectors.csv` | `tests/ecc/_data/bip340_test_vectors.csv` | `01c8cabb…d98ccfb` |
| `bip32_test_vectors.json` | `tests/bip32/_data/bip32_test_vectors.json` | `5a0e3411…fb85594` |

The full digests, which `vectors_test.py` checks on every run so that a copy
that stops matching this file fails a test rather than passing quietly:

```text
01c8cabba63b4c9b2f44c975902990086a4fe56eee9d265b187d1e2c1d98ccfb  bip340_test_vectors.csv
5a0e3411f974989d9c65ee542101f175ce3847300fd5bdafdd2812ce5fb85594  bip32_test_vectors.json
```

## What is in them, and what that catches

`bip340_test_vectors.csv` is BIP340's own, and its value is the half that is
not a signature to reproduce: of its nineteen rows, eight carry a secret key
and are signing cases, and the rest are verification cases that must be
*rejected* — a public key not on the curve, an s past the order, an r that
is not a field element, a signature over the wrong message. An
implementation that answers true to all of them passes a naive round-trip
test and fails these.

`bip32_test_vectors.json` is BIP32's, four seeds and seventeen chains, each
step publishing the extended private and public key it derives to. It is
keyed by seed, with a list of `[path, xpub, xprv]` per seed.

## What is not here yet

The address encodings are timed in `scripts/bitcoin_libraries.py` and their
vectors are not vendored: BIP173's and BIP350's valid and invalid address
lists belong beside these two, and the bech32m defect that benchmark found
in `python-bitcoinlib` is exactly what an invalid-address list is for.
Wycheproof's `ecdsa_secp256k1_sha256_bitcoin_test.json`, which btclib also
vendors, is the same argument for ECDSA verification.

<!-- The block of digests and the table of paths are both content whose
     columns are not this file's to choose. -->
<!-- markdownlint-configure-file {
       "MD013": { "code_blocks": false, "tables": false }
     } -->
