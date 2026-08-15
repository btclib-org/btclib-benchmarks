# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What the second signature under the same key costs, and the hundredth.

The other four benchmarks time one operation once: a key, a message, a
signature, and a row. That is the right shape for asking what an
operation costs, and the wrong shape for asking what a verifier pays,
because a verifier does not verify one signature. A node checks every
input of every transaction, a wallet checks a batch, a message checker
checks a list -- and does it, over and over, under a key it already has.

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
  the point has that saving today. It has no prepared key beyond that:
  the multiplication tables built from the point are dropped when the
  call returns and rebuilt on the next one, which is
  btclib-org/btclib#893.
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

The numbers are written to `results/key-reuse.json` as this finishes,
and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from hashlib import sha256
from itertools import cycle

import btclib
import btclib_secp256k1
import ecdsa
from _provenance import described
from _results import (
    BreakEven,
    Measurement,
    Preparation,
    Provenance,
    Ratios,
    Timing,
    rendered_output,
    rendered_provenance,
    save,
    slug,
    taken_now,
)
from _vectors import signing
from btclib.curves import curve, sec_point
from btclib.ecc import dsa
from btclib.to_pub_key import pub_keyinfo_from_prv_key


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
            ("btclib", btclib.__file__),
            ("btclib-secp256k1", btclib_secp256k1.__file__),
            ("ecdsa", ecdsa.__file__),
        ),
    )


# every BIP340 signing vector, cycled, as every other script here takes them:
# keys nobody chose, so that no row is flattered by one, and a row's number is
# an average over the set rather than a measurement of one input.
#
# pycoin's constraint applies to python-ecdsa too by way of the digest: a
# vector message of zero is not a legal digest for an ECDSA row, so the ECDSA
# cycles take the vectors whose message reduces to something else
SIGNING = [v for v in signing() if int.from_bytes(v.msg, "big") % curve.secp256k1.n]

# the two forms of each key: the octets a verifier is handed, and the point
# they decompress to. Both are built here, before anything is timed, because
# which one a row passes is the whole of what it measures
SEC_OCTETS = [pub_keyinfo_from_prv_key(v.prvkey)[0] for v in SIGNING]
POINTS = [sec_point.point_from_octets(octets) for octets in SEC_OCTETS]

# grind=False: one signature per vector, and the same one both paths verify
DSA_SIGS = [dsa.sign_(v.msg, v.prvkey, grind=False) for v in SIGNING]

# python-ecdsa's keys, built from the secret exponent rather than from the
# octets: `precompute` raises on a key built from octets, and the docstring
# above says why that is worth a sentence rather than a workaround nobody sees
ECDSA_SIGNING_KEYS = [
    ecdsa.SigningKey.from_secret_exponent(
        int.from_bytes(v.prvkey, "big"), curve=ecdsa.SECP256k1
    )
    for v in SIGNING
]
ECDSA_KEYS = [key.verifying_key for key in ECDSA_SIGNING_KEYS]
ECDSA_SIGS = [
    key.sign_digest_deterministic(v.msg, hashfunc=sha256)
    for key, v in zip(ECDSA_SIGNING_KEYS, SIGNING, strict=True)
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
    """Return one precomputed key per vector, the tables built once."""
    keys = [_unprepared_key(v.prvkey) for v in SIGNING]
    for key in keys:
        key.precompute()
    return keys


ECDSA_KEYS_PREPARED = _prepared_keys()

# the specification's own public keys, checked before anything is timed
for _v, _octets, _sig in zip(SIGNING, SEC_OCTETS, DSA_SIGS, strict=True):
    assert _octets[1:] == _v.xonly_pubkey
    assert dsa.verify_(_v.msg, _octets, _sig)

VERIFY_OCTETS = cycle(
    [
        (v.msg, octets, sig)
        for v, octets, sig in zip(SIGNING, SEC_OCTETS, DSA_SIGS, strict=True)
    ]
)
VERIFY_POINT = cycle(
    [
        (v.msg, point, sig)
        for v, point, sig in zip(SIGNING, POINTS, DSA_SIGS, strict=True)
    ]
)
VERIFY_ECDSA = cycle(
    [
        (v.msg, key, sig)
        for v, key, sig in zip(SIGNING, ECDSA_KEYS, ECDSA_SIGS, strict=True)
    ]
)
VERIFY_ECDSA_PREPARED = cycle(
    [
        (v.msg, key, sig)
        for v, key, sig in zip(SIGNING, ECDSA_KEYS_PREPARED, ECDSA_SIGS, strict=True)
    ]
)
PARSE = cycle(list(zip(SEC_OCTETS, POINTS, strict=True)))
PREPARE = cycle([v.prvkey for v in SIGNING])


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    Called once, from `main`, after every bindings row has been timed:
    the assignment cannot be undone within a process, so the order of the
    rows below is the measurement's own requirement and not a choice.
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


def verify_ecdsa() -> None:
    """Time a python-ecdsa verification, no table prepared."""
    msg, key, sig = next(VERIFY_ECDSA)
    key.verify_digest(sig, msg)


def verify_ecdsa_prepared() -> None:
    """Time a python-ecdsa verification against a precomputed table."""
    msg, key, sig = next(VERIFY_ECDSA_PREPARED)
    key.verify_digest(sig, msg)


def parse_point() -> None:
    """Time the preparation btclib offers: decompressing the key once."""
    octets, _expected = next(PARSE)
    sec_point.point_from_octets(octets)


def benchmark(func: Callable[[], None], calls: int) -> float:
    """Return microseconds per call, `calls` calls of `func`.

    Returned and not printed, as the other four scripts do it: every row
    divides by the fastest of its table, so no line can be written until
    the whole table is in hand.
    """
    # perf_counter and not time(): the wall clock can step backwards
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def prepare_once(func: Callable[[], object], calls: int) -> float:
    """Return microseconds for one preparation, `calls` of them timed.

    Separate from `benchmark` because a preparation is not a row of the
    table above: it happens once per key and is paid before the first
    verification, so what it belongs in is the break-even below.
    """
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def precompute_once(calls: int) -> float:
    """Return microseconds for one `precompute()`, keys built off the clock.

    Not `prepare_once(...)` of a function that builds a key and prepares
    it, which is what this was: building the verifying key is work the
    caller who does *not* prepare pays too, so a break-even -- a
    difference between the two -- must not carry it. It is a tenth of what
    the preparation itself costs and it moved the break-even by a whole
    verification.

    `precompute` builds the table once and has nothing to do on a second
    call, so a timed call needs a key of its own. One at a time and not a
    list of them built up front: a caller holds one prepared key, not
    twenty, and the clock is started after each is built and stopped
    before the next -- which is what leaves the construction out.
    """
    elapsed = 0.0
    for _ in range(calls):
        key = _unprepared_key(next(PREPARE))
        start = time.perf_counter()
        key.precompute()
        elapsed += time.perf_counter() - start
    return elapsed / calls * 1e6


# what the run block claims about how these numbers were taken. Every row
# here is timed once: the two paths and the two libraries are orders of
# magnitude apart, and what this table asks -- whether preparing a key is
# worth it -- is not a question rounds would sharpen
METHOD = "one run, kept whole \N{EM DASH} nothing repeated, no outlier discarded"


def main() -> None:
    """Time every row, bindings first, print the tables and save the run.

    The order is `python_arithmetic_only`'s requirement: it cannot be
    undone within a process, so every row that is meant to reach the
    bindings runs before it and every row that is meant to measure Python
    runs after.

    Nothing is printed until it is all measured, both tables being sorted
    and ratioed across their own rows. What reaches the terminal is what
    `render.py` puts in the page, the two coming from one rendering of one
    saved run.
    """
    bindings_octets = benchmark(verify_octets, 20_000)
    bindings_point = benchmark(verify_point, 20_000)
    bindings_parse = prepare_once(parse_point, 20_000)

    ecdsa_plain = benchmark(verify_ecdsa, 500)
    ecdsa_prepared = benchmark(verify_ecdsa_prepared, 500)
    ecdsa_prepare = precompute_once(20)

    python_arithmetic_only()

    python_octets = benchmark(verify_octets, 500)
    python_point = benchmark(verify_point, 500)
    python_parse = prepare_once(parse_point, 2_000)

    verify = Ratios(
        title="ECDSA verify, one key, every signature under it",
        rows=[
            Timing(label=label, us_per_call=value)
            for label, value in (
                ("btclib, bindings, octets", bindings_octets),
                ("btclib, bindings, parsed point", bindings_point),
                ("btclib, Python, octets", python_octets),
                ("btclib, Python, parsed point", python_point),
                ("python-ecdsa", ecdsa_plain),
                ("python-ecdsa, precomputed", ecdsa_prepared),
            )
        ],
    )

    # what a preparation saves, and after how many calls it has paid, are
    # the renderer's to divide out: what is measured is the preparation and
    # the two verifications it sits between. Those two are the same
    # implementation's own rows and not the fastest of the table -- what a
    # caller decides is whether to prepare *this* key, and the row that
    # answers is the one they would otherwise have run
    costs = BreakEven(
        title="what preparing the key costs, and after how many verifications it pays",
        rows=[
            Preparation(
                label="btclib, bindings, parse once",
                prepare=bindings_parse,
                plain=bindings_octets,
                prepared=bindings_point,
            ),
            Preparation(
                label="btclib, Python, parse once",
                prepare=python_parse,
                plain=python_octets,
                prepared=python_point,
            ),
            Preparation(
                label="python-ecdsa, precompute()",
                prepare=ecdsa_prepare,
                plain=ecdsa_plain,
                prepared=ecdsa_prepared,
            ),
        ],
    )

    measurement = Measurement(
        benchmark=slug(__file__),
        run=taken_now(__file__, METHOD),
        provenance=provenance(),
        tables=[verify, costs],
    )
    print(rendered_provenance(measurement.provenance))
    print()
    print(rendered_output(measurement))
    print(f"\nsaved to {save(measurement)}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
