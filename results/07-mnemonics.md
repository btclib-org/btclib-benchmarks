# Mnemonics

BIP39 and SLIP-0039, as [bip39-slip39][bip39-slip39] implements them,
against its peers: Trezor's `mnemonic` for BIP39, Trezor's
`shamir-mnemonic` for SLIP-0039, and `embit`, which implements both. A
table holds a row for each package that implements its operation, and an
`NA` row for a package that implements the scheme and not that operation.

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package          version     released
bip39-slip39     2026.10.24  2026-10-24
embit            0.8.0       2024-05-30
shamir-mnemonic  0.3.0       2024-05-16
mnemonic         0.21        2024-01-05
```
<!-- provenance: end -->

Every row runs Python code over the standard library alone, each seed and
each share encryption through `hashlib.pbkdf2_hmac`, so no column names a
backend.

## This run

<!-- run: begin -->
```text
when    : 2026-10-28 04:23 CET (03:23 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
commit  : not recorded
uv.lock : not recorded
```
<!-- run: end -->

## What each table asks

**BIP39.** Encoding entropy to words, decoding words to entropy with the
language given, detecting the language of a sentence, and stretching a
sentence to its seed. `bip39-slip39` and `embit` verify the checksum
before stretching, and each also offers to skip it; Trezor's `mnemonic`
never verifies. So the seed table has a verify and a noverify row for
each package that offers both, and only the `noverify` rows answer the
same question. `embit` ships the english word-list alone, and has no
language detection.

**SLIP-0039.** Splitting a master secret into shares, combining shares
back into the secret, parsing a share's words, and encoding a share back
into words. The shares are one group, three of five members needed, at
iteration exponent 0, and not extendable: `embit` reads no extendable
flag, and the same shares then serve every package. `embit`'s combine row
parses each share and calls `ShareSet.recover`, the one call that returns
the secret; `ShareSet.recover_mnemonic` adds a BIP39 encoding of it.
`embit` has no split row: `generate_shares` splits a BIP39 sentence rather
than a master secret, and into one-member groups.

## The fixtures

The entropy and the master secrets are read from the top of
[`_inputs`][inputs]' pool: the BIP39 entropy is a whole 32-byte key, and a
SLIP-0039 master secret is the first 16 bytes of one. The sentences and
the shares are `bip39-slip39`'s encoding of them, built once before
anything is timed, and each package parses its own share objects from the
same words.

`tests/mnemonic_rows_test.py` holds every package to a published BIP39
vector and a published SLIP-0039 one, and to `bip39-slip39`'s answers on
these fixtures. No row checks what it returns.

## The benchmarks

Each row is timed in rounds, and the quickest round is kept. The numbers
are an order of magnitude, never a figure to quote.

**`vs best`** is a row's time over the fastest row of its table.
**`halves`** is in microseconds, like the number beside it. The rounds are
split in half, and the column is how far the quickest round of one half
sat from the quickest of the other: this run's agreement with itself. Two
adjacent rows closer together than their `halves` are not ordered by the
run. Each row prints its rounds and its calls per round beside it.

<!-- output: begin -->
```text
method  : 10 rounds per row in two halves, minimum kept; calls per row
command : uv run python scripts/07-mnemonics.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/, not by a script
  (CONTRIBUTING.md's Writing a row names where)

1. BIP39 encode: 256 bits of entropy to 24 words
                             μs/call     vs best   halves
  mnemonic                      2.57       1.00x     0.01   (10x50,000 calls)
  bip39-slip39                 12.93       5.03x     0.14   (10x10,000 calls)
  embit                        13.86       5.39x     0.14   (10x10,000 calls)

2. BIP39 decode: 24 words to their entropy, the language given
                             μs/call     vs best   halves
  bip39-slip39                 15.49       1.00x     0.05   (10x8,000 calls)
  mnemonic                    138.62       8.95x     0.58   (10x1,500 calls)
  embit                       185.32      11.96x     0.54   (10x1,000 calls)

3. BIP39 language detection: 24 words
                             μs/call     vs best   halves
  bip39-slip39                  4.46       1.00x     0.05   (10x25,000 calls)
  mnemonic                   2180.73     489.24x     6.27   (10x70 calls)
  embit                           NA

4. BIP39 seed: 24 words, an empty passphrase
                             μs/call     vs best   halves
  embit, noverify             351.00       1.00x     0.07   (10x400 calls)
  mnemonic, noverify          351.23       1.00x     0.18   (10x400 calls)
  bip39-slip39, noverify      351.90       1.00x     0.11   (10x400 calls)
  bip39-slip39, verify        374.13       1.07x     0.06   (10x400 calls)
  embit, verify               535.83       1.53x     1.06   (10x400 calls)

5. SLIP-0039 split: a 128-bit master secret into three-of-five shares
                             μs/call     vs best   halves
  bip39-slip39                739.51       1.00x     0.80   (10x200 calls)
  shamir-mnemonic             774.37       1.05x     1.27   (10x200 calls)
  embit                           NA

6. SLIP-0039 combine: three of five shares into the master secret
                             μs/call     vs best   halves
  bip39-slip39                717.85       1.00x     1.34   (10x200 calls)
  shamir-mnemonic             738.68       1.03x     0.29   (10x200 calls)
  embit                       847.15       1.18x     0.95   (10x200 calls)

7. SLIP-0039 share parse: 20 words to a share
                             μs/call     vs best   halves
  bip39-slip39                  7.51       1.00x     0.08   (10x8,000 calls)
  shamir-mnemonic              12.26       1.63x     0.01   (10x15,000 calls)
  embit                        48.97       6.52x     0.33   (10x3,000 calls)

8. SLIP-0039 share encode: a share to 20 words
                             μs/call     vs best   halves
  bip39-slip39                  6.35       1.00x     0.03   (10x10,000 calls)
  embit                        10.59       1.67x     0.06   (10x15,000 calls)
  shamir-mnemonic              12.18       1.92x     0.02   (10x15,000 calls)
```
<!-- output: end -->

## More benchmarks

The other sets of benchmarks published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four bindings of one C library,
  side by side
- [btclib's two paths][two-paths] — btclib against itself, its
  pure-Python arithmetic against the wrappers measured there
- [python libraries][libs] — where a wrapper, if there is one, is just
  one component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second
  verification under a key costs, which a table of fresh keys cannot show
- [Silent Payments][sp] — what only `btclib_secp256k1` offers of BIP352,
  which no other comparand here implements at all

[bip39-slip39]: https://github.com/btclib-org/bip39-slip39
[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md
[inputs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/src/btclib_benchmarks/_inputs.py

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
