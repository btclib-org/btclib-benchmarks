# Silent Payments

[ISS 83][i83] took a census of what `btclib_secp256k1` exports that no
other comparand on [the wrappers page][wrappers] does, and found two whole
modules with no sibling to be read against there: `ellswift` and
`silentpayments`. `ellswift`'s two deterministic calls turned out to have a
real second arithmetic after all — btclib's own pure-Python `ecc/ellswift.py`
dispatches through the same switch [btclib's own page][two-paths] already
reads every row through, so `decode` and `xdh` are timed there now, against
Python rather than against a same-package ratio. `silentpayments` has no
such split anywhere in btclib, so this page is the whole of where it is
priced: one comparand, and every ratio between two of its own calls rather
than between two packages.

## This run

<!-- run: begin -->
```text
when    : 2026-08-21 03:06 CEST (01:06 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
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
btclib-secp256k1    : 0.8.0.3

method  : the quickest of ten rounds; the halves' gap is beside it
command : uv run python scripts/06-silentpayments.py

1. a payment, made and found
                           μs/call     vs best   halves
  scan_outputs               30.10       1.00x     0.06
  create_outputs             45.70       1.52x     0.40

2. the recipient's setup, before any scan
                           μs/call     vs best   halves
  prevouts_summary            3.89       1.00x     0.01
  labeled_spend_pubkey        6.04       1.55x     0.01
  label                       8.14       2.10x     0.10
```
<!-- output: end -->

## More benchmarks

Five other sets of benchmarks are published in `results/`, each with its
own comparands:

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

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[inputs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/src/btclib_benchmarks/_inputs.py
[i83]: https://github.com/btclib-org/btclib-benchmarks/issues/83
