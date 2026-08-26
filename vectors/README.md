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
`btclib-org/btclib` at commit `2e5f944697e9d4fd9ec0c47956b7f9643bcae503`.
Copying that copy rather than fetching upstream again is deliberate: btclib
is the package under test here, its provenance file is maintained, and one
chain of custody with two links that are both checkable beats two chains.

The near link is what the entries below pin: btclib's blob against ours,
which `git hash-object` reproduces without downloading anything. The far
one is [btclib's own provenance file][pins] at that commit, and the
upstream it names is not one project but several: `bitcoin/bips` for
`bip340_test_vectors.csv`, `C2SP/wycheproof` for
`ecdsa_secp256k1_sha256_bitcoin_test.json` and for the licence beside it,
`bitcoin/bitcoin` for `base58_encode_decode.json`. There is no far blob for
`bip32_test_vectors.json` at all: BIP32 publishes its vectors as prose, so
btclib's entry for that one is transcribed from `bip-0032.mediawiki` rather
than compared to a file, and the chain from here ends at btclib's
transcription.

`WYCHEPROOF_COPYING` sits beside the Wycheproof file, as it does beside
btclib's copy: that file is Google's, under Apache 2.0, and a licence
travels with what it covers. It has an entry like the rest, and it is the
one entry no benchmark reads: `_vectors.read` checks a file as it hands it
over, so what guards the licence is `vectors_test.py` reading this file
instead.

### `vectors/bip340_test_vectors.csv`

```text
repo    btclib-org/btclib
path    tests/ecc/_data/bip340_test_vectors.csv
commit  51ed80e4c8947c9a84f1e51bd97aaeeb68bddd33  2026-07-30
blob    aa317a3b3d53aa904def8b5a625b13073898b349
pulled  2026-08-14
behind  0 revisions; that commit is the tip of the path
```

Verdict: **identical**.

### `vectors/bip32_test_vectors.json`

```text
repo    btclib-org/btclib
path    tests/bip32/_data/bip32_test_vectors.json
commit  9478bf5376088052f84711faf44e86883c3331dc  2023-01-04
blob    eb692228a6fb84a694a699f62937808bc2c640aa
pulled  2026-08-14
behind  0 revisions; that commit is the tip of the path
```

Verdict: **identical**.

### `vectors/ecdsa_secp256k1_sha256_bitcoin_test.json`

```text
repo    btclib-org/btclib
path    tests/ecc/_data/ecdsa_secp256k1_sha256_bitcoin_test.json
commit  c44634e3e0fbbe39d3d04d36ccc6d62bd671871c  2026-08-13
blob    f737aabce273eb9485f21b84d32aa01d3e8b0246
pulled  2026-08-15
behind  1 revision: 2c3ba10bd39f0e580f331d488ae5177a16b36d44, 2026-08-25
```

Verdict: **identical** to the pinned blob. Taking btclib's newer revision
is a decision rather than a chore, and it is not a free one here: the file
carries a `valid`/`invalid` verdict per case and this suite asserts each
package's answer against it, so a case whose verdict moved changes what the
comparands are held to. What `behind` buys is that the choice is visible
without anybody opening btclib.

### `vectors/base58_encode_decode.json`

```text
repo    btclib-org/btclib
path    tests/_data/base58_encode_decode.json
commit  76b006c06462d4485f2ccd4f3b158d2155fbe6aa  2026-08-02
blob    7255fd45c8003ad99ee95c507d8c54f49b50e4c2
pulled  2026-08-15
behind  0 revisions; that commit is the tip of the path
```

Verdict: **identical**.

### `vectors/WYCHEPROOF_COPYING`

```text
repo    btclib-org/btclib
path    tests/ecc/_data/WYCHEPROOF_COPYING
commit  c44634e3e0fbbe39d3d04d36ccc6d62bd671871c  2026-08-13
blob    d645695673349e3947e8e5ae42332d0ac3164cd7
pulled  2026-08-15
behind  0 revisions; that commit is the tip of the path
```

Verdict: **identical**.

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

The address encodings are timed in `scripts/03-libraries.py` and their
vectors are not vendored: BIP173's and BIP350's valid and invalid address
lists belong beside these four, and the bech32m defect that benchmark found
in `python-bitcoinlib` is exactly what an invalid-address list is for.

[pins]: https://github.com/btclib-org/btclib/blob/2e5f944/tests/_data/README.md
