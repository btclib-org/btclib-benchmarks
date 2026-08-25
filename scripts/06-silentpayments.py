# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of BIP352, which no comparand on any other page here offers.

[ISS 83][iss83] took a census of what `btclib_secp256k1` exports that the
three other wrappers of `results/01-libsecp256k1.md` do not, and found two
whole modules with no sibling to be read against: `ellswift` and
`silentpayments`. `ellswift`'s two deterministic calls turned out to have a
real second arithmetic after all -- btclib's own pure-Python
`ecc/ellswift.py` dispatches through the same switch every row of
`02-btclib-vs-btclib.py` already reads, so `decode` and `xdh` are timed
there now, against Python rather than against a same-package ratio.
`silentpayments` has no such split anywhere in btclib: `pkgutil.iter_modules`
over `btclib.ecc` names no such module, so this page is the whole of where
it is priced, one comparand and no ratio against anything but itself.

[iss83]: https://github.com/btclib-org/btclib-benchmarks/issues/83

## What is here, and what a ratio between two rows means

Every table below prices two or three calls against each other rather than
one wrapper against another, and each table stays the rule the wrappers
page's own exclusives kept: a ratio is between two things that answer one
question, never between two unrelated operations. `keys.pubkey_sum` and its
aggregation siblings are exclusives too and are not here -- they have no
part in BIP352, and folding them into a page about Silent Payments would be
the same "ratio of nothing" ISS 83 already refused for an ElligatorSwift
encode divided by a silent-payment scan.

**A payment, made and found.** `create_outputs` is the sender's side and
`scan_outputs` the recipient's, and BIP352 is not answered by either alone:
a wallet that only ever created outputs would never confirm they can be
found, and the fixture for the second row is the first row's own output,
scanned for and found before either is timed. The pair is the claim and its
verification, the shape the wrappers page's tweak-check table already
settled.

**The recipient's setup, before any scan.** `prevouts_summary`, `label` and
`labeled_spend_pubkey` are the three calls a recipient makes that are not
themselves a scan: summarizing a transaction's inputs once for every scan
key that will scan it, deriving the m-th label of a scan key, and adding
that label to a spend key to publish the address it opens. None of the
three is a "fresh" and a "prepared" measurement of the other two -- each
answers a different question about what a wallet does before it looks for
a payment -- so the table is read as three prices next to each other rather
than as a claim about which is fastest.

## The fixtures, and what they are not

The keys are three disjoint slices of `_inputs`' shared pool: one for the
sender's funding input, one for the recipient's scan key, one for the
recipient's spend key -- read straight from the top of the pool rather than
shared with a stated reason the way the wrappers page's own exclusives
share theirs, because nothing here competes with `01-libsecp256k1.py` for
the same ten slices; that pool is read by every script in this project
independently; see its own docstring.

The outpoint every fixture uses is 36 zero bytes. BIP352 asks for the
lexicographically smallest outpoint of the whole transaction, and nothing
timed here reads or checks that ordering -- what both `create_outputs` and
`prevouts_summary` are handed is one caller-chosen value, folded into a
hash either way, so any 36 bytes serve every call alike, the way `AUX`
serves the wrappers page's BIP340 rows.

Nothing here reaches past the module's own API into the C it wraps: a row
is either its own call or `NA`, and there is no `NA` on this page because
there is one comparand and every one of its five relevant calls has a row.

## What a run leaves behind

The numbers are written to `results/06-silentpayments.json` as this
finishes, and `scripts/render.py` writes the page beside it from that
file alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from itertools import cycle
from typing import TYPE_CHECKING

import btclib_secp256k1.keys
from btclib_secp256k1 import silentpayments

from btclib_benchmarks import _inputs
from btclib_benchmarks._provenance import described
from btclib_benchmarks._results import (
    Measurement,
    Provenance,
    Ratios,
    Timing,
    Unavailable,
    labels,
    page_of,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def provenance() -> Provenance:
    """Say which build of `btclib_secp256k1` these rows are about.

    One line and no columns, as [the held-key page][reuse] states its own
    single comparand: what a reader of this table needs is which build
    answered, and a header over one cell would be furniture.

    [reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
    """
    return Provenance(
        columns=[],
        rows=[],
        notes=described(("btclib-secp256k1", btclib_secp256k1.keys.__file__)),
    )


# the outpoint every fixture below uses -- see the module docstring for why
# 36 zero bytes serve every call the same as any other 36 bytes would
OUTPOINT = bytes(36)

# BIP352 reserves m = 0 for the change label, and every `label` row below
# derives that one: which label a wallet derives first is not this page's
# question, and a fixed m keeps the row comparable with itself across calls
# the way a fixed AUX keeps a BIP340 row comparable on the wrappers page
LABEL_M = 0

# three disjoint slices of the shared pool, read from the top rather than
# shared with a stated reason: see the module docstring for why this page
# does not compete with the wrappers page's own ten
SLICE = 2_000
_KEYS = _inputs.keys()
_PUBKEYS = _inputs.pubkeys_33()

FUNDING_KEYS = _KEYS[:SLICE]
SCAN_KEYS = _KEYS[SLICE : 2 * SLICE]
SPEND_PUBKEYS = _PUBKEYS[2 * SLICE : 3 * SLICE]
SCAN_PUBKEYS = _PUBKEYS[SLICE : 2 * SLICE]

FUNDING_PUBKEYS = [
    btclib_secp256k1.keys.pubkey_from_prvkey(prvkey) for prvkey in FUNDING_KEYS
]

# one output per recipient, one funding input per output: the smallest
# transaction BIP352 defines, repeated over the slice rather than built
# larger, since what a bigger transaction costs is the same call summing
# more keys and is not a different question
CREATED = [
    silentpayments.create_outputs(
        [(scan_pk, spend_pk)], OUTPOINT, taproot_prvkeys=[funding_key]
    )[0]
    for scan_pk, spend_pk, funding_key in zip(
        SCAN_PUBKEYS, SPEND_PUBKEYS, FUNDING_KEYS, strict=True
    )
]
SUMMARIES = [
    silentpayments.prevouts_summary(OUTPOINT, taproot_pubkeys_bytes=[funding_pubkey])
    for funding_pubkey in FUNDING_PUBKEYS
]

# the claim above and its verification, checked once per slice entry before
# any of it is timed: what create_outputs made, scan_outputs has to find,
# an output that were not found being the one failure a timed loop -- which
# discards what it returns -- could not see
for _output, _scan_key, _summary, _spend_pk in zip(
    CREATED, SCAN_KEYS, SUMMARIES, SPEND_PUBKEYS, strict=True
):
    _found = silentpayments.scan_outputs([_output], _scan_key, _summary, _spend_pk)
    assert len(_found) == 1
    assert _found[0][0] == _output
    assert _found[0][2] is None

LABELS = [silentpayments.label(scan_key, LABEL_M) for scan_key in SCAN_KEYS]

# the labeled half of the same claim and verification: a payment to the
# address the label opens is found under that label and not under the
# unlabeled one, which is what a wallet publishing a labeled address is
# trusting `scan_outputs`' `labels` argument for
_labeled_spend_pubkey = silentpayments.labeled_spend_pubkey(
    SPEND_PUBKEYS[0], LABELS[0][0]
)
_labeled_output = silentpayments.create_outputs(
    [(SCAN_PUBKEYS[0], _labeled_spend_pubkey)],
    OUTPOINT,
    taproot_prvkeys=[FUNDING_KEYS[0]],
)[0]
_labeled_found = silentpayments.scan_outputs(
    [_labeled_output],
    SCAN_KEYS[0],
    SUMMARIES[0],
    SPEND_PUBKEYS[0],
    labels={LABELS[0][0]: LABELS[0][1]},
)
assert len(_labeled_found) == 1
assert _labeled_found[0][0] == _labeled_output
assert _labeled_found[0][2] == LABELS[0][0]

CREATE_CYCLE = cycle(list(zip(SCAN_PUBKEYS, SPEND_PUBKEYS, FUNDING_KEYS, strict=True)))
SCAN_CYCLE = cycle(list(zip(CREATED, SCAN_KEYS, SUMMARIES, SPEND_PUBKEYS, strict=True)))
SUMMARY_CYCLE = cycle(FUNDING_PUBKEYS)
LABEL_CYCLE = cycle(SCAN_KEYS)
LABELED_SPEND_CYCLE = cycle(
    list(zip(SPEND_PUBKEYS, [label for label, _tweak in LABELS], strict=True))
)


def sp_create_outputs() -> None:
    """Time creating the one taproot output that pays one address."""
    scan_pk, spend_pk, funding_key = next(CREATE_CYCLE)
    silentpayments.create_outputs(
        [(scan_pk, spend_pk)], OUTPOINT, taproot_prvkeys=[funding_key]
    )


def sp_scan_outputs() -> None:
    """Time finding the one output the row above made."""
    output, scan_key, summary, spend_pk = next(SCAN_CYCLE)
    silentpayments.scan_outputs([output], scan_key, summary, spend_pk)


def sp_prevouts_summary() -> None:
    """Time summarizing a transaction's inputs, for scanning it."""
    funding_pubkey = next(SUMMARY_CYCLE)
    silentpayments.prevouts_summary(OUTPOINT, taproot_pubkeys_bytes=[funding_pubkey])


def sp_label() -> None:
    """Time deriving the change label of a scan key, and its tweak."""
    scan_key = next(LABEL_CYCLE)
    silentpayments.label(scan_key, LABEL_M)


def sp_labeled_spend_pubkey() -> None:
    """Time adding a label to a spend public key."""
    spend_pk, label_bytes = next(LABELED_SPEND_CYCLE)
    silentpayments.labeled_spend_pubkey(spend_pk, label_bytes)


PAYMENT_ROWS = (sp_create_outputs, sp_scan_outputs)
SETUP_ROWS = (sp_prevouts_summary, sp_label, sp_labeled_spend_pubkey)

# every row is called once before anything is timed: a fixture built wrong
# would otherwise be timed rather than reported
for _row in PAYMENT_ROWS + SETUP_ROWS:
    _row()

# ten thousand calls: `create_outputs` and `scan_outputs` both derive a
# shared secret, which is one point multiplication and a tagged hash apart
# from the wrappers page's own signing rows, and this count puts a round
# in the same fraction of a second theirs are. `prevouts_summary`, `label`
# and `labeled_spend_pubkey` are cheaper -- a sum of one point, a tagged
# hash, and a point addition -- and share the count rather than ask for
# their own: unlike the wrappers page's parse tables, none of the three is
# two orders of magnitude from the rest of this page
DEFAULT_CALLS = 10_000

ROUNDS = 10


def benchmark(func: Callable[[], None], calls: int) -> tuple[float, float]:
    """Return the quickest round's microseconds per call, and the halves' gap.

    `ROUNDS` rounds of `calls` calls each, the minimum of the quickest half
    against the quickest of the other half -- `01-libsecp256k1.py`'s own
    `benchmark`, copied rather than imported: `_results.py` holds the shape
    of a run and never the arithmetic that produces one, so each script
    that wants this statistic carries its own copy of the formula, and that
    function's docstring carries the reasoning for it.
    """
    rounds = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(calls):
            func()
        rounds.append((time.perf_counter() - start) / calls * 1e6)
    half = len(rounds) // 2
    first, second = min(rounds[:half]), min(rounds[half:])
    return min(first, second), abs(first - second)


def measured(title: str, rows: tuple[Callable[[], None], ...]) -> Ratios:
    """Time every row of one table and return it, fastest row first.

    No `missing` argument: this page has one comparand and every row it
    could offer does, so there is no `NA` to print. See `01-libsecp256k1.py`'s
    own `measured` for the reasoning this one is a smaller copy of.
    """
    timings: list[Timing | Unavailable] = []
    for label, func in zip(labels([f.__name__ for f in rows]), rows, strict=True):
        print(f"\r{label:<24}", end="", file=sys.stderr)
        value, apart = benchmark(func, DEFAULT_CALLS)
        timings.append(
            Timing(
                label=label,
                us_per_call=value,
                halves_apart=apart,
                calls=DEFAULT_CALLS,
                rounds=ROUNDS,
            )
        )
    print("\r" + " " * 30 + "\r", end="", file=sys.stderr)
    return Ratios(title=title, decimals=2, rows=timings)


TABLES: tuple[tuple[str, tuple[Callable[[], None], ...]], ...] = (
    ("1. a payment, made and found", PAYMENT_ROWS),
    ("2. the recipient's setup, before any scan", SETUP_ROWS),
)

# what the run block claims about how these numbers were taken
METHOD = "the quickest of ten rounds; the halves' gap is beside it"


def main() -> None:
    """Print the two tables and save the run.

    One pass, unlike the wrappers page: that page pays for a second one
    because it is the cheapest of the six and states how far two passes
    of it disagree for every page here to read. This one does not carry
    that line, the way the other four do not either.
    """
    packages = provenance()
    print(rendered_provenance(packages))
    print()
    width = width_for(
        [label for _, rows in TABLES for label in labels([f.__name__ for f in rows])]
    )
    tables = []
    for title, rows in TABLES:
        table = measured(title, rows)
        print(rendered_table(table, width, counted=True))
        print()
        tables.append(table)

    saved = save(
        Measurement(
            benchmark=page_of(__file__),
            run=taken_now(__file__, METHOD),
            provenance=packages,
            tables=tables,
            timing_note=[],
        )
    )
    print(f"saved to {saved}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
