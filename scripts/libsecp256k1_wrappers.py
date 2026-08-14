# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Verification timings of four wrappers of one C library, side by side.

Every row calls `bitcoin-core/secp256k1`, so what separates them is the
boundary crossing and not the arithmetic: cffi against ctypes, a
signature in DER against one in 64 bytes, a public key handed over as
bytes against one held as a Python object. That is the whole of the
question here, and it is why there is no pure-Python row:
`scripts/pure_python.py` asks what staying in Python costs and asks it
better -- one reference column, a ratio against btclib's own Python path
beside it, and every backend forced off rather than one switch flipped. A
fallback implementation dropped into a table about bindings answers
neither question well.

btclib is therefore not imported here at all, the fixtures below coming
from `btclib_secp256k1` and `hashlib`. Nothing in this script reaches
into btclib's private dispatch, so importing it leaves the bindings on
for the rest of the process -- which `pure_python.py` and
`btclib_two_paths.py` cannot offer, each having a Python row to measure
and one switch to throw for it.

Measured is one call each of ECDSA and BIP340 *verification*, on one
fixed key and message. Verification, because it is the operation all
four expose with the same meaning and no nonce to agree on.

## The public key is parsed inside every timing

Two of the four leave no choice: `btclib_secp256k1` takes bytes and
parses per call, and electrum-ecc's `ECPubkey` holds x and y as Python
integers and parses a `secp256k1_pubkey` again on every verify.
coincurve and secp256k1-py could each be handed a parsed key once and
are not, because a row that skipped what two of the four cannot skip
would be timing a different operation.

The signature is another matter. Each row takes the encoding its own API
asks for and parses it wherever that API does; converting between the
encodings happens once, in the fixtures, being no part of verifying.

## "The same C library" is a claim about the API, not about the binary

The four vendor different revisions of libsecp256k1, so
`report_libsecp256k1` says which one is under each row: a current build
timed against a stale one is not the comparison this table looks like.
Three of them link the library into a cffi extension at build time,
where the revision cannot be recovered at run time, so each pin is
recorded below against the release it was read from and reported as
unrecorded for any other release -- a pin that outlived the release it
describes would be the one figure in this output that nothing
re-derives.

Not part of the test suite and not run by CI: measuring is done by a
person on a machine whose state they know.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from hashlib import sha256
from importlib.metadata import version
from importlib.util import find_spec
from itertools import cycle
from pathlib import Path

import btclib_secp256k1
import btclib_secp256k1.dsa
import btclib_secp256k1.keys
import btclib_secp256k1.ssa
import coincurve
import electrum_ecc
import electrum_ecc.ecc_fast
import secp256k1
from _provenance import report
from _vectors import signing, verification


def report_provenance() -> None:
    """Say which build of each package these rows are about.

    Printed before any number: a released wheel and a working
    tree satisfy the same requirement and resolve in silence, so
    which one ran is something the output has to state rather
    than something the reader assumes.
    """
    report(
        ("btclib-secp256k1", btclib_secp256k1.__file__),
        ("coincurve", coincurve.__file__),
        ("secp256k1", secp256k1.__file__),
        ("electrum-ecc", electrum_ecc.__file__),
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


# Where each row's libsecp256k1 came from, read from the release named
# beside it:
#
# - btclib-secp256k1: the `secp256k1` submodule pin at its own v0.8.0.1
#   tag, 6e2c8bc, which is upstream's v0.8.0 tag exactly
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
    "btclib-secp256k1": ("0.8.0.1", "v0.8.0"),
    "coincurve": ("21.0.0", "v0.6.0"),
    "secp256k1": ("0.14.0", "9526874d, pre-v0.1.0"),
    "electrum-ecc": ("0.0.7", "v0.7.1"),
}

# how each row reaches the library, which is the difference this whole
# script is about: three link it into a cffi extension at build time,
# one opens the shared object beside the package through ctypes
WRAPPERS = (
    ("btclib-secp256k1", f"cffi bindings, {_artifact('_btclib_secp256k1')}"),
    ("coincurve", f"cffi bindings, {_artifact('coincurve._libsecp256k1')}"),
    ("secp256k1", f"cffi bindings, {_artifact('secp256k1._libsecp256k1')}"),
    ("electrum-ecc", f"ctypes bindings, {_electrum_ecc_library()}"),
)


def report_libsecp256k1() -> None:
    """Print which libsecp256k1 is under each row, and how the row calls it.

    Beside the versions rather than in prose, because it is the premise
    of the table: these four wrap one library, and they wrap four
    different revisions of it.
    """
    print("libsecp256k1 under each row")
    for dist_name, how in WRAPPERS:
        recorded, pin = LIBSECP256K1_PINS[dist_name]
        installed = version(dist_name)
        underneath = pin if installed == recorded else f"unrecorded, read at {recorded}"
        print(f"  {dist_name:<18}{installed:<10}{underneath:<22}  {how}")
    print()


def dsa_coincurve() -> None:
    """Time coincurve's ECDSA verification, which takes a DER signature."""
    pubkey, msg, sig = next(DSA_VERIFY)
    assert coincurve.PublicKey(pubkey).verify(sig, msg, None)


def dsa_secp256k1() -> None:
    """Time secp256k1-py's ECDSA verification, over its own parsed signature."""
    pubkey, msg, sig = next(DSA_VERIFY_SECP)
    assert pubkey.ecdsa_verify(msg, pubkey.ecdsa_deserialize(sig), raw=True)


def dsa_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA verification, over a 64-byte signature."""
    pubkey, msg, sig = next(DSA_VERIFY_64)
    assert electrum_ecc.ECPubkey(pubkey).ecdsa_verify(sig, msg)


def dsa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA verification, bytes in every argument."""
    pubkey, msg, sig = next(DSA_VERIFY)
    assert btclib_secp256k1.dsa.verify(msg, pubkey, sig)


def ssa_coincurve() -> None:
    """Time coincurve's BIP340 verification, over an x-only public key."""
    xonly, msg, sig = next(SSA_VERIFY)
    assert coincurve.PublicKeyXOnly(xonly).verify(sig, msg)


def ssa_secp256k1() -> None:
    """Time secp256k1-py's BIP340 verification, over a full public key."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    assert secp256k1.PublicKey(pubkey, raw=True).schnorr_verify(
        msg, sig, None, raw=True
    )


def ssa_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 verification, x-only derived per call."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    assert electrum_ecc.ECPubkey(pubkey).schnorr_verify(sig, msg)


def ssa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 verification, over an x-only key."""
    xonly, msg, sig = next(SSA_VERIFY)
    assert btclib_secp256k1.ssa.verify(msg, xonly, sig)


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
    the other three produce. The row below times the default.
    """
    prvkey, msg = next(DSA_SIGN_ELECTRUM)
    prvkey.ecdsa_sign(msg, grind_r_value=False)


def dsa_sign_electrum_ecc_grind() -> None:
    """Time electrum-ecc's ECDSA signing as it signs unless told otherwise.

    Its `ENABLE_ECDSA_R_VALUE_GRINDING` is true, so a caller writing
    `ecdsa_sign(msg32)` signs repeatedly until r fits in 32 bytes. Grinding
    is a loop around a wrapper rather than anything libsecp256k1 does, which
    is why it is one row of four here and a pair of rows in the tables about
    libraries.
    """
    prvkey, msg = next(DSA_SIGN_ELECTRUM)
    prvkey.ecdsa_sign(msg)


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
    dsa_sign_electrum_ecc_grind,
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

# one count for all eight rows, where the scripts that mix Python in
# need one per function: every row here is a call into C, and they land
# within a factor of a few of each other. Picked from a first timed call
# to put a row near a second and a half of wall clock -- long enough
# that Python's own call overhead is a rounding error beside the C, short
# enough that the whole script is a run to wait for
CALLS = 100_000


def benchmark(func: Callable[[], None], calls: int) -> float:
    """Call `func` `calls` times and return microseconds per call.

    Returned and not printed: a table sorted fastest to slowest, each row
    divided by one of the others, cannot be written a line at a time --
    every number has to be in hand before the first line is.
    """
    # perf_counter and not time(): the wall clock can step backwards
    # under an NTP correction, and a benchmark is the one place that
    # shows up as a negative duration
    start = time.perf_counter()
    for _ in range(calls):
        func()
    end = time.perf_counter()
    return (end - start) / calls * 1e6


def table(title: str, rows: tuple[Callable[[], None], ...]) -> None:
    """Time every row of one operation, then print them fastest first.

    The ratio is against the fastest row, whichever it turns out to be,
    so the top row reads 1.0x and every other says what it costs to use
    that one instead. Against a named row -- btclib_secp256k1's, the
    obvious candidate here -- the column would answer a question the
    reader did not ask on the runs where that row is not the quickest,
    and half the column would sit under one, which reads as a defect
    rather than as a result.
    """
    us = {func.__name__: benchmark(func, CALLS) for func in rows}
    against = min(us.values())
    print(title)
    print(f"  {'':<30}{'μs/call':>10}{'vs best':>12}")
    for name, value in sorted(us.items(), key=lambda row: row[1]):
        # two decimals on the ratio where the other scripts print one:
        # every row here calls the same C and they land within a few
        # percent of each other, so one decimal prints 1.0x for the whole
        # column and says nothing at all
        print(f"  {name:<30}{value:10.2f}{value / against:11.2f}x   ({CALLS} calls)")


def main() -> None:
    """Print the two tables, one operation each.

    No order is forced on the timing any more: with the pure-Python rows
    gone, nothing here changes state a later row would read. The order
    the rows are *printed* in is the measurement's own, fastest first,
    which is a property of the run rather than of this file.
    """
    report_provenance()
    report_libsecp256k1()

    table("ECDSA verify (32-byte digest, the public key parsed per call)", DSA_ROWS)
    print()
    table("BIP340 verify (32-byte message, the public key parsed per call)", SSA_ROWS)
    print()
    table("ECDSA sign (32-byte digest)", DSA_SIGN_ROWS)
    print()
    table("BIP340 sign (32-byte message)", SSA_SIGN_ROWS)
    print()
    table("public key tweak by a scalar, which is BIP32's step", TWEAK_ROWS)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
