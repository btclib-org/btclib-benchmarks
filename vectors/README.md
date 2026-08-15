# Vendored test vectors

Four files, and what they are for: every package this project measures is
held to them, in the configuration it is measured in, before any of its
timings are believed. A benchmark row is a number produced by code nobody
here wrote, and the only thing that makes one worth printing is that the
code answered a published question correctly first.

`tests/vectors_test.py` is what runs them. btclib is held to them too, which
its own suite already does: redundant is the right amount for the one
package whose numbers this project exists to publish.

## Where each file came from

All four are copies of btclib's own vendored copies, taken from
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
| `ecdsa_secp256k1_sha256_bitcoin_test.json` | `tests/ecc/_data/ecdsa_secp256k1_sha256_bitcoin_test.json` | `27c848b8…3771c756` |
| `base58_encode_decode.json` | `tests/_data/base58_encode_decode.json` | `20d51011…c2682ca` |

The full digests, which `vectors_test.py` checks on every run so that a copy
that stops matching this file fails a test rather than passing quietly:

```text
01c8cabba63b4c9b2f44c975902990086a4fe56eee9d265b187d1e2c1d98ccfb  bip340_test_vectors.csv
5a0e3411f974989d9c65ee542101f175ce3847300fd5bdafdd2812ce5fb85594  bip32_test_vectors.json
27c848b8cfa4e3f3bfbda27971542dd9b827e393842d5549fdfdf1923771c756  ecdsa_secp256k1_sha256_bitcoin_test.json
20d51011f49339714c28b9244cc5238f4c78bb9206dc8fc61500aed6fc2682ca  base58_encode_decode.json
```

`WYCHEPROOF_COPYING` sits beside the Wycheproof file, as it does beside
btclib's copy: that file is Google's, under Apache 2.0, and a licence
travels with what it covers. It carries no digest here because nothing reads
it — a test checking a licence for drift would be checking the wrong thing.

## What is in them, and what that catches

`bip340_test_vectors.csv` is BIP340's own, and its value is the half that is
not a signature to reproduce. Rows carrying a secret key are signing cases;
the rest are verifications, and the ones expecting FALSE are a public key not
on the curve, an s past the order, an r that is not a field element, a
signature over the wrong message. An implementation that answers true to all
of them passes a naive round-trip test and fails these.

`bip32_test_vectors.json` is BIP32's, keyed by seed, with a list of
`[path, xpub, xprv]` per seed: every step publishes the extended private and
public key it derives to.

`ecdsa_secp256k1_sha256_bitcoin_test.json` is Wycheproof's, and it is the
adversarial one: verifications over a public key each, most of them
signatures to *reject*. Where BIP340's file publishes a few bad inputs
alongside its good ones, this one is built to break a verifier — BER lengths
where DER has one form, lengths that overflow a uint64, bytes appended to a
signature that then still parses, an r past the field, a k·G with an extreme
x-coordinate.

It found things, which is the point of having it:

- **pycoin accepts signatures it should refuse**, and buidl fewer of them.
  Both are the DER decoder rather than the arithmetic: a length in long
  form, a leading zero, trailing bytes. buidl has arithmetic ones besides,
  and one of those rejects a signature that is valid.
- **The packages that implement ECDSA themselves leave low s to their
  caller**, which is not a defect and is why the file's name says `bitcoin`.
  Refusing the high s of a malleable pair is policy rather than arithmetic,
  and libsecp256k1 applies it inside `secp256k1_ecdsa_verify` — so the
  packages that reach that C inherit the rule and the others do not. Both
  answers are right to a different question, and `tests/vectors_test.py`
  asserts each package's own.

The wrong answers are recorded there as expected failures rather than
excluded, so that a release fixing one of them fails the suite and somebody
comes back to read it.

`base58_encode_decode.json` is Bitcoin Core's, a list of `[hex, base58]`
pairs, and it is base58 with no checksum on it. The rows that time it encode
a *base58check* address, so what this file pins is the layer under them, and
the layer where implementations differ: the alphabet is easy, and the
leading zeros are not — a zero byte is a `1` rather than a digit of a
number, and the file opens with the empty payload and carries several
starting in zeros.

Two answers here are worth reading. buidl cannot encode the empty payload at
all: `encode_base58` goes through `int(s.hex(), 16)`, which raises on the
empty string, so that pair is an expected failure like the ones above. And
buidl is absent from the decoding half, because it publishes no base58
decode without a checksum — which of these packages can be asked a question
is a property of its API, and the suite says which rather than skipping
whatever raises.

## What is not here yet

The address encodings are timed in `scripts/bitcoin_libraries.py` and their
vectors are not vendored: BIP173's and BIP350's valid and invalid address
lists belong beside these four, and the bech32m defect that benchmark found
in `python-bitcoinlib` is exactly what an invalid-address list is for.

<!-- The block of digests and the table of paths are both content whose
     columns are not this file's to choose. -->
<!-- markdownlint-configure-file {
       "MD013": { "code_blocks": false, "tables": false }
     } -->
