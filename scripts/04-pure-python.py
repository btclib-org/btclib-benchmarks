# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of every pure-Python implementation of the same operation.

Every row is Python arithmetic and the question is which is quicker at it, so
no row is a reference line and the ratio is against whichever came out
fastest. What Python costs against C is `scripts/02-btclib-vs-btclib.py`'s
question; what `pip install <package>` gives is
`scripts/03-libraries.py`'s, where the same package names mean something
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

## Which flags a signing row passed, in its label

Every signing row states both of its flags, in the order the call performs
them: `grind` or `nogrind`, and `verify` or `noverify`. A row named for one
flag beside a row named for neither is a flag read against a silence, and
the silence says nothing about what that call did -- so an implementation
that takes no argument is labelled as plainly as the one that does.

Both flags are written out on every btclib row, the defaults included: a row
that took a default would be a row whose label is a claim about btclib's
defaults on the day it was measured rather than about the call it made.

btclib alone grinds for a low-r signature, and btclib alone *takes an
argument* for the check, so btclib alone carries the pairs. Which other rows
check was read out of each implementation rather than assumed, and the two
schemes do not answer alike.

In the ECDSA table nothing else checks, so a single checked btclib row would
sit among three implementations that sign and stop and would read as btclib's
arithmetic having grown several times slower, when what changed is that its
row had become a different operation from the ones beside it. That is the
pair's whole reason here, and the increment is the largest the check comes to
anywhere in this project: on this arm a verification is two point
multiplications where a signature is one, and none of it is amortised by a
keypair. The verify table below is where that increment is priced on its own.

In the BIP340 table both comparands check and neither can decline.
secp256k1lab ends `schnorr_sign` on `assert schnorr_verify(...)`, which is
how the specification's own reference code writes BIP340's last step, and
buidl verifies under the point its key holds and raises on a failure. So
there it is btclib's *checked* row that has comparands and its unchecked row
that stands alone -- which is the same pair read the other way round, and the
reason the pair is a pair rather than a choice between two rows.

The four ECDSA combinations are four rows and not two: the check runs once
on the signature the grinding loop settled on, so grinding and verifying add
rather than multiply.

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

The numbers are written to `results/04-pure-python.json` as this finishes,
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
from btclib.curves import curve
from btclib.ecc import dsa, ssa
from btclib.to_pub_key import pub_keyinfo_from_prv_key
from secp256k1lab.secp256k1 import G as LAB_G

from btclib_benchmarks import _inputs
from btclib_benchmarks._provenance import WHAT_A_TIMING_CONTAINS, origin_of
from btclib_benchmarks._results import (
    Measurement,
    Provenance,
    Ratios,
    Timing,
    Unavailable,
    page_of,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)

# the release each version was published on, recorded because no installed
# metadata carries it: a wheel's METADATA has a Version and no date, and the
# dist-info directory's mtime is when the package was installed here. Keyed
# by the release it was read for, so an upgraded comparand prints
# `unrecorded` rather than a date that has stopped being true.
# secp256k1lab is on no index and is taken from a git tag, which is still a
# release someone cut on a day, so it is recorded like the other four
RELEASE_DATES = {
    "btclib": ("2026.8.21", "2026-08-21"),
    "secp256k1lab": ("1.0.0", "2025-03-26"),
    "ecdsa": ("0.19.2", "2026-03-26"),
    "pycoin": ("0.92718.20260405", "2026-04-05"),
    "buidl": ("0.2.36", "2022-02-28"),
}


def _released(dist_name: str) -> str:
    """Say when this build was published, or where it came from instead.

    A build resolved from a branch has no publish date to report -- a
    release that has not happened cannot be dated -- so the column names
    the branch and the commit instead, which is what a reader has to look
    up to get that build again. Every package this script prices now
    resolves from a release, so this path exists for a future comparand
    rather than for a row currently on it. `scripts/03-libraries.py`
    prints the same column by the same rule, over an overlapping set of
    packages.
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

# The inputs are `_inputs`': one pool, shared by every benchmark here, built
# once and read from `.inputs/` afterwards. That module holds the seed, the
# pool size and the reason for both, and `GENERATION` there is what "new
# inputs" means.
#
# Two hundred is the longest column on this page -- these rows are Python
# arithmetic and a hundred calls is already tenths of a second -- so that is
# what the pool is read for. Each package's own fixtures are built only as
# deep as its own longest row reads, which is the difference between a
# second of setup and most of a minute: one buidl key is a generator
# multiplication in Python, and its rows make ten calls. Nothing here
# asserts -- whether these implementations agree is
# `tests/round_trip_test.py`'s subject, and BIP340's own answers are
# `tests/vectors_test.py`'s.
CALLS = 200
ECDSA_CALLS = 100
PYCOIN_CALLS = 20
BUIDL_CALLS = 10
BTCLIB_CALLS = 50

MESSAGES = _inputs.messages()[:CALLS]
PRVKEYS = _inputs.keys()[:CALLS]
SCALARS = [int.from_bytes(prvkey, "big") for prvkey in PRVKEYS]
PUBKEYS = _inputs.pubkeys_33()[:CALLS]
XONLY = _inputs.xonly()[:CALLS]

# BIP340's auxiliary randomness, thirty-two zeros throughout: it is an input
# to the nonce and not to the arithmetic, so one value keeps every row
# signing the same way and none of them is quicker for it
AUX = bytes(32)

# signed here, deterministically, so that every row verifies the same
# signature rather than one of its own: grind=False takes dsa.sign_'s plain
# RFC6979 nonce, and AUX replaces ssa.sign_'s random default.
#
# pycoin and buidl take an ECDSA digest as an integer rather than as bytes,
# and pycoin refuses a value at or above the group order. Reducing modulo
# the order is what every implementation does with a digest internally, so
# that keeps all of them on one value
ORDER = curve.secp256k1.n
DSA_SCALARS = SCALARS
DSA_SIGS = [
    dsa.sign_(msg, prvkey, grind=False)
    for msg, prvkey in zip(MESSAGES[:BTCLIB_CALLS], PRVKEYS[:BTCLIB_CALLS], strict=True)
]
DSA_SIG_BYTES = [sig.serialize() for sig in DSA_SIGS]
SSA_SIGS = [
    ssa.sign_(msg, prvkey, aux=AUX).serialize()
    for msg, prvkey in zip(MESSAGES[:BTCLIB_CALLS], PRVKEYS[:BTCLIB_CALLS], strict=True)
]


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    `_libsecp256k1_serves` reads `_libsecp256k1_available` on every call, so
    this one assignment reaches the nine modules that imported the predicate
    by name. Patching those modules one at a time is what leaves a row meant
    to measure Python measuring C, and it does so silently: a public key
    derived through `to_pub_key` asks `curves.sec_point`, which is the module
    such a list forgets. No row added below can reintroduce that.

    Called before anything is timed, and after every fixture above is built:
    those want libsecp256k1, and there is no reason to slow them down.
    """
    curve._libsecp256k1_available = False


# which module a native mixin came from, and therefore which library
# `PYCOIN_NATIVE` failed to keep out. The module and not the class name,
# because the name is `Optimizations` in both of them and the fallback is
# `noop` in both of them: a probe reading names sees nothing to report
# however loudly a shared object is being called, which is what
# `03-libraries.py` was doing before it read modules instead.
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
    generator ended up with, as `03-libraries.py` does.
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
    scalar = next(PUBKEY_BTCLIB)
    pub_keyinfo_from_prv_key(scalar)[0]


def pubkey_lab() -> None:
    """Time secp256k1lab's, which multiplies G through a table of its own."""
    scalar = next(PUBKEY_LAB)
    (scalar * LAB_G).to_bytes_compressed()


def pubkey_buidl() -> None:
    """Time buidl's pure-Python S256Point."""
    scalar = next(PUBKEY_BUIDL)
    buidl.pecc.PrivateKey(scalar).point.sec()


def pubkey_ecdsa() -> None:
    """Time python-ecdsa's."""
    scalar = next(PUBKEY_ECDSA)
    ecdsa.SigningKey.from_secret_exponent(
        scalar, curve=ecdsa.SECP256k1
    ).verifying_key.to_string("compressed")


def pubkey_pycoin() -> None:
    """Time pycoin's, its native backends turned off."""
    scalar = next(PUBKEY_PYCOIN)
    pycoin.symbols.btc.network.keys.private(secret_exponent=scalar).sec()


# ----------------------------------------------------------------- ECDSA


def dsa_sign_btclib_nogrind_noverify() -> None:
    """Time one unchecked ECDSA signature through btclib.

    `grind=False`, which is not btclib's default: one signature is what every
    other row in the table produces.

    `verify=False`, which is not btclib's default either, and on this page it
    is the flag that matters most. btclib verifies the signature it has just
    made before answering with it, on this arm as on the other, and here that
    check is a verification in Python -- the table below prices one, and it
    is several signatures. No other implementation in this table checks
    anything after signing, so this is the row they are read against.
    """
    msg, prvkey = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey, grind=False, verify=False)


def dsa_sign_btclib_nogrind_verify() -> None:
    """Time one ECDSA signature with the check btclib performs by default.

    The pair with the row above, and the reason the page carries a pair
    rather than moving the one row: a single checked row would sit among
    implementations that sign and stop, and would read as btclib's Python
    arithmetic having grown several times slower rather than as a row that
    had become a different operation from the ones beside it.

    What is added is btclib's own pure-Python verification and the public key
    derivation it needs, which the verify table below is the price of. It is
    the largest share of a signature the check comes to anywhere in this
    project: a verification here is two point multiplications where a
    signature is one, and none of it is amortised by a keypair.
    """
    msg, prvkey = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey, grind=False, verify=True)


def dsa_sign_btclib_grind_noverify() -> None:
    """Time unchecked ECDSA signing with btclib's low-r grinding.

    btclib grinds for a low-r signature by default: it signs until r fits in
    32 bytes, an expectation of two signatures and, for one fixed key and
    message, a fixed number of them. No other implementation in this table
    grinds, so the pair with the row above says what one signature costs and
    what a caller who declines nothing but the check waits for.
    """
    msg, prvkey = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey, grind=True, verify=False)


def dsa_sign_btclib_grind_verify() -> None:
    """Time ECDSA signing as btclib performs it unless told otherwise.

    Both defaults, which is what a caller who writes `dsa.sign_(msg, key)`
    waits for. The check is of the signature the loop settled on and not of
    every attempt, so grinding and verifying add rather than multiply, and
    this row is the grinding row plus the increment the ungrinding pair
    prices.
    """
    msg, prvkey = next(DSA_SIGN_BTCLIB)
    dsa.sign_(msg, prvkey, grind=True, verify=True)


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


def ssa_sign_btclib_noverify() -> None:
    """Time an unchecked BIP340 signature, over the vector's aux_rand.

    `verify=False`. Neither comparand in this table checks what it signed,
    so this is the row they are read against; the row below is BIP340's own
    last step, priced.
    """
    msg, prvkey, aux = next(SSA_BTCLIB_SIGN)
    ssa.sign_(msg, prvkey, aux=aux, verify=False).serialize()


def ssa_sign_btclib_verify() -> None:
    """Time BIP340 signing with the check btclib performs by default.

    BIP340 puts the step inside Default Signing -- "If Verify(bytes(P), m,
    sig) returns failure, abort" -- so this row is the scheme's algorithm run
    whole. On this arm the step is btclib's own Python verification, which
    the BIP340 verify table below prices, and it is not the smaller of the
    two increments this page carries the way it is where a keypair has
    already derived the point.
    """
    msg, prvkey, aux = next(SSA_BTCLIB_SIGN)
    ssa.sign_(msg, prvkey, aux=aux, verify=True).serialize()


def ssa_verify_btclib() -> None:
    """Time a BIP340 verification through btclib."""
    msg, xonly_pubkey, sig = next(SSA_BTCLIB_VERIFY)
    ssa.assert_as_valid_(msg, xonly_pubkey, sig)


def ssa_sign_lab() -> None:
    """Time a BIP340 signature through secp256k1lab, which checks it.

    `verify`, and no argument declines it: `schnorr_sign` ends on
    `assert schnorr_verify(...)`, BIP340's own last step, written the way the
    specification's reference code writes it. So this row's comparand is
    btclib's checked one.
    """
    msg, prvkey, aux = next(SSA_LAB_SIGN)
    secp256k1lab.bip340.schnorr_sign(msg, prvkey, aux)


def ssa_verify_lab() -> None:
    """Time a BIP340 verification through secp256k1lab."""
    msg, xonly_pubkey, sig = next(SSA_LAB_VERIFY)
    secp256k1lab.bip340.schnorr_verify(msg, xonly_pubkey, sig)


def ssa_sign_buidl() -> None:
    """Time a BIP340 signature through buidl's pure-Python module, checked.

    `verify`, and no argument declines it: `sign_schnorr` ends by verifying
    the signature under the point its key holds and raising on a failure,
    which is BIP340's own last step. Its comparand is btclib's checked row.
    """
    key, msg, aux = next(SSA_BUIDL_SIGN)
    key.sign_schnorr(msg, aux)


def ssa_verify_buidl() -> None:
    """Time a BIP340 verification through buidl's pure-Python module."""
    key, msg, sig = next(SSA_BUIDL_VERIFY)
    key.point.verify_schnorr(msg, sig)


# ------------------------------------------------------------- the timing


# four, and even, which is what the estimator below halves. Three did not
# halve -- half a round is the minimum of nothing -- so this page adopts
# `scripts/03-libraries.py`'s constant along with its statistic.
#
# What this page said against rounds was that "three rounds of the slowest
# would be a run nobody waits for", and it was measured rather than
# reasoned: every row of the published one-round run together came to under
# four seconds of clock. The counts below are what made that true, and they
# are the defect ISS 111 found -- picked so that the *slowest* rows were
# bearable, they left the quickest running for milliseconds, where a
# scheduler taking one is a large fraction of the number. Chosen per row to
# a target instead, four rounds of this page cost under a minute.
ROUNDS = 4


def benchmark(func: Callable[[], None], calls: int) -> tuple[float, float]:
    """Return the quickest round's microseconds per call, and the halves' gap.

    `ROUNDS` rounds of `calls` calls each. The minimum is the estimate:
    noise is one-sided -- nothing on this machine makes a call quicker than
    it is -- so the quickest round is the one that ran with least taken from
    it, where a mean would carry every interruption into the number.

    The second number is how far that estimate moved when the row was
    measured twice, which is what the rounds are halved for, and it is the
    column this page had none of. Its rows are the slowest this project
    prints and its tables are read by subtracting one row from another --
    a checked signing row less its unchecked one is what the check costs --
    so an error that a ratio would divide away is an error a difference
    keeps, and there was nothing beside a row to say how large it was.

    Saved as `halves_apart`, which is the key `_results.py` already carries
    for this statistic; the page has never printed the `spread` that key
    stands against, so nothing here is a redefinition.

    Contiguous halves rather than alternate rounds, as on the pages that
    print it already: the rows of a table are measured minutes apart, and a
    machine that drifts over a row's rounds will drift over a table's rows.
    Two halves seconds apart say nothing about two runs a day apart, and
    nothing here can see the second.

    A returned number and not a printed one: every row is a ratio against
    the quickest of its table, so the reference has to be in hand before
    anything is printed.

    `calls` is per function rather than shared: the slowest row here is
    four orders of magnitude off the reference, and one count for all of
    them would either sit for minutes on the slowest or measure the
    fastest against the resolution of the clock. Each is picked so a round
    lands near half a second -- long enough that a scheduler's slice is a
    rounding error next to it, which is what the counts it replaces were
    not.
    """
    # perf_counter and not time(): the wall clock can step backwards
    rounds = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(calls):
            func()
        rounds.append((time.perf_counter() - start) / calls * 1e6)
    # halved on what the loop above produced rather than on `ROUNDS`, the
    # two being the same number until somebody changes one
    half = len(rounds) // 2
    first, second = min(rounds[:half]), min(rounds[half:])
    return min(first, second), abs(first - second)


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
    # the union, not `list[Timing]`: `Ratios` takes rows either way and a
    # list is invariant. No row here is ever unavailable -- every comparand
    # on this page implements every operation, which is what makes it a
    # page -- so this is the annotation and not a case to handle
    timings: list[Timing | Unavailable] = []
    for label, func, calls in rows:
        value, apart = benchmark(func, calls)
        timings.append(
            Timing(
                label=label,
                us_per_call=value,
                halves_apart=apart,
                calls=calls,
                rounds=ROUNDS,
            )
        )
    return Ratios(title=title, rows=timings)


# the fixtures each comparand signs and verifies, built once from the pool
ECDSA_KEYS = [
    ecdsa.SigningKey.from_secret_exponent(scalar, curve=ecdsa.SECP256k1)
    for scalar in SCALARS[:ECDSA_CALLS]
]
ECDSA_SIGS = [
    key.sign_digest_deterministic(msg, hashfunc=sha256)
    for key, msg in zip(ECDSA_KEYS, MESSAGES, strict=False)
]
PYCOIN_DIGESTS = [int.from_bytes(msg, "big") % ORDER for msg in MESSAGES]
PYCOIN_POINTS = [PYCOIN_GENERATOR * scalar for scalar in SCALARS[:PYCOIN_CALLS]]
PYCOIN_PAIRS = [(point[0], point[1]) for point in PYCOIN_POINTS]
PYCOIN_SIGS = [
    PYCOIN_GENERATOR.sign(scalar, digest)
    for scalar, digest in zip(SCALARS[:PYCOIN_CALLS], PYCOIN_DIGESTS, strict=False)
]
BUIDL_KEYS = [buidl.pecc.PrivateKey(scalar) for scalar in SCALARS[:BUIDL_CALLS]]
BUIDL_SIGS = [
    key.sign(digest) for key, digest in zip(BUIDL_KEYS, PYCOIN_DIGESTS, strict=False)
]
BUIDL_SSA_KEYS = BUIDL_KEYS
BUIDL_SSA_SIGS = [
    key.sign_schnorr(msg, AUX)
    for key, msg in zip(BUIDL_SSA_KEYS, MESSAGES, strict=False)
]

# one cycle per row
PUBKEY_BTCLIB = cycle(SCALARS)
PUBKEY_LAB = cycle(SCALARS)
PUBKEY_ECDSA = cycle(SCALARS)
PUBKEY_PYCOIN = cycle(SCALARS)
PUBKEY_BUIDL = cycle(SCALARS)
DSA_SIGN_BTCLIB = cycle(list(zip(MESSAGES, PRVKEYS, strict=True)))
DSA_VERIFY_BTCLIB = cycle(list(zip(MESSAGES, PUBKEYS, DSA_SIG_BYTES, strict=False)))
DSA_ECDSA = cycle(list(zip(MESSAGES, ECDSA_KEYS, ECDSA_SIGS, strict=False)))
DSA_PYCOIN = cycle(
    list(zip(SCALARS, PYCOIN_DIGESTS, PYCOIN_PAIRS, PYCOIN_SIGS, strict=False))
)
DSA_BUIDL = cycle(list(zip(BUIDL_KEYS, PYCOIN_DIGESTS, BUIDL_SIGS, strict=False)))
SSA_BTCLIB_SIGN = cycle(
    [(msg, prvkey, AUX) for msg, prvkey in zip(MESSAGES, PRVKEYS, strict=True)]
)
SSA_BTCLIB_VERIFY = cycle(list(zip(MESSAGES, XONLY, SSA_SIGS, strict=False)))
SSA_LAB_SIGN = cycle(
    [(msg, prvkey, AUX) for msg, prvkey in zip(MESSAGES, PRVKEYS, strict=True)]
)
SSA_LAB_VERIFY = cycle(list(zip(MESSAGES, XONLY, SSA_SIGS, strict=False)))
SSA_BUIDL_SIGN = cycle(
    [(key, msg, AUX) for key, msg in zip(BUIDL_SSA_KEYS, MESSAGES, strict=False)]
)
SSA_BUIDL_VERIFY = cycle(
    list(zip(BUIDL_SSA_KEYS, MESSAGES, BUIDL_SSA_SIGS, strict=False))
)


# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page, which is a fact about all five
# tables and cannot be known while the first is being measured
TABLES: tuple[tuple[str, Rows], ...] = (
    (
        "public key from a private key: a multiplication of the generator",
        (
            ("btclib", pubkey_btclib, 2_700),
            ("secp256k1lab", pubkey_lab, 400),
            ("python-ecdsa", pubkey_ecdsa, 1_800),
            ("pycoin", pubkey_pycoin, 90),
            ("buidl.pecc", pubkey_buidl, 17),
        ),
    ),
    (
        "ECDSA sign, over a 32-byte digest",
        (
            ("btclib, nogrind, noverify", dsa_sign_btclib_nogrind_noverify, 3_000),
            ("btclib, nogrind, verify", dsa_sign_btclib_nogrind_verify, 500),
            ("btclib, grind, noverify", dsa_sign_btclib_grind_noverify, 1_300),
            ("btclib, grind, verify", dsa_sign_btclib_grind_verify, 500),
            ("python-ecdsa, nogrind, noverify", dsa_sign_ecdsa, 1_700),
            ("pycoin, nogrind, noverify", dsa_sign_pycoin, 88),
            ("buidl.pecc, nogrind, noverify", dsa_sign_buidl, 17),
        ),
    ),
    (
        "ECDSA verify, over a 32-byte digest",
        (
            ("btclib", dsa_verify_btclib, 750),
            ("python-ecdsa", dsa_verify_ecdsa, 450),
            ("pycoin", dsa_verify_pycoin, 28),
            ("buidl.pecc", dsa_verify_buidl, 8),
        ),
    ),
    (
        "BIP340 sign, over a 32-byte message",
        (
            ("btclib, noverify", ssa_sign_btclib_noverify, 1_500),
            ("btclib, verify", ssa_sign_btclib_verify, 500),
            ("secp256k1lab, verify", ssa_sign_lab, 65),
            ("buidl.pecc, verify", ssa_sign_buidl, 5),
        ),
    ),
    (
        "BIP340 verify, over a 32-byte message",
        (
            ("btclib", ssa_verify_btclib, 740),
            ("secp256k1lab", ssa_verify_lab, 100),
            ("buidl.pecc", ssa_verify_buidl, 7),
        ),
    ),
)

# what the run block claims about how these numbers were taken. `calls` is
# per row and prints beside its row, the counts above spanning three orders
# of magnitude and the sort putting rows of either end next to each other
METHOD = f"{ROUNDS} rounds per row in two halves, minimum kept; calls per row"


def main() -> None:
    """Throw the switch, print a table per operation, and save the run.

    `python_arithmetic_only` comes first and nothing here is timed before
    it: with no reference row left to measure through libsecp256k1, the one
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
            benchmark=page_of(__file__),
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
