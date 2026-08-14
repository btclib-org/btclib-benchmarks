# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib as installed, against other Python bitcoin libraries.

`pip install btclib` installs the `btclib_secp256k1` bindings with it, so
this times that path and never the pure-Python fallback, which
`scripts/pure_python.py` covers. Every comparand is timed at its own latest
PyPI release, on operations it offers: nothing here is compared against a
library that lacks the feature.

## What each row's arithmetic is

`report_setup` prints it per row, because for two of them it is not a
property of the package:

- pycoin bundles no library and builds no extension. Its `native/secp256k1`
  and `native/openssl` modules are ctypes loaders, so a PyPI install is pure
  Python unless the machine has a library answering the name they probe for.
  This row is C for two reasons that belong to the import list above:
  `bitcoin.core.key` imports `ctypes.util`, which pycoin's loader needs and
  does not import, and the name it then asks for resolves to nothing, so the
  load falls through to the symbols `btclib_secp256k1`'s extension has put
  in the process. Drop either import and the row is Python. Its loop count
  follows the answer rather than being written once: `pycoin_calls` below.
- buidl reaches C only if `libsec_build.py` was run against a system
  library, which `pip install buidl` does not do, so `buidl.pecc` is what an
  install gets.
- embit bundles ElementsProject's `secp256k1-zkp`, prebuilt per platform,
  not `bitcoin-core/secp256k1`. Its row is always C and never the same C as
  the others.
- python-bitcoinlib's `CECKey` uses OpenSSL's `EC_KEY`, and calls
  libsecp256k1 only if a caller opts in, which nothing here does.
- `ecdsa` has no compiled backend to fall back from.

None of this invalidates a row: it is what `pip install <package>` gives on
this machine. It does mean pycoin's row is not comparable across import
lists, which is why the backend it resolved to is in the output.

## `bit` is not a row

It installs, and its ECDSA is coincurve's libsecp256k1, which has a row of
its own in `scripts/libsecp256k1_wrappers.py`. A `bit` row would add its
wallet layer, not arithmetic.

## What is measured

Every input is a published vector, cycled: `_vectors` reads BIP340's file
and BIP32's, and each row takes the next per call. The address rows are the
exception and say so where they are defined.

- ECDSA sign and verify, over each vector's 32 bytes read as a digest. Every
  comparand takes a digest directly, so none of them hashes it again.

  btclib and embit grind for a low-r signature by default -- they sign until
  r fits in 32 bytes -- so each has two rows: a `grind=False` row, which is
  the one signature the other four produce, and its default beside it. A
  grinding row is a multiple of the row above it, and the multiple is a
  property of the key and message rather than of the library.
- BIP340 sign and verify, over each vector's message and aux_rand. BIP340
  does not hash its message, so this is the value every implementation signs
  byte for byte, and it is libsecp256k1's fixed-size entry point, which is
  what keeps btclib's row on the bindings path. The vector's aux_rand makes
  both signing rows reproducible, and therefore checkable against BIP340.
- BIP32 derivation, every chain the vector file publishes, checked against
  the public key it publishes for that path.
- base58check, bech32 and bech32m, encoding and decoding. Pure Python in
  every library here, so these rows say nothing about bindings and
  everything about the code -- and they hold the one wrong answer in this
  benchmark: `python-bitcoinlib` encodes a witness-v1 program with bech32's
  checksum constant where BIP350 requires bech32m's, and rejects the address
  BIP350 publishes. It has no bech32m row, and the script asserts both
  halves of why.

python-ecdsa carries only ECDSA and python-bitcoinlib carries neither BIP340
nor BIP32, so neither has a row in those tables. pycoin's `ecdsa.Generator`
has no derivation function either, which is why its BIP32 row goes through
`pycoin.symbols.btc.network`.

A timed function calls one library and discards what it returns: no row
checks its own answer, which would put the check inside the number.
`tests/vectors_test.py` is where the answers are checked, running the
vendored vectors against every library timed here. The assertions below run
at import, where the fixtures are built, so the suite loading this module
runs them and no timing carries them.

Not part of the test suite and not run by CI: a shared runner disagrees with
a laptop by more than most of the differences here.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from importlib.metadata import version
from importlib.util import find_spec
from itertools import cycle
from pathlib import Path

import bitcoin.bech32
import bitcoin.core.key as bitcoinlib_key
import bitcoin.wallet as bitcoinlib_wallet
import btclib
import btclib.b32
import btclib.b58

# imported for its side effect, which one row of this table turns on:
# loading the extension puts libsecp256k1's symbols in the process, and
# pycoin's ctypes probe -- run when pycoin is imported, below -- finds them
# there or falls back to Python. Drop this line and pycoin's rows become
# Python rows, which the docstring above is about. btclib's own dispatch
# imports the bindings when it first needs them, too late for that probe
import btclib_secp256k1  # noqa: F401
import buidl.bech32
import buidl.hd
import buidl.helper
import buidl.libsec_status
import buidl.pecc
import ecdsa
import embit.base58
import embit.bech32
import embit.bip32
import embit.ec
import embit.util.ctypes_secp256k1
import pycoin.encoding.b58
import pycoin.symbols.btc
from _provenance import report
from _vectors import bip32, signing
from btclib.bip32 import bip32 as btclib_bip32
from btclib.curves import curve
from btclib.ecc import dsa, ssa
from btclib.to_pub_key import pub_keyinfo_from_key, pub_keyinfo_from_prv_key


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


# every published vector, cycled, rather than one input repeated: a row that
# calls one input fifty thousand times measures that input. `_vectors` reads
# BIP340's file and BIP32's, checks their digests and decodes them; each row
# below takes the next of what they publish per call.
#
# The address encodings are the exception and say so where they are defined:
# one witness-v0 address and one witness-v1 address are what BIP173 and BIP350
# publish in a form vendored here, so those rows still call one input.
SIGNING = signing()
CHAINS = bip32()

# pycoin and buidl take an ECDSA digest as an integer rather than as bytes,
# and pycoin refuses a value at or above the group order and refuses zero --
# BIP340's messages include both. Reducing modulo the order is what any
# implementation does with a digest internally, so that keeps every row on one
# value; the zero leaves the ECDSA cycles, and the BIP340 rows keep it
ORDER = curve.secp256k1.n
DSA_VECTORS = [v for v in SIGNING if int.from_bytes(v.msg, "big") % ORDER]
DIGESTS = [int.from_bytes(v.msg, "big") % ORDER for v in DSA_VECTORS]


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
# Which library each row's bindings reach, keyed to the release the pin was
# read from. Neither revision can be recovered at run time: btclib's is
# compiled into a cffi extension, and embit's is a prebuilt binary carrying
# no version string. Both are printed as unrecorded for any other release,
# because a floor is a floor and a comparand upgrades without a word.
#
# - btclib_secp256k1 0.8.0.2: its `secp256k1` submodule pin, 6e2c8bc, which
#   is upstream's v0.8.0 tag exactly, and the same commit 0.8.0.1 pinned
# - embit 0.8.0: its `secp256k1/secp256k1-zkp` submodule pin, d9560e0a --
#   ElementsProject's fork and not bitcoin-core/secp256k1, which is worth
#   saying in a table that calls four other rows the same library
PINS = {"btclib-secp256k1": ("0.8.0.2", "v0.8.0"), "embit": ("0.8.0", "d9560e0a")}


def _pinned(dist_name: str) -> str:
    """Return the pinned revision, or say the installed release has no pin."""
    recorded, pin = PINS[dist_name]
    installed = version(dist_name)
    return pin if installed == recorded else f"unrecorded for {installed}"


def _artifact(module_name: str) -> str:
    """Return the file name of the compiled extension a wrapper calls into."""
    spec = find_spec(module_name)
    return Path(spec.origin).name if spec and spec.origin else "not found"


# pycoin bundles no library and builds no extension: `native/secp256k1.py`
# and `native/openssl.py` are ctypes loaders, and what they find is a
# property of the machine. So a PyPI install gets pure Python unless a
# system library answers to the name `ctypes.util.find_library` is given --
# and the row below is C only because this process already holds
# btclib_secp256k1's copy, which is not what pip install produces
PYCOIN_NATIVE_MIXINS = {
    "pycoin.ecdsa.native.secp256k1": (
        "ctypes bindings to a libsecp256k1 it neither bundles nor builds: "
        "btclib_secp256k1's, already in this process, which a PyPI install "
        "does not give"
    ),
    "pycoin.ecdsa.native.openssl": "OpenSSL's libcrypto ctypes bindings",
}


def _buidl_backend() -> str:
    """Say which arithmetic buidl resolved to, and what the other would take.

    `buidl.cecc` is cffi bindings to a libsecp256k1 buidl neither bundles
    nor builds at install time: `libsec_build.py` compiles them against a
    system library, on its own, and `pip install buidl` does not run it. So
    a PyPI install is `buidl.pecc`, pure Python, unless somebody ran that
    step by hand.
    """
    if buidl.libsec_status.is_libsec_enabled():
        return "built libsecp256k1 cffi bindings, buidl.cecc"
    return "pure Python; buidl.cecc cffi bindings need libsec_build.py, unrun"


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
    print(
        f"  {'btclib':<20}bundled libsecp256k1 {_pinned('btclib-secp256k1')} "
        f"cffi bindings, {_artifact('_btclib_secp256k1')}"
    )
    print(f"  {'ecdsa':<20}pure Python; no bindings of any kind, bundled or built")
    print(f"  {'pycoin':<20}{_pycoin_backend()}")
    print(f"  {'buidl':<20}{_buidl_backend()}")
    print(
        f"  {'embit':<20}bundled secp256k1-zkp {_pinned('embit')} ctypes bindings, "
        f"{Path(str(embit.util.ctypes_secp256k1._find_library())).name}"
    )
    optional = (
        "a libsecp256k1 it found and does not use"
        if bitcoinlib_key.is_libsec256k1_available()
        else "no libsecp256k1 bundled, built or found"
    )
    print(
        f"  {'python-bitcoinlib':<20}OpenSSL's libcrypto ctypes bindings, "
        f"{Path(str(bitcoinlib_key._ssl._name)).name}; {optional}"
    )
    print()


# --- ECDSA sign and verify ---------------------------------------------

# grind=False wherever a library offers it, so that the signature a verify row
# checks is the one its sign row produces, and so that every comparand is
# handed a signature none of them would have refused
BTCLIB_PUBKEYS = [pub_keyinfo_from_prv_key(v.prvkey)[0] for v in DSA_VECTORS]
BTCLIB_DSA_SIGS = [dsa.sign_(v.msg, v.prvkey, grind=False) for v in DSA_VECTORS]

ECDSA_KEYS = [
    ecdsa.SigningKey.from_secret_exponent(
        int.from_bytes(v.prvkey, "big"), curve=ecdsa.SECP256k1
    )
    for v in DSA_VECTORS
]
ECDSA_SIGS = [
    key.sign_digest_deterministic(
        v.msg, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der
    )
    for key, v in zip(ECDSA_KEYS, DSA_VECTORS, strict=True)
]

pycoin_generator = pycoin.symbols.btc.network.generator
PYCOIN_SCALARS = [int.from_bytes(v.prvkey, "big") for v in DSA_VECTORS]
PYCOIN_PAIRS = [
    (point[0], point[1])
    for point in (pycoin_generator * scalar for scalar in PYCOIN_SCALARS)
]
PYCOIN_SIGS = [
    pycoin_generator.sign(scalar, digest)
    for scalar, digest in zip(PYCOIN_SCALARS, DIGESTS, strict=True)
]

BUIDL_KEYS = [buidl.pecc.PrivateKey(scalar) for scalar in PYCOIN_SCALARS]
BUIDL_SIGS = [key.sign(digest) for key, digest in zip(BUIDL_KEYS, DIGESTS, strict=True)]


def _bitcoinlib_key(prvkey: bytes) -> bitcoinlib_key.CECKey:
    """Return python-bitcoinlib's key object for one secret key."""
    key = bitcoinlib_key.CECKey()
    key.set_secretbytes(prvkey)
    key.set_compressed(True)
    return key


BITCOINLIB_KEYS = [_bitcoinlib_key(v.prvkey) for v in DSA_VECTORS]
BITCOINLIB_PUBKEYS = [
    bitcoinlib_key.CPubKey(key.get_pubkey()) for key in BITCOINLIB_KEYS
]
BITCOINLIB_SIGS = [
    key.sign(v.msg) for key, v in zip(BITCOINLIB_KEYS, DSA_VECTORS, strict=True)
]

EMBIT_KEYS = [embit.ec.PrivateKey(v.prvkey) for v in DSA_VECTORS]
EMBIT_PUBKEYS = [key.get_public_key() for key in EMBIT_KEYS]
EMBIT_DSA_SIGS = [
    key.sign(v.msg, grind=False) for key, v in zip(EMBIT_KEYS, DSA_VECTORS, strict=True)
]

for (
    _v,
    _btclib_pubkey,
    _btclib_sig,
    _ecdsa_key,
    _ecdsa_sig,
    _pair,
    _digest,
    _pycoin_sig,
    _buidl_key,
    _buidl_sig,
    _bitcoinlib_pubkey,
    _bitcoinlib_sig,
    _embit_pubkey,
    _embit_sig,
) in zip(
    DSA_VECTORS,
    BTCLIB_PUBKEYS,
    BTCLIB_DSA_SIGS,
    ECDSA_KEYS,
    ECDSA_SIGS,
    PYCOIN_PAIRS,
    DIGESTS,
    PYCOIN_SIGS,
    BUIDL_KEYS,
    BUIDL_SIGS,
    BITCOINLIB_PUBKEYS,
    BITCOINLIB_SIGS,
    EMBIT_PUBKEYS,
    EMBIT_DSA_SIGS,
    strict=True,
):
    assert dsa.verify_(_v.msg, _btclib_pubkey, _btclib_sig)
    assert _ecdsa_key.verifying_key.verify_digest(
        _ecdsa_sig, _v.msg, sigdecode=ecdsa.util.sigdecode_der
    )
    assert pycoin_generator.verify(_pair, _digest, _pycoin_sig)
    assert _buidl_key.point.verify(_digest, _buidl_sig)
    assert _bitcoinlib_pubkey.verify(_v.msg, _bitcoinlib_sig)
    assert _embit_pubkey.verify(_embit_sig, _v.msg)

DSA_BTCLIB = cycle(
    [
        (v.msg, v.prvkey, pubkey, sig)
        for v, pubkey, sig in zip(
            DSA_VECTORS, BTCLIB_PUBKEYS, BTCLIB_DSA_SIGS, strict=True
        )
    ]
)
DSA_ECDSA = cycle(
    [
        (v.msg, key, sig)
        for v, key, sig in zip(DSA_VECTORS, ECDSA_KEYS, ECDSA_SIGS, strict=True)
    ]
)
DSA_PYCOIN = cycle(
    [
        (scalar, digest, pair, sig)
        for scalar, digest, pair, sig in zip(
            PYCOIN_SCALARS, DIGESTS, PYCOIN_PAIRS, PYCOIN_SIGS, strict=True
        )
    ]
)
DSA_BUIDL = cycle(
    [
        (key, digest, sig)
        for key, digest, sig in zip(BUIDL_KEYS, DIGESTS, BUIDL_SIGS, strict=True)
    ]
)
DSA_BITCOINLIB = cycle(
    [
        (v.msg, key, pubkey, sig)
        for v, key, pubkey, sig in zip(
            DSA_VECTORS,
            BITCOINLIB_KEYS,
            BITCOINLIB_PUBKEYS,
            BITCOINLIB_SIGS,
            strict=True,
        )
    ]
)
DSA_EMBIT = cycle(
    [
        (v.msg, key, pubkey, sig)
        for v, key, pubkey, sig in zip(
            DSA_VECTORS, EMBIT_KEYS, EMBIT_PUBKEYS, EMBIT_DSA_SIGS, strict=True
        )
    ]
)


def dsa_sign_btclib() -> None:
    """Time one ECDSA signature through btclib, bindings enabled.

    `grind=False`, which is not btclib's default and is what makes this row
    comparable: every other row in the table produces one signature, and
    btclib's default produces as many as it takes to find one whose r fits in
    32 bytes. `dsa_sign_btclib_grind` below times the default.
    """
    msg, prvkey, _, _ = next(DSA_BTCLIB)
    dsa.sign_(msg, prvkey, grind=False)


def dsa_sign_btclib_grind() -> None:
    """Time ECDSA signing as `pip install btclib` performs it.

    btclib grinds for a low-r signature unless told not to, so this row signs
    repeatedly until r fits in 32 bytes: an expectation of two signatures and,
    for one fixed key and message, a fixed number of them. It is here because
    it is what a caller who writes `dsa.sign_(msg, key)` gets, and a row of
    its own rather than *the* btclib row because no comparand in this table
    grinds, so per-signature it compares with nothing.
    """
    msg, prvkey, _, _ = next(DSA_BTCLIB)
    dsa.sign_(msg, prvkey)


def dsa_verify_btclib() -> None:
    """Time ECDSA verification through btclib, bindings enabled."""
    msg, _, pubkey, sig = next(DSA_BTCLIB)
    dsa.verify_(msg, pubkey, sig)


def dsa_sign_ecdsa() -> None:
    """Time ECDSA signing through the `ecdsa` PyPI package."""
    msg, key, _ = next(DSA_ECDSA)
    key.sign_digest_deterministic(
        msg, hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der
    )


def dsa_verify_ecdsa() -> None:
    """Time ECDSA verification through the `ecdsa` PyPI package."""
    msg, key, sig = next(DSA_ECDSA)
    key.verifying_key.verify_digest(sig, msg, sigdecode=ecdsa.util.sigdecode_der)


def dsa_sign_pycoin() -> None:
    """Time ECDSA signing through pycoin's Generator, backend as reported."""
    scalar, digest, _, _ = next(DSA_PYCOIN)
    pycoin_generator.sign(scalar, digest)


def dsa_verify_pycoin() -> None:
    """Time ECDSA verification through pycoin's Generator."""
    _, digest, pair, sig = next(DSA_PYCOIN)
    pycoin_generator.verify(pair, digest, sig)


def dsa_sign_buidl() -> None:
    """Time ECDSA signing through buidl's pure-Python PrivateKey."""
    key, digest, _ = next(DSA_BUIDL)
    key.sign(digest)


def dsa_verify_buidl() -> None:
    """Time ECDSA verification through buidl's pure-Python S256Point."""
    key, digest, sig = next(DSA_BUIDL)
    key.point.verify(digest, sig)


def dsa_sign_bitcoinlib() -> None:
    """Time ECDSA signing through python-bitcoinlib's CECKey, over OpenSSL."""
    msg, key, _, _ = next(DSA_BITCOINLIB)
    key.sign(msg)


def dsa_verify_bitcoinlib() -> None:
    """Time ECDSA verification through python-bitcoinlib's CPubKey."""
    msg, _, pubkey, sig = next(DSA_BITCOINLIB)
    pubkey.verify(msg, sig)


def dsa_sign_embit() -> None:
    """Time one ECDSA signature through embit's bundled library.

    `grind=False`, for the reason btclib's row passes it: embit is the other
    library here that grinds by default, and one signature is what the rest of
    the table produces.
    """
    msg, key, _, _ = next(DSA_EMBIT)
    key.sign(msg, grind=False)


def dsa_sign_embit_grind() -> None:
    """Time ECDSA signing as embit performs it by default.

    embit grinds with a counter in the extra entropy where btclib grinds by
    re-deriving its nonce: the same expectation of two signatures reached
    differently, and for one fixed key and message each lands on its own fixed
    number of them.
    """
    msg, key, _, _ = next(DSA_EMBIT)
    key.sign(msg)


def dsa_verify_embit() -> None:
    """Time ECDSA verification through embit's bundled library."""
    msg, _, pubkey, sig = next(DSA_EMBIT)
    pubkey.verify(sig, msg)


# --- BIP340 (Schnorr) sign and verify -----------------------------------

# each vector's own aux_rand rather than a random one, which makes both
# signatures below reproducible and therefore checkable against BIP340 itself.
# embit's API exposes no aux, so its own signature cannot be pinned and it is
# held to the vectors the other way, by verifying theirs
SSA_VECTORS = signing()
SSA_BTCLIB_KEYS = [(v.msg, v.prvkey, v.aux, v.sig) for v in SSA_VECTORS]
SSA_BUIDL_KEYS = [
    buidl.pecc.PrivateKey(int.from_bytes(v.prvkey, "big")) for v in SSA_VECTORS
]
SSA_BUIDL_SIGS = [
    key.sign_schnorr(v.msg, v.aux)
    for key, v in zip(SSA_BUIDL_KEYS, SSA_VECTORS, strict=True)
]
SSA_EMBIT_KEYS = [embit.ec.PrivateKey(v.prvkey) for v in SSA_VECTORS]
SSA_EMBIT_PUBKEYS = [key.get_public_key() for key in SSA_EMBIT_KEYS]
SSA_EMBIT_SIGS = [
    key.schnorr_sign(v.msg) for key, v in zip(SSA_EMBIT_KEYS, SSA_VECTORS, strict=True)
]

for _v, _buidl_key, _buidl_sig, _embit_pubkey, _embit_sig in zip(
    SSA_VECTORS,
    SSA_BUIDL_KEYS,
    SSA_BUIDL_SIGS,
    SSA_EMBIT_PUBKEYS,
    SSA_EMBIT_SIGS,
    strict=True,
):
    assert pub_keyinfo_from_prv_key(_v.prvkey)[0][1:] == _v.xonly_pubkey
    assert ssa.sign_(_v.msg, _v.prvkey, aux=_v.aux).serialize() == _v.sig
    assert _buidl_sig.serialize() == _v.sig
    assert _embit_pubkey.schnorr_verify(embit.ec.SchnorrSig.parse(_v.sig), _v.msg)
    assert ssa.verify_(_v.msg, _v.xonly_pubkey, _v.sig)
    assert _buidl_key.point.verify_schnorr(_v.msg, _buidl_sig)
    assert _embit_pubkey.schnorr_verify(_embit_sig, _v.msg)

SSA_BTCLIB = cycle(SSA_BTCLIB_KEYS)
SSA_BUIDL = cycle(
    [
        (key, v.msg, v.aux, sig)
        for key, v, sig in zip(SSA_BUIDL_KEYS, SSA_VECTORS, SSA_BUIDL_SIGS, strict=True)
    ]
)
SSA_EMBIT = cycle(
    [
        (key, pubkey, v.msg, sig)
        for key, pubkey, v, sig in zip(
            SSA_EMBIT_KEYS, SSA_EMBIT_PUBKEYS, SSA_VECTORS, SSA_EMBIT_SIGS, strict=True
        )
    ]
)


def ssa_sign_btclib() -> None:
    """Time BIP340 signing through btclib, bindings enabled."""
    msg, prvkey, aux, _ = next(SSA_BTCLIB)
    ssa.sign_(msg, prvkey, aux=aux)


def ssa_verify_btclib() -> None:
    """Time BIP340 verification through btclib, bindings enabled."""
    msg, prvkey, _, sig = next(SSA_BTCLIB)
    ssa.verify_(msg, pub_keyinfo_from_prv_key(prvkey)[0][1:], sig)


def ssa_sign_buidl() -> None:
    """Time BIP340 signing through buidl's pure-Python PrivateKey."""
    key, msg, aux, _ = next(SSA_BUIDL)
    key.sign_schnorr(msg, aux)


def ssa_verify_buidl() -> None:
    """Time BIP340 verification through buidl's pure-Python S256Point."""
    key, msg, _, sig = next(SSA_BUIDL)
    key.point.verify_schnorr(msg, sig)


def ssa_sign_embit() -> None:
    """Time BIP340 signing through embit's bundled library."""
    key, _, msg, _ = next(SSA_EMBIT)
    key.schnorr_sign(msg)


def ssa_verify_embit() -> None:
    """Time BIP340 verification through embit's bundled library."""
    _, pubkey, msg, sig = next(SSA_EMBIT)
    pubkey.schnorr_verify(sig, msg)


# --- BIP32 derivation ---------------------------------------------------

# every chain the vector file publishes, less the root: deriving `m` is no
# derivation, and a cycle mixing it in would average a step against no step.
# The four libraries spell a hardened step differently, `H` against `'`, and
# pycoin takes the steps without the leading `m`
DERIVATIONS = [chain for chain in CHAINS if chain.path != "m"]
EXPECTED_CHILDREN = [pub_keyinfo_from_key(chain.xpub)[0] for chain in DERIVATIONS]


def _btclib_child_pubkey(seed: bytes, path: str) -> bytes:
    root = btclib_bip32.rootxprv_from_seed(seed)
    return bytes(pub_keyinfo_from_key(btclib_bip32.derive(root, path))[0])


def _pycoin_child_pubkey(seed: bytes, path: str) -> bytes:
    root = pycoin.symbols.btc.network.keys.bip32_seed(seed)
    steps = path.removeprefix("m").removeprefix("/")
    return bytes(root.subkey_for_path(steps).sec())


def _embit_child_pubkey(seed: bytes, path: str) -> bytes:
    root = embit.bip32.HDKey.from_seed(seed)
    return bytes(root.derive(path.replace("H", "'")).sec())


def _buidl_child_pubkey(seed: bytes, path: str) -> bytes:
    root = buidl.hd.HDPrivateKey.from_seed(seed)
    return bytes(root.traverse(path.replace("H", "'")).pub.point.sec())


# the four against each other and all four against what BIP32 publishes for
# that path: agreeing with one another is what four implementations of the same
# mistake also do
for _chain, _expected in zip(DERIVATIONS, EXPECTED_CHILDREN, strict=True):
    assert (
        _btclib_child_pubkey(_chain.seed, _chain.path)
        == _pycoin_child_pubkey(_chain.seed, _chain.path)
        == _embit_child_pubkey(_chain.seed, _chain.path)
        == _buidl_child_pubkey(_chain.seed, _chain.path)
        == _expected
    )

BIP32 = cycle(list(zip(DERIVATIONS, EXPECTED_CHILDREN, strict=True)))


def bip32_derive_btclib() -> None:
    """Time seed-to-child BIP32 derivation through btclib, bindings enabled."""
    chain, _expected = next(BIP32)
    _btclib_child_pubkey(chain.seed, chain.path)


def bip32_derive_pycoin() -> None:
    """Time seed-to-child BIP32 derivation through pycoin's BIP32Node."""
    chain, _expected = next(BIP32)
    _pycoin_child_pubkey(chain.seed, chain.path)


def bip32_derive_embit() -> None:
    """Time seed-to-child BIP32 derivation through embit's HDKey."""
    chain, _expected = next(BIP32)
    _embit_child_pubkey(chain.seed, chain.path)


def bip32_derive_buidl() -> None:
    """Time seed-to-child BIP32 derivation through buidl's HDPrivateKey."""
    chain, _expected = next(BIP32)
    _buidl_child_pubkey(chain.seed, chain.path)


# --- base58check, bech32 and bech32m, over published addresses ---------

# BIP173's own witness-v0 test vector: a 20-byte program and the address it
# publishes for it. The same 20 bytes are the hash160 of a P2PKH address,
# which is what makes one fixture serve the base58 rows too
WITNESS_V0 = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
BECH32_ADDRESS = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
BASE58_ADDRESS = "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"
BASE58_PAYLOAD = b"\x00" + WITNESS_V0

# a witness-v1 program and its bech32m address, which is BIP350's business:
# the same string under bech32's checksum constant is a different address
# and not a valid one, and one row of five gets that wrong
WITNESS_V1 = bytes.fromhex(
    "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
)
BECH32M_ADDRESS = "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0"


def base58_encode_btclib() -> None:
    """Time btclib's base58check encoding of a P2PKH address."""
    btclib.b58.address_from_h160("p2pkh", WITNESS_V0)


def base58_encode_pycoin() -> None:
    """Time pycoin's, which takes the version byte in the payload."""
    pycoin.encoding.b58.b2a_hashed_base58(BASE58_PAYLOAD)


def base58_encode_embit() -> None:
    """Time embit's, which spells the checksum in the function name."""
    embit.base58.encode_check(BASE58_PAYLOAD)


def base58_encode_buidl() -> None:
    """Time buidl's, whose helper module carries it."""
    buidl.helper.encode_base58_checksum(BASE58_PAYLOAD)


def base58_encode_bitcoinlib() -> None:
    """Time python-bitcoinlib's, reached through the address class.

    Its `base58.encode` is base58 without the checksum, which is not the
    operation the other four perform: `P2PKHBitcoinAddress.from_bytes` is
    where the checksummed encoding lives.
    """
    str(bitcoinlib_wallet.P2PKHBitcoinAddress.from_bytes(WITNESS_V0, 0))


def base58_decode_btclib() -> None:
    """Time btclib's base58check decoding, which returns the script type too."""
    btclib.b58.h160_from_address(BASE58_ADDRESS)[1]


def base58_decode_pycoin() -> None:
    """Time pycoin's, which returns the version byte with the payload."""
    pycoin.encoding.b58.a2b_hashed_base58(BASE58_ADDRESS)


def base58_decode_embit() -> None:
    """Time embit's."""
    embit.base58.decode_check(BASE58_ADDRESS)


def base58_decode_buidl() -> None:
    """Time buidl's, which drops the version byte and returns the hash160."""
    buidl.helper.decode_base58(BASE58_ADDRESS)


def base58_decode_bitcoinlib() -> None:
    """Time python-bitcoinlib's, through the address class again."""
    bytes(bitcoinlib_wallet.CBitcoinAddress(BASE58_ADDRESS))


def bech32_encode_btclib() -> None:
    """Time btclib's bech32 encoding of a witness-v0 address."""
    btclib.b32.address_from_witness(0, WITNESS_V0)


def bech32_encode_embit() -> None:
    """Time embit's, which takes the human-readable part per call."""
    embit.bech32.encode("bc", 0, WITNESS_V0)


def bech32_encode_buidl() -> None:
    """Time buidl's, which takes a serialized witness program."""
    buidl.bech32.encode_bech32_checksum(
        b"\x00" + bytes([len(WITNESS_V0)]) + WITNESS_V0, network="mainnet"
    )


def bech32_encode_bitcoinlib() -> None:
    """Time python-bitcoinlib's, a copy of the reference implementation."""
    bitcoin.bech32.encode("bc", 0, WITNESS_V0)


def bech32_decode_btclib() -> None:
    """Time btclib's bech32 decoding, which returns the witness version too."""
    btclib.b32.witness_from_address(BECH32_ADDRESS)[1]


def bech32_decode_embit() -> None:
    """Time embit's, which returns the program as a list of integers."""
    bytes(embit.bech32.decode("bc", BECH32_ADDRESS)[1])


def bech32_decode_buidl() -> None:
    """Time buidl's, which returns the network beside the program."""
    buidl.bech32.decode_bech32(BECH32_ADDRESS)[2]


def bech32_decode_bitcoinlib() -> None:
    """Time python-bitcoinlib's."""
    bytes(bitcoin.bech32.decode("bc", BECH32_ADDRESS)[1])


def bech32m_encode_btclib() -> None:
    """Time btclib's bech32m encoding of a witness-v1 address."""
    btclib.b32.address_from_witness(1, WITNESS_V1)


def bech32m_encode_embit() -> None:
    """Time embit's, which picks the constant from the witness version."""
    embit.bech32.encode("bc", 1, WITNESS_V1)


def bech32m_encode_buidl() -> None:
    """Time buidl's, from a serialized witness-v1 program."""
    buidl.bech32.encode_bech32_checksum(
        b"\x51" + bytes([len(WITNESS_V1)]) + WITNESS_V1, network="mainnet"
    )


def bech32m_decode_btclib() -> None:
    """Time btclib's bech32m decoding."""
    btclib.b32.witness_from_address(BECH32M_ADDRESS)[1]


def bech32m_decode_embit() -> None:
    """Time embit's."""
    bytes(embit.bech32.decode("bc", BECH32M_ADDRESS)[1])


def bech32m_decode_buidl() -> None:
    """Time buidl's."""
    buidl.bech32.decode_bech32(BECH32M_ADDRESS)[2]


# python-bitcoinlib has no bech32m row in either direction, and the reason
# is not that its API lacks one: `bitcoin.bech32.encode("bc", 1, program)`
# answers, with bech32's checksum constant where BIP350 requires bech32m's,
# so what it returns for a witness-v1 program is a string no consumer should
# accept -- and `decode` returns (None, None) for the address BIP350
# publishes. A row cannot be timed against an answer this project would have
# to assert is wrong
assert bitcoin.bech32.encode("bc", 1, WITNESS_V1) != BECH32M_ADDRESS
assert bitcoin.bech32.decode("bc", BECH32M_ADDRESS) == (None, None)

# every encoding row is called once before any of them is timed, its own
# assert holding it to the published address
for _encoding_row in (
    base58_encode_btclib,
    base58_encode_pycoin,
    base58_encode_embit,
    base58_encode_buidl,
    base58_encode_bitcoinlib,
    base58_decode_btclib,
    base58_decode_pycoin,
    base58_decode_embit,
    base58_decode_buidl,
    base58_decode_bitcoinlib,
    bech32_encode_btclib,
    bech32_encode_embit,
    bech32_encode_buidl,
    bech32_encode_bitcoinlib,
    bech32_decode_btclib,
    bech32_decode_embit,
    bech32_decode_buidl,
    bech32_decode_bitcoinlib,
    bech32m_encode_btclib,
    bech32m_encode_embit,
    bech32m_encode_buidl,
    bech32m_decode_btclib,
    bech32m_decode_embit,
    bech32m_decode_buidl,
):
    _encoding_row()


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
    print(f"  {'':<26}{'μs/call':>10}{'vs best':>12}")
    for name, (value, calls) in sorted(us.items(), key=lambda row: row[1][0]):
        print(f"  {name:<26}{value:10.2f}{value / against:11.1f}x   ({calls} calls)")


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
        "base58check encode, a P2PKH address from a hash160",
        (
            (base58_encode_btclib, 200_000),
            (base58_encode_pycoin, 200_000),
            (base58_encode_embit, 200_000),
            (base58_encode_buidl, 200_000),
            (base58_encode_bitcoinlib, 100_000),
        ),
    )
    print()

    table(
        "base58check decode, a hash160 from a P2PKH address",
        (
            (base58_decode_btclib, 200_000),
            (base58_decode_pycoin, 200_000),
            (base58_decode_embit, 200_000),
            (base58_decode_buidl, 200_000),
            (base58_decode_bitcoinlib, 100_000),
        ),
    )
    print()

    table(
        "bech32 encode, a witness-v0 address from a 20-byte program",
        (
            (bech32_encode_btclib, 200_000),
            (bech32_encode_embit, 200_000),
            (bech32_encode_buidl, 100_000),
            (bech32_encode_bitcoinlib, 200_000),
        ),
    )
    print()

    table(
        "bech32 decode, a 20-byte program from a witness-v0 address",
        (
            (bech32_decode_btclib, 200_000),
            (bech32_decode_embit, 200_000),
            (bech32_decode_buidl, 100_000),
            (bech32_decode_bitcoinlib, 200_000),
        ),
    )
    print()

    table(
        "bech32m encode, a witness-v1 address from a 32-byte program",
        (
            (bech32m_encode_btclib, 200_000),
            (bech32m_encode_embit, 200_000),
            (bech32m_encode_buidl, 100_000),
        ),
    )
    print()

    table(
        "bech32m decode, a 32-byte program from a witness-v1 address",
        (
            (bech32m_decode_btclib, 200_000),
            (bech32m_decode_embit, 200_000),
            (bech32m_decode_buidl, 100_000),
        ),
    )
    print()

    table(
        "BIP32 derive, seed to child, every chain BIP32 publishes",
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
