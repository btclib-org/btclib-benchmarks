# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib, bindings enabled, against other Python bitcoin libraries.

btclib, with the `btclib_secp256k1` bindings it depends on and cannot be
installed without, is what `pip install btclib` gives an end user -- so
this times exactly that path, never the pure-Python fallback of
`curves/curve_group.py`, which `scripts/pure_python.py` covers instead.

Every comparand is timed at its own latest PyPI release, on operations it
actually offers: signing a message is compared against a package that
signs, deriving a BIP32 child against one that has BIP32, and nothing
is compared against a package that lacks the feature.

## One library that is not a row

`bit` installs on this interpreter and is still not here. Its declared
dependency is `coincurve`, so its ECDSA is coincurve's libsecp256k1, and
that build already has a row of its own in
`scripts/libsecp256k1_wrappers.py`. What a `bit` row would add over that
row is its wallet layer, not arithmetic, and a table comparing arithmetic
would be reporting the layer as though it were the curve. It belongs here
the day this benchmark grows a question about wallet APIs.

## What each comparand is actually running, and how that was checked

A raw ctypes.util.find_library lookup answers "is a shared object
findable on this machine", and that answer moves with what happens to be
installed system-wide -- so two of the rows below are not always timing
what they seem to:

- pycoin optimizes its pure-Python arithmetic with libsecp256k1 or
  OpenSSL through ctypes *if* either is importable at runtime
  (`pycoin.ecdsa.native.secp256k1.libsecp256k1`,
  `pycoin.ecdsa.native.openssl` through the same mechanism); with
  neither found it falls back to the plain-Python `Generator` class.
  `_pycoin_backend()` below reports which one actually ran, because
  nothing here should claim a Python number without checking that it is
  one -- and here it reports libsecp256k1, on two conditions that are
  both properties of the import list above rather than of pycoin.
  pycoin's loader calls `ctypes.util.find_library` having imported only
  `ctypes`, so unless something else imported `ctypes.util` first the
  attribute lookup raises and its own `except AttributeError` reports
  that as no library found; `bitcoin.core.key` imports it. And the name
  it then asks for, `libsecp256k1`, resolves to nothing, so the load
  falls through to the process's own symbols -- which
  `btclib_secp256k1`'s extension has already put there. So this row is
  C, and the build it calls is the one btclib's row calls: drop either
  import and the same row is Python again. Its loop count follows that
  answer rather than being written once, `pycoin_calls` below saying why.
- python-bitcoinlib's `CECKey` defaults to OpenSSL's `EC_KEY` (loaded the
  same way, `ctypes.util.find_library`) and only calls libsecp256k1 if a
  caller opts in with `use_libsecp256k1_for_signing` -- not done here, so
  this row is OpenSSL's C and not Python either way, and stays that on
  every machine that has OpenSSL, which is to say every machine this
  installs on.
- embit does not probe the system at all: `embit/util/prebuilt/` ships a
  compiled libsecp256k1 for six platforms, and `embit.ec` loads the one
  matching `platform.machine()` through ctypes unconditionally. This row
  is always C, and always a libsecp256k1 build embit vendors rather than
  the one `btclib_secp256k1` vendors -- two different builds of the same
  library, not the same binary measured twice.
- buidl tries `buidl.cecc`, a compiled extension against Core's
  secp256k1 that `pip install buidl` does not build (`libsec_build.py`
  is a separate step this script does not run), and falls back to
  `buidl.pecc`, pure Python -- deterministically, since nothing here
  attempts the build. `ecdsa` (the PyPI package) has no native path to
  fall back from: it is pure Python unconditionally.

None of this makes a row invalid -- it is what `pip install <package>`
actually gives a user on this machine, which is the same question this
whole script asks of btclib. It does mean a pycoin row is not always
comparable across two runs of this script -- on two machines, or on two
import lists -- which is why the backend it picked is part of the output
rather than a footnote.

## What is measured

Three operations on secp256k1, over published test vectors: BIP340's
first, whose key and 32-byte message the ECDSA rows take as well, and
BIP32's first, whose seed the derivation rows take.

- ECDSA sign and verify, over the vector's 32 bytes read as a digest --
  every comparand that exposes ECDSA takes a digest directly rather than a
  message, so none of them hash it a second time.

  Two of the six grind for a low-r signature by default, btclib and embit,
  which means their default is not one signature but as many as it takes
  to find one whose r fits in 32 bytes. Both therefore have two rows: a
  `grind=False` row, which is one signature and is what the other four
  produce, and a row of the default beside it. A grinding row is not a
  per-signature number and does not pretend to be one -- for a fixed key
  and message it is a fixed multiple of the row above it, four signatures
  for this pair against the expected two, which is a property of the pair
  and not of either library: BIP340's vector key wants four where two is
  the expectation, and a key wanting two makes grinding look like ordinary
  overhead rather than a second signature.
- BIP340 (Schnorr) sign and verify, over the vector's message and
  aux_rand -- BIP340 does not hash its message internally, so this is the
  value every implementation signs and checks, byte for byte, and it
  doubles as libsecp256k1's own fixed-size entry point, which is what
  keeps btclib's row on the bindings path (`ecc.ssa.sign_`'s dispatch is
  exactly this size or the arbitrary-size Python fallback, and this
  script wants the former). Signing over the vector's aux_rand rather than
  a random one is what makes both signing rows reproducible, and therefore
  checkable against BIP340 itself.
- one BIP32 derivation, `m/0h/1` from the vector's seed -- a hardened step
  and a normal one, which is what every comparand's own derivation
  function takes a path string or a chain of `child`/`subkey` calls for.
  All four implementations were checked against each other *and* against
  the public key BIP32 publishes for that path before any of this was
  timed.

python-ecdsa and python-bitcoinlib carry neither BIP340 nor BIP32, so
neither has a row in those two tables; pycoin's own `ecdsa.Generator` is
a bare elliptic-curve object with no seed-derivation function either,
which is why its BIP32 row goes through `pycoin.symbols.btc.network`
instead, the layer above that actually has one. Nothing here compares a
feature against a library that lacks it.

Not part of the test suite and not run by CI: measuring is done by a
person on a machine whose state they know, and a shared runner disagrees
with a laptop by more than most of the differences here.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path

import bitcoin.core.key as bitcoinlib_key
import btclib

# imported for its side effect, which one row of this table turns on:
# loading the extension puts libsecp256k1's symbols in the process, and
# pycoin's ctypes probe -- run when pycoin is imported, below -- finds them
# there or falls back to Python. Drop this line and pycoin's rows become
# Python rows, which the docstring above is about. btclib's own dispatch
# imports the bindings when it first needs them, too late for that probe
import btclib_secp256k1  # noqa: F401
import buidl.hd
import buidl.libsec_status
import buidl.pecc
import ecdsa
import embit.bip32
import embit.ec
import embit.util.ctypes_secp256k1
import pycoin.symbols.btc
from _provenance import report
from btclib.bip32 import bip32
from btclib.ecc import dsa, ssa
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def report_provenance() -> None:
    """Say which build of every package in the table these rows are about.

    Printed before any number: a released wheel and a working tree satisfy
    the same requirement and resolve in silence, so which one ran is
    something the output has to state rather than something the reader
    assumes.

    Every package, comparands included, so that a version number appears
    once in this output and `report_setup` below is left with the one thing
    a version cannot say: which arithmetic the row reached.
    """
    report(
        ("btclib", btclib.__file__),
        ("ecdsa", ecdsa.__file__),
        ("pycoin", pycoin.symbols.btc.__file__),
        ("buidl", buidl.pecc.__file__),
        ("embit", embit.ec.__file__),
        ("python-bitcoinlib", bitcoinlib_key.__file__),
    )


# BIP340 test vector 1 and BIP32 test vector 1, transcribed from btclib's
# vendored copies (`tests/ecc/_data/bip340_test_vectors.csv` and
# `tests/bip32/_data/bip32_test_vectors.json`, whose
# `tests/_data/README.md` pins each to a commit of bitcoin/bips and
# compares the bytes). Published inputs rather than inputs chosen here, and
# what each vector publishes is asserted below: the cross-comparand checks
# hold every row against btclib's answer, which cannot catch a mistake
# btclib and a comparand share, and a specification can.
#
# A published key matters to one row more than to the rest. python-ecdsa
# returns the generator *object* for the public key of the private key 1 --
# precomputed table and all -- so a row verifying against that key verifies
# with a table no real key gets, at about half the cost of verification.
# Every other row measures the same through any valid key, three of them
# having been timed to check it: the vector is here for what it forbids
# rather than for what it changes.
PRVKEY = 0xB7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF
MSG_HASH = bytes.fromhex(
    "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89"
)
AUX = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
VECTOR_XONLY_PUBKEY = bytes.fromhex(
    "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"
)
VECTOR_SSA_SIG = bytes.fromhex(
    "6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE3341"
    "8906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"
)
SEED = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
BIP32_PATH = "m/0h/1"
VECTOR_BIP32_CHILD_PUBKEY = bytes.fromhex(
    "03501E454BF00751F24B1B489AA925215D66AF2234E3891C3B21A52BEDB3CD711C"
)


# the two modules a native mixin can come from, and what each one means.
# Keyed by module rather than by class name because the name cannot tell
# them apart: both call their real mixin `Optimizations` and both call
# their fallback `noop`. `LibSECP256K1Optimizations` is an alias pycoin
# binds to that same `Optimizations` class, so a probe looking for that
# spelling among the base names could not fire at all -- which is how
# this table came to print "pure Python" beside timings that were C.
# The strings are a line of `report_setup`'s block, so they name the code
# and then the mechanism, as every other line there does. Which copy of
# libsecp256k1 is a property of the process rather than of pycoin, and the
# module docstring is where that is spelled out.
# Which libsecp256k1 btclib's row calls, keyed to the btclib_secp256k1
# release it was read from: the library is compiled into a cffi extension,
# where nothing at run time can say which revision that was. Read from that
# release's own `secp256k1` submodule pin, 6e2c8bc, which is upstream's
# v0.8.0 tag exactly -- and printed as unrecorded for any other release,
# because a floor is a floor and a comparand upgrades without a word.
# `scripts/libsecp256k1_wrappers.py` holds the same pin for the same reason
# and for three packages more; two scripts naming one revision is the price
# of neither of them naming it silently
LIBSECP256K1_PIN = ("0.8.0.1", "v0.8.0")


def _btclib_secp256k1_libsecp256k1() -> str:
    """Name the revision btclib's row reaches, and the artifact carrying it."""
    recorded, pin = LIBSECP256K1_PIN
    installed = version("btclib_secp256k1")
    revision = pin if installed == recorded else f"an unrecorded revision ({recorded})"
    spec = find_spec("_btclib_secp256k1")
    artifact = Path(spec.origin).name if spec and spec.origin else "not found"
    return (
        f"libsecp256k1 {revision} compiled into btclib_secp256k1 {installed}, "
        f"{artifact}"
    )


def _embit_libsecp256k1() -> str:
    """Name the shared object embit's ctypes loader opened.

    A file name and not a revision: embit ships one prebuilt library per
    platform, none of them carrying a version anywhere a caller can read,
    so what can be said is which of the seven this platform got.
    """
    return Path(str(embit.util.ctypes_secp256k1._find_library())).name


PYCOIN_NATIVE_MIXINS = {
    "pycoin.ecdsa.native.secp256k1": (
        "the same libsecp256k1 btclib's row calls, which it neither bundles "
        "nor compiles, through ctypes bindings"
    ),
    "pycoin.ecdsa.native.openssl": "OpenSSL's libcrypto, through ctypes bindings",
}


def _pycoin_native_module() -> str | None:
    """Return the module of the native mixin pycoin's generator got, if any.

    `create_LibSECP256K1Optimizations`/`create_OpenSSLOptimizations` (in
    `pycoin.ecdsa.native.*`) each resolve to a `noop` mixin class when
    the shared library they probe for is not importable -- there is no
    public flag to read instead, so this reads the MRO the generator
    ended up with, and reads each base's module for the reason above.

    What it answers is not a property of pycoin alone, which is the whole
    reason it is read at run time rather than written down: the module
    docstring has the two imports this script happens to make that turn
    pycoin's row into C, and neither of them is pycoin's doing. Two
    things need the answer -- the line `report_setup` prints, and the
    loop count `pycoin_calls` picks -- so it is one function and not a
    string parsed twice.
    """
    for base in type(pycoin.symbols.btc.network.generator).__mro__:
        if "noop" in base.__qualname__:
            continue
        if base.__module__ in PYCOIN_NATIVE_MIXINS:
            return base.__module__
    return None


def _pycoin_backend() -> str:
    """Name the arithmetic pycoin's Generator actually runs, this machine."""
    module = _pycoin_native_module()
    return PYCOIN_NATIVE_MIXINS[module] if module else "pure Python"


# read once, at import, because that is when pycoin decided it: the mixin
# is chosen while `pycoin.ecdsa.native.*` is being imported and never
# revisited
PYCOIN_REACHES_C = _pycoin_native_module() is not None


def pycoin_calls(c: int, python: int) -> int:
    """Pick a pycoin row's loop count from the backend it resolved to.

    A count written once is wrong on one machine or the other. The same
    call is a few microseconds through libsecp256k1 and several
    milliseconds in Python -- three orders of magnitude -- and which one
    runs is decided by the imports above rather than by anything here, so
    a count sized for Python measures almost nothing when the row turns
    out to be C, and a count sized for C sits for minutes when it does
    not. Both numbers are written at each call site, and the row prints
    the one it used.
    """
    return c if PYCOIN_REACHES_C else python


def report_setup() -> None:
    """Print which arithmetic each row reached, and how it reached it.

    Not a version number: `report_provenance` above prints those, for every
    package here, and this block answers the question a version cannot.
    Every line names the same two things in the same order -- the code that
    does the arithmetic, and the mechanism the row calls it through -- so
    that two rows can be read against each other without translating
    between one line's vocabulary and the next.

    A benchmark result is not among them. What is here is what the numbers
    below mean nothing without.
    """
    print("arithmetic under each row")
    print(f"  {'btclib':<20}{_btclib_secp256k1_libsecp256k1()}, through cffi bindings")
    print(f"  {'ecdsa':<20}pure Python; it has no bindings of any kind")
    print(f"  {'pycoin':<20}{_pycoin_backend()}")
    buidl_arithmetic = (
        "the libsecp256k1 compiled into buidl.cecc, through cffi bindings"
        if buidl.libsec_status.is_libsec_enabled()
        else "pure Python; the cffi bindings of buidl.cecc are not built"
    )
    print(f"  {'buidl':<20}{buidl_arithmetic}")
    print(
        f"  {'embit':<20}the prebuilt libsecp256k1 it bundles, "
        f"{_embit_libsecp256k1()}, through ctypes bindings"
    )
    optional = (
        "its own bundled libsecp256k1 available and unused"
        if bitcoinlib_key.is_libsec256k1_available()
        else "no libsecp256k1 of its own to opt into"
    )
    print(
        f"  {'python-bitcoinlib':<20}OpenSSL's libcrypto, through ctypes bindings, "
        f"{optional}"
    )
    print()


# --- ECDSA sign and verify, over MSG_HASH -----------------------------

btclib_pubkey = pub_keyinfo_from_prv_key(PRVKEY)[0]
# grind=False here too, so that the signature the verify rows check is
# the one the sign rows above produce, and so that every comparand is
# handed a signature none of them would have refused
btclib_dsa_sig = dsa.sign_(MSG_HASH, PRVKEY, grind=False)

ecdsa_signing_key = ecdsa.SigningKey.from_secret_exponent(PRVKEY, curve=ecdsa.SECP256k1)
ecdsa_verifying_key = ecdsa_signing_key.verifying_key
ecdsa_sig = ecdsa_signing_key.sign_digest_deterministic(
    MSG_HASH, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der
)

pycoin_generator = pycoin.symbols.btc.network.generator
pycoin_val = int.from_bytes(MSG_HASH, "big")
pycoin_pubpoint = pycoin_generator * PRVKEY
pycoin_public_pair = (pycoin_pubpoint[0], pycoin_pubpoint[1])
pycoin_sig = pycoin_generator.sign(PRVKEY, pycoin_val)

buidl_prvkey = buidl.pecc.PrivateKey(PRVKEY)
buidl_z = int.from_bytes(MSG_HASH, "big")
buidl_sig = buidl_prvkey.sign(buidl_z)

bitcoinlib_key_ = bitcoinlib_key.CECKey()
bitcoinlib_key_.set_secretbytes(PRVKEY.to_bytes(32, "big"))
bitcoinlib_key_.set_compressed(True)
bitcoinlib_pubkey = bitcoinlib_key.CPubKey(bitcoinlib_key_.get_pubkey())
bitcoinlib_sig = bitcoinlib_key_.sign(MSG_HASH)

embit_prvkey = embit.ec.PrivateKey(PRVKEY.to_bytes(32, "big"))
embit_pubkey = embit_prvkey.get_public_key()
# grind=False, as btclib's fixture above: embit grinds for a low-r
# signature by default too, and a fixture that is one signature is what
# lets every verify row below check comparable work
embit_dsa_sig = embit_prvkey.sign(MSG_HASH, grind=False)

assert dsa.verify_(MSG_HASH, btclib_pubkey, btclib_dsa_sig)
assert ecdsa_verifying_key.verify_digest(
    ecdsa_sig, MSG_HASH, sigdecode=ecdsa.util.sigdecode_der
)
assert pycoin_generator.verify(pycoin_public_pair, pycoin_val, pycoin_sig)
assert buidl_prvkey.point.verify(buidl_z, buidl_sig)
assert bitcoinlib_pubkey.verify(MSG_HASH, bitcoinlib_sig)
assert embit_pubkey.verify(embit_dsa_sig, MSG_HASH)


def dsa_sign_btclib() -> None:
    """Time one ECDSA signature through btclib, bindings enabled.

    `grind=False`, which is not btclib's default and is what makes this
    row comparable: every other row in the table produces one signature,
    and btclib's default produces as many as it takes to find one whose r
    fits in 32 bytes. `dsa_sign_btclib_grind` below times the default.
    """
    dsa.sign_(MSG_HASH, PRVKEY, grind=False)


def dsa_sign_btclib_grind() -> None:
    """Time ECDSA signing as `pip install btclib` performs it.

    btclib grinds for a low-r signature unless told not to, so this row
    signs repeatedly until r fits in 32 bytes -- an expectation of two
    signatures, and for any one fixed key and message a fixed number of
    them, this pair costing four times that. It is here because it is what
    a caller who writes `dsa.sign_(msg, key)` gets, and it is a row of its
    own rather than *the* btclib row because no comparand in this table
    grinds, so per-signature it compares with nothing.
    """
    dsa.sign_(MSG_HASH, PRVKEY)


def dsa_verify_btclib() -> None:
    """Time ECDSA verification through btclib, bindings enabled."""
    assert dsa.verify_(MSG_HASH, btclib_pubkey, btclib_dsa_sig)


def dsa_sign_ecdsa() -> None:
    """Time ECDSA signing through the `ecdsa` PyPI package."""
    ecdsa_signing_key.sign_digest_deterministic(
        MSG_HASH, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der
    )


def dsa_verify_ecdsa() -> None:
    """Time ECDSA verification through the `ecdsa` PyPI package."""
    assert ecdsa_verifying_key.verify_digest(
        ecdsa_sig, MSG_HASH, sigdecode=ecdsa.util.sigdecode_der
    )


def dsa_sign_pycoin() -> None:
    """Time ECDSA signing through pycoin's Generator, backend as reported."""
    pycoin_generator.sign(PRVKEY, pycoin_val)


def dsa_verify_pycoin() -> None:
    """Time ECDSA verification through pycoin's Generator."""
    assert pycoin_generator.verify(pycoin_public_pair, pycoin_val, pycoin_sig)


def dsa_sign_buidl() -> None:
    """Time ECDSA signing through buidl's pure-Python PrivateKey."""
    buidl_prvkey.sign(buidl_z)


def dsa_verify_buidl() -> None:
    """Time ECDSA verification through buidl's pure-Python S256Point."""
    assert buidl_prvkey.point.verify(buidl_z, buidl_sig)


def dsa_sign_bitcoinlib() -> None:
    """Time ECDSA signing through python-bitcoinlib's OpenSSL wrapper."""
    bitcoinlib_key_.sign(MSG_HASH)


def dsa_verify_bitcoinlib() -> None:
    """Time ECDSA verification through python-bitcoinlib's OpenSSL wrapper."""
    assert bitcoinlib_pubkey.verify(MSG_HASH, bitcoinlib_sig)


def dsa_sign_embit() -> None:
    """Time one ECDSA signature through embit's bundled libsecp256k1.

    `grind=False`, for the reason btclib's row passes it: embit is the
    other library here that grinds by default, and one signature is what
    the rest of the table produces.
    """
    embit_prvkey.sign(MSG_HASH, grind=False)


def dsa_sign_embit_grind() -> None:
    """Time ECDSA signing as embit performs it by default.

    embit grinds for a low-r signature with a counter in the extra
    entropy, where btclib grinds by re-deriving its nonce; the two are the
    same expectation of two signatures reached differently, and for one
    fixed key and message each lands on its own fixed number of them.
    """
    embit_prvkey.sign(MSG_HASH)


def dsa_verify_embit() -> None:
    """Time ECDSA verification through embit's bundled libsecp256k1."""
    assert embit_pubkey.verify(embit_dsa_sig, MSG_HASH)


# --- BIP340 (Schnorr) sign and verify, over MSG_HASH -------------------

btclib_xonly_pubkey = btclib_pubkey[1:]
# the vector's aux_rand rather than the random default, which makes both
# signatures below reproducible and therefore checkable against BIP340
# itself; embit's API exposes no aux, so its own signature cannot be
# pinned and it is held to the vector the other way, by verifying it
btclib_ssa_sig = ssa.sign_(MSG_HASH, PRVKEY, aux=AUX)
buidl_ssa_sig = buidl_prvkey.sign_schnorr(MSG_HASH, AUX)
embit_ssa_sig = embit_prvkey.schnorr_sign(MSG_HASH)

assert btclib_xonly_pubkey == VECTOR_XONLY_PUBKEY
assert btclib_ssa_sig.serialize() == VECTOR_SSA_SIG
assert buidl_ssa_sig.serialize() == VECTOR_SSA_SIG
assert embit_pubkey.schnorr_verify(embit.ec.SchnorrSig.parse(VECTOR_SSA_SIG), MSG_HASH)
assert ssa.verify_(MSG_HASH, btclib_xonly_pubkey, btclib_ssa_sig)
assert buidl_prvkey.point.verify_schnorr(MSG_HASH, buidl_ssa_sig)
assert embit_pubkey.schnorr_verify(embit_ssa_sig, MSG_HASH)


def ssa_sign_btclib() -> None:
    """Time BIP340 signing through btclib, bindings enabled."""
    ssa.sign_(MSG_HASH, PRVKEY, aux=AUX)


def ssa_verify_btclib() -> None:
    """Time BIP340 verification through btclib, bindings enabled."""
    assert ssa.verify_(MSG_HASH, btclib_xonly_pubkey, btclib_ssa_sig)


def ssa_sign_buidl() -> None:
    """Time BIP340 signing through buidl's pure-Python PrivateKey."""
    buidl_prvkey.sign_schnorr(MSG_HASH, AUX)


def ssa_verify_buidl() -> None:
    """Time BIP340 verification through buidl's pure-Python S256Point."""
    assert buidl_prvkey.point.verify_schnorr(MSG_HASH, buidl_ssa_sig)


def ssa_sign_embit() -> None:
    """Time BIP340 signing through embit's bundled libsecp256k1."""
    embit_prvkey.schnorr_sign(MSG_HASH)


def ssa_verify_embit() -> None:
    """Time BIP340 verification through embit's bundled libsecp256k1."""
    assert embit_pubkey.schnorr_verify(embit_ssa_sig, MSG_HASH)


# --- BIP32 derivation, seed to "m/0h/1" child ---------------------------

# the whole path from SEED, rebuilt inside every function below rather
# than once here: pycoin's BIP32Node keeps a `_subkey_cache` dict keyed
# by index, so a root reused across 1000 calls of the same path answers
# the 999 after the first from that cache and times a dict lookup, not a
# derivation. Rebuilding the root from the seed on every call is the one
# methodology that measures the same thing for all four -- one HMAC-SHA512
# to the root plus the path below it -- and none of the other three reads
# any faster for it: none keeps a cross-call cache of its own


def _btclib_child_pubkey(seed: bytes) -> bytes:
    xprv = bip32.rootxprv_from_seed(seed)
    child = bip32.derive(xprv, BIP32_PATH)
    return bip32.BIP32KeyData.b58decode(bip32.xpub_from_xprv(child)).key


def _pycoin_child_pubkey(seed: bytes) -> bytes:
    root = pycoin.symbols.btc.network.keys.bip32_seed(seed)
    return bytes(root.subkey_for_path("0H/1").sec())


def _embit_child_pubkey(seed: bytes) -> bytes:
    root = embit.bip32.HDKey.from_seed(seed)
    return bytes(root.derive(BIP32_PATH).sec())


def _buidl_child_pubkey(seed: bytes) -> bytes:
    root = buidl.hd.HDPrivateKey.from_seed(seed)
    return bytes(root.traverse(BIP32_PATH).pub.point.sec())


# the four against each other, and all four against what BIP32 publishes
# for this seed and this path: agreeing with one another is what four
# implementations of the same mistake also do
assert (
    _btclib_child_pubkey(SEED)
    == _pycoin_child_pubkey(SEED)
    == _embit_child_pubkey(SEED)
    == _buidl_child_pubkey(SEED)
    == VECTOR_BIP32_CHILD_PUBKEY
)


def bip32_derive_btclib() -> None:
    """Time seed-to-child BIP32 derivation through btclib, bindings enabled."""
    _btclib_child_pubkey(SEED)


def bip32_derive_pycoin() -> None:
    """Time seed-to-child BIP32 derivation through pycoin's BIP32Node."""
    _pycoin_child_pubkey(SEED)


def bip32_derive_embit() -> None:
    """Time seed-to-child BIP32 derivation through embit's HDKey."""
    _embit_child_pubkey(SEED)


def bip32_derive_buidl() -> None:
    """Time seed-to-child BIP32 derivation through buidl's HDPrivateKey."""
    _buidl_child_pubkey(SEED)


def benchmark(func: Callable[[], None], calls: int) -> float:
    """Call `func` `calls` times and return microseconds per call.

    Returned and not printed: the tables below are sorted fastest to
    slowest and each row divides by btclib's, neither of which can be
    done a line at a time -- every number has to be in hand before the
    first line is.

    `calls` is chosen per function rather than shared: buidl's
    pure-Python rows are three to four orders of magnitude slower than
    the C-backed ones, so one loop count for all of them would either sit
    for minutes on the slowest or measure the fastest against the
    resolution of the clock. Each count below was picked from a first
    timed call to land near 1.5 seconds -- long enough that Python's own
    call overhead is a rounding error next to it, short enough that the
    whole script is a run to wait for, not start and leave. pycoin's rows
    are the exception and carry two counts each, being the only rows whose
    backend this script does not decide: `pycoin_calls` above.
    """
    # perf_counter and not time(): the wall clock can step backwards
    # under an NTP correction, and a benchmark is the one place that
    # shows up as a negative duration
    start = time.perf_counter()
    for _ in range(calls):
        func()
    end = time.perf_counter()
    return (end - start) / calls * 1e6


def table(
    title: str,
    rows: tuple[tuple[Callable[[], None], int], ...],
) -> None:
    """Time one operation's rows, then print them fastest first.

    The ratio is against the fastest row, whichever package that turns out
    to be, so the top row reads 1.0x and each row below says what
    choosing it instead would cost. Against btclib's row -- the obvious
    candidate, this being btclib's benchmark -- the column would print
    fractions under one for anything quicker, which reads as btclib's
    score rather than as the table's answer; where btclib stands is the
    row's own position in the order, and that is now visible without a
    column claiming it.

    Sorted on the measurement rather than written in an order, so the
    order carries the run's answer instead of an editor's opinion of it.
    The loop counts stay per row and print beside their rows: they are
    part of what a row is, and sorting mixes rows whose counts differ by
    orders of magnitude.
    """
    us = {func.__name__: (benchmark(func, calls), calls) for func, calls in rows}
    against = min(value for value, _ in us.values())
    print(title)
    print(f"  {'':<22}{'us/call':>10}{'vs best':>12}")
    for name, (value, calls) in sorted(us.items(), key=lambda row: row[1][0]):
        print(f"  {name:<22}{value:10.2f}{value / against:11.1f}x   ({calls} calls)")


def main() -> None:
    """Print every table, one operation at a time."""
    report_provenance()

    report_setup()

    table(
        "ECDSA sign (32-byte digest, secp256k1)",
        (
            (dsa_sign_btclib, 50_000),
            (dsa_sign_btclib_grind, 20_000),
            (dsa_sign_ecdsa, 5_000),
            (dsa_sign_pycoin, pycoin_calls(50_000, 200)),
            (dsa_sign_buidl, 50),
            (dsa_sign_bitcoinlib, 8_000),
            (dsa_sign_embit, 50_000),
            (dsa_sign_embit_grind, 20_000),
        ),
    )
    print()

    table(
        "ECDSA verify (32-byte digest, secp256k1)",
        (
            (dsa_verify_btclib, 50_000),
            (dsa_verify_ecdsa, 3_000),
            (dsa_verify_pycoin, pycoin_calls(50_000, 80)),
            (dsa_verify_buidl, 25),
            (dsa_verify_bitcoinlib, 7_000),
            (dsa_verify_embit, 50_000),
        ),
    )
    print()

    table(
        "BIP340 sign (32-byte message)",
        (
            (ssa_sign_btclib, 50_000),
            (ssa_sign_buidl, 20),
            (ssa_sign_embit, 50_000),
        ),
    )
    print()

    table(
        "BIP340 verify (32-byte message)",
        (
            (ssa_verify_btclib, 50_000),
            (ssa_verify_buidl, 25),
            (ssa_verify_embit, 50_000),
        ),
    )
    print()

    table(
        f"BIP32 derive, seed to {BIP32_PATH} ({len(SEED)}-byte seed)",
        (
            (bip32_derive_btclib, 30_000),
            (bip32_derive_pycoin, pycoin_calls(30_000, 75)),
            (bip32_derive_embit, 15_000),
            (bip32_derive_buidl, 12),
        ),
    )


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
