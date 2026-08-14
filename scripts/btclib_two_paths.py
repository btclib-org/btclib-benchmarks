# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib against btclib: its two arithmetics, side by side.

Not btclib against btclib_secp256k1. Both rows of every pair are btclib,
called the same way through the same public function, and what differs
underneath is which arithmetic answers: the libsecp256k1 that
btclib_secp256k1 bundles and compiles into a cffi extension, or the Python
of `curves/curve_group.py`. `pip install btclib` installs both, the bindings
being a dependency btclib cannot be installed without, so neither row is a
package a reader would choose between -- they are one package's two answers,
and the ratio is what the second costs when the first declines.

It declines for every curve that is not secp256k1, for a zero scalar, for
the point at infinity, and for everything else outside what libsecp256k1's
entry points take. This times both answers through every operation that has
them.

Which operations those are is not a judgement call: `_libsecp256k1_serves`
is the predicate every dispatch site asks, and the modules holding one are
`curves/sec_point.py`, `curves/curve.py`, `ecc/dsa.py`, `ecc/ssa.py`,
`ecc/dh.py`, `ecc/bms.py`, `ecc/ellswift.py`, `ecc/commit_nonce.py`,
`ecc/pedersen.py` and `script/taproot.py`. The rows below cover the ones
reachable through a public function a caller would call, one row each.
`commit_nonce` and `pedersen` have no row: anti-exfil signing and Pedersen
commitments are protocol machinery rather than operations an application
performs, and a table has to end somewhere.

## BIP32 derivation was a row here and cannot be one

It looked like the obvious addition -- an operation an application really
performs, reaching libsecp256k1 through `curves.sec_point` without asking for
a dispatch of its own. Its pair came out far narrower than every other, which
is what a row measuring something other than what it claims looks like.

btclib's BIP32 does not have two paths. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither of them gated on the dispatch, and btclib says
why beside the call: BIP32 is defined for secp256k1 and for nothing else,
so there is no other curve for a fallback to serve. Turning the switch off
therefore leaves the derivation itself in C and moves only the public key
`to_pub_key` derives for the fingerprint -- one multiplication out of a
whole derivation, which is the five-fold difference that was showing.

So the row is gone rather than annotated: this table is about operations
that have two paths, and that is a property to prove rather than assume.
`tests/pure_python_path_test.py` blocks every bindings entry point and
asserts that each operation below still answers, which is what catches the
next `bip32_derive` on the day it is added rather than four runs later.
BIP32 derivation is still timed in `scripts/bitcoin_libraries.py`, against
three other libraries, where being C is the premise rather than the
question.

The point is not a number to quote: the two paths answer the same
equations, one in C and one in Python, and what this shows is an order of
magnitude. Nothing here repeats a measurement or discards an outlier.

## Both halves of every pair are one function, timed twice

There is no `mult_libsecp256k1` beside a `mult_python` with the same body
any more. `python_arithmetic_only` is process-wide, so which path a call takes
is a property of *when* it runs, not of which function was called: one
function per operation, timed before the switch and again after, is what
that actually is. The two labels the table prints are made from the
operation's name -- `_libsecp256k1` and `_pure_python`, which name the two
arithmetics rather than a package and a language: every row here is
Python-invoked, and every row here is btclib.

## The inputs are published test vectors, not values chosen here

The fixture is BIP340 test vector 1, read from btclib's own vendored copy
(`tests/ecc/_data/bip340_test_vectors.csv`, whose `tests/_data/README.md`
pins it to a commit of bitcoin/bips and compares the bytes). The values are
transcribed rather than the file copied: this script times one input per
row, and vendoring sixty CSV rows to use one of them would be a file
nobody reads.

That buys the assertions, not the timings. Timings first: a key is a key,
and three different valid keys through the bindings measure the same to
within the noise of the machine -- so no number here would move if the
fixture went back to being arbitrary. What moves is what a failure can
catch. The public key and the BIP340 signature below are checked against
what the specification publishes, so btclib agreeing with itself is no
longer the whole of the check; and the one fixture that cannot come from a
vector, ECDSA's nonce being btclib's own RFC6979, is still cross-checked
between the paths.

A vector is worth insisting on even where the timings do not care, and the
private key 1 is why. Its public key is the generator: a pure-Python
implementation handed that key derives it in one ladder step rather than a
full-width scalar's worth, and python-ecdsa hands back the generator object
itself, precomputed table and all. A key nobody chose cannot flatter a row
that way.

Not part of the test suite and not run by CI: nothing here is a
correctness check of btclib, and `tests/script_engine/python_path_test.py`
in btclib already is one, over the vendored consensus vectors. No
third-party dependency either -- btclib_secp256k1 is already a dependency
of btclib itself.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path

import btclib
from _provenance import report
from btclib import b58
from btclib.curves import curve, sec_point
from btclib.ecc import bms, dh, dsa, ellswift, ssa
from btclib.script import taproot
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def report_setup() -> None:
    """Say what the two arithmetics are, once, above the table.

    The version that belongs here is btclib_secp256k1's, because that is
    what a caller installs and what the row is: which revision of
    libsecp256k1 it bundled is recorded in
    `scripts/libsecp256k1_wrappers.py`, against the release it was read
    from, and one script naming a pin is enough.
    """
    spec = find_spec("_btclib_secp256k1")
    artifact = Path(spec.origin).name if spec and spec.origin else "not found"
    print("the two arithmetics under each pair")
    print(
        f"  {'libsecp256k1':<20}bundled and compiled into btclib_secp256k1 "
        f"{version('btclib_secp256k1')}, through cffi bindings, {artifact}"
    )
    print(f"  {'pure python':<20}btclib's own curves/curve_group.py, the dispatch off")
    print()


def report_provenance() -> None:
    """Say which build of each package these rows are about.

    Printed before any number: a released wheel and a working
    tree satisfy the same requirement and resolve in silence, so
    which one ran is something the output has to state rather
    than something the reader assumes.
    """
    report(("btclib", btclib.__file__))


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

# what the specification says, checked before anything is timed: the
# public key and the signature below are BIP340's own, so this is btclib
# against the specification rather than btclib against itself -- a mistake
# shared by the two paths could survive the cross-path checks in the rows
# below, and cannot survive these
assert XONLY_PUBKEY == VECTOR_XONLY_PUBKEY
assert SSA_SIG.serialize() == VECTOR_SSA_SIG
assert ssa.verify_(MSG, VECTOR_XONLY_PUBKEY, VECTOR_SSA_SIG)


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
    """Time one ECDSA signature: RFC6979's nonce, and no low-r grinding.

    `grind=False`, and no second row for the default, where the benchmarks
    that compare packages carry one. Grinding signs repeatedly until r fits
    in 32 bytes, and the number of attempts is a property of the key and
    message rather than of the arithmetic: both paths make the same number,
    so both rows would be multiplied by it and the ratio -- which is what
    this table is read for -- would not move, as measuring it confirms. In a
    table of packages the multiple matters, not everybody grinding; here it
    is a restatement.
    """
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
    dh_shared_secret,
    bms_sign,
    bms_verify,
    taproot_tweak,
    ellswift_decode,
):
    _op()


def benchmark(func: Callable[[], None], mult_: int) -> float:
    """Call `func` 1000 * `mult_` times and return the microseconds per call.

    Microseconds per call, as every table in this project prints: a unit
    that changes between benchmarks is a unit a reader has to convert
    before comparing two of them. Five significant digits, which is four
    more than the machine can be held to and enough that two rows within a
    percent of each other are still two numbers.

    Returned and not printed: the table is sorted on the ratio and each
    row divides by its own pair, so no line can be written until every
    number is in hand.

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
    return (end - start) / (1000 * mult_) * 1e6


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
    report_setup()

    seconds = {
        f"{name}_libsecp256k1": benchmark(op, calls)
        for name, op, calls, _ in OPERATIONS
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
            seconds[f"{name}_libsecp256k1"], seconds[f"{name}_pure_python"]
        )
        for name, _, _, _ in OPERATIONS
        for path in ("libsecp256k1", "pure_python")
    }
    # sorted on the ratio and not on the seconds, which is the column this
    # table is read for: what an operation costs is a fact about the
    # operation, and what its fallback costs is a fact about the two paths.
    # The seconds break the tie, so the bindings rows -- 1.0x every one of
    # them -- still read fastest first among themselves
    rows = sorted(
        ((name, value, value / against[name]) for name, value in seconds.items()),
        key=lambda row: (row[2], row[1]),
    )
    print(f"{'':<28} {'μs/call':>10}{'vs best':>14}")
    for name, value, ratio in rows:
        print(f"{name:<28} {value:#10.5g}{ratio:13.1f}x")


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
