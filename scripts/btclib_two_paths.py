# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib's own two arithmetic paths, side by side.

btclib delegates secp256k1 work to the btclib_secp256k1 bindings and
falls back to the pure Python arithmetic of curves/curve_group.py for
every other curve, a zero scalar, the point at infinity, and everything
else the bindings decline. This times both paths through every operation
that has them.

Which operations those are is not a judgement call: `_libsecp256k1_serves`
is the predicate every dispatch site asks, and the modules holding one are
`curves/sec_point.py`, `curves/curve.py`, `ecc/dsa.py`, `ecc/ssa.py`,
`ecc/dh.py`, `ecc/bms.py`, `ecc/ellswift.py`, `ecc/commit_nonce.py`,
`ecc/pedersen.py` and `script/taproot.py`. The rows below cover the ones
reachable through a public function a caller would call, one row each.
BIP32 derivation is here for the opposite reason -- it asks for no
dispatch of its own and gets one anyway, deriving through
`curves.sec_point`, which is exactly the sort of row that made naming
modules by hand untenable. `commit_nonce` and `pedersen` have no row:
anti-exfil signing and Pedersen commitments are protocol machinery rather
than operations an application performs, and a table has to end somewhere.

The point is not a number to quote: the two paths answer the same
equations, one in C and one in Python, and what this shows is an order of
magnitude. Nothing here repeats a measurement or discards an outlier.

## Both halves of every pair are one function, timed twice

There is no `mult_bindings` beside a `mult_python` with the same body any
more. `python_arithmetic_only` is process-wide, so which path a call takes
is a property of *when* it runs, not of which function was called: one
function per operation, timed before the switch and again after, is what
that actually is. The two labels the table prints are made from the
operation's name -- `_bindings` and `_pure_python`, spelled out, because
"python" alone was the row of a table whose every row is Python-invoked.

## The inputs are published test vectors, not values chosen here

The fixtures are BIP340 test vector 1 and BIP32 test vector 1, read from
btclib's own vendored copies (`tests/ecc/_data/bip340_test_vectors.csv`
and `tests/bip32/_data/bip32_test_vectors.json`, whose
`tests/_data/README.md` pins each to a commit of bitcoin/bips and compares
the bytes). The values are transcribed rather than the files copied: this
script times one input per row, and vendoring sixty CSV rows to use one of
them would be a file nobody reads.

That buys the assertions, not the timings. Timings first: a key is a key,
and three different valid keys through the bindings measure the same to
within the noise of the machine -- so no number here would move if the
fixture went back to being arbitrary. What moves is what a failure can
catch. The public key, the BIP340 signature and the BIP32 xprv below are
checked against what the specification publishes, so btclib agreeing with
itself is no longer the whole of the check; and the one fixture that
cannot come from a vector, ECDSA's nonce being btclib's own RFC6979, is
still cross-checked between the paths.

A key of 1 is what this file used to sign with, and it is the reason to
prefer a vector even where the timings do not care: deriving a public key
from 1 costs a pure-Python implementation a single bit of ladder --
measured at hundreds of times less than a real scalar -- so the one row
this script would have added next would have been silently wrong.

Not part of the test suite and not run by CI: nothing here is a
correctness check of btclib, and `tests/script_engine/python_path_test.py`
in btclib already is one, over the vendored consensus vectors. No
third-party dependency either -- btclib_secp256k1 is already a dependency
of btclib itself.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import btclib
import btclib_secp256k1
from _provenance import report
from btclib import b58
from btclib.bip32 import bip32
from btclib.curves import curve, sec_point
from btclib.ecc import bms, dh, dsa, ellswift, ssa
from btclib.script import taproot
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def report_provenance() -> None:
    """Say which build of each package these rows are about.

    Printed before any number: a released wheel and a working
    tree satisfy the same requirement and resolve in silence, so
    which one ran is something the output has to state rather
    than something the reader assumes.
    """
    report(("btclib", btclib.__file__), ("btclib-secp256k1", btclib_secp256k1.__file__))


# BIP340 test vector 1: secret key, aux_rand and message, with the public
# key and signature it publishes asserted below rather than trusted
PRVKEY = 0xB7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF
MSG = bytes.fromhex("243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89")
AUX = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
VECTOR_XONLY_PUBKEY = bytes.fromhex(
    "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"
)
VECTOR_SSA_SIG = bytes.fromhex(
    "6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE3341"
    "8906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"
)

# BIP340 test vector 2's secret key, which the Diffie-Hellman row needs a
# counterparty for. Its own vector rows are not used: what is wanted here
# is a second published key, not a second signature
COUNTERPARTY_PRVKEY = 0xC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9

# BIP32 test vector 1: the seed, one hardened step and one normal one, and
# the extended private key the vector publishes for that path
SEED = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
BIP32_PATH = "m/0h/1"
VECTOR_BIP32_XPRV = (
    "xprv9wTYmMFdV23N2TdNG573QoEsfRrWKQgWeibmLntzniatZvR9BmLnvSxqu53Kw"
    "1UmYPxLgboyZQaXwTCg8MSY3H2EU4pWcQDnRnrVA1xe8fs"
)

# the message the bitcoin-message rows sign, which is text rather than a
# digest: `bms` hashes it itself, and no vector publishes a signature over
# one, RFC6979's nonce being btclib's own
BMS_MSG = b"Satoshi Nakamoto"

# every fixture is built while the bindings are still the default, and
# deterministically where the API allows it: grind=False takes dsa.sign_'s
# plain RFC6979 nonce with no low-r search, and the vector's aux replaces
# ssa.sign_'s random default, so the pure Python path is checked against
# the very same signature rather than a fresh, unrelated one
PUBKEY = pub_keyinfo_from_prv_key(PRVKEY)[0]
XONLY_PUBKEY = PUBKEY[1:]
POINT = sec_point.point_from_octets(PUBKEY)
DSA_SIG = dsa.sign_(MSG, PRVKEY, grind=False)
SSA_SIG = ssa.sign_(MSG, PRVKEY, aux=AUX)
ADDRESS = b58.p2pkh(PUBKEY)
BMS_SIG = bms.sign(BMS_MSG, PRVKEY)
COUNTERPARTY_POINT = sec_point.point_from_octets(
    pub_keyinfo_from_prv_key(COUNTERPARTY_PRVKEY)[0]
)
DH_SECRET = dh.diffie_hellman(PRVKEY, COUNTERPARTY_POINT, 32)
TAPROOT_PUBKEY = taproot.output_pubkey(PUBKEY)[0]
# ElligatorSwift encoding draws a random field element, so the encoded
# form is a fixture and never a row: what is deterministic, and what the
# dispatch is on, is decoding one
ELL = ellswift.encode_var(PUBKEY)

# what the specification says, checked before anything is timed. Three of
# the four fixtures above are published values, so this is btclib against
# BIP340 and BIP32 rather than btclib against itself -- a shared mistake
# between the two paths could survive the cross-path checks in the rows
# below, and cannot survive these
assert XONLY_PUBKEY == VECTOR_XONLY_PUBKEY
assert SSA_SIG.serialize() == VECTOR_SSA_SIG
assert ssa.verify_(MSG, VECTOR_XONLY_PUBKEY, VECTOR_SSA_SIG)
assert bip32.derive(bip32.rootxprv_from_seed(SEED), BIP32_PATH) == VECTOR_BIP32_XPRV


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
    assert pub_keyinfo_from_prv_key(PRVKEY)[0] == PUBKEY


def point_parse() -> None:
    """Time parsing a compressed public key, which recovers y from x."""
    assert sec_point.point_from_octets(PUBKEY) == POINT


def mult() -> None:
    """Time the generator multiplication every key derivation is built on."""
    assert curve.mult(PRVKEY) == POINT


def dsa_sign() -> None:
    """Time ECDSA signing, RFC6979's nonce and no low-r grinding."""
    assert dsa.sign_(MSG, PRVKEY, grind=False) == DSA_SIG


def dsa_verify() -> None:
    """Time ECDSA verification."""
    assert dsa.verify_(MSG, PUBKEY, DSA_SIG)


def dsa_recover() -> None:
    """Time recovering the candidate public keys of an ECDSA signature."""
    assert POINT in dsa.recover_pub_keys_(MSG, DSA_SIG)


def ssa_sign() -> None:
    """Time BIP340 signing, over the vector's aux_rand."""
    assert ssa.sign_(MSG, PRVKEY, aux=AUX) == SSA_SIG


def ssa_verify() -> None:
    """Time BIP340 verification."""
    assert ssa.verify_(MSG, XONLY_PUBKEY, SSA_SIG)


def bip32_derive() -> None:
    """Time BIP32 derivation, seed to child, one hardened step and one not.

    No dispatch of its own: it reaches the bindings through
    `curves.sec_point` deriving each child's public key, which is why the
    row is here.
    """
    assert bip32.derive(bip32.rootxprv_from_seed(SEED), BIP32_PATH) == VECTOR_BIP32_XPRV


def dh_shared_secret() -> None:
    """Time the ECDH shared secret of the two vector keys."""
    assert dh.diffie_hellman(PRVKEY, COUNTERPARTY_POINT, 32) == DH_SECRET


def bms_sign() -> None:
    """Time signing a bitcoin message, which signs recoverably."""
    assert bms.sign(BMS_MSG, PRVKEY) == BMS_SIG


def bms_verify() -> None:
    """Time verifying a bitcoin message, which recovers the key from it."""
    assert bms.verify(BMS_MSG, ADDRESS, BMS_SIG)


def taproot_tweak() -> None:
    """Time tweaking a public key into a taproot output key."""
    assert taproot.output_pubkey(PUBKEY)[0] == TAPROOT_PUBKEY


def ellswift_decode() -> None:
    """Time decoding an ElligatorSwift-encoded public key."""
    assert ellswift.decode_var(ELL) == POINT


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
    bip32_derive,
    dh_shared_secret,
    bms_sign,
    bms_verify,
    taproot_tweak,
    ellswift_decode,
):
    _op()


def benchmark(func: Callable[[], None], mult_: int) -> float:
    """Call `func` 1000 * `mult_` times and return the seconds per 1000.

    Returned and not printed: the table is sorted on the measurement and
    each row divides by its own pair, so no line can be written until
    every number is in hand.

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
    return (end - start) / mult_


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
    ("bip32_derive", bip32_derive, 10, 2),
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

    seconds = {
        f"{name}_bindings": benchmark(op, calls) for name, op, calls, _ in OPERATIONS
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
            seconds[f"{name}_bindings"], seconds[f"{name}_pure_python"]
        )
        for name, _, _, _ in OPERATIONS
        for path in ("bindings", "pure_python")
    }
    print(f"{'':<28} {'s/1000':>9}{'vs best':>14}")
    for name, value in sorted(seconds.items(), key=lambda row: row[1]):
        print(f"{name:<28} {value:9.6f}{value / against[name]:13.1f}x")


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
