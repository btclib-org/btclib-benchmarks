# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What the second signature under the same key costs, and the hundredth.

Nearly every row of the other benchmarks times one operation once: a
key, a message, a signature, and a row. That is the right shape for asking
what an operation costs, and the wrong shape for asking what a verifier
pays, because a verifier does not verify one signature. A node checks every
input of every transaction, a wallet checks a batch, a message checker
checks a list -- and does it, over and over, under a key it already has.

The exception is `scripts/01-libsecp256k1.py`'s BIP340 signing pair, which
asks this same question on the signing side: what the four wrappers charge
for a second signature under a key a caller is holding. So this page is the
verifier's half of it rather than the only place the question is put.

Whatever a verification derives from the key alone is the same on the
second call as on the first. This times what that is worth: the same
verification, with the key handed in raw and with it prepared, per
implementation and on both of btclib's paths.

## Reusing this state is not the usual caching trade

The objection to keeping key-derived state alive is that key material
outlives its use. It does not arise here: what is worth preparing is
derived from the *public* key, and a public key is public. There is no
secret in a decompressed point or in a table of its odd multiples, and
nothing is being kept alive that an observer of the signature does not
already have.

The private key has no counterpart to prepare. The one table a signature
leans on is the generator's, which every key shares and which btclib
already memoizes; there is no per-private-key state any of these
implementations builds. So this benchmark is about verification, and its
absence of a signing table is a result and not an omission.

## What it does not show, said before the rows say it

Preparing the key does not bring Python within reach of the C library.
The Python rows move by a small factor and the C rows move by a small
factor, and the order across the two groups is what it was: the gap is
the arithmetic, and no amount of reuse is an amount of C. A reader
hoping the reuse column is where Python catches libsecp256k1 should read
the ratio and stop hoping. What the column does show is where a caller
already has a saving available, and where btclib has none to offer.

## What each implementation lets a caller reuse

- **btclib**, on either path, accepts the public key as a parsed point
  wherever it accepts sec octets, so a caller who parses once and keeps
  the point saves the decompression that every verification from octets
  repeats. On the Python path it also has `curve.PreparedPoint`, which a
  caller builds from a point to say that the key will come back: a
  verification handed one reads the key's multiplication tables from
  btclib's cache, where a bare point's are built again on every call. The
  cache is bounded, so the rows below keep few prepared keys. On the
  libsecp256k1 path a prepared point is accepted too, and its tables go
  unused, the bindings holding tables of their own; its row is there to
  show what is left of the saving.
- **python-ecdsa** has `VerifyingKey.precompute()`, which builds the
  table once and reuses it. On version 0.19.2 it raises `AssertionError`
  on a key built by `from_string` -- `precompute` hands the point to
  `PointJacobi.from_affine`, which does not carry the curve order over,
  and the precomputation asserts on it. A key built from the secret
  exponent works. The caller who cannot use it is therefore the verifier,
  who has the public key as bytes and nothing else, which is the caller
  the method is for; the row below uses the construction that works, so
  it measures the method rather than the defect.

The reference is the fastest row of each table, as the pure-Python
benchmark prints it, and not a row named in advance: with two paths and
two libraries in one table, naming one would be choosing.

## What a run leaves behind

The numbers are written to `results/05-key-reuse.json` as this finishes,
and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from hashlib import sha256
from itertools import cycle
from typing import TYPE_CHECKING, TypeVar

import btclib_secp256k1
import ecc
import ecdsa
from ecc.curves import curve, sec_point
from ecc.ecc import dsa

from btclib_benchmarks import _inputs
from btclib_benchmarks._provenance import described
from btclib_benchmarks._results import (
    BreakEven,
    Measurement,
    Preparation,
    Provenance,
    Ratios,
    Timing,
    page_of,
    rendered_output,
    rendered_provenance,
    save,
    taken_now,
)
from btclib_benchmarks._timing import benchmark, estimate, interleaved, saving_apart

if TYPE_CHECKING:
    from collections.abc import Callable

    from ecc.alias import Point

T = TypeVar("T")


def provenance() -> Provenance:
    """Say which build of each package these rows are about.

    Three lines and no columns: what a reader of this table needs is which
    build answered, and `describe` already lays a version out against a
    name -- a header over three cells would be furniture.
    """
    return Provenance(
        columns=[],
        rows=[],
        notes=described(
            ("ecc", ecc.__file__),
            ("btclib-secp256k1", btclib_secp256k1.__file__),
            ("ecdsa", ecdsa.__file__),
        ),
    )


# The inputs are `_inputs`': one pool, shared by every benchmark here, built
# once and read from `.inputs/` afterwards. Keys nobody chose, so that no row
# is flattered by one, and a row's number is an average over the set rather
# than a measurement of one input. Nothing here asserts: what these
# implementations answer is `tests/`' subject.
#
# Two sizes, because the two halves of this page are far apart in cost. The
# bindings rows make `BINDINGS_CALLS` calls and the Python and python-ecdsa
# rows `SLOW_CALLS`, and a fixture is only worth building for as many calls
# as will read it: `precompute()` alone is slow per key, so `BINDINGS_CALLS`
# prepared python-ecdsa keys would be a long setup for rows that read
# `SLOW_CALLS` of them.
BINDINGS_CALLS = 20_000
SLOW_CALLS = 500

# how many prepared keys the Python rows cycle through. A prepared key's
# tables live in btclib's cache, which holds a bounded number of them
# (`_cached_odd_multiples_aff`'s docstring has the bound): a row cycling
# through more keys than it holds finds none of them and times the build on
# every call. Few enough to stay inside it, and the rows are warmed through
# all of them before they are timed
PREPARED_KEYS = 32

# rounds per row, in two halves; a pair of rows takes its rounds in turn
ROUNDS = 10

MESSAGES = _inputs.messages()[:BINDINGS_CALLS]
PRVKEYS = _inputs.keys()[:BINDINGS_CALLS]

# the two forms of each key: the octets a verifier is handed, and the point
# they decompress to. Both are built here, before anything is timed, because
# which one a row passes is the whole of what it measures
SEC_OCTETS = _inputs.pubkeys_33()[:BINDINGS_CALLS]
POINTS = [sec_point.point_from_octets_var(octets) for octets in SEC_OCTETS]

# grind=False: one signature per key, and the same one both paths verify
DSA_SIGS = [
    dsa.sign_(msg, prvkey, grind=False)
    for msg, prvkey in zip(MESSAGES, PRVKEYS, strict=True)
]

# python-ecdsa's keys, built from the secret exponent rather than from the
# octets: `precompute` raises on a key built from octets, and the docstring
# above says why that is worth a sentence rather than a workaround nobody
# sees. Only as many as its rows will read
ECDSA_SIGNING_KEYS = [
    ecdsa.SigningKey.from_secret_exponent(
        int.from_bytes(prvkey, "big"), curve=ecdsa.SECP256k1
    )
    for prvkey in PRVKEYS[:SLOW_CALLS]
]
ECDSA_KEYS = [key.verifying_key for key in ECDSA_SIGNING_KEYS]
ECDSA_SIGS = [
    key.sign_digest_deterministic(msg, hashfunc=sha256)
    for key, msg in zip(ECDSA_SIGNING_KEYS, MESSAGES, strict=False)
]


def _unprepared_key(prvkey: bytes) -> ecdsa.VerifyingKey:
    """Return a python-ecdsa verifying key with no table built yet.

    From the secret exponent, which is the construction `precompute` accepts:
    on 0.19.2 it raises on a key built from octets, as the docstring above
    says. A function rather than a constant because `precompute_once` below
    needs a fresh one per timed call.
    """
    return ecdsa.SigningKey.from_secret_exponent(
        int.from_bytes(prvkey, "big"), curve=ecdsa.SECP256k1
    ).verifying_key


def _prepared_keys() -> list[ecdsa.VerifyingKey]:
    """Return one precomputed key per input, the tables built once."""
    keys = [_unprepared_key(prvkey) for prvkey in PRVKEYS[:SLOW_CALLS]]
    for key in keys:
        key.precompute()
    return keys


ECDSA_KEYS_PREPARED = _prepared_keys()

# btclib's prepared points, which build nothing until the first verification
# under them asks. `curve.PreparedPoint` is the constructor, and the tables
# fill the cache as `warm_python_rows` walks the keys
PREPARED_POINTS = [curve.PreparedPoint(point) for point in POINTS[:PREPARED_KEYS]]

VERIFY_OCTETS = cycle(list(zip(MESSAGES, SEC_OCTETS, DSA_SIGS, strict=True)))
VERIFY_POINT = cycle(list(zip(MESSAGES, POINTS, DSA_SIGS, strict=True)))
VERIFY_PREPARED = cycle(list(zip(MESSAGES, PREPARED_POINTS, DSA_SIGS, strict=False)))
# the parsed point over the same few keys, the baseline of the prepared rows:
# a row cycling through few keys is not a row cycling through many, and the
# difference between the two is not what a prepared point saves
VERIFY_POINT_FEW = cycle(
    list(
        zip(
            MESSAGES,
            POINTS[:PREPARED_KEYS],
            DSA_SIGS,
            strict=False,
        )
    )
)
VERIFY_ECDSA = cycle(list(zip(MESSAGES, ECDSA_KEYS, ECDSA_SIGS, strict=False)))
VERIFY_ECDSA_PREPARED = cycle(
    list(zip(MESSAGES, ECDSA_KEYS_PREPARED, ECDSA_SIGS, strict=False))
)
PARSE = cycle(SEC_OCTETS)
PARSED = cycle(POINTS)
PREPARE = cycle(PRVKEYS[:SLOW_CALLS])

# triples no prepared point above was built from, so that preparing one of
# them finds no table in the cache. Walked once per preparation timed, and
# far more of them than a run times
FRESH = cycle(
    list(zip(MESSAGES, POINTS, DSA_SIGS, strict=True))[PREPARED_KEYS:BINDINGS_CALLS]
)


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    Called once, from `main`, after every libsecp256k1 row has been timed:
    the run never turns it back on, so the order of the rows below is the
    measurement's own requirement and not a choice.
    """
    curve._libsecp256k1_available = False


def verify_octets() -> None:
    """Time a verification handed the key as sec octets."""
    msg, octets, sig = next(VERIFY_OCTETS)
    dsa.assert_as_valid_(msg, octets, sig)


def verify_point() -> None:
    """Time a verification handed the key as an already-parsed point."""
    msg, point, sig = next(VERIFY_POINT)
    dsa.assert_as_valid_(msg, point, sig)


def verify_point_few() -> None:
    """Time a verification handed a parsed point, over the prepared keys."""
    msg, point, sig = next(VERIFY_POINT_FEW)
    dsa.assert_as_valid_(msg, point, sig)


def verify_prepared() -> None:
    """Time a verification handed the key as a `curve.PreparedPoint`."""
    msg, prepared, sig = next(VERIFY_PREPARED)
    dsa.assert_as_valid_(msg, prepared, sig)


def prepare_point() -> None:
    """Time building a `curve.PreparedPoint`, which builds no table.

    The cost of the preparation on the libsecp256k1 path, where no table is
    built later either. On the Python path the tables are built by the first
    verification, which `prepare_point_once` includes.
    """
    curve.PreparedPoint(next(PARSED))


def warm_python_rows() -> None:
    """Call every Python row once, and the prepared row once per key.

    btclib builds its generator tables lazily, inside the first call that
    needs them, and builds a prepared key's on the first verification under
    it. Called after the switch and before the first Python round, so that
    neither lands in a timed loop: the rows are timed in rounds and keep
    the quickest, which discards a one-time cost only when it is not every
    round's.
    """
    for row in (verify_octets, verify_point, verify_point_few, parse_point):
        row()
    for _ in range(PREPARED_KEYS):
        verify_prepared()


def verify_ecdsa() -> None:
    """Time a python-ecdsa verification, no table prepared."""
    msg, key, sig = next(VERIFY_ECDSA)
    key.verify_digest(sig, msg)


def verify_ecdsa_prepared() -> None:
    """Time a python-ecdsa verification against a precomputed table."""
    msg, key, sig = next(VERIFY_ECDSA_PREPARED)
    key.verify_digest(sig, msg)


def parse_point() -> None:
    """Time decompressing the key once, which parsing a point once saves."""
    octets = next(PARSE)
    sec_point.point_from_octets_var(octets)


def _mean_of_fresh(
    make: Callable[[], T], use: Callable[[T], object], calls: int
) -> float:
    """Return microseconds per `use`, each on a state built off the clock.

    A preparation happens once per key, so a timed call needs a key of its
    own, and building it is work the caller who does *not* prepare pays too:
    a break-even is a difference between the two and must not carry it. One
    state at a time and not a list of them built up front, the clock being
    started after each is built and stopped before the next.
    """
    elapsed = 0.0
    for _ in range(calls):
        state = make()
        start = time.perf_counter()
        use(state)
        elapsed += time.perf_counter() - start
    return elapsed / calls * 1e6


def precompute_once(calls: int, rounds: int) -> float:
    """Return microseconds for one `precompute()`, the quickest of `rounds`.

    `precompute` builds the table once and has nothing to do on a second
    call, so every timed call is on a key of its own.
    """
    return estimate(
        [
            _mean_of_fresh(
                lambda: _unprepared_key(next(PREPARE)),
                lambda key: key.precompute(),
                calls,
            )
            for _ in range(rounds)
        ]
    )[0]


def _prepare_and_verify(triple: tuple[bytes, Point, dsa.Sig]) -> None:
    """Prepare the point and verify once under it, which builds its tables."""
    msg, point, sig = triple
    dsa.assert_as_valid_(msg, curve.PreparedPoint(point), sig)


def prepare_point_and_verify() -> None:
    """Prepare a fresh point and verify once under it, one call of the row."""
    _prepare_and_verify(next(FRESH))


def prepare_point_once(calls: int, rounds: int) -> float:
    """Return microseconds to prepare a point and verify once, the quickest.

    The first verification under a prepared point builds its tables, so
    this is the preparation and one verification. The caller subtracts what
    a verification costs once the tables are there, which leaves the cost
    of getting there.
    """
    return estimate(
        [
            _mean_of_fresh(lambda: next(FRESH), _prepare_and_verify, calls)
            for _ in range(rounds)
        ]
    )[0]


def timing(label: str, rounds: list[float], calls: int) -> Timing:
    """Return a row from its rounds: the quickest, and the halves' gap."""
    value, apart = estimate(rounds)
    return Timing(
        label=label,
        us_per_call=value,
        halves_apart=apart,
        calls=calls,
        rounds=ROUNDS,
    )


def preparation(
    label: str, prepare: float, plain: list[float], prepared: list[float]
) -> Preparation:
    """Return a break-even row from the preparation and the two rows' rounds."""
    return Preparation(
        label=label,
        prepare=prepare,
        plain=estimate(plain)[0],
        prepared=estimate(prepared)[0],
        saving_halves_apart=saving_apart(plain, prepared),
    )


# what the run block claims about how these numbers were taken. A pair of
# rows whose difference is printed takes its rounds in turn, so that a
# machine drifting over the measurement drifts under both
METHOD = f"{ROUNDS} rounds per row, pairs in turn, minimum kept; calls per row"


def main() -> None:
    """Time every row, libsecp256k1 first, print the tables and save the run.

    The order is `python_arithmetic_only`'s requirement: the run never
    turns it back on, so every row that is meant to reach the
    libsecp256k1 runs before it and every row that is meant to measure Python
    runs after. The cost of preparing a point is timed last, after the rows
    that read the cache: a cold preparation puts new tables in it.

    Nothing is printed until it is all measured, both tables being sorted
    and ratioed across their own rows. What reaches the terminal is what
    `render.py` puts in the page, the two coming from one rendering of one
    saved run, which is saved first: a rendering that failed would otherwise
    lose the run.
    """
    bindings_octets, bindings_point, bindings_few, bindings_prepared = interleaved(
        [verify_octets, verify_point, verify_point_few, verify_prepared],
        BINDINGS_CALLS,
        ROUNDS,
    )
    bindings_parse, _ = benchmark(parse_point, BINDINGS_CALLS, ROUNDS)
    bindings_prepare, _ = benchmark(prepare_point, BINDINGS_CALLS, ROUNDS)

    ecdsa_plain, ecdsa_prepared = interleaved(
        [verify_ecdsa, verify_ecdsa_prepared], SLOW_CALLS, ROUNDS
    )
    ecdsa_prepare = precompute_once(20, ROUNDS)

    python_arithmetic_only()
    warm_python_rows()

    python_octets, python_point, python_few, python_prepared = interleaved(
        [verify_octets, verify_point, verify_point_few, verify_prepared],
        SLOW_CALLS,
        ROUNDS,
    )
    python_parse, _ = benchmark(parse_point, 2_000, ROUNDS)
    # what a prepared point costs to get is the preparation and the
    # verification that builds its tables, less a verification once they are
    # built: that verification is paid by the prepared row as well
    python_prepare = prepare_point_once(20, ROUNDS) - estimate(python_prepared)[0]

    verify = Ratios(
        title="ECDSA verify, one key, every signature under it",
        rows=[
            timing("btclib, libsecp256k1, octets", bindings_octets, BINDINGS_CALLS),
            timing(
                "btclib, libsecp256k1, parsed point", bindings_point, BINDINGS_CALLS
            ),
            timing(
                "btclib, libsecp256k1, parsed point, few keys",
                bindings_few,
                BINDINGS_CALLS,
            ),
            timing(
                "btclib, libsecp256k1, PreparedPoint",
                bindings_prepared,
                BINDINGS_CALLS,
            ),
            timing("btclib, Python, octets", python_octets, SLOW_CALLS),
            timing("btclib, Python, parsed point", python_point, SLOW_CALLS),
            timing("btclib, Python, parsed point, few keys", python_few, SLOW_CALLS),
            timing("btclib, Python, PreparedPoint", python_prepared, SLOW_CALLS),
            timing("python-ecdsa", ecdsa_plain, SLOW_CALLS),
            timing("python-ecdsa, precomputed", ecdsa_prepared, SLOW_CALLS),
        ],
    )

    # a PreparedPoint is answered against the parsed point over the same
    # keys, not against the octets: the caller who prepares has parsed the
    # key already, and `prepare` does not pay the parse. The parse is the
    # "parse once" rows' saving
    #
    # what a preparation saves, and after how many calls it has paid, are
    # the renderer's to divide out: what is measured is the preparation and
    # the two verifications it sits between. Those two are the same
    # implementation's own rows and not the fastest of the table -- what a
    # caller decides is whether to prepare *this* key, and the row that
    # answers is the one they would otherwise have run
    costs = BreakEven(
        title="what preparing the key costs, and after how many verifications it pays",
        rows=[
            preparation(
                "btclib, libsecp256k1, parse once",
                bindings_parse,
                bindings_octets,
                bindings_point,
            ),
            preparation(
                "btclib, libsecp256k1, PreparedPoint",
                bindings_prepare,
                bindings_few,
                bindings_prepared,
            ),
            preparation(
                "btclib, Python, parse once", python_parse, python_octets, python_point
            ),
            preparation(
                "btclib, Python, PreparedPoint",
                python_prepare,
                python_few,
                python_prepared,
            ),
            preparation(
                "python-ecdsa, precompute()",
                ecdsa_prepare,
                ecdsa_plain,
                ecdsa_prepared,
            ),
        ],
    )

    measurement = Measurement(
        benchmark=page_of(__file__),
        run=taken_now(__file__, METHOD),
        provenance=provenance(),
        tables=[verify, costs],
    )
    saved = save(measurement)
    print(rendered_provenance(measurement.provenance))
    print()
    print(rendered_output(measurement))
    print(f"\nsaved to {saved}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
