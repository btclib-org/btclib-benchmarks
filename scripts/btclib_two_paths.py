# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib against btclib: its two arithmetics, side by side.

Not btclib against btclib_secp256k1. Both rows of every pair are btclib,
called through the same public function; what differs underneath is which
arithmetic answers -- the libsecp256k1 that btclib_secp256k1 bundles and
compiles into a cffi extension, or the Python of `curves/curve_group.py`.
`pip install btclib` installs both, so neither row is a package a reader
chooses between, and the ratio is what the second costs when the first
declines.

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
C and moves only the public key derived for the fingerprint, so a pair of
rows would compare C against C with a Python step added. Its pair was far
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
"""

from __future__ import annotations

import time
from collections.abc import Callable
from importlib.metadata import version
from importlib.util import find_spec
from itertools import cycle
from pathlib import Path

import btclib
from _provenance import report
from _vectors import signing, verification
from btclib import b58
from btclib.curves import curve, sec_point
from btclib.ecc import bms, dh, dsa, ellswift, ssa
from btclib.script import taproot
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def report_setup() -> None:
    """Say what the two arithmetics are, once, above the table.

    The version that belongs here is btclib_secp256k1's, because that is
    what a caller installs and what the row is: which revision of
    libsecp256k1 it bundled is recorded in
    `scripts/libsecp256k1_wrappers.py`, against the release it was read
    from, and one script naming a pin is enough.
    """
    spec = find_spec("_btclib_secp256k1")
    artifact = Path(spec.origin).name if spec and spec.origin else "not found"
    print("the two arithmetics under each pair")
    print(
        f"  {'libsecp256k1':<20}bundled and compiled into btclib_secp256k1 "
        f"{version('btclib_secp256k1')}, through cffi bindings, {artifact}"
    )
    print(f"  {'pure python':<20}btclib's own curves/curve_group.py, the dispatch off")
    print()


def report_provenance() -> None:
    """Say which build of each package these rows are about.

    Printed before any number: a released wheel and a working
    tree satisfy the same requirement and resolve in silence, so
    which one ran is something the output has to state rather
    than something the reader assumes.
    """
    report(("btclib", btclib.__file__))


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
    """Time the public key btclib derives from a private key."""
    prvkey, _expected = next(PUBKEY_CYCLE)
    pub_keyinfo_from_prv_key(prvkey)[0]


def point_parse() -> None:
    """Time parsing a compressed public key, which recovers y from x."""
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

    Returned and not printed: the table is sorted on the ratio and each
    row divides by its own pair, so no line can be written until every
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
# the bindings and through Python. Each pair was picked from a first timed
# call to put both of its rows near half a second -- long enough that the
# loop's own overhead is a rounding error, short enough that fourteen
# operations through two paths is a run to wait for
OPERATIONS = (
    ("pubkey", pubkey, 25, 2),
    ("point_parse", point_parse, 50, 5),
    ("mult", mult, 25, 2),
    ("dsa_sign", dsa_sign, 25, 2),
    ("dsa_verify", dsa_verify, 25, 1),
    ("dsa_recover", dsa_recover, 10, 1),
    ("ssa_sign", ssa_sign, 25, 2),
    ("ssa_verify", ssa_verify, 25, 1),
    ("dh", dh_shared_secret, 25, 2),
    ("bms_sign", bms_sign, 15, 2),
    ("bms_verify", bms_verify, 15, 1),
    ("taproot_tweak", taproot_tweak, 25, 2),
    ("ellswift_decode", ellswift_decode, 25, 3),
)


def main() -> None:
    """Time every operation through both paths, and print the table sorted.

    The timing order is what the measurement requires:
    `python_arithmetic_only` cannot be undone within a process, so every
    operation is timed through the bindings before it runs, and through
    Python after. The printing order is the run's own, fastest first,
    which is why the two are no longer the same loop.
    """
    report_provenance()
    report_setup()

    seconds = {
        f"{name}_libsecp256k1": benchmark(op, calls)
        for name, op, calls, _ in OPERATIONS
    }

    python_arithmetic_only()

    seconds |= {
        f"{name}_pure_python": benchmark(op, calls) for name, op, _, calls in OPERATIONS
    }

    # each row divides by the quicker of its own pair, and by nothing
    # else. The fastest row of the whole table is the reference in the
    # other three benchmarks; here it would divide a signature by a point
    # parse, which is two different amounts of work and no comparison at
    # all. Read off the measurement rather than assumed to be the bindings
    # row, so a pair where it is not says so instead of printing a
    # fraction under one and leaving the reader to work out why
    against = {
        f"{name}_{path}": min(
            seconds[f"{name}_libsecp256k1"], seconds[f"{name}_pure_python"]
        )
        for name, _, _, _ in OPERATIONS
        for path in ("libsecp256k1", "pure_python")
    }
    # sorted on the ratio and not on the seconds, which is the column this
    # table is read for: what an operation costs is a fact about the
    # operation, and what its fallback costs is a fact about the two paths.
    # The seconds break the tie, so the bindings rows -- 1.0x every one of
    # them -- still read fastest first among themselves
    rows = sorted(
        ((name, value, value / against[name]) for name, value in seconds.items()),
        key=lambda row: (row[2], row[1]),
    )
    print(f"{'':<28} {'μs/call':>10}{'vs best':>14}")
    for name, value, ratio in rows:
        print(f"{name:<28} {value:#10.5g}{ratio:13.1f}x")


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
