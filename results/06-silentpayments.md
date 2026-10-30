# Silent Payments

[ISS 83][i83] took a census of what `btclib_secp256k1` exports that no other
comparand on [the wrappers page][wrappers] does, and found two whole modules
with no sibling to be read against there: `ellswift` and `silentpayments`.
`ellswift`'s two deterministic calls have a second arithmetic in Python —
`decode_var` in `ecc.ecc.ellswift`, and `xdh` in `btclib.ecc.ellswift`, which
builds on it — reached through the same switch [btclib's own page][two-paths]
reads every row through, so `decode` and `xdh` are timed there, against Python
rather than against a same-package ratio. `btclib-wallet`'s `silent_payments`
has a Python arm too, but no page times it against the bindings, so this page
is the whole of where BIP352 is priced: one comparand, and every ratio between
two of its own calls rather than between two packages.

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
btclib-secp256k1    : 0.8.0.13
```
<!-- provenance: end -->

## This run

<!-- run: begin -->
```text
when    : 2026-10-30 19:50 +07 (12:50 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
commit  : 090c60363adc1833453098ce2061d77d85e842a2
uv.lock : b4fdc6f0fe4ab496c148f7c13430bf4f1c6035704a40258237f28ae753b2e344
```
<!-- run: end -->

## What each table asks

**A payment, made and found.** `create_outputs` is the sender's side and
`scan_outputs` the recipient's, and BIP352 is answered by neither alone: a
wallet that only ever created outputs would never confirm they can be
found. The fixture for the second row is the first row's own output,
scanned for and found before either is timed — the shape [the wrappers
page][wrappers]'s tweak-check table already settled, verifying a claim
against making it.

**The recipient's setup, before any scan.** `prevouts_summary`, `label`
and `labeled_spend_pubkey` are the three calls a recipient makes that are
not themselves a scan: summarizing a transaction's inputs once for every
scan key that will scan it, deriving the change label of a scan key, and
adding that label to a spend key to publish the address it opens. None of
the three is a fresh-versus-prepared pair of the other two — each answers
a different question about what a wallet does before it looks for a
payment — so the table is three prices beside each other rather than a
claim about which is fastest.

`keys.pubkey_sum` and its aggregation siblings are exclusives too, from
the same census, and are not here: they have no part in BIP352, and
folding them into a page about Silent Payments would be the same "ratio
of nothing" the wrappers page's own exclusives already refused for an
ElligatorSwift encode divided by a tweak check.

## The fixtures

Three disjoint slices of [`_inputs`][inputs]' shared pool — one for the
sender's funding input, one for the recipient's scan key, one for the
recipient's spend key — read straight from the top of the pool rather
than shared with a stated reason the way the wrappers page's own
exclusives share theirs: that pool is read by every script in this
project independently, and this page does not compete with the wrappers
page for the same ten slices.

The outpoint every fixture uses is 36 zero bytes. BIP352 asks for the
lexicographically smallest outpoint of the whole transaction, and nothing
timed here reads or checks that ordering — what both `create_outputs` and
`prevouts_summary` are handed is one caller-chosen value, folded into a
hash either way, so any 36 bytes serve every call alike, the way `AUX`
serves the wrappers page's BIP340 rows.

Nothing here reaches past the module's own API into the C it wraps: a row
is either its own call or `NA`, and this page has no `NA` — one comparand,
and every one of its five relevant calls has a row.

## The benchmarks

<!-- output: begin -->
```text
method  : the quickest of 10 rounds; the halves' gap is beside it
command : uv run python scripts/06-silentpayments.py

1. a payment, made and found
                           μs/call     vs best   halves
  scan_outputs               33.15       1.00x     0.00
  create_outputs             44.83       1.35x     0.52

2. the recipient's setup, before any scan
                           μs/call     vs best   halves
  labeled_spend_pubkey        6.04       1.00x     0.07
  label                       8.06       1.33x     0.00
  prevouts_summary            8.99       1.49x     0.00
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
- [mnemonics][mnemonics] — BIP39 and SLIP-0039, `bip39-slip39` against
  Trezor's packages and `embit`

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[mnemonics]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/07-mnemonics.md
[inputs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/src/btclib_benchmarks/_inputs.py
[i83]: https://github.com/btclib-org/btclib-benchmarks/issues/83
