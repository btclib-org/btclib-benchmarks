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


prvkey = 1
pubkey = btclib_secp256k1.keys.pubkey_from_prvkey(prvkey)
xonly_pubkey = pubkey[1:]
msg = sha256(b"Satoshi Nakamoto").digest()
dsa_sig = btclib_secp256k1.dsa.sign(msg, prvkey)
ssa_sig = btclib_secp256k1.ssa.sign(msg, prvkey)
# electrum-ecc's ECDSA verify takes the 64-byte encoding and no other,
# where coincurve and btclib_secp256k1 take DER. Converted once here
# rather than inside the row: a re-encoding no consumer of that API
# would repeat is not part of what verifying costs
dsa_sig64 = electrum_ecc.ecdsa_sig64_from_der_sig(dsa_sig)


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
    ("btclib-secp256k1", f"cffi, {_artifact('_btclib_secp256k1')}"),
    ("coincurve", f"cffi, {_artifact('coincurve._libsecp256k1')}"),
    ("secp256k1", f"cffi, {_artifact('secp256k1._libsecp256k1')}"),
    ("electrum-ecc", f"ctypes, {_electrum_ecc_library()}"),
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
    assert coincurve.PublicKey(pubkey).verify(dsa_sig, msg, None)


def dsa_secp256k1() -> None:
    """Time secp256k1-py's ECDSA verification, over its own parsed signature."""
    pubkey_secp = secp256k1.PublicKey(pubkey, raw=True)
    assert pubkey_secp.ecdsa_verify(
        msg, pubkey_secp.ecdsa_deserialize(dsa_sig), raw=True
    )


def dsa_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA verification, over a 64-byte signature."""
    assert electrum_ecc.ECPubkey(pubkey).ecdsa_verify(dsa_sig64, msg)


def dsa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA verification, bytes in every argument."""
    assert btclib_secp256k1.dsa.verify(msg, pubkey, dsa_sig)


def ssa_coincurve() -> None:
    """Time coincurve's BIP340 verification, over an x-only public key."""
    assert coincurve.PublicKeyXOnly(xonly_pubkey).verify(ssa_sig, msg)


def ssa_secp256k1() -> None:
    """Time secp256k1-py's BIP340 verification, over a full public key."""
    assert secp256k1.PublicKey(pubkey, raw=True).schnorr_verify(
        msg, ssa_sig, None, raw=True
    )


def ssa_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 verification, x-only derived per call."""
    assert electrum_ecc.ECPubkey(pubkey).schnorr_verify(ssa_sig, msg)


def ssa_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 verification, over an x-only key."""
    assert btclib_secp256k1.ssa.verify(msg, xonly_pubkey, ssa_sig)


DSA_ROWS = (dsa_coincurve, dsa_secp256k1, dsa_electrum_ecc, dsa_btclib_secp256k1)
SSA_ROWS = (ssa_coincurve, ssa_secp256k1, ssa_electrum_ecc, ssa_btclib_secp256k1)

# every row is called once before any of them is timed, which is what
# each row's own assert is for: four wrappers of one library have to
# agree that this signature is valid, or the table is comparing answers
# rather than implementations
for _row in DSA_ROWS + SSA_ROWS:
    _row()

# and none of them accepts the same signature against a message it was
# not made for. Written out per row rather than looped, each API taking
# the message in its own place -- and the point of the block is the one
# thing a positive check cannot show, that a row is not answering true
# to whatever it is handed
wrong_msg = sha256(b"not Satoshi Nakamoto").digest()
_secp256k1_pubkey = secp256k1.PublicKey(pubkey, raw=True)
assert not coincurve.PublicKey(pubkey).verify(dsa_sig, wrong_msg, None)
assert not _secp256k1_pubkey.ecdsa_verify(
    wrong_msg, _secp256k1_pubkey.ecdsa_deserialize(dsa_sig), raw=True
)
assert not electrum_ecc.ECPubkey(pubkey).ecdsa_verify(dsa_sig64, wrong_msg)
assert not btclib_secp256k1.dsa.verify(wrong_msg, pubkey, dsa_sig)
assert not coincurve.PublicKeyXOnly(xonly_pubkey).verify(ssa_sig, wrong_msg)
assert not _secp256k1_pubkey.schnorr_verify(wrong_msg, ssa_sig, None, raw=True)
assert not electrum_ecc.ECPubkey(pubkey).schnorr_verify(ssa_sig, wrong_msg)
assert not btclib_secp256k1.ssa.verify(wrong_msg, xonly_pubkey, ssa_sig)

# one count for all eight rows, where the scripts that mix Python in
# need one per function: every row here is a call into C, and they land
# within a factor of a few of each other. Picked from a first timed call
# to put a row near a second and a half of wall clock -- long enough
# that Python's own call overhead is a rounding error beside the C, short
# enough that the whole script is a run to wait for
CALLS = 100_000


def benchmark(func: Callable[[], None], calls: int) -> None:
    """Call `func` `calls` times and print microseconds per call."""
    # perf_counter and not time(): the wall clock can step backwards
    # under an NTP correction, and a benchmark is the one place that
    # shows up as a negative duration
    start = time.perf_counter()
    for _ in range(calls):
        func()
    end = time.perf_counter()
    us_per_call = (end - start) / calls * 1e6
    print(f"{func.__name__:<22}: {us_per_call:10.2f} us/call ({calls} calls)")


def main() -> None:
    """Print the two tables, one operation each.

    No order is forced on the rows any more: with the pure-Python rows
    gone, nothing here changes state a later row would read, so the
    order below is the reading order and nothing else.
    """
    report_provenance()
    report_libsecp256k1()

    print("ECDSA verify (32-byte digest, the public key parsed per call)")
    for func in DSA_ROWS:
        benchmark(func, CALLS)
    print()

    print("BIP340 verify (32-byte message, the public key parsed per call)")
    for func in SSA_ROWS:
        benchmark(func, CALLS)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
