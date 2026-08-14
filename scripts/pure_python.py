# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of every pure-Python implementation of the same operation.

Every row is Python arithmetic and the question is which is quicker at it, so
no row is a reference line and the ratio is against whichever came out
fastest. What Python costs against C is `scripts/btclib_two_paths.py`'s
question; what `pip install <package>` gives is
`scripts/bitcoin_libraries.py`'s, where the same package names mean something
else -- pycoin is C there and Python here.

## How each row is held to Python

`report_setup` prints this per row, once, above the tables.

- **btclib**: `curves.curve._libsecp256k1_available` is the switch every
  dispatch reads, so clearing it turns the delegation off everywhere at once.
  `python_arithmetic_only` below says why nothing less will do.
- **pycoin** decides at import, `pycoin.ecdsa.native.secp256k1` and
  `.openssl` reading `PYCOIN_NATIVE`. This file sets it before the import,
  after which the decision is made.
- **buidl** is imported as `buidl.pecc` rather than through `buidl.ecc`,
  which prefers the compiled `buidl.cecc` where a separate build step has
  produced one.
- **python-ecdsa** and **secp256k1lab** have nothing to turn off.

## Two packages worth a note

`secp256k1lab` is on no index: `[tool.uv.sources]` takes it from its git tag.
It declares >=3.11, which is why this project's floor is 3.11.

**hwilib** would be a row -- `hwilib.key.point_mul` is a double-and-add over
Python integers -- and `hwi` is not a dependency because of what it drags in:
it caps `cbor2` at <5.8 and `protobuf` at <5.0.0, where the advisories
against those are fixed in 5.9.0 and 5.29.6, so the row would cost standing
security alerts for as long as those ceilings hold. It also declares
`requires_python <3.13`, and `.python-version` is 3.13.

## The inputs

Every BIP340 signing vector, cycled, `_vectors` reading the file and checking
its digest. With each vector's aux_rand, BIP340 signing is deterministic, so
both implementations that do it are held to the signatures the specification
publishes. ECDSA has no such line -- RFC6979's nonce is btclib's own -- and
stays cross-checked between implementations.

A published key is worth insisting on even where the timings do not turn on
it: python-ecdsa returns the generator *object* as the public key of the
private key 1, precomputed table and all, so a row verifying against that key
verifies with a table no real key gets.

A timed function calls one implementation and discards what it returns:
nothing here is a correctness check. `tests/vectors_test.py` is, and it runs
the vendored vectors against every implementation timed here, in this
script's pure-Python configuration as well as the default one. The
assertions below run at import, where the fixtures are built, so the suite
loading this module runs them and no timing carries them.

Not part of the test suite and not run by CI, as the others are not.
"""

from __future__ import annotations

import os

# before the pycoin import below, and the reason is in the docstring:
# the native lookup runs at import time and never again
os.environ["PYCOIN_NATIVE"] = "none"

import time
from collections.abc import Callable
from hashlib import sha256
from itertools import cycle

import btclib
import buidl.pecc
import ecdsa
import pycoin.symbols.btc
import secp256k1lab.bip340
from _provenance import report
from _vectors import signing, verification
from btclib.curves import curve
from btclib.ecc import dsa, ssa
from btclib.to_pub_key import pub_keyinfo_from_prv_key
from secp256k1lab.secp256k1 import G as LAB_G


def report_provenance() -> None:
    """Say which build of each package these rows are about.

    Printed before any number: a released wheel and a working
    tree satisfy the same requirement and resolve in silence, so
    which one ran is something the output has to state rather
    than something the reader assumes.
    """
    report(
        ("btclib", btclib.__file__),
        ("secp256k1lab", secp256k1lab.bip340.__file__),
        ("ecdsa", ecdsa.__file__),
        ("pycoin", pycoin.symbols.btc.__file__),
        ("buidl", buidl.pecc.__file__),
    )


PYCOIN_GENERATOR = pycoin.symbols.btc.network.generator

# every published vector, cycled, rather than one input repeated: a row that
# calls one input a thousand times measures that input. `_vectors` reads
# BIP340's file and checks its digest, and each row below takes the next of
# what it publishes per call
SIGNING = signing()
VERIFYING = verification()

SCALARS = [int.from_bytes(v.prvkey, "big") for v in SIGNING]
PUBKEYS = [pub_keyinfo_from_prv_key(scalar)[0] for scalar in SCALARS]

# signed here, deterministically, so that every row verifies the same
# signature rather than one of its own: grind=False takes dsa.sign_'s plain
# RFC6979 nonce, and each vector's own aux_rand replaces ssa.sign_'s random
# default -- which is also what makes the BIP340 rows checkable against the
# specification
# pycoin and buidl take an ECDSA digest as an integer rather than as bytes,
# and pycoin refuses two values BIP340's messages happen to include: one at or
# above the group order, and zero. Reducing modulo the order is what every
# implementation does with a digest internally, so that keeps all of them on
# one value; the zero leaves the ECDSA cycles, the BIP340 rows keeping it
ORDER = curve.secp256k1.n
DSA_VECTORS = [v for v in SIGNING if int.from_bytes(v.msg, "big") % ORDER]
DSA_SCALARS = [int.from_bytes(v.prvkey, "big") for v in DSA_VECTORS]
DSA_SIGS = [dsa.sign_(v.msg, v.prvkey, grind=False) for v in DSA_VECTORS]
DSA_SIG_BYTES = [sig.serialize() for sig in DSA_SIGS]

# against BIP340 before anything is timed. ECDSA has no such line: RFC6979's
# nonce is btclib's own and no vendored file publishes a signature over these
# messages, so those rows stay cross-checked between implementations
for _v, _pubkey in zip(SIGNING, PUBKEYS, strict=True):
    assert _pubkey[1:] == _v.xonly_pubkey
    assert ssa.sign_(_v.msg, _v.prvkey, aux=_v.aux).serialize() == _v.sig


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    `_libsecp256k1_serves` reads `_libsecp256k1_available` on every call, so
    this one assignment reaches the nine modules that imported the predicate
    by name. Patching those modules one at a time is what leaves a row meant
    to measure Python measuring C, and it does so silently: a public key
    derived through `to_pub_key` asks `curves.sec_point`, which is the module
    such a list forgets. No row added below can reintroduce that.

    Called before anything is timed, and after every fixture above is built:
    those want the bindings, and there is no reason to slow them down.
    """
    curve._libsecp256k1_available = False


# which module a native mixin came from, and therefore which library
# `PYCOIN_NATIVE` failed to keep out. The module and not the class name,
# because the name is `Optimizations` in both of them and the fallback is
# `noop` in both of them: a probe reading names sees nothing to report
# however loudly a shared object is being called, which is what
# `bitcoin_libraries.py` was doing before it read modules instead.
PYCOIN_NATIVE_MIXINS = {
    "pycoin.ecdsa.native.secp256k1": "libsecp256k1",
    "pycoin.ecdsa.native.openssl": "OpenSSL",
}


def _pycoin_backend() -> str:
    """Return which of pycoin's three arithmetic backends this run loaded.

    `PYCOIN_NATIVE` is set above, so the answer is expected to be pure
    Python; it is read back rather than assumed, a benchmark that says
    "Python" on a row that loaded a shared object being worse than no
    benchmark. There is no public flag to read, so this reads the MRO the
    generator ended up with, as `bitcoin_libraries.py` does.
    """
    for base in type(PYCOIN_GENERATOR).__mro__:
        if "noop" in base.__qualname__:
            continue
        library = PYCOIN_NATIVE_MIXINS.get(base.__module__)
        if library is not None:
            return f"{library} -- PYCOIN_NATIVE did not take"
    return "pure Python"


def report_setup() -> None:
    """Print what holds each row to Python, having said once that all are.

    Not a version number: `report_provenance` above prints those. Not "pure
    Python" per row either -- every row in this table is, so the word
    belongs in the heading and what belongs beside each name is the thing
    that made it true, which is different for each of them and is the only
    part a reader could doubt.
    """
    print("every row is pure Python arithmetic, held to it by")
    print(
        f"  {'btclib':<20}its delegation to btclib_secp256k1's cffi bindings "
        "switched off"
    )
    print(
        f"  {'pycoin':<20}PYCOIN_NATIVE=none before its import, resolving to "
        f"{_pycoin_backend()}"
    )
    print(f"  {'buidl':<20}being imported as buidl.pecc, not buidl.ecc")
    print(f"  {'ecdsa':<20}having no compiled backend at all")
    print(f"  {'secp256k1lab':<20}having no compiled backend at all")
    print()


# --------------------------------------------------------------- pub key


def pubkey_btclib() -> None:
    """Time the generator multiplication btclib answers a public key with."""
    scalar, _expected = next(PUBKEY_BTCLIB)
    pub_keyinfo_from_prv_key(scalar)[0]


def pubkey_lab() -> None:
    """Time secp256k1lab's, which multiplies G through a table of its own."""
    scalar, _expected = next(PUBKEY_LAB)
    (scalar * LAB_G).to_bytes_compressed()


def pubkey_buidl() -> None:
    """Time buidl's pure-Python S256Point."""
    scalar, _expected = next(PUBKEY_BUIDL)
    buidl.pecc.PrivateKey(scalar).point.sec()


def pubkey_ecdsa() -> None:
    """Time python-ecdsa's."""
    scalar, _expected = next(PUBKEY_ECDSA)
    ecdsa.SigningKey.from_secret_exponent(
        scalar, curve=ecdsa.SECP256k1
    ).verifying_key.to_string("compressed")


def pubkey_pycoin() -> None:
    """Time pycoin's, its native backends turned off."""
    scalar, _expected = next(PUBKEY_PYCOIN)
    pycoin.symbols.btc.network.keys.private(secret_exponent=scalar).sec()


# ----------------------------------------------------------------- ECDSA


def dsa_sign_btclib() -> None:
    """Time one ECDSA signature through btclib.

    `grind=False`, which is not btclib's default: one signature is what every
    other row in the table produces, and the default is the row below.
    """
    msg, prvkey, _expected = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey, grind=False)


def dsa_sign_btclib_grind() -> None:
    """Time ECDSA signing as btclib performs it unless told otherwise.

    btclib grinds for a low-r signature by default: it signs until r fits in
    32 bytes, an expectation of two signatures and, for one fixed key and
    message, a fixed number of them. No other implementation in this table
    grinds, so the two rows say which question is being answered -- what one
    signature costs, and what a caller who writes `dsa.sign_(msg, key)` waits
    for.
    """
    msg, prvkey, _ = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey)


def dsa_verify_btclib() -> None:
    """Time an ECDSA verification through btclib."""
    msg, pubkey, sig = next(DSA_VERIFY_BTCLIB)
    dsa.assert_as_valid_(msg, pubkey, sig)


def dsa_sign_ecdsa() -> None:
    """Time an ECDSA signature through python-ecdsa."""
    msg, key, _ = next(DSA_ECDSA)
    key.sign_digest_deterministic(msg, hashfunc=sha256)


def dsa_verify_ecdsa() -> None:
    """Time an ECDSA verification through python-ecdsa."""
    msg, key, sig = next(DSA_ECDSA)
    key.verifying_key.verify_digest(sig, msg)


def dsa_sign_pycoin() -> None:
    """Time an ECDSA signature through pycoin's Generator."""
    scalar, digest, _, _ = next(DSA_PYCOIN)
    PYCOIN_GENERATOR.sign(scalar, digest)


def dsa_verify_pycoin() -> None:
    """Time an ECDSA verification through pycoin's Generator."""
    _, digest, pair, sig = next(DSA_PYCOIN)
    PYCOIN_GENERATOR.verify(pair, digest, sig)


def dsa_sign_buidl() -> None:
    """Time an ECDSA signature through buidl's pure-Python module."""
    key, digest, _ = next(DSA_BUIDL)
    key.sign(digest)


def dsa_verify_buidl() -> None:
    """Time an ECDSA verification through buidl's pure-Python module."""
    key, digest, sig = next(DSA_BUIDL)
    key.point.verify(digest, sig)


# ---------------------------------------------------------------- BIP340


def ssa_sign_btclib() -> None:
    """Time a BIP340 signature through btclib, over the vector's aux_rand."""
    msg, prvkey, aux, _expected = next(SSA_BTCLIB_SIGN)
    ssa.sign_(msg, prvkey, aux=aux).serialize()


def ssa_verify_btclib() -> None:
    """Time a BIP340 verification through btclib."""
    msg, xonly_pubkey, sig = next(SSA_BTCLIB_VERIFY)
    ssa.assert_as_valid_(msg, xonly_pubkey, sig)


def ssa_sign_lab() -> None:
    """Time a BIP340 signature through secp256k1lab."""
    msg, prvkey, aux, _expected = next(SSA_LAB_SIGN)
    secp256k1lab.bip340.schnorr_sign(msg, prvkey, aux)


def ssa_verify_lab() -> None:
    """Time a BIP340 verification through secp256k1lab."""
    msg, xonly_pubkey, sig = next(SSA_LAB_VERIFY)
    secp256k1lab.bip340.schnorr_verify(msg, xonly_pubkey, sig)


def ssa_sign_buidl() -> None:
    """Time a BIP340 signature through buidl's pure-Python module."""
    key, msg, aux = next(SSA_BUIDL_SIGN)
    key.sign_schnorr(msg, aux)


def ssa_verify_buidl() -> None:
    """Time a BIP340 verification through buidl's pure-Python module."""
    key, msg, sig = next(SSA_BUIDL_VERIFY)
    key.point.verify_schnorr(msg, sig)


# ------------------------------------------------------------- the timing


def benchmark(func: Callable[[], None], calls: int) -> float:
    """Return microseconds per call, `calls` calls of `func`.

    A returned number and not a printed one: every row is a ratio against
    the bindings, which is the column this script exists for, so the
    reference has to be in hand before anything is printed.

    `calls` is per function rather than shared: the slowest row here is
    four orders of magnitude off the reference, and one count for all of
    them would either sit for minutes on the slowest or measure the
    fastest against the resolution of the clock.
    """
    # perf_counter and not time(): the wall clock can step backwards
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def table(title: str, rows: tuple[tuple[str, Callable[[], None], int], ...]) -> None:
    """Time one operation's rows, then print them fastest first.

    One ratio, against whichever row came out quickest, as the other three
    benchmarks print: with every row a Python implementation of the same
    operation, the fastest of them is the only reference that is not a
    choice. Naming a row instead -- btclib's, this being btclib's benchmark
    -- would print fractions under one on the runs where another row won,
    and where btclib stands is its own place in the order.

    The order is the measurement's, which is what makes the table an answer
    rather than a list.
    """
    us = {label: benchmark(func, calls) for label, func, calls in rows}
    against = min(us.values())
    print(f"\n{title}")
    print(f"  {'':26s} {'':10s}      {'vs best':>8s}")
    for label, value in sorted(us.items(), key=lambda row: row[1]):
        print(f"  {label:26s} {value:10.2f} μs   {value / against:8.1f}x")


# the fixtures the third-party rows sign and verify, built once and
# checked against btclib's own answers below
# the fixtures each comparand signs and verifies, one per vector, built once
# and checked against btclib's answers and BIP340's below
ECDSA_KEYS = [
    ecdsa.SigningKey.from_secret_exponent(scalar, curve=ecdsa.SECP256k1)
    for scalar in DSA_SCALARS
]
ECDSA_SIGS = [
    key.sign_digest_deterministic(v.msg, hashfunc=sha256)
    for key, v in zip(ECDSA_KEYS, DSA_VECTORS, strict=True)
]
PYCOIN_DIGESTS = [int.from_bytes(v.msg, "big") % ORDER for v in DSA_VECTORS]
PYCOIN_POINTS = [PYCOIN_GENERATOR * scalar for scalar in DSA_SCALARS]
PYCOIN_PAIRS = [(point[0], point[1]) for point in PYCOIN_POINTS]
PYCOIN_SIGS = [
    PYCOIN_GENERATOR.sign(scalar, digest)
    for scalar, digest in zip(DSA_SCALARS, PYCOIN_DIGESTS, strict=True)
]
BUIDL_KEYS = [buidl.pecc.PrivateKey(scalar) for scalar in DSA_SCALARS]
BUIDL_SIGS = [
    key.sign(digest) for key, digest in zip(BUIDL_KEYS, PYCOIN_DIGESTS, strict=True)
]
BUIDL_SSA_KEYS = [buidl.pecc.PrivateKey(scalar) for scalar in SCALARS]
BUIDL_SSA_SIGS = [
    key.sign_schnorr(v.msg, v.aux)
    for key, v in zip(BUIDL_SSA_KEYS, SIGNING, strict=True)
]

# every row answers what btclib answers, and where BIP340 publishes an answer
# every row answers that: a table of numbers is worth nothing if one of the
# implementations in it is computing something else
for _v, _pubkey, _scalar in zip(SIGNING, PUBKEYS, SCALARS, strict=True):
    assert (_scalar * LAB_G).to_bytes_compressed() == _pubkey
    assert buidl.pecc.PrivateKey(_scalar).point.sec() == _pubkey
    assert (
        ecdsa.SigningKey.from_secret_exponent(
            _scalar, curve=ecdsa.SECP256k1
        ).verifying_key.to_string("compressed")
        == _pubkey
    )
    assert (
        pycoin.symbols.btc.network.keys.private(secret_exponent=_scalar).sec()
        == _pubkey
    )
    assert secp256k1lab.bip340.schnorr_sign(_v.msg, _v.prvkey, _v.aux) == _v.sig
    assert secp256k1lab.bip340.schnorr_verify(_v.msg, _v.xonly_pubkey, _v.sig)

for _key, _v, _ssa_sig in zip(BUIDL_SSA_KEYS, SIGNING, BUIDL_SSA_SIGS, strict=True):
    assert _ssa_sig.serialize() == _v.sig
    assert _key.point.verify_schnorr(_v.msg, _ssa_sig)

for (
    _v,
    _dsa_sig,
    _ecdsa_key,
    _ecdsa_sig,
    _pair,
    _digest,
    _pycoin_sig,
    _buidl_key,
    _buidl_sig,
) in zip(
    DSA_VECTORS,
    DSA_SIG_BYTES,
    ECDSA_KEYS,
    ECDSA_SIGS,
    PYCOIN_PAIRS,
    PYCOIN_DIGESTS,
    PYCOIN_SIGS,
    BUIDL_KEYS,
    BUIDL_SIGS,
    strict=True,
):
    assert dsa.verify_(_v.msg, pub_keyinfo_from_prv_key(_v.prvkey)[0], _dsa_sig)
    assert _ecdsa_key.verifying_key.verify_digest(_ecdsa_sig, _v.msg)
    assert PYCOIN_GENERATOR.verify(_pair, _digest, _pycoin_sig)
    assert _buidl_key.point.verify(_digest, _buidl_sig)

# one cycle per row
PUBKEY_BTCLIB = cycle(list(zip(SCALARS, PUBKEYS, strict=True)))
PUBKEY_LAB = cycle(list(zip(SCALARS, PUBKEYS, strict=True)))
PUBKEY_ECDSA = cycle(list(zip(SCALARS, PUBKEYS, strict=True)))
PUBKEY_PYCOIN = cycle(list(zip(SCALARS, PUBKEYS, strict=True)))
PUBKEY_BUIDL = cycle(list(zip(SCALARS, PUBKEYS, strict=True)))
DSA_SIGN_BTCLIB = cycle(
    [(v.msg, v.prvkey, sig) for v, sig in zip(DSA_VECTORS, DSA_SIGS, strict=True)]
)
DSA_VERIFY_BTCLIB = cycle(
    [
        (v.msg, pub_keyinfo_from_prv_key(v.prvkey)[0], sig)
        for v, sig in zip(DSA_VECTORS, DSA_SIG_BYTES, strict=True)
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
            DSA_SCALARS, PYCOIN_DIGESTS, PYCOIN_PAIRS, PYCOIN_SIGS, strict=True
        )
    ]
)
DSA_BUIDL = cycle(
    [
        (key, digest, sig)
        for key, digest, sig in zip(BUIDL_KEYS, PYCOIN_DIGESTS, BUIDL_SIGS, strict=True)
    ]
)
SSA_BTCLIB_SIGN = cycle([(v.msg, v.prvkey, v.aux, v.sig) for v in SIGNING])
SSA_BTCLIB_VERIFY = cycle([(v.msg, v.xonly_pubkey, v.sig) for v in VERIFYING])
SSA_LAB_SIGN = cycle([(v.msg, v.prvkey, v.aux, v.sig) for v in SIGNING])
SSA_LAB_VERIFY = cycle([(v.msg, v.xonly_pubkey, v.sig) for v in VERIFYING])
SSA_BUIDL_SIGN = cycle(
    [(key, v.msg, v.aux) for key, v in zip(BUIDL_SSA_KEYS, SIGNING, strict=True)]
)
SSA_BUIDL_VERIFY = cycle(
    [
        (key, v.msg, sig)
        for key, v, sig in zip(BUIDL_SSA_KEYS, SIGNING, BUIDL_SSA_SIGS, strict=True)
    ]
)


def main() -> None:
    """Throw the switch, then print a table per operation.

    `python_arithmetic_only` comes first and nothing here is timed before
    it: with no reference row left to measure through the bindings, the one
    ordering this script needs is that the switch precede every timing.
    """
    report_provenance()
    report_setup()
    python_arithmetic_only()

    table(
        "public key from a private key: a multiplication of the generator",
        (
            ("btclib", pubkey_btclib, 200),
            ("secp256k1lab", pubkey_lab, 100),
            ("python-ecdsa", pubkey_ecdsa, 200),
            ("pycoin", pubkey_pycoin, 20),
            ("buidl.pecc", pubkey_buidl, 10),
        ),
    )

    table(
        "ECDSA sign, over a 32-byte digest",
        (
            ("btclib, one signature", dsa_sign_btclib, 50),
            ("btclib, grinding (default)", dsa_sign_btclib_grind, 20),
            ("python-ecdsa", dsa_sign_ecdsa, 100),
            ("pycoin", dsa_sign_pycoin, 20),
            ("buidl.pecc", dsa_sign_buidl, 10),
        ),
    )

    table(
        "ECDSA verify, over a 32-byte digest",
        (
            ("btclib", dsa_verify_btclib, 50),
            ("python-ecdsa", dsa_verify_ecdsa, 50),
            ("pycoin", dsa_verify_pycoin, 10),
            ("buidl.pecc", dsa_verify_buidl, 10),
        ),
    )

    table(
        "BIP340 sign, over a 32-byte message",
        (
            ("btclib", ssa_sign_btclib, 50),
            ("secp256k1lab", ssa_sign_lab, 50),
            ("buidl.pecc", ssa_sign_buidl, 5),
        ),
    )

    table(
        "BIP340 verify, over a 32-byte message",
        (
            ("btclib", ssa_verify_btclib, 50),
            ("secp256k1lab", ssa_verify_lab, 50),
            ("buidl.pecc", ssa_verify_buidl, 10),
        ),
    )


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
