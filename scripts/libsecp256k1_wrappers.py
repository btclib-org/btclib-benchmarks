# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of four wrappers of one C library, side by side.

Every row calls `bitcoin-core/secp256k1`, so what separates them is the
boundary crossing rather than the arithmetic: cffi against ctypes, a signature
in DER against one in 64 bytes, a public key handed over as bytes against one
held as a Python object. There is no pure-Python row --
`scripts/pure_python.py` asks what staying in Python costs, and asks it with
every backend forced off rather than one switch flipped.

btclib is not imported here at all: the fixtures come from
`btclib_secp256k1`, `_vectors` and `hashlib` -- the module, btclib-secp256k1
being the package -- so nothing reaches into btclib's
private dispatch and importing this module leaves the bindings on for the rest
of the process.

Measured are ECDSA and BIP340 signing and verification, and a public key
tweaked by a scalar, which is BIP32's step -- none of the four implements
BIP32 itself, and all four expose the primitive it is built from.
`electrum-ecc` has no tweak-add on `ECPubkey`, so it reaches the same point as
a scalar times the generator plus an addition: two crossings where the others
make one.

Every call cycles a published input rather than repeating one:
`_vectors.signing()`'s keys and messages for tables 1-2 and the tweak, whose
scalar is the next vector's secret key, and `_vectors.signing()` and
`_vectors.verification()` for tables 3-4, where the *signature* is also the
vector's own. The file has no signature published for tables 1-2's scheme --
those rows sign a published key and message with RFC6979, which is what
`btclib_secp256k1.dsa.sign` below produces and the other three are checked
against.

`electrum-ecc` is the only one of the four offering low-r grinding, so its
row is `grind=False`: without it, its signing time would not be comparable
with the other three, which sign once. The tables about libraries carry the
distinction the other way, as a pair of rows, because there both btclib and
embit grind by default -- two grinding libraries are worth comparing to each
other, and one is not.

## The public key is parsed inside every timing

Two of the four leave no choice: `btclib_secp256k1` takes bytes and parses per
call, and electrum-ecc's `ECPubkey` holds x and y as Python integers and
parses a `secp256k1_pubkey` again on every verify. coincurve and secp256k1-py
could each be handed a parsed key once and are not, because a row skipping
what two of the four cannot skip would be timing a different operation.

The signature is another matter: each row takes the encoding its own API asks
for, and converting between encodings happens once, in the fixtures.

## "The same C library" is a claim about the API, not about the binary

The four vendor different revisions, so `provenance` says which is under
each row -- from a pin, because none of them can be asked. Neither
compiled artifact exports a version symbol; `btclib_secp256k1.version` is
`importlib.metadata.version` re-exported, which answers for the wrapper and
not for the library; coincurve and secp256k1-py expose only their own
`__version__`; and electrum-ecc's `version_info` returns the path of the
shared object it opened and nothing about its contents. So each pin is
recorded against the release it was read from and reported as unrecorded for
any other, and re-reading it is what a comparand's release costs.

The durable fix belongs upstream rather than here: a wrapper that recorded its
vendored revision at build time -- a constant its build script writes from the
submodule it just compiled -- would let this row read what it now asserts.

## Correctness is not measured here

A timed function calls one API and discards what it returns. It compares
nothing, because a comparison inside the loop is time attributed to the
wrapper that did not spend it, and a row that checks itself is measuring the
check.

Whether the answers are right is `tests/vectors_test.py`'s subject: it runs
the vendored vectors against every implementation this project times, in the
configuration it times it in. The cross-wrapper assertions below run where
the fixtures are built, at import, so the suite loading this module runs them
and no timing carries them.

What the four agree on there is not everything: three produce the same ECDSA
bytes for a key and a message, libsecp256k1's default nonce being RFC6979,
while secp256k1-py's build does on x86-64 and does not on aarch64. So every
wrapper is held to the portable claim -- that its signature verifies -- and
to BIP340's own signatures where its API takes an aux_rand. secp256k1-py's
`schnorr_sign` does not.

Not part of the test suite and not run by CI: measuring is done by a person on
a machine whose state they know.

## What a run leaves behind

The numbers are written to `results/libsecp256k1-wrappers.json` as this
finishes, and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from hashlib import sha256
from importlib.metadata import version
from importlib.util import find_spec
from itertools import cycle
from pathlib import Path

import btclib_secp256k1.dsa
import btclib_secp256k1.keys
import btclib_secp256k1.ssa
import coincurve
import electrum_ecc
import electrum_ecc.ecc_fast
import secp256k1
from _provenance import WHAT_A_TIMING_CONTAINS, from_a_declared_source, origin_of
from _results import (
    Measurement,
    Provenance,
    Ratios,
    Timing,
    rendered_provenance,
    rendered_table,
    save,
    slug,
    taken_now,
    width_for,
)
from _vectors import signing, verification


def provenance() -> Provenance:
    """Return one row per wrapper: what it is, and what is under it.

    Six columns, because the reader of this table needs all six and each
    answers a different question. The version and the release date say which
    build these rows are; the revision says which library that build carries,
    the four being four vendored trees of one project; the bindings and the
    binary say how a row crosses into it. Sorted newest release first.

    Two of the six cannot be read at run time and are recorded against the
    release they were read for, printing `unrecorded` for any other: no
    compiled artifact exports a version symbol, and no installed metadata
    carries a release date.

    A package installed from anywhere other than its declared source is named
    under the table rather than in it: `editable:` and `sys.path:` are what a
    reader has to act on, and a column of "released" repeated four times is
    not.
    """
    rows = []
    by_date = sorted(WRAPPERS, key=lambda row: RELEASE_DATES[row[0]][1], reverse=True)
    for dist_name, bindings, binary in by_date:
        installed = version(dist_name)
        recorded_pin, pin = LIBSECP256K1_PINS[dist_name]
        recorded_date, date = RELEASE_DATES[dist_name]
        rows.append(
            [
                dist_name,
                installed,
                date if installed == recorded_date else "unrecorded",
                pin if installed == recorded_pin else "unrecorded",
                bindings,
                binary,
            ]
        )
    return Provenance(
        columns=[
            "package",
            "version",
            "released",
            "libsecp256k1 pin",
            "bindings",
            "binary",
        ],
        rows=rows,
        notes=[
            f"{dist_name} is installed from {origin_of(dist_name)}"
            for dist_name, _, _ in WRAPPERS
            if not from_a_declared_source(dist_name)
        ],
    )


# every published vector, cycled, rather than one input repeated: a row that
# calls one input a hundred thousand times measures that input. `_vectors`
# reads BIP340's file and checks its digest; each row below takes the next of
# what it publishes per call.
#
# Every row of this table is a wrapper of one library, so "they agree with
# each other" is the check that proves least here, and agreeing with BIP340
# is one with an outside answer.
SIGNING = signing()
VERIFYING = verification()

PUBKEYS = [btclib_secp256k1.keys.pubkey_from_prvkey(v.prvkey) for v in SIGNING]

# ECDSA has no published signature to cycle: RFC6979's nonce is what
# libsecp256k1 signs with, and no vendored file publishes signatures over it.
# The keys and messages are the vector file's all the same, and the four
# wrappers are held to producing the same bytes below
DSA_SIGS = [btclib_secp256k1.dsa.sign(v.msg, v.prvkey) for v in SIGNING]

# a public key tweaked by a scalar, which is BIP32's step. The scalar is the
# next vector's secret key: a message would serve arithmetically, but one of
# BIP340's is not below the order and a tweak has to be, where a secret key is
# by construction
TWEAKS = [v.prvkey for v in SIGNING[1:]] + [SIGNING[0].prvkey]
TWEAKED = [
    btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak)
    for pubkey, tweak in zip(PUBKEYS, TWEAKS, strict=True)
]

# what the four have to agree on before any of them is timed. BIP340 first,
# where a published signature exists: three reproduce it byte for byte, and
# secp256k1-py's `schnorr_sign` takes no aux_rand, so what its API leaves
# checkable is that its signature verifies
for _v in SIGNING:
    assert btclib_secp256k1.ssa.sign(_v.msg, _v.prvkey, _v.aux) == _v.sig
    assert coincurve.PrivateKey(_v.prvkey).sign_schnorr(_v.msg, _v.aux) == _v.sig
    assert (
        electrum_ecc.ECPrivkey(_v.prvkey).schnorr_sign(_v.msg, aux_rand32=_v.aux)
        == _v.sig
    )
    assert btclib_secp256k1.ssa.verify(
        _v.msg,
        _v.xonly_pubkey,
        secp256k1.PrivateKey(_v.prvkey, raw=True).schnorr_sign(_v.msg, None, raw=True),
    )

# and ECDSA, where what is portable is that every signature verifies.
# libsecp256k1's default nonce is RFC6979, so one key and one message ought to
# give one signature through four APIs -- and on x86-64 they do. On aarch64
# secp256k1-py's does not match the other three, so its build disagrees about
# the nonce or about what it was given, and a benchmark is the wrong place to
# assert a claim that holds on one architecture
for _v, _der in zip(SIGNING, DSA_SIGS, strict=True):
    _pubkey = btclib_secp256k1.keys.pubkey_from_prvkey(_v.prvkey)
    assert coincurve.PrivateKey(_v.prvkey).sign(_v.msg, hasher=None) == _der
    _secp = secp256k1.PrivateKey(_v.prvkey, raw=True)
    assert btclib_secp256k1.dsa.verify(
        _v.msg, _pubkey, _secp.ecdsa_serialize(_secp.ecdsa_sign(_v.msg, raw=True))
    )
    assert (
        electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
            electrum_ecc.ECPrivkey(_v.prvkey).ecdsa_sign(_v.msg, grind_r_value=False)
        )
        == _der
    )

# and the tweak, which electrum-ecc reaches in two calls where the others
# take one: two routes to the same point, which is the comparison
for _pubkey, _tweak, _expected in zip(PUBKEYS, TWEAKS, TWEAKED, strict=True):
    assert coincurve.PublicKey(_pubkey).add(_tweak).format(compressed=True) == _expected
    assert (
        secp256k1.PublicKey(_pubkey, raw=True)
        .tweak_add(_tweak)
        .serialize(compressed=True)
        == _expected
    )
    assert (
        electrum_ecc.ECPubkey(_pubkey)
        + int.from_bytes(_tweak, "big") * electrum_ecc.GENERATOR
    ).get_public_key_bytes(compressed=True) == _expected

# and none of them accepts a signature against a message it was not made for,
# which a positive check cannot tell from a row answering true to anything
for _v, _pubkey, _der in zip(SIGNING, PUBKEYS, DSA_SIGS, strict=True):
    _wrong = sha256(_v.msg).digest()
    _sig64 = electrum_ecc.ecdsa_sig64_from_der_sig(_der)
    _secp_pubkey = secp256k1.PublicKey(_pubkey, raw=True)
    assert not coincurve.PublicKey(_pubkey).verify(_der, _wrong, None)
    assert not _secp_pubkey.ecdsa_verify(
        _wrong, _secp_pubkey.ecdsa_deserialize(_der), raw=True
    )
    assert not electrum_ecc.ECPubkey(_pubkey).ecdsa_verify(_sig64, _wrong)
    assert not btclib_secp256k1.dsa.verify(_wrong, _pubkey, _der)
    assert not coincurve.PublicKeyXOnly(_v.xonly_pubkey).verify(_v.sig, _wrong)
    assert not _secp_pubkey.schnorr_verify(_wrong, _v.sig, None, raw=True)
    assert not electrum_ecc.ECPubkey(_pubkey).schnorr_verify(_v.sig, _wrong)
    assert not btclib_secp256k1.ssa.verify(_wrong, _v.xonly_pubkey, _v.sig)

# one cycle per row, carrying whatever that API wants prepared: a key object
# built per call would time the constructor of whichever API has the slowest
DSA_VERIFY = cycle(
    [
        (pubkey, v.msg, sig)
        for pubkey, v, sig in zip(PUBKEYS, SIGNING, DSA_SIGS, strict=True)
    ]
)
DSA_VERIFY_64 = cycle(
    [
        (pubkey, v.msg, electrum_ecc.ecdsa_sig64_from_der_sig(sig))
        for pubkey, v, sig in zip(PUBKEYS, SIGNING, DSA_SIGS, strict=True)
    ]
)
DSA_VERIFY_SECP = cycle(
    [
        (secp256k1.PublicKey(pubkey, raw=True), v.msg, sig)
        for pubkey, v, sig in zip(PUBKEYS, SIGNING, DSA_SIGS, strict=True)
    ]
)
SSA_VERIFY = cycle([(v.xonly_pubkey, v.msg, v.sig) for v in VERIFYING])
SSA_VERIFY_FULL = cycle([(b"\x02" + v.xonly_pubkey, v.msg, v.sig) for v in VERIFYING])
DSA_SIGN = cycle([(v.prvkey, v.msg) for v in SIGNING])
DSA_SIGN_COINCURVE = cycle([(coincurve.PrivateKey(v.prvkey), v.msg) for v in SIGNING])
DSA_SIGN_SECP = cycle(
    [(secp256k1.PrivateKey(v.prvkey, raw=True), v.msg) for v in SIGNING]
)
DSA_SIGN_ELECTRUM = cycle([(electrum_ecc.ECPrivkey(v.prvkey), v.msg) for v in SIGNING])
SSA_SIGN = cycle([(v.prvkey, v.msg, v.aux) for v in SIGNING])
SSA_SIGN_COINCURVE = cycle(
    [(coincurve.PrivateKey(v.prvkey), v.msg, v.aux) for v in SIGNING]
)
SSA_SIGN_SECP = cycle(
    [(secp256k1.PrivateKey(v.prvkey, raw=True), v.msg) for v in SIGNING]
)
SSA_SIGN_ELECTRUM = cycle(
    [(electrum_ecc.ECPrivkey(v.prvkey), v.msg, v.aux) for v in SIGNING]
)
TWEAK = cycle(list(zip(PUBKEYS, TWEAKS, strict=True)))


def _artifact(module_name: str) -> str:
    """Return the file name of the compiled module a wrapper calls into.

    `find_spec` and not an import: these are the private extensions the
    three cffi wrappers ship, each already imported by its own package,
    and what is wanted is where one came from rather than a second
    reference to it.
    """
    spec = find_spec(module_name)
    if spec is None or spec.origin is None:
        return "not found"
    return Path(spec.origin).name


def _electrum_ecc_library() -> str:
    """Return the shared object electrum-ecc's ctypes loader opened.

    Its own `version_info` answers this, that function existing for the
    purpose. The name is worth printing where the three cffi rows have
    nothing to print: it carries the ABI version of the build, the
    loader having asked for the newest one it knows by file name.
    """
    return Path(str(electrum_ecc.ecc_fast.version_info()["libsecp256k1.path"])).name


# When each of these releases was published, read from the index and
# recorded against the release it was read for. Not available at run time:
# a wheel's METADATA carries a Version and no date, and the dist-info
# directory's mtime is when the package was installed on this machine. A
# comparand's age is worth a column here -- one of these four is years older
# than the others, and the revision it vendors follows from that
RELEASE_DATES = {
    "btclib-secp256k1": ("0.8.0.2", "2026-08-14"),
    "coincurve": ("21.0.0", "2025-03-08"),
    "secp256k1": ("0.14.0", "2021-11-06"),
    "electrum-ecc": ("0.0.7", "2026-02-25"),
}


# Where each row's libsecp256k1 came from, read from the release named
# beside it:
#
# - btclib-secp256k1: the `secp256k1` submodule pin at its own v0.8.0.2
#   tag, 6e2c8bc, which is upstream's v0.8.0 tag exactly -- the same commit
#   its v0.8.0.1 pinned, so that release moved and the library did not
# - coincurve: `VENDORED_UPSTREAM_REF` in its pyproject.toml, 0cdc758a,
#   which is upstream's v0.6.0
# - secp256k1: `LIB_TARBALL_URL` in its setup.py, 9526874d, a master
#   commit older than upstream's first tagged release -- the configure.ac
#   of the tree it bundles still calls itself 0.1
# - electrum-ecc: the libsecp256k1 tree carried in its sdist and compiled
#   at install time, whose configure.ac names 0.7.1 as a release
#
# Keyed by the release each was read at, because the floors in
# pyproject.toml are floors: a comparand upgrades without a word, and a
# pin has to stop being claimed when the release it was read from is no
# longer the one installed.
LIBSECP256K1_PINS = {
    "btclib-secp256k1": ("0.8.0.2", "v0.8.0"),
    "coincurve": ("21.0.0", "v0.6.0"),
    "secp256k1": ("0.14.0", "9526874d, pre-v0.1.0"),
    "electrum-ecc": ("0.0.7", "v0.7.1"),
}

# how each row reaches the library, which is the difference this whole
# script is about: three link it into a cffi extension at build time,
# one opens the shared object beside the package through ctypes
WRAPPERS = (
    ("btclib-secp256k1", "cffi", _artifact("_btclib_secp256k1")),
    ("coincurve", "cffi", _artifact("coincurve._libsecp256k1")),
    ("secp256k1", "cffi", _artifact("secp256k1._libsecp256k1")),
    ("electrum-ecc", "ctypes", _electrum_ecc_library()),
)


def dsa_coincurve() -> None:
    """Time coincurve's ECDSA verification, which takes a DER signature."""
    pubkey, msg, sig = next(DSA_VERIFY)
    coincurve.PublicKey(pubkey).verify(sig, msg, None)


def dsa_secp256k1() -> None:
    """Time secp256k1-py's ECDSA verification, over its own parsed signature."""
    pubkey, msg, sig = next(DSA_VERIFY_SECP)
    pubkey.ecdsa_verify(msg, pubkey.ecdsa_deserialize(sig), raw=True)


def dsa_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA verification, over a 64-byte signature."""
    pubkey, msg, sig = next(DSA_VERIFY_64)
    electrum_ecc.ECPubkey(pubkey).ecdsa_verify(sig, msg)


def dsa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA verification, bytes in every argument."""
    pubkey, msg, sig = next(DSA_VERIFY)
    btclib_secp256k1.dsa.verify(msg, pubkey, sig)


def ssa_coincurve() -> None:
    """Time coincurve's BIP340 verification, over an x-only public key."""
    xonly, msg, sig = next(SSA_VERIFY)
    coincurve.PublicKeyXOnly(xonly).verify(sig, msg)


def ssa_secp256k1() -> None:
    """Time secp256k1-py's BIP340 verification, over a full public key."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    secp256k1.PublicKey(pubkey, raw=True).schnorr_verify(msg, sig, None, raw=True)


def ssa_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 verification, x-only derived per call."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    electrum_ecc.ECPubkey(pubkey).schnorr_verify(sig, msg)


def ssa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 verification, over an x-only key."""
    xonly, msg, sig = next(SSA_VERIFY)
    btclib_secp256k1.ssa.verify(msg, xonly, sig)


def dsa_sign_coincurve() -> None:
    """Time coincurve's ECDSA signing, over a digest it is told not to hash."""
    prvkey, msg = next(DSA_SIGN_COINCURVE)
    prvkey.sign(msg, hasher=None)


def dsa_sign_secp256k1() -> None:
    """Time secp256k1-py's ECDSA signing, which returns a parsed signature."""
    prvkey, msg = next(DSA_SIGN_SECP)
    prvkey.ecdsa_sign(msg, raw=True)


def dsa_sign_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA signing, one signature.

    `grind_r_value=False`, which is not its default: it is the only wrapper
    of the four offering low-r grinding at all, and one signature is what
    the other three produce.
    """
    prvkey, msg = next(DSA_SIGN_ELECTRUM)
    prvkey.ecdsa_sign(msg, grind_r_value=False)


def dsa_sign_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA signing, bytes in and DER out."""
    prvkey, msg = next(DSA_SIGN)
    btclib_secp256k1.dsa.sign(msg, prvkey)


def ssa_sign_coincurve() -> None:
    """Time coincurve's BIP340 signing, over each vector's aux_rand."""
    prvkey, msg, aux = next(SSA_SIGN_COINCURVE)
    prvkey.sign_schnorr(msg, aux)


def ssa_sign_secp256k1() -> None:
    """Time secp256k1-py's BIP340 signing, which takes no aux_rand.

    Its signature is therefore not the vector's. Timed all the same: the work
    is the same, and the fixtures above check the one thing this API leaves
    checkable, that the signature verifies.
    """
    prvkey, msg = next(SSA_SIGN_SECP)
    prvkey.schnorr_sign(msg, None, raw=True)


def ssa_sign_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 signing, over each vector's aux_rand."""
    prvkey, msg, aux = next(SSA_SIGN_ELECTRUM)
    prvkey.schnorr_sign(msg, aux_rand32=aux)


def ssa_sign_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 signing, over each vector's aux_rand."""
    prvkey, msg, aux = next(SSA_SIGN)
    btclib_secp256k1.ssa.sign(msg, prvkey, aux)


def tweak_coincurve() -> None:
    """Time coincurve's public key tweak, which returns a new PublicKey."""
    pubkey, tweak = next(TWEAK)
    coincurve.PublicKey(pubkey).add(tweak)


def tweak_secp256k1() -> None:
    """Time secp256k1-py's public key tweak, in place on a parsed key."""
    pubkey, tweak = next(TWEAK)
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak)


def tweak_electrum_ecc() -> None:
    """Time electrum-ecc's public key tweak, which its API spells in two calls.

    There is no tweak-add on `ECPubkey`: a scalar times the generator and a
    point addition is how the same tweak is reached, both libsecp256k1 calls.
    Two crossings where the others make one is the difference this table
    exists to show.
    """
    pubkey, tweak = next(TWEAK)
    (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    )


def tweak_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's public key tweak, bytes in and bytes out."""
    pubkey, tweak = next(TWEAK)
    btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak)


DSA_ROWS = (dsa_coincurve, dsa_secp256k1, dsa_electrum_ecc, dsa_btclib_secp256k1)
SSA_ROWS = (ssa_coincurve, ssa_secp256k1, ssa_electrum_ecc, ssa_btclib_secp256k1)
DSA_SIGN_ROWS = (
    dsa_sign_coincurve,
    dsa_sign_secp256k1,
    dsa_sign_electrum_ecc,
    dsa_sign_btclib_secp256k1,
)
SSA_SIGN_ROWS = (
    ssa_sign_coincurve,
    ssa_sign_secp256k1,
    ssa_sign_electrum_ecc,
    ssa_sign_btclib_secp256k1,
)
TWEAK_ROWS = (
    tweak_coincurve,
    tweak_secp256k1,
    tweak_electrum_ecc,
    tweak_btclib_secp256k1,
)

for _row in DSA_ROWS + SSA_ROWS + DSA_SIGN_ROWS + SSA_SIGN_ROWS + TWEAK_ROWS:
    _row()

# One count for every row, where the scripts that mix Python in need one per
# function: every row here is a call into C and they land within a factor of a
# few. Five rounds of it, and the row reports the *minimum*: interference on a
# shared machine only ever adds time, so the fastest round is the one least
# disturbed, and a mean would carry every interruption into the number. The
# spread beside it says how much there was to discard -- a row whose rounds
# disagree by a few percent measured a busy machine, and the reader can see it
# rather than being told the machine was quiet.
#
# The count is a fifth of what one round used to be, so five rounds cost what
# one run cost: robustness here is a rearrangement rather than a bill.
CALLS = 20_000
ROUNDS = 5


def benchmark(func: Callable[[], None], calls: int) -> tuple[float, float]:
    """Return the microseconds per call of the quickest round, and the spread.

    `ROUNDS` rounds of `calls` calls each. The minimum is the estimate: noise
    is one-sided, so the quickest round is the one that ran with least taken
    from it. The spread is how far the slowest round ran from the quickest, as
    a fraction of the quickest, and it is printed rather than hidden because
    it is the only thing in the output that says whether the machine was quiet.
    """
    # perf_counter and not time(): the wall clock can step backwards under an
    # NTP correction, and a benchmark is the one place that shows up as a
    # negative duration
    rounds = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(calls):
            func()
        rounds.append((time.perf_counter() - start) / calls * 1e6)
    quickest = min(rounds)
    return quickest, max(rounds) / quickest - 1


def measured(title: str, rows: tuple[Callable[[], None], ...]) -> Ratios:
    """Time every row of one operation and return them as a table.

    The sort and the ratio are the renderer's. The ratio is against the
    fastest row, whichever it turns out to be, so the top row reads 1.00x
    and every other says what it costs to use that one instead; against a
    named row the column would answer a question the reader did not ask on
    the runs where that row is not the quickest.

    Two decimals where the other scripts ask for one: every row here calls
    the same C and they land within a few percent of each other, so one
    decimal prints 1.0x for the whole column.
    """
    timings = []
    for func in rows:
        value, spread = benchmark(func, CALLS)
        timings.append(
            Timing(
                label=func.__name__,
                us_per_call=value,
                spread=spread,
                calls=CALLS,
                rounds=ROUNDS,
            )
        )
    return Ratios(title=title, decimals=2, rows=timings)


# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page, which is a fact about all five
# tables and cannot be known while the first is being measured
TABLES = (
    ("1. ECDSA sign (32-byte digest)", DSA_SIGN_ROWS),
    ("2. ECDSA verify (32-byte digest, the public key parsed per call)", DSA_ROWS),
    ("3. BIP340 sign (32-byte message)", SSA_SIGN_ROWS),
    ("4. BIP340 verify (32-byte message, the public key parsed per call)", SSA_ROWS),
    ("5. public key tweak by a scalar, which is BIP32's step", TWEAK_ROWS),
)

# what the run block claims about how these numbers were taken, said by
# the script that takes them: `benchmark` above is where the five rounds
# and the minimum are, and the spread column is what a reader checks it by
METHOD = f"{ROUNDS} rounds per row, minimum kept; nothing else repeated"


def main() -> None:
    """Print the five tables, one operation each, and save the run.

    No order is forced on the timing: with the pure-Python rows gone,
    nothing here changes state a later row would read. The order the rows
    are *printed* in is the measurement's own, fastest first, which is a
    property of the run rather than of this file.

    Each table is printed as it is measured, this being a run somebody
    watches, and printed through the same renderer that writes the page.
    """
    packages = provenance()
    print(rendered_provenance(packages))
    print()
    print("\n".join(WHAT_A_TIMING_CONTAINS))
    print()

    width = width_for([func.__name__ for _, rows in TABLES for func in rows])
    tables = []
    for title, rows in TABLES:
        table = measured(title, rows)
        print(rendered_table(table, width))
        print()
        tables.append(table)

    saved = save(
        Measurement(
            benchmark=slug(__file__),
            run=taken_now(__file__, METHOD),
            provenance=packages,
            tables=tables,
        )
    )
    print(f"saved to {saved}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
