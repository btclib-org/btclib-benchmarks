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


# BIP340 test vector 1, transcribed from btclib's vendored copy of it,
# `tests/ecc/_data/bip340_test_vectors.csv`, whose own
# `tests/_data/README.md` pins that file to a commit of bitcoin/bips and
# compares the bytes. A published key rather than one chosen here, and the
# public key and signature it publishes are asserted below rather than
# taken on trust: every row of this table is a wrapper of the same library,
# so "they agree with each other" is the one check that proves least, and
# agreeing with BIP340 is a check that has an outside answer.
#
# The timings do not turn on it -- three different valid keys through these
# bindings measure the same to within the noise of the machine, which was
# checked. What it buys is that the signature being verified is the
# specification's rather than one made by the package whose row the others
# are being compared against.
prvkey = 0xB7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF
msg = bytes.fromhex("243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89")
aux = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
vector_xonly_pubkey = bytes.fromhex(
    "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"
)
vector_ssa_sig = bytes.fromhex(
    "6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE3341"
    "8906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"
)
pubkey = btclib_secp256k1.keys.pubkey_from_prvkey(prvkey)
xonly_pubkey = pubkey[1:]
dsa_sig = btclib_secp256k1.dsa.sign(msg, prvkey)
# the vector's aux_rand, not the default: BIP340 signing is deterministic
# given it, so what the rows below verify is the signature the
# specification publishes and not one of this package's making
ssa_sig = btclib_secp256k1.ssa.sign(msg, prvkey, aux)
assert xonly_pubkey == vector_xonly_pubkey
assert ssa_sig == vector_ssa_sig
# electrum-ecc's ECDSA verify takes the 64-byte encoding and no other,
# where coincurve and btclib_secp256k1 take DER. Converted once here
# rather than inside the row: a re-encoding no consumer of that API
# would repeat is not part of what verifying costs
dsa_sig64 = electrum_ecc.ecdsa_sig64_from_der_sig(dsa_sig)

prvkey_bytes = prvkey.to_bytes(32, "big")
coincurve_prvkey = coincurve.PrivateKey(prvkey_bytes)
secp256k1_prvkey = secp256k1.PrivateKey(prvkey_bytes, raw=True)
electrum_prvkey = electrum_ecc.ECPrivkey(prvkey_bytes)
electrum_pubkey = electrum_ecc.ECPubkey(pubkey)

# a full-size scalar to tweak a public key by, which is the operation BIP32
# derivation is built out of. The vector's message reused as a scalar: an
# arbitrary tweak would do, and a published one costs nothing
tweak = msg
tweaked_pubkey = btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak)

# one signature each, and all four are the same bytes: libsecp256k1's
# default nonce is RFC6979, so four wrappers signing one message with one
# key produce one signature -- which is the strongest agreement this table
# can ask for, and it holds every signing row below to the other three
assert coincurve_prvkey.sign(msg, hasher=None) == dsa_sig
assert secp256k1_prvkey.ecdsa_serialize(secp256k1_prvkey.ecdsa_sign(msg, raw=True)) == (
    dsa_sig
)
assert (
    electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
        electrum_prvkey.ecdsa_sign(msg, grind_r_value=False)
    )
    == dsa_sig
)

# BIP340 is deterministic given aux_rand, so three of the four reproduce the
# vector's signature byte for byte. secp256k1-py's `schnorr_sign` takes no
# aux_rand at all -- its signature is a valid one over another nonce, and
# checking it is all its API allows
assert coincurve_prvkey.sign_schnorr(msg, aux) == vector_ssa_sig
assert electrum_prvkey.schnorr_sign(msg, aux_rand32=aux) == vector_ssa_sig
assert btclib_secp256k1.ssa.verify(
    msg, xonly_pubkey, secp256k1_prvkey.schnorr_sign(msg, None, raw=True)
)

# and the four agree on the tweaked key, which is the check the tweak rows
# need: electrum-ecc reaches it through two calls where the others take one,
# and two routes to the same point is the comparison, not a discrepancy
assert coincurve.PublicKey(pubkey).add(tweak).format(compressed=True) == tweaked_pubkey
assert (
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak).serialize(compressed=True)
    == tweaked_pubkey
)
assert (
    electrum_pubkey + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
).get_public_key_bytes(compressed=True) == tweaked_pubkey


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


def dsa_sign_coincurve() -> None:
    """Time coincurve's ECDSA signing, over a digest it is told not to hash."""
    coincurve_prvkey.sign(msg, hasher=None)


def dsa_sign_secp256k1() -> None:
    """Time secp256k1-py's ECDSA signing, which returns a parsed signature."""
    secp256k1_prvkey.ecdsa_sign(msg, raw=True)


def dsa_sign_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA signing, one signature.

    `grind_r_value=False`, which is not its default: it is the only wrapper
    of the four offering low-r grinding at all, and one signature is what
    the other three produce. The row below times the default.
    """
    electrum_prvkey.ecdsa_sign(msg, grind_r_value=False)


def dsa_sign_electrum_ecc_grind() -> None:
    """Time electrum-ecc's ECDSA signing as it signs unless told otherwise.

    Its `ENABLE_ECDSA_R_VALUE_GRINDING` is true, so a caller writing
    `ecdsa_sign(msg32)` signs repeatedly until r fits in 32 bytes: an
    expectation of two signatures and, for one fixed key and message, a
    fixed number of them. Grinding is a loop around a wrapper rather than
    anything libsecp256k1 does, which is why it is one row of four here and
    a pair of rows in the tables about libraries.
    """
    electrum_prvkey.ecdsa_sign(msg)


def dsa_sign_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA signing, bytes in and DER out."""
    btclib_secp256k1.dsa.sign(msg, prvkey)


def ssa_sign_coincurve() -> None:
    """Time coincurve's BIP340 signing, over the vector's aux_rand."""
    coincurve_prvkey.sign_schnorr(msg, aux)


def ssa_sign_secp256k1() -> None:
    """Time secp256k1-py's BIP340 signing, which takes no aux_rand.

    Its signature is therefore not the vector's, and not reproducible
    between runs of libsecp256k1 that seed the nonce differently. Timed all
    the same: what it does is the same work, and the fixtures above check
    the one thing this API leaves checkable, that the signature verifies.
    """
    secp256k1_prvkey.schnorr_sign(msg, None, raw=True)


def ssa_sign_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 signing, over the vector's aux_rand."""
    electrum_prvkey.schnorr_sign(msg, aux_rand32=aux)


def ssa_sign_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 signing, over the vector's aux_rand."""
    btclib_secp256k1.ssa.sign(msg, prvkey, aux)


def tweak_coincurve() -> None:
    """Time coincurve's public key tweak, which returns a new PublicKey."""
    coincurve.PublicKey(pubkey).add(tweak)


def tweak_secp256k1() -> None:
    """Time secp256k1-py's public key tweak, in place on a parsed key."""
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak)


def tweak_electrum_ecc() -> None:
    """Time electrum-ecc's public key tweak, which its API spells in two calls.

    There is no tweak-add on `ECPubkey`: a scalar times the generator and a
    point addition is how the same tweak is reached, and both of those are
    libsecp256k1 calls. Two crossings where the others make one is the
    difference this table exists to show.
    """
    (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    )


def tweak_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's public key tweak, bytes in and bytes out."""
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

# every row is called once before any of them is timed, which is what
# each row's own assert is for: four wrappers of one library have to
# agree that this signature is valid, or the table is comparing answers
# rather than implementations
for _row in DSA_ROWS + SSA_ROWS + DSA_SIGN_ROWS + SSA_SIGN_ROWS + TWEAK_ROWS:
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
    print(f"  {'':<30}{'us/call':>10}{'vs best':>12}")
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
