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

`provenance` says this per row, in the column beside the version:
every row here is Python, so the word belongs in the heading and what belongs
beside each name is whatever made it true, which is different for each of them
and is the only part a reader could doubt.

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

## What a run leaves behind

The numbers are written to `results/pure-python.json` as this finishes,
and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import os

# before the pycoin import below, and the reason is in the docstring:
# the native lookup runs at import time and never again
os.environ["PYCOIN_NATIVE"] = "none"

import sys
import time
from collections.abc import Callable
from hashlib import sha256
from importlib.metadata import version
from itertools import cycle

import buidl.pecc
import ecdsa
import pycoin.symbols.btc
import secp256k1lab.bip340
from _provenance import WHAT_A_TIMING_CONTAINS, origin_of
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
from btclib.curves import curve
from btclib.ecc import dsa, ssa
from btclib.to_pub_key import pub_keyinfo_from_prv_key
from secp256k1lab.secp256k1 import G as LAB_G

# the release each version was published on, recorded because no installed
# metadata carries it: a wheel's METADATA has a Version and no date, and the
# dist-info directory's mtime is when the package was installed here. Keyed
# by the release it was read for, so an upgraded comparand prints
# `unrecorded` rather than a date that has stopped being true.
# secp256k1lab is on no index and is taken from a git tag, which is still a
# release someone cut on a day, so it is recorded like the other four
RELEASE_DATES = {
    "secp256k1lab": ("1.0.0", "2025-03-26"),
    "ecdsa": ("0.19.2", "2026-03-26"),
    "pycoin": ("0.92718.20260405", "2026-04-05"),
    "buidl": ("0.2.36", "2022-02-28"),
}


def _released(dist_name: str) -> str:
    """Say when this build was published, or where it came from instead.

    btclib resolves from its branch until 2026.9 is on PyPI, and a date would
    be a claim about a release that has not happened: what the column says for
    it is the branch and the commit, which is what a reader has to look up to
    get these rows again. `scripts/bitcoin_libraries.py` prints the same
    column by the same rule, over an overlapping set of packages.
    """
    if not (recorded := RELEASE_DATES.get(dist_name)):
        # the branch and the commit, without the repository the package
        # column has already named
        return origin_of(dist_name).split()[-1]
    return recorded[1] if version(dist_name) == recorded[0] else "unrecorded"


def provenance() -> Provenance:
    """Return one row per package: the build, and what holds it to Python.

    Above every number, because a released wheel and a working tree satisfy
    the same requirement and resolve in silence. Not "pure Python" per row:
    every row in these tables is, so the last column carries the mechanism
    instead, which is the only part of the claim a reader could doubt.
    pycoin's cell is read back rather than written down, a benchmark that
    says Python on a row that loaded a shared object being worse than no
    benchmark. Sorted newest release first.
    """
    rows = (
        ("btclib", "its delegation to btclib-secp256k1's cffi bindings switched off"),
        (
            "pycoin",
            f"PYCOIN_NATIVE=none before its import, resolving to {_pycoin_backend()}",
        ),
        ("buidl", "being imported as buidl.pecc, not buidl.ecc"),
        ("ecdsa", "having no compiled backend at all"),
        ("secp256k1lab", "having no compiled backend at all"),
    )
    return Provenance(
        columns=["package", "version", "released", "held to Python by"],
        rows=[
            [dist_name, version(dist_name), _released(dist_name), mechanism]
            for dist_name, mechanism in sorted(
                rows, key=lambda row: _released(row[0]), reverse=True
            )
        ],
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


Rows = tuple[tuple[str, Callable[[], None], int], ...]


def measured(title: str, rows: Rows) -> Ratios:
    """Time one operation's rows and return them as a table.

    The sort and the ratio are the renderer's: one ratio, against whichever
    row came out quickest, as the other three benchmarks print it. With
    every row a Python implementation of the same operation, the fastest of
    them is the only reference that is not a choice -- naming a row instead,
    btclib's, this being btclib's benchmark, would print fractions under one
    on the runs where another row won, and where btclib stands is its own
    place in the order.
    """
    return Ratios(
        title=title,
        rows=[
            Timing(label=label, us_per_call=benchmark(func, calls))
            for label, func, calls in rows
        ],
    )


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


# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page, which is a fact about all five
# tables and cannot be known while the first is being measured
TABLES: tuple[tuple[str, Rows], ...] = (
    (
        "public key from a private key: a multiplication of the generator",
        (
            ("btclib", pubkey_btclib, 200),
            ("secp256k1lab", pubkey_lab, 100),
            ("python-ecdsa", pubkey_ecdsa, 200),
            ("pycoin", pubkey_pycoin, 20),
            ("buidl.pecc", pubkey_buidl, 10),
        ),
    ),
    (
        "ECDSA sign, over a 32-byte digest",
        (
            ("btclib, one signature", dsa_sign_btclib, 50),
            ("btclib, grinding (default)", dsa_sign_btclib_grind, 20),
            ("python-ecdsa", dsa_sign_ecdsa, 100),
            ("pycoin", dsa_sign_pycoin, 20),
            ("buidl.pecc", dsa_sign_buidl, 10),
        ),
    ),
    (
        "ECDSA verify, over a 32-byte digest",
        (
            ("btclib", dsa_verify_btclib, 50),
            ("python-ecdsa", dsa_verify_ecdsa, 50),
            ("pycoin", dsa_verify_pycoin, 10),
            ("buidl.pecc", dsa_verify_buidl, 10),
        ),
    ),
    (
        "BIP340 sign, over a 32-byte message",
        (
            ("btclib", ssa_sign_btclib, 50),
            ("secp256k1lab", ssa_sign_lab, 50),
            ("buidl.pecc", ssa_sign_buidl, 5),
        ),
    ),
    (
        "BIP340 verify, over a 32-byte message",
        (
            ("btclib", ssa_verify_btclib, 50),
            ("secp256k1lab", ssa_verify_lab, 50),
            ("buidl.pecc", ssa_verify_buidl, 10),
        ),
    ),
)

# what the run block claims about how these numbers were taken. Every row
# here is timed once: the counts are small, these being the slowest rows
# this project prints, and three rounds of the slowest would be a run
# nobody waits for
METHOD = "one run, kept whole \N{EM DASH} nothing repeated, no outlier discarded"


def main() -> None:
    """Throw the switch, print a table per operation, and save the run.

    `python_arithmetic_only` comes first and nothing here is timed before
    it: with no reference row left to measure through the bindings, the one
    ordering this script needs is that the switch precede every timing.

    Each table is printed as it is measured, this being a run somebody
    watches, and printed through the same renderer that writes the page --
    so the terminal is not a preview of the published block, it is that
    block.
    """
    packages = provenance()
    print(rendered_provenance(packages))
    print()
    print("\n".join(WHAT_A_TIMING_CONTAINS))
    print()

    python_arithmetic_only()

    width = width_for([label for _, rows in TABLES for label, _, _ in rows])
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
