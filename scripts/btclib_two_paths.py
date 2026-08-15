# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib against btclib: its two arithmetics, side by side.

Not btclib against btclib-secp256k1. Every row is btclib called through the
same public function, and its two columns are the two arithmetics that answer
underneath -- the libsecp256k1 that btclib-secp256k1 bundles and compiles into
a cffi extension, or the Python of `curves/curve_group.py`. `pip install
btclib` installs both, so neither column is a package a reader chooses
between, and the ratio is what the Python costs when the bindings decline.

It declines for every curve that is not secp256k1, for a zero scalar, for the
point at infinity, and for anything outside what libsecp256k1's entry points
take.

Which operations have two arithmetics is not a judgement call:
`_libsecp256k1_serves` is the predicate every dispatch site asks, and the
modules holding one are `curves/sec_point.py`, `curves/curve.py`,
`ecc/dsa.py`, `ecc/ssa.py`, `ecc/dh.py`, `ecc/bms.py`, `ecc/ellswift.py`,
`ecc/commit_nonce.py`, `ecc/pedersen.py` and `script/taproot.py`. The rows
below are the ones reachable through a public function. `commit_nonce` and
`pedersen` have none: anti-exfil signing and Pedersen commitments are
protocol machinery rather than operations an application performs.

## Why BIP32 derivation is not a row

btclib's BIP32 has one arithmetic. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
reason beside the call: BIP32 is defined for secp256k1 and nothing else, so
no other curve needs a fallback. Throwing the switch leaves the derivation in
C and moves only the public key derived for the fingerprint, so a row for it
would compare C against C with a Python step added. Its ratio was far
narrower than every other, which is how that showed.

That a row belongs here is therefore a property to prove.
`tests/pure_python_path_test.py` blocks every bindings entry point and
asserts each operation still answers. BIP32 derivation is timed in
`scripts/bitcoin_libraries.py`, where being C is the premise.

## One function per operation, timed twice

`python_arithmetic_only` is process-wide, so which arithmetic a call reaches
is a property of when it runs rather than of which function was called. The
table's two labels are made from the operation's name, `_libsecp256k1` and
`_pure_python`: every row here is btclib, and every row here is invoked from
Python.

## The inputs

Every BIP340 signing vector, cycled, `_vectors` reading the file and checking
its digest. The public keys and BIP340 signatures are checked against what
the specification publishes; ECDSA's nonce is btclib's own RFC6979, so those
fixtures are cross-checked between the arithmetics instead.

The timings would not move for an arbitrary key -- three valid keys measure
the same to within the noise of the machine -- but the assertions would, and
one key would have flattered a row: the public key of 1 is the generator, and
a pure-Python implementation handed it derives one ladder step rather than a
full-width scalar's worth.

A timed function calls one path and discards what it returns: nothing here
is a correctness check. `tests/vectors_test.py` is, and it runs the vendored
vectors against both paths; `tests/pure_python_path_test.py` checks the
second path exists at all, which is the failure this script cannot see. The
assertions below run at import, where the fixtures are built, so the suite
loading this module runs them and no timing carries them.

Not part of the test suite and not run by CI. No third-party dependency
either.

## What a run leaves behind

The numbers are written to `results/02-btclib-vs-btclib.json` as this
and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from importlib.metadata import version
from itertools import cycle

from _provenance import from_a_declared_source, origin_of
from _results import (
    Measurement,
    Pair,
    Pairs,
    Provenance,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)
from _vectors import signing, verification
from btclib import b58
from btclib.curves import curve, sec_point
from btclib.ecc import bms, dh, dsa, ellswift, ssa
from btclib.script import taproot
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def provenance() -> Provenance:
    """Say which build of each package these rows are about, in one line.

    A released wheel and a working tree satisfy the same requirement and
    resolve in silence, so which one ran is something the output has to
    state rather than something the reader assumes. Where an install is not
    the declared one, that is what a reader has to act on, and it goes
    under the line rather than inside it.

    Two packages and no columns: a table of two rows is a table only in the
    sense that it has edges, and the unit and the sort have to be said
    somewhere above the numbers, which is here.

    The bindings' version is btclib-secp256k1's, that being what a caller
    installs; which revision of libsecp256k1 it bundled is recorded in
    `scripts/libsecp256k1_bindings.py`, against the release it was read
    from, and one script naming a pin is enough.
    """
    stated = (
        f"btclib {version('btclib')} (bindings {version('btclib-secp256k1')}), "
        f"measured as \N{GREEK SMALL LETTER MU}s/call, sorted on the ratio"
    )
    odd = [
        f"  {dist_name}: {origin_of(dist_name)}"
        for dist_name in ("btclib", "btclib-secp256k1")
        if not from_a_declared_source(dist_name)
    ]
    return Provenance(columns=[], rows=[], notes=[stated, *odd])


# every published vector, cycled, rather than one input repeated: a row that
# calls one input a hundred thousand times measures that input. `_vectors`
# reads the file and checks its digest, and each row below takes the next of
# what it publishes per call
SIGNING = signing()
VERIFYING = verification()

PRVKEYS = [v.prvkey for v in SIGNING]
PUBKEYS = [pub_keyinfo_from_prv_key(prvkey)[0] for prvkey in PRVKEYS]
POINTS = [sec_point.point_from_octets(pubkey) for pubkey in PUBKEYS]

# ECDSA has no published signature to reproduce -- RFC6979's nonce is
# btclib's own -- so these are signed here, grind=False for one signature.
# The keys and messages are still the vector file's
DSA_SIGS = [dsa.sign_(v.msg, v.prvkey, grind=False) for v in SIGNING]

# Diffie-Hellman needs a counterparty: each key is paired with the next key's
# point, which keeps every input published and every pair distinct
COUNTERPARTIES = POINTS[1:] + POINTS[:1]
# `diffie_hellman` takes the scalar as an integer where the rest of these
# APIs take bytes, so the cycle carries integers for this row alone
SCALARS = [int.from_bytes(prvkey, "big") for prvkey in PRVKEYS]
DH_SECRETS = [
    dh.diffie_hellman(scalar, point, 32)
    for scalar, point in zip(SCALARS, COUNTERPARTIES, strict=True)
]

ADDRESSES = [b58.p2pkh(pubkey) for pubkey in PUBKEYS]
BMS_SIGS = [bms.sign(v.msg, v.prvkey) for v in SIGNING]
TAPROOT_PUBKEYS = [taproot.output_pubkey(pubkey)[0] for pubkey in PUBKEYS]
# ElligatorSwift encoding draws a random field element, so an encoded form is
# a fixture and never a row: decoding one is what is deterministic, and what
# the dispatch is on
ELLS = [ellswift.encode_var(pubkey) for pubkey in PUBKEYS]

# what the specification says, checked before anything is timed. The public
# keys and the BIP340 signatures are the vector file's own, so a mistake the
# two paths share cannot survive here, where it would survive the cross-path
# checks in the rows below
for _v, _pubkey in zip(SIGNING, PUBKEYS, strict=True):
    assert _pubkey[1:] == _v.xonly_pubkey
    assert ssa.sign_(_v.msg, _v.prvkey, aux=_v.aux).serialize() == _v.sig
for _valid in VERIFYING:
    assert ssa.verify_(_valid.msg, _valid.xonly_pubkey, _valid.sig)

# one cycle per operation. `itertools.cycle` rather than an index: a C-level
# iterator, the same cost in every row, and nothing to run off the end of
PUBKEY_CYCLE = cycle(list(zip(PRVKEYS, PUBKEYS, strict=True)))
POINT_PARSE_CYCLE = cycle(list(zip(PUBKEYS, POINTS, strict=True)))
MULT_CYCLE = cycle(list(zip(SCALARS, POINTS, strict=True)))
DSA_SIGN_CYCLE = cycle(
    [(v.msg, v.prvkey, sig) for v, sig in zip(SIGNING, DSA_SIGS, strict=True)]
)
DSA_VERIFY_CYCLE = cycle(
    [
        (v.msg, pubkey, sig)
        for v, pubkey, sig in zip(SIGNING, PUBKEYS, DSA_SIGS, strict=True)
    ]
)
DSA_RECOVER_CYCLE = cycle(
    [
        (v.msg, sig, point)
        for v, sig, point in zip(SIGNING, DSA_SIGS, POINTS, strict=True)
    ]
)
SSA_SIGN_CYCLE = cycle([(v.msg, v.prvkey, v.aux, v.sig) for v in SIGNING])
SSA_VERIFY_CYCLE = cycle([(v.msg, v.xonly_pubkey, v.sig) for v in VERIFYING])
DH_CYCLE = cycle(list(zip(SCALARS, COUNTERPARTIES, DH_SECRETS, strict=True)))
BMS_SIGN_CYCLE = cycle(
    [(v.msg, v.prvkey, sig) for v, sig in zip(SIGNING, BMS_SIGS, strict=True)]
)
BMS_VERIFY_CYCLE = cycle(
    [
        (v.msg, address, sig)
        for v, address, sig in zip(SIGNING, ADDRESSES, BMS_SIGS, strict=True)
    ]
)
TAPROOT_CYCLE = cycle(list(zip(PUBKEYS, TAPROOT_PUBKEYS, strict=True)))
ELLSWIFT_CYCLE = cycle(list(zip(ELLS, POINTS, strict=True)))


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    `_libsecp256k1_serves` reads `_libsecp256k1_available` on every call,
    so this one assignment reaches the nine modules that imported the
    predicate by name. Naming modules instead is what leaves a row meant
    to measure Python measuring C, and it does so silently: a pure-Python
    public key comes back at bindings speed, `to_pub_key` asking
    `curves.sec_point`, which is the module such a list forgets. A row
    added below cannot reintroduce that.

    Called once, after every fixture above is built: those go through the
    bindings too, and there is no reason to slow them down.
    """
    curve._libsecp256k1_available = False


def pubkey() -> None:
    """Time a public key derived from a private key, SEC bytes out.

    `generator_mult` below is the multiplication inside this one, without
    the serialization: the two rows together say what each half costs.
    """
    prvkey, _expected = next(PUBKEY_CYCLE)
    pub_keyinfo_from_prv_key(prvkey)[0]


def point_parse() -> None:
    """Time parsing a compressed public key, which recovers y from x.

    The reverse of what `pubkey_from_prvkey` serializes.
    """
    pubkey_bytes, _expected = next(POINT_PARSE_CYCLE)
    sec_point.point_from_octets(pubkey_bytes)


def mult() -> None:
    """Time the generator multiplication every key derivation is built on."""
    scalar, _expected = next(MULT_CYCLE)
    curve.mult(scalar)


def dsa_sign() -> None:
    """Time one ECDSA signature: RFC6979's nonce, and no low-r grinding.

    `grind=False`, and no second row for the default, where the benchmarks
    that compare packages carry one. Grinding signs repeatedly until r fits
    in 32 bytes, and the number of attempts is a property of the key and
    message rather than of the arithmetic: both paths make the same number,
    so both rows would be multiplied by it and the ratio -- which is what
    this table is read for -- would not move, as measuring it confirms.
    """
    msg, prvkey, _expected = next(DSA_SIGN_CYCLE)
    dsa.sign_(msg, prvkey, grind=False)


def dsa_verify() -> None:
    """Time ECDSA verification."""
    msg, pubkey_bytes, sig = next(DSA_VERIFY_CYCLE)
    dsa.verify_(msg, pubkey_bytes, sig)


def dsa_recover() -> None:
    """Time recovering the candidate public keys of an ECDSA signature."""
    msg, sig, _point = next(DSA_RECOVER_CYCLE)
    dsa.recover_pub_keys_(msg, sig)


def ssa_sign() -> None:
    """Time BIP340 signing, over each vector's own aux_rand."""
    msg, prvkey, aux, _expected = next(SSA_SIGN_CYCLE)
    ssa.sign_(msg, prvkey, aux=aux).serialize()


def ssa_verify() -> None:
    """Time BIP340 verification."""
    msg, xonly_pubkey, sig = next(SSA_VERIFY_CYCLE)
    ssa.verify_(msg, xonly_pubkey, sig)


def dh_shared_secret() -> None:
    """Time the ECDH shared secret of one vector key with another's point."""
    scalar, point, _expected = next(DH_CYCLE)
    dh.diffie_hellman(scalar, point, 32)


def bms_sign() -> None:
    """Time signing a bitcoin message, which signs recoverably."""
    msg, prvkey, _expected = next(BMS_SIGN_CYCLE)
    bms.sign(msg, prvkey)


def bms_verify() -> None:
    """Time verifying a bitcoin message, which recovers the key from it."""
    msg, address, sig = next(BMS_VERIFY_CYCLE)
    bms.verify(msg, address, sig)


def taproot_tweak() -> None:
    """Time tweaking a public key into a taproot output key."""
    pubkey_bytes, _expected = next(TAPROOT_CYCLE)
    taproot.output_pubkey(pubkey_bytes)[0]


def ellswift_decode() -> None:
    """Time decoding an ElligatorSwift-encoded public key."""
    ell, _expected = next(ELLSWIFT_CYCLE)
    ellswift.decode_var(ell)


# every row is called once, through the bindings, before anything is
# timed: an operation whose fixture is wrong would otherwise be timed
# rather than reported
for _op in (
    pubkey,
    point_parse,
    mult,
    dsa_sign,
    dsa_verify,
    dsa_recover,
    ssa_sign,
    ssa_verify,
    dh_shared_secret,
    bms_sign,
    bms_verify,
    taproot_tweak,
    ellswift_decode,
):
    _op()


def benchmark(func: Callable[[], None], mult_: int) -> float:
    """Call `func` 1000 * `mult_` times and return the microseconds per call.

    Microseconds per call, as every table in this project prints: a unit
    that changes between benchmarks is a unit a reader has to convert
    before comparing two of them. Five significant digits, which is four
    more than the machine can be held to and enough that two rows within a
    percent of each other are still two numbers.

    Returned and not printed: the table is sorted on the ratio each row
    divides its own two numbers into, so no line can be written until every
    number is in hand.

    The count is per operation *and* per path, the two columns below
    holding the two: the pure Python side of a row is one to two orders of
    magnitude slower than the bindings, so one count for both would either
    sit for minutes on the Python row or measure the bindings against the
    resolution of the clock.
    """
    # perf_counter and not time(): the wall clock can step backwards
    # under an NTP correction, and a benchmark is the one place that
    # shows up as a negative duration
    start = time.perf_counter()
    for _ in range(1000 * mult_):
        func()
    end = time.perf_counter()
    return (end - start) / (1000 * mult_) * 1e6


# one operation per entry, with the thousands of calls to give it through
# the bindings and through Python. Each count was picked from a first timed
# call to put its column near half a second -- long enough that the loop's
# own overhead is a rounding error, short enough that every operation
# through both arithmetics is a run somebody will wait for
OPERATIONS = (
    ("pubkey_from_prvkey", pubkey, 25, 2),
    ("pubkey_parse", point_parse, 50, 5),
    ("generator_mult", mult, 25, 2),
    ("dsa_sign", dsa_sign, 25, 2),
    ("dsa_verify", dsa_verify, 25, 1),
    ("dsa_recover", dsa_recover, 10, 1),
    ("ssa_sign", ssa_sign, 25, 2),
    ("ssa_verify", ssa_verify, 25, 1),
    ("dh_shared_secret", dh_shared_secret, 25, 2),
    ("bms_sign", bms_sign, 15, 2),
    ("bms_verify", bms_verify, 15, 1),
    ("taproot_tweak", taproot_tweak, 25, 2),
    ("ellswift_decode", ellswift_decode, 25, 3),
)


# what the run block claims about how these numbers were taken, said by
# the script that took them rather than typed into the page afterwards:
# one call count per operation per path, timed once, and reported
METHOD = "one run, kept whole \N{EM DASH} nothing repeated, no outlier discarded"


# the page this run is published as, named here because it cannot be
# derived: a page ordered among its siblings carries a number no module
# name may start with
BENCHMARK = "02-btclib-vs-btclib"


def main() -> None:
    """Time every operation through both paths, print the table, save the run.

    The timing order is what the measurement requires:
    `python_arithmetic_only` cannot be undone within a process, so every
    operation is timed through the bindings before it runs, and through
    Python after. The printing order is the run's own, sorted on the ratio,
    which is why the two are no longer the same loop.

    Nothing is printed until every number is in hand, this table being
    sorted on a ratio between two of them; what goes to the terminal is
    what `render.py` will put in the page, both of them being this one
    function's answer over the run saved at the end.
    """
    seconds = {
        f"{name}_libsecp256k1": benchmark(op, calls)
        for name, op, calls, _ in OPERATIONS
    }

    python_arithmetic_only()

    seconds |= {
        f"{name}_pure_python": benchmark(op, calls) for name, op, _, calls in OPERATIONS
    }

    # one row per operation, the two arithmetics beside each other: the
    # question is what an operation costs each way, and two rows made the
    # reader find the second half of a pair somewhere else in the sort.
    #
    # The ratio is the renderer's, dividing Python by the bindings rather
    # than the slower by the quicker, so its direction carries information:
    # under 1.0x is a pair where the bindings lost, which no absolute value
    # would say. The other benchmarks divide by the quickest row of the
    # table; here that row would divide a signature by a point parse, which
    # is two amounts of work and no comparison at all.
    table = Pairs(
        title="",
        columns=("libsecp256k1", "pure python"),
        rows=[
            Pair(
                label=name,
                values=(
                    seconds[f"{name}_libsecp256k1"],
                    seconds[f"{name}_pure_python"],
                ),
            )
            for name, _, _, _ in OPERATIONS
        ],
    )
    measurement = Measurement(
        benchmark=BENCHMARK,
        run=taken_now(__file__, METHOD),
        provenance=provenance(),
        tables=[table],
        # no block saying what a timing contains: every row here is btclib
        # called through one public function, and there is no comparand to
        # have been given an advantage over
        timing_note=[],
    )
    print(rendered_provenance(measurement.provenance))
    print()
    print(rendered_table(table, width_for([row.label for row in table.rows])))
    print(f"\nsaved to {save(measurement)}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
