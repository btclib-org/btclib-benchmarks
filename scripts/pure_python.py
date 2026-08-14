# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of every pure-Python implementation of the same operation.

Every row here is Python arithmetic, and the question is which of them is
quicker at it. Nothing in this table is C, so no row is a reference line
and the ratio column is against whichever row came out fastest, as it is
in the other three benchmarks. What Python costs against C is the question
`scripts/btclib_two_paths.py` answers, over btclib's own two paths, and
what `pip install <package>` gives is what `scripts/bitcoin_libraries.py`
answers -- where the same package names appear and mean something else,
pycoin being C there and Python here.

## How each row is held to Python, and how that was checked

- **btclib**: `curves.curve._libsecp256k1_available` is the switch every
  dispatch reads, so clearing it turns the delegation off for every
  module at once, which is what `python_arithmetic_only` below does and
  says why nothing less than the switch will do.
- **pycoin** decides at import: `pycoin.ecdsa.native.secp256k1` and
  `.openssl` each read `PYCOIN_NATIVE` and return their no-op unless it
  names them. `os.environ` is set at the top of this file, before the
  import, because after it the decision is already made.
- **buidl** is imported as `buidl.pecc`, its pure-Python module, rather
  than through `buidl.ecc`, which prefers the compiled `buidl.cecc`
  when a separate build step has produced one.
- **python-ecdsa** and **secp256k1lab** have nothing to turn off: neither
  ships or loads a native backend at all.

`report_setup` prints what each row resolved to, because nothing here
should claim a Python number without checking that it is one. It says it
once, in a block above the tables: with every row Python, a row saying so
is a column of the same word.

## secp256k1lab's marker

It is on no index at all: `[tool.uv.sources]` takes it from its git tag.
It declares >=3.11, which is this project's floor as well -- that is why
the floor is what it is -- so this script imports it unguarded.

## The row that is not here

**hwilib** would be one: `hwilib.key.point_mul` is a double-and-add over
Python integers, with nothing to turn off, and it would be the slowest
public key in the table. `hwi` is not a dependency here because of what it
drags in: it caps `cbor2` at <5.8 and `protobuf` at <5.0.0, where the
advisories against those two are fixed in 5.9.0 and 5.29.6, so the row
costs three standing security alerts, two of them high, for as long as
those ceilings hold. It is also a row nobody here would see: `hwi`
declares `requires_python <3.13`, and `.python-version` is 3.13.

## The inputs are a published test vector

The fixtures are BIP340 test vector 1, transcribed from btclib's vendored
copy. What it buys is mostly the checks: with the vector's aux_rand, BIP340
signing is deterministic, so both implementations that do it are held to
the signature the specification publishes rather than to btclib's answer.
ECDSA has no such line here, RFC6979's nonce being btclib's own, and stays
cross-checked between implementations.

A published key matters to one comparand more than to the rest, which is
why it is worth insisting on even where the timings do not care:
python-ecdsa returns the generator *object* for the public key of the
private key 1, precomputed table and all, so a row verifying against that
key verifies with a table no real key gets, at about half the cost of
verification. A vector's key cannot do that to a row by accident.

Not part of the test suite and not run by CI, as the other two are not:
nothing here is a correctness check, though every row is checked before it
is timed -- against btclib's answer, and against BIP340's where there is
one.
"""

from __future__ import annotations

import os

# before the pycoin import below, and the reason is in the docstring:
# the native lookup runs at import time and never again
os.environ["PYCOIN_NATIVE"] = "none"

import time
from collections.abc import Callable
from hashlib import sha256

import btclib
import buidl.pecc
import ecdsa
import pycoin.symbols.btc
import secp256k1lab.bip340
from _provenance import report
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

# BIP340 test vector 1, transcribed from btclib's vendored copy of it,
# `tests/ecc/_data/bip340_test_vectors.csv`, whose own
# `tests/_data/README.md` pins that file to a commit of bitcoin/bips and
# compares the bytes. The key this file used to carry was a published one
# too -- RFC6979's secp256k1 example, paired with "Satoshi Nakamoto" -- and
# the reason for the change is the aux_rand: BIP340 signing is
# deterministic given it, so with the vector's aux every implementation
# below can be held to the signature the specification publishes instead of
# to btclib's answer, and a mistake btclib shares with a comparand stops
# being invisible.
PRVKEY = 0xB7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF
PRVKEY_BYTES = PRVKEY.to_bytes(32, "big")
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

# signed while the bindings are still the default and deterministically,
# so that every row below verifies the same signature rather than one of
# its own: grind=False takes dsa.sign_'s plain RFC6979 nonce with no
# low-r search, and the vector's aux replaces ssa.sign_'s random default
DSA_SIG = dsa.sign_(MSG_HASH, PRVKEY, grind=False)
DSA_SIG_BYTES = DSA_SIG.serialize()
SSA_SIG = ssa.sign_(MSG_HASH, PRVKEY, aux=AUX)
SSA_SIG_BYTES = SSA_SIG.serialize()
PUBKEY = pub_keyinfo_from_prv_key(PRVKEY)[0]
XONLY_PUBKEY = PUBKEY[1:]

# against BIP340 before anything is timed, where the block further down
# checks the comparands against btclib. The ECDSA fixtures have no such
# line: RFC6979's nonce is btclib's own and no vector here publishes a
# signature over this message, so those stay cross-checked between
# implementations
assert XONLY_PUBKEY == VECTOR_XONLY_PUBKEY
assert SSA_SIG_BYTES == VECTOR_SSA_SIG


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
    pub_keyinfo_from_prv_key(PRVKEY)


def pubkey_lab() -> None:
    """Time secp256k1lab's, which multiplies G through a table of its own."""
    (PRVKEY * LAB_G).to_bytes_compressed()


def pubkey_buidl() -> None:
    """Time buidl's pure-Python S256Point."""
    buidl.pecc.PrivateKey(PRVKEY).point.sec()


def pubkey_ecdsa() -> None:
    """Time python-ecdsa's."""
    ecdsa.SigningKey.from_secret_exponent(
        PRVKEY, curve=ecdsa.SECP256k1
    ).verifying_key.to_string("compressed")


def pubkey_pycoin() -> None:
    """Time pycoin's, its native backends turned off."""
    pycoin.symbols.btc.network.keys.private(secret_exponent=PRVKEY).sec()


# ----------------------------------------------------------------- ECDSA


def dsa_sign_btclib() -> None:
    """Time one ECDSA signature through btclib.

    `grind=False`, which is not btclib's default: one signature is what
    every other row in the table produces, and the default is the row
    below.
    """
    dsa.sign_(MSG_HASH, PRVKEY, grind=False)


def dsa_sign_btclib_grind() -> None:
    """Time ECDSA signing as btclib performs it unless told otherwise.

    btclib grinds for a low-r signature by default: it signs until r fits
    in 32 bytes, an expectation of two signatures and, for one fixed key
    and message, a fixed number of them. No other implementation in this
    table grinds, so the two rows say which question is being answered --
    what one signature costs, and what a caller who writes
    `dsa.sign_(msg, key)` waits for.

    The pair is one switch thrown both ways, and the labels say so rather
    than leaving `btclib` to name the setting btclib does not use. It is
    worth the two rows because this is the only place in the whole file
    where another implementation's number comes out smaller than a
    btclib number, and reading that as btclib being slower would be
    reading a row against the wrong operation: what is on the other side
    of it is one signature, not this one made faster.
    """
    dsa.sign_(MSG_HASH, PRVKEY)


def dsa_verify_btclib() -> None:
    """Time an ECDSA verification through btclib."""
    dsa.assert_as_valid_(MSG_HASH, PUBKEY, DSA_SIG)


def dsa_sign_ecdsa() -> None:
    """Time an ECDSA signature through python-ecdsa."""
    ECDSA_SIGNING_KEY.sign_digest_deterministic(MSG_HASH, hashfunc=sha256)


def dsa_verify_ecdsa() -> None:
    """Time an ECDSA verification through python-ecdsa."""
    ECDSA_VERIFYING_KEY.verify_digest(ECDSA_SIG, MSG_HASH)


def dsa_sign_pycoin() -> None:
    """Time an ECDSA signature through pycoin's Generator."""
    PYCOIN_GENERATOR.sign(PRVKEY, PYCOIN_DIGEST)


def dsa_verify_pycoin() -> None:
    """Time an ECDSA verification through pycoin's Generator."""
    PYCOIN_GENERATOR.verify(PYCOIN_PUBLIC_PAIR, PYCOIN_DIGEST, PYCOIN_SIG)


def dsa_sign_buidl() -> None:
    """Time an ECDSA signature through buidl's pure-Python module."""
    BUIDL_KEY.sign(BUIDL_DIGEST)


def dsa_verify_buidl() -> None:
    """Time an ECDSA verification through buidl's pure-Python module."""
    BUIDL_KEY.point.verify(BUIDL_DIGEST, BUIDL_SIG)


# ---------------------------------------------------------------- BIP340


def ssa_sign_btclib() -> None:
    """Time a BIP340 signature through btclib."""
    ssa.sign_(MSG_HASH, PRVKEY, aux=AUX)


def ssa_verify_btclib() -> None:
    """Time a BIP340 verification through btclib."""
    ssa.assert_as_valid_(MSG_HASH, XONLY_PUBKEY, SSA_SIG)


def ssa_sign_lab() -> None:
    """Time a BIP340 signature through secp256k1lab."""
    secp256k1lab.bip340.schnorr_sign(MSG_HASH, PRVKEY_BYTES, AUX)


def ssa_verify_lab() -> None:
    """Time a BIP340 verification through secp256k1lab."""
    secp256k1lab.bip340.schnorr_verify(MSG_HASH, XONLY_PUBKEY, SSA_SIG_BYTES)


def ssa_sign_buidl() -> None:
    """Time a BIP340 signature through buidl's pure-Python module."""
    BUIDL_KEY.sign_schnorr(MSG_HASH, AUX)


def ssa_verify_buidl() -> None:
    """Time a BIP340 verification through buidl's pure-Python module."""
    BUIDL_KEY.point.verify_schnorr(MSG_HASH, BUIDL_SSA_SIG)


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
ECDSA_SIGNING_KEY = ecdsa.SigningKey.from_secret_exponent(PRVKEY, curve=ecdsa.SECP256k1)
ECDSA_VERIFYING_KEY = ECDSA_SIGNING_KEY.verifying_key
ECDSA_SIG = ECDSA_SIGNING_KEY.sign_digest_deterministic(MSG_HASH, hashfunc=sha256)
PYCOIN_DIGEST = int.from_bytes(MSG_HASH, "big")
PYCOIN_POINT = PYCOIN_GENERATOR * PRVKEY
PYCOIN_PUBLIC_PAIR = (PYCOIN_POINT[0], PYCOIN_POINT[1])
PYCOIN_SIG = PYCOIN_GENERATOR.sign(PRVKEY, PYCOIN_DIGEST)
BUIDL_KEY = buidl.pecc.PrivateKey(PRVKEY)
BUIDL_DIGEST = int.from_bytes(MSG_HASH, "big")
BUIDL_SIG = BUIDL_KEY.sign(BUIDL_DIGEST)
BUIDL_SSA_SIG = BUIDL_KEY.sign_schnorr(MSG_HASH, AUX)

# every row answers what btclib answers, before any of them is timed: a
# table of numbers is worth nothing if one of the implementations in it
# is computing something else
assert (PRVKEY * LAB_G).to_bytes_compressed() == PUBKEY
assert buidl.pecc.PrivateKey(PRVKEY).point.sec() == PUBKEY
assert ECDSA_VERIFYING_KEY.to_string("compressed") == PUBKEY
assert pycoin.symbols.btc.network.keys.private(secret_exponent=PRVKEY).sec() == PUBKEY
# both BIP340 implementations against the vector's signature, which is
# also btclib's: with the vector's aux_rand these are the same assertion
# made twice, and it is worth making twice, one half of it being the
# comparand and the other the specification
assert secp256k1lab.bip340.schnorr_sign(MSG_HASH, PRVKEY_BYTES, AUX) == VECTOR_SSA_SIG
assert secp256k1lab.bip340.schnorr_verify(MSG_HASH, XONLY_PUBKEY, VECTOR_SSA_SIG)
assert BUIDL_SSA_SIG.serialize() == VECTOR_SSA_SIG
assert BUIDL_KEY.point.verify_schnorr(MSG_HASH, BUIDL_SSA_SIG)
assert ECDSA_VERIFYING_KEY.verify_digest(ECDSA_SIG, MSG_HASH)
assert PYCOIN_GENERATOR.verify(PYCOIN_PUBLIC_PAIR, PYCOIN_DIGEST, PYCOIN_SIG)
assert BUIDL_KEY.point.verify(BUIDL_DIGEST, BUIDL_SIG)

# the reference column, every one of it taken before the dispatch goes
# off: these are the numbers a consumer gets from `pip install btclib`


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    `_libsecp256k1_serves` reads `_libsecp256k1_available` on every call,
    so this one assignment reaches the nine modules that imported the
    predicate by name. Patching those modules one at a time is what
    leaves a row meant to measure Python measuring C, and it does so
    silently: a public key derived through `to_pub_key` asks
    `curves.sec_point`, which is the module such a list forgets, and the
    row comes back at the reference's own microseconds. No row added
    below can reintroduce that.

    Called after the reference above and after every fixture is signed,
    both of which want the bindings.
    """
    curve._libsecp256k1_available = False


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
