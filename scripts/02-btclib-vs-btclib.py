# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of btclib against btclib: its two arithmetics, side by side.

Not btclib against btclib-secp256k1. Every row is btclib called through the
same public function, and its two columns are the two arithmetics that answer
underneath -- the libsecp256k1 that btclib-secp256k1 bundles and compiles into
a cffi extension, or the Python of `curves/curve_group.py`. `pip install
btclib` installs both, so neither column is a package a reader chooses
between, and the ratio is what the Python costs when libsecp256k1 declines.

It declines for every curve that is not secp256k1, for a zero scalar, for the
point at infinity, and for anything outside what libsecp256k1's entry points
take.

Which operations have two arithmetics is not a judgement call:
`_libsecp256k1_serves` is the predicate every dispatch site asks, and the
modules holding one are `curves/sec_point.py`, `curves/curve.py`,
`ecc/dsa.py`, `ecc/ssa.py`, `ecc/dh.py`, `ecc/bms.py`, `ecc/ellswift.py`,
`ecc/commit_nonce.py`, `ecc/pedersen.py` and `script/taproot.py`. The rows
below are the ones reachable through a public function. `commit_nonce` and
`pedersen` have none: anti-exfil signing and Pedersen commitments are
protocol machinery rather than operations an application performs.

## Why BIP32 derivation is not a row

btclib's BIP32 has one arithmetic. `_prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` and `_pub_key_offsets` builds a
`PubkeyTweakChain`, neither gated on the dispatch, and btclib gives the
reason beside the call: BIP32 is defined for secp256k1 and nothing else, so
no other curve needs a fallback. Throwing the switch leaves the derivation in
C and moves only the public key derived for the fingerprint, so a row for it
would compare C against C with a Python step added. Its ratio was far
narrower than every other, which is how that showed.

That a row belongs here is therefore a property to prove.
`tests/pure_python_path_test.py` blocks every libsecp256k1 entry point and
asserts each operation still answers. BIP32 derivation is timed in
`scripts/03-libraries.py`, where being C is the premise.

## One function per operation, timed twice

`python_arithmetic_only` is process-wide, so which arithmetic a call reaches
is a property of when it runs rather than of which function was called. The
table's two labels are made from the operation's name, `_libsecp256k1` and
`_pure_python`: every row here is btclib, and every row here is invoked from
Python.

## The one row whose two columns do not save the same thing

`ssa_sign_held_noverify` signs under an `ssa.Signer`, which holds across
calls the keypair that `ssa.sign_` builds and wipes inside each one. There
is a keypair to hold only where libsecp256k1 answers: with the dispatch off
a `Signer` holds a scalar and every signature is `sign_`'s again. So that
row's ratio is the crossing multiplied by a saving one column has and the
other does not, and it is read against the fresh signing row above it rather
than against the rest of the table. It is here because the asymmetry is the
answer -- what btclib's fallback cannot offer is as much this page's subject
as what it costs.

It is also the one fixture `python_arithmetic_only` cannot reach. A signer
decides which arm it is on when it is built and keeps the answer, so the
held objects are built twice, once per pass, off the clock both times. Every
other fixture here is bytes or a point and is read by whichever arithmetic
is switched on when the row runs.

## Which flags a signing row passed, in its name

btclib verifies the signature it has just made before answering with it,
by default and on both arms. The two rows that can decline it do, and say
so in their names: what this table is a ratio of has to be the same work
on both sides, and the check is not -- a fraction of a signature where
libsecp256k1 answers, a full verification where the Python does. A row
taking the default would move a long way with neither arithmetic having
changed.

`bms_sign` names no such flag because its two columns do not share one:
recoverable signing takes no argument that declines, and what the fast
path performs is a recovery and a comparison on that side alone. A name
is silent there because no flag would be true of both columns, and not
because nothing happens.

## One input per call, and no two operations over the same ones

The inputs are drawn from a seed written into this file, the way
`scripts/01-libsecp256k1.py` draws its own: a secret key and a message per
call, sha256 of the seed and a counter rather than `random`, whose stream is
CPython's business and could change under a table nobody re-derived. Each
operation reads a slice of that stream long enough for its own longest
column, so no row measures one input repeated and nothing an operation does
can be quick because the one before it left the same key in a cache.

Random rather than published, and that is what the seed is for. Both columns
of a row are btclib computing the same answer two ways, so a vector proves
nothing here about either that another input would not, and what this page
is read for -- which arithmetic answered, and what that cost -- is the same
for every input. It also removes the one way a chosen key could flatter a
row: the public key of 1 is the generator, and a pure-Python implementation
handed it derives one ladder step rather than a full-width scalar's worth.

A timed function calls one path and discards what it returns, and nothing
here is a correctness check of any kind. `tests/vectors_test.py` is the one
that runs the vendored vectors against both paths, and
`tests/pure_python_path_test.py` checks the second path exists at all, which
is the failure a timing cannot see.

Not part of the test suite and not run by CI. No third-party dependency
either.

## What a run leaves behind

The numbers are written to `results/02-btclib-vs-btclib.json` as this
and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from importlib.metadata import version
from itertools import cycle
from typing import TYPE_CHECKING

from btclib import b58
from btclib.curves import curve, sec_point
from btclib.ecc import bms, dh, dsa, ellswift, ssa
from btclib.script import taproot
from btclib.to_pub_key import pub_keyinfo_from_prv_key

from btclib_benchmarks import _inputs
from btclib_benchmarks._provenance import from_a_declared_source, origin_of
from btclib_benchmarks._results import (
    Measurement,
    Pair,
    Pairs,
    Provenance,
    page_of,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def provenance() -> Provenance:
    """Say which build of each package these rows are about, in one line.

    A released wheel and a working tree satisfy the same requirement and
    resolve in silence, so which one ran is something the output has to
    state rather than something the reader assumes. Where an install is not
    the declared one, that is what a reader has to act on, and it goes
    under the line rather than inside it.

    Two packages and no columns: a table of two rows is a table only in the
    sense that it has edges, and the unit and the sort have to be said
    somewhere above the numbers, which is here.

    The wrapper's version is btclib-secp256k1's, that being what a caller
    installs; which revision of libsecp256k1 it bundled is recorded in
    `scripts/01-libsecp256k1.py`, against the release it was read
    from, and one script naming a pin is enough.
    """
    stated = (
        f"btclib {version('btclib')} (wrapper {version('btclib-secp256k1')}), "
        f"measured as \N{GREEK SMALL LETTER MU}s/call, sorted on the ratio"
    )
    odd = [
        f"  {dist_name}: {origin_of(dist_name)}"
        for dist_name in ("btclib", "btclib-secp256k1")
        if not from_a_declared_source(dist_name)
    ]
    return Provenance(columns=[], rows=[], notes=[stated, *odd])


# The inputs are `_inputs`': one pool, shared by every benchmark here, built
# once and read from `.inputs/` afterwards. That module holds the seed, the
# pool size and the reason for both, and `GENERATION` there is what "new
# inputs" means.
#
# Random rather than published: both columns of a row are btclib answering
# the same question two ways, so a vector proves nothing here that another
# input would not. What vectors are for is correctness, and correctness is
# `tests/`, which runs them against both paths -- so nothing below asserts.
#
# Every operation reads the pool from its own offset, so two operations do
# not start on the same key, and a column longer than the pool wraps and
# reads it again -- which is the pool's size doing its job: a second pass
# over the same keys is where an implementation that caches per key shows
# up as one.
_KEYS = _inputs.keys()
_MESSAGES = _inputs.messages()
_PUBKEYS_33 = _inputs.pubkeys_33()
POOL = len(_KEYS)

# the operations, in the order their slices are cut from the pool
_OPERATION_NAMES = (
    "pubkey_from_prvkey",
    "pubkey_parse_33",
    "generator_mult",
    "dsa_sign_nogrind_noverify",
    "dsa_verify",
    "dsa_recover",
    "ssa_sign_noverify",
    "ssa_verify",
    "dh_shared_secret",
    "bms_sign",
    "bms_verify",
    "taproot_tweak",
    "ellswift_decode",
    "ellswift_xdh",
)

# where each operation starts reading. Spread across the pool rather than
# packed, so that operations measured one after another are not walking the
# same keys in the same order.
#
# Divided by how many operations there are and not by a number written here:
# the two were the same until an operation was added, and the count written
# out is the one that does not follow -- it would have packed the new slice
# on top of an old one rather than re-spreading them, silently and only for
# the rows past where it was added
_OFFSETS = {
    name: (index * POOL // len(_OPERATION_NAMES))
    for index, name in enumerate(_OPERATION_NAMES)
}

# how many of the pool each operation prepares. A fixture is only needed for
# as many calls as the operation's longest column makes, and preparing more
# would be signing what nothing verifies
DRAW_SIZES = {
    "pubkey_from_prvkey": 25_000,
    "pubkey_parse_33": 50_000,
    "generator_mult": 25_000,
    "dsa_sign_nogrind_noverify": 25_000,
    "dsa_verify": 25_000,
    "dsa_recover": 10_000,
    "ssa_sign_noverify": 25_000,
    "ssa_verify": 25_000,
    "dh_shared_secret": 25_000,
    "bms_sign": 15_000,
    "bms_verify": 15_000,
    "taproot_tweak": 25_000,
    "ellswift_decode": 25_000,
    "ellswift_xdh": 25_000,
}


def _rotated(of: list[bytes], operation: str) -> list[bytes]:
    """Return one operation's window of the pool, wrapping at the end."""
    start = _OFFSETS[operation]
    size = DRAW_SIZES[operation]
    doubled = of + of
    return doubled[start : start + size]


def _keys(operation: str) -> list[bytes]:
    """Return the secret keys one operation reads."""
    return _rotated(_KEYS, operation)


def _messages(operation: str) -> list[bytes]:
    """Return the messages one operation reads."""
    return _rotated(_MESSAGES, operation)


# public keys are derived per operation rather than for the whole stream:
# a derivation is a generator multiplication, and the operations that need
# no public key are most of them
PUBKEYS_33 = _rotated(_PUBKEYS_33, "pubkey_parse_33")
DSA_VERIFY_KEYS = [pub_keyinfo_from_prv_key(k)[0] for k in _keys("dsa_verify")]
TAPROOT_KEYS = [pub_keyinfo_from_prv_key(k)[0] for k in _keys("taproot_tweak")]
ELLSWIFT_KEYS = [pub_keyinfo_from_prv_key(k)[0] for k in _keys("ellswift_decode")]
BMS_VERIFY_KEYS = [pub_keyinfo_from_prv_key(k)[0] for k in _keys("bms_verify")]

# ECDSA signatures for the rows that verify and recover, made here with
# grind=False so that each is one signature
DSA_SIGS = [
    dsa.sign_(msg, prvkey, grind=False)
    for msg, prvkey in zip(_messages("dsa_verify"), _keys("dsa_verify"), strict=True)
]
DSA_RECOVER_SIGS = [
    dsa.sign_(msg, prvkey, grind=False)
    for msg, prvkey in zip(_messages("dsa_recover"), _keys("dsa_recover"), strict=True)
]
SSA_SIGS = [
    ssa.sign_(msg, prvkey).serialize()
    for msg, prvkey in zip(_messages("ssa_verify"), _keys("ssa_verify"), strict=True)
]
XONLY = [pub_keyinfo_from_prv_key(k)[0][1:] for k in _keys("ssa_verify")]

# Diffie-Hellman needs a counterparty: each key is paired with the point of
# the next key in its own slice, which keeps every pair distinct
DH_SCALARS = [int.from_bytes(k, "big") for k in _keys("dh_shared_secret")]
_DH_POINTS = [
    sec_point.point_from_octets(pub_keyinfo_from_prv_key(k)[0])
    for k in _keys("dh_shared_secret")
]
COUNTERPARTIES = _DH_POINTS[1:] + _DH_POINTS[:1]

ADDRESSES = [b58.p2pkh(pubkey) for pubkey in BMS_VERIFY_KEYS]
BMS_SIGS = [
    bms.sign(msg, prvkey)
    for msg, prvkey in zip(_messages("bms_verify"), _keys("bms_verify"), strict=True)
]
# ElligatorSwift encoding draws a random field element, so an encoded form is
# a fixture and never a row: decoding one is what is deterministic, and what
# the dispatch is on
ELLS = [ellswift.encode_var(pubkey) for pubkey in ELLSWIFT_KEYS]

# the x-only ECDH is deterministic like the decode above it and unlike the
# encoding that built ELLS: no field element is drawn inside the call, only
# hashed. It needs a counterparty the same way dh_shared_secret does, each
# key paired with the next one's encoding in its own slice
ELLSWIFT_XDH_KEYS = _keys("ellswift_xdh")
_ELLSWIFT_XDH_ELLS = [
    ellswift.encode_var(pub_keyinfo_from_prv_key(prvkey)[0])
    for prvkey in ELLSWIFT_XDH_KEYS
]
ELLSWIFT_XDH_COUNTERPARTIES = _ELLSWIFT_XDH_ELLS[1:] + _ELLSWIFT_XDH_ELLS[:1]

# one cycle per operation, each exactly its slice long. `itertools.cycle`
# rather than an index: a C-level iterator, the same cost in every row, and
# nothing to run off the end of
PUBKEY_CYCLE = cycle(_keys("pubkey_from_prvkey"))
PARSE_33_CYCLE = cycle(PUBKEYS_33)
MULT_CYCLE = cycle([int.from_bytes(k, "big") for k in _keys("generator_mult")])
DSA_SIGN_CYCLE = cycle(
    list(
        zip(
            _messages("dsa_sign_nogrind_noverify"),
            _keys("dsa_sign_nogrind_noverify"),
            strict=True,
        )
    )
)
DSA_VERIFY_CYCLE = cycle(
    list(zip(_messages("dsa_verify"), DSA_VERIFY_KEYS, DSA_SIGS, strict=True))
)
DSA_RECOVER_CYCLE = cycle(
    list(zip(_messages("dsa_recover"), DSA_RECOVER_SIGS, strict=True))
)
SSA_SIGN_CYCLE = cycle(
    list(zip(_messages("ssa_sign_noverify"), _keys("ssa_sign_noverify"), strict=True))
)


def _held_signers() -> cycle[tuple[ssa.Signer, bytes]]:
    """Return one `ssa.Signer` per key of the signing slice, and its messages.

    Built before anything is timed, because what a held row prices is
    holding the key: an object built inside the timed call is the fresh row
    again. The signing slice and not one of its own, so that the two rows
    differ by the holding and not by their inputs -- the one place this file
    reads a slice twice, and the reason is the pair rather than a shortcut.

    One signer per key and not one for the slice: a round is the slice once
    through, and a single held key signed twenty-five thousand times would
    measure one key's second signature over and over, which is a cache and
    not a benchmark.

    A function rather than a list because these have to be built twice, once
    per arithmetic. `SSA_HELD` below says why, and `python_arithmetic_only`
    is what calls it the second time.
    """
    signers = [ssa.Signer(prvkey) for prvkey in _keys("ssa_sign_noverify")]
    return cycle(list(zip(signers, _messages("ssa_sign_noverify"), strict=True)))


# **A held object is the one fixture `python_arithmetic_only` cannot reach**,
# and this is the whole of why it is a list with one cycle in it rather than
# the cycle. `ssa.Signer.__init__` asks `_libsecp256k1_serves` once and keeps
# the answer: where the bindings serve it builds their signer and sets its
# own scalar to zero, that scalar being a second copy of the secret it would
# otherwise be holding for nothing. So a signer built while the dispatch was
# on stays on the bindings for the rest of its life and could not sign in
# Python if asked -- it has no scalar left to sign with.
#
# Every other fixture here is bytes or a point and is read by whichever
# arithmetic is switched on when the row runs. This one carries its
# arithmetic inside it. Built once at import for the libsecp256k1 pass and
# rebuilt by `python_arithmetic_only` for the Python one, both times off the
# clock, and the rebuild is not an optimisation: without it the pure-Python
# column of that row prints a libsecp256k1 number, silently and
# convincingly -- it did, when this row was first written, and
# `tests/pure_python_path_test.py` is what said so.
SSA_HELD = [_held_signers()]
SSA_VERIFY_CYCLE = cycle(
    list(zip(_messages("ssa_verify"), XONLY, SSA_SIGS, strict=True))
)
DH_CYCLE = cycle(list(zip(DH_SCALARS, COUNTERPARTIES, strict=True)))
BMS_SIGN_CYCLE = cycle(list(zip(_messages("bms_sign"), _keys("bms_sign"), strict=True)))
BMS_VERIFY_CYCLE = cycle(
    list(zip(_messages("bms_verify"), ADDRESSES, BMS_SIGS, strict=True))
)
TAPROOT_CYCLE = cycle(TAPROOT_KEYS)
ELLSWIFT_CYCLE = cycle(ELLS)
ELLSWIFT_XDH_CYCLE = cycle(
    list(
        zip(
            ELLSWIFT_XDH_KEYS,
            _ELLSWIFT_XDH_ELLS,
            ELLSWIFT_XDH_COUNTERPARTIES,
            strict=True,
        )
    )
)


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    `_libsecp256k1_serves` reads `_libsecp256k1_available` on every call,
    so this one assignment reaches the nine modules that imported the
    predicate by name. Naming modules instead is what leaves a row meant
    to measure Python measuring C, and it does so silently: a pure-Python
    public key comes back at libsecp256k1 speed, `to_pub_key` asking
    `curves.sec_point`, which is the module such a list forgets. A row
    added below cannot reintroduce that.

    Called once, after every fixture above is built: those go through
    libsecp256k1 too, and there is no reason to slow them down.

    The held signers are rebuilt here rather than by the caller, and that is
    the whole of why this function has a second line. `SSA_HELD` above says
    what they are: the one fixture the assignment cannot reach, each object
    having decided which arm it is on when it was built. Leaving the rebuild
    to whoever throws the switch is leaving it to be forgotten, and what
    forgetting it produces is not an error -- it is a pure-Python column
    printing a libsecp256k1 number. `tests/pure_python_path_test.py` throws
    this switch too, and it caught exactly that.

    Off the clock, as the first set was: this runs between the two passes and
    inside neither.
    """
    curve._libsecp256k1_available = False
    SSA_HELD[0] = _held_signers()


def pubkey() -> None:
    """Time a public key derived from a private key, SEC bytes out.

    `generator_mult` below is the multiplication inside this one, without
    the serialization: the two rows together say what each half costs.
    """
    pub_keyinfo_from_prv_key(next(PUBKEY_CYCLE))[0]


def point_parse_33() -> None:
    """Time parsing a 33-byte compressed public key, which recovers y from x.

    The reverse of what `pubkey_from_prvkey` serializes, and the 33 bytes
    are in the name because the size is the whole of what is being timed:
    a compressed key carries x alone, so parsing one is a modular square
    root, and that root is the only part of a parse btclib delegates. The
    65-byte form hands both coordinates over and is read in Python either
    way -- one code path, no dispatch, and nothing for a pair of columns
    to be a ratio of.
    """
    sec_point.point_from_octets(next(PARSE_33_CYCLE))


def mult() -> None:
    """Time the generator multiplication every key derivation is built on."""
    curve.mult(next(MULT_CYCLE))


def dsa_sign_nogrind_noverify() -> None:
    """Time one ECDSA signature: RFC6979's nonce, no grinding, no check.

    `grind=False`, and no second row for the default, where the benchmarks
    that compare packages carry one. Grinding signs repeatedly until r fits
    in 32 bytes, and the number of attempts is a property of the key and
    message rather than of the arithmetic: both paths make the same number,
    so both rows would be multiplied by it and the ratio -- which is what
    this table is read for -- would not move, as measuring it confirms.

    `verify=False`, and here the reason is the opposite one: the check
    btclib performs by default is *not* the same work on the two arms. On
    this side of the ratio it is a fraction of a signature, on the other it
    is a verification, which the rows below put well above one. A row taking
    the default would divide one checked signing by another and move a long
    way with neither arithmetic having changed, which is the one thing this
    table is read for. What the default costs is priced where it is
    performed: the wrappers page for the crossing, and this page's own
    verify row for the Python.
    """
    msg, prvkey = next(DSA_SIGN_CYCLE)
    dsa.sign_(msg, prvkey, grind=False, verify=False)


def dsa_verify() -> None:
    """Time ECDSA verification."""
    msg, pubkey_bytes, sig = next(DSA_VERIFY_CYCLE)
    dsa.verify_(msg, pubkey_bytes, sig)


def dsa_recover() -> None:
    """Time recovering the candidate public keys of an ECDSA signature."""
    msg, sig = next(DSA_RECOVER_CYCLE)
    dsa.recover_pub_keys_(msg, sig)


def ssa_sign_noverify() -> None:
    """Time BIP340 signing, no check, the auxiliary randomness left to btclib.

    `verify=False` for the reason the ECDSA row above passes it: the two
    arms do not pay the same check, so a row taking the default would move
    this row's ratio without either arithmetic having moved. There is no
    grinding flag to name beside it -- BIP340 has no DER length to shorten,
    so no scheme here grinds for it.
    """
    msg, prvkey = next(SSA_SIGN_CYCLE)
    ssa.sign_(msg, prvkey, verify=False).serialize()


def ssa_sign_held_noverify() -> None:
    """Time BIP340 signing under a key the signer is already holding.

    `ssa.Signer` holds the keypair that `ssa.sign_` builds and wipes inside
    every call, and a keypair is a multiplication of the generator -- about
    half of what a BIP340 signature costs on the arm that has one. So the
    pair with the row above is what a caller who signs more than once under
    a key saves by asking for it, which is the decision a caller actually
    takes; it is not the keypair alone, the held spelling also answering
    with the octets where the fresh one answers with a `Sig`.

    **The two columns do not save the same thing, and that is the row's
    finding rather than a defect in it.** There is a keypair to hold only
    where libsecp256k1 answers. Turn the dispatch off and `Signer` holds a
    scalar and nothing else -- every signature is `sign_`'s again -- so the
    pure-Python column here is the pure-Python column above, and this row's
    ratio is the crossing multiplied by a saving one side has and the other
    does not. Read it against the row above rather than against the rest of
    the table.

    `verify=False`, as the fresh row passes, so nothing in the pair is the
    check.
    """
    signer, msg = next(SSA_HELD[0])
    signer.sign_(msg, verify=False)


def ssa_verify() -> None:
    """Time BIP340 verification."""
    msg, xonly_pubkey, sig = next(SSA_VERIFY_CYCLE)
    ssa.verify_(msg, xonly_pubkey, sig)


def dh_shared_secret() -> None:
    """Time the ECDH shared secret of one key with the next key's point."""
    scalar, point = next(DH_CYCLE)
    dh.diffie_hellman(scalar, point, 32)


def bms_sign() -> None:
    """Time signing a bitcoin message, which signs recoverably.

    The one signing row here that names no verify flag, and the name is
    silent because the two columns do not share one. Recoverable signing
    takes no argument that declines a check, and what the fast path
    performs is not the verification the two rows above decline: it
    recovers the key from the signature and refuses one that is not the
    signer's, which reads the recovery id -- the one value the call is made
    for that nothing downstream re-derives. The Python arm performs no such
    check. So this row's libsecp256k1 column carries a check its pure-Python
    column does not, and no flag in a label shared by both could say so.

    What follows for the ratio is what the page says beside the table: part
    of what this row prints is a default of the bindings rather than the
    price of the crossing.
    """
    msg, prvkey = next(BMS_SIGN_CYCLE)
    bms.sign(msg, prvkey)


def bms_verify() -> None:
    """Time verifying a bitcoin message, which recovers the key from it."""
    msg, address, sig = next(BMS_VERIFY_CYCLE)
    bms.verify(msg, address, sig)


def taproot_tweak() -> None:
    """Time tweaking a public key into a taproot output key."""
    taproot.output_pubkey(next(TAPROOT_CYCLE))[0]


def ellswift_decode() -> None:
    """Time decoding an ElligatorSwift-encoded public key."""
    ellswift.decode_var(next(ELLSWIFT_CYCLE))


def ellswift_xdh() -> None:
    """Time the x-only ECDH shared secret of two ElligatorSwift-encoded keys.

    The pair with the row above: `decode_var` and `xdh` are the module's
    two deterministic calls, `create_var` and `encode_var` being what
    built the fixture rather than what either row times.
    """
    prvkey, own_ell, counterparty_ell = next(ELLSWIFT_XDH_CYCLE)
    ellswift.xdh(own_ell, counterparty_ell, prvkey, 0)


# every row is called once, through libsecp256k1, before anything is
# timed: an operation whose fixture is wrong would otherwise be timed
# rather than reported
for _op in (
    pubkey,
    point_parse_33,
    mult,
    dsa_sign_nogrind_noverify,
    dsa_verify,
    dsa_recover,
    ssa_sign_noverify,
    ssa_sign_held_noverify,
    ssa_verify,
    dh_shared_secret,
    bms_sign,
    bms_verify,
    taproot_tweak,
    ellswift_decode,
    ellswift_xdh,
):
    _op()


def benchmark(func: Callable[[], None], mult_: int) -> float:
    """Call `func` 1000 * `mult_` times and return the microseconds per call.

    Microseconds per call, as every table in this project prints: a unit
    that changes between benchmarks is a unit a reader has to convert
    before comparing two of them. Five significant digits, which is four
    more than the machine can be held to and enough that two rows within a
    percent of each other are still two numbers.

    Returned and not printed: the table is sorted on the ratio each row
    divides its own two numbers into, so no line can be written until every
    number is in hand.

    The count is per operation *and* per path, the two columns below
    holding the two: the pure Python side of a row is one to two orders of
    magnitude slower than libsecp256k1, so one count for both would either
    sit for minutes on the Python row or measure libsecp256k1 against the
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
# libsecp256k1 and through Python. Each count was picked from a first timed
# call to put its column near half a second -- long enough that the loop's
# own overhead is a rounding error, short enough that every operation
# through both arithmetics is a run somebody will wait for
OPERATIONS = (
    ("pubkey_from_prvkey", pubkey, 25, 2),
    ("pubkey_parse_33", point_parse_33, 50, 5),
    ("generator_mult", mult, 25, 2),
    ("dsa_sign_nogrind_noverify", dsa_sign_nogrind_noverify, 25, 2),
    ("dsa_verify", dsa_verify, 25, 1),
    ("dsa_recover", dsa_recover, 10, 1),
    ("ssa_sign_noverify", ssa_sign_noverify, 25, 2),
    ("ssa_sign_held_noverify", ssa_sign_held_noverify, 25, 2),
    ("ssa_verify", ssa_verify, 25, 1),
    ("dh_shared_secret", dh_shared_secret, 25, 2),
    ("bms_sign", bms_sign, 15, 2),
    ("bms_verify", bms_verify, 15, 1),
    ("taproot_tweak", taproot_tweak, 25, 2),
    ("ellswift_decode", ellswift_decode, 25, 3),
    ("ellswift_xdh", ellswift_xdh, 25, 2),
)


# what the run block claims about how these numbers were taken, said by
# the script that took them rather than typed into the page afterwards:
# one call count per operation per path, timed once, and reported
METHOD = "one run, kept whole \N{EM DASH} nothing repeated, no outlier discarded"


def main() -> None:
    """Time every operation through both paths, print the table, save the run.

    The timing order is what the measurement requires:
    `python_arithmetic_only` cannot be undone within a process, so every
    operation is timed through libsecp256k1 before it runs, and through
    Python after. The printing order is the run's own, sorted on the ratio,
    which is why the two are no longer the same loop.

    Nothing is printed until every number is in hand, this table being
    sorted on a ratio between two of them; what goes to the terminal is
    what `render.py` will put in the page, both of them being this one
    function's answer over the run saved at the end.
    """
    seconds = {
        f"{name}_libsecp256k1": benchmark(op, calls)
        for name, op, calls, _ in OPERATIONS
    }

    # this also rebuilds the held signers, which is the one fixture the
    # assignment cannot reach: see `SSA_HELD`
    python_arithmetic_only()

    seconds |= {
        f"{name}_pure_python": benchmark(op, calls) for name, op, _, calls in OPERATIONS
    }

    # one row per operation, the two arithmetics beside each other: the
    # question is what an operation costs each way, and two rows made the
    # reader find the second half of a pair somewhere else in the sort.
    #
    # The ratio is the renderer's, dividing Python by libsecp256k1 rather
    # than the slower by the quicker, so its direction carries information:
    # under 1.0x is a pair where libsecp256k1 lost, which no absolute value
    # would say. The other benchmarks divide by the quickest row of the
    # table; here that row would divide a signature by a point parse, which
    # is two amounts of work and no comparison at all.
    table = Pairs(
        title="",
        columns=("libsecp256k1", "pure python"),
        rows=[
            Pair(
                label=name,
                values=(
                    seconds[f"{name}_libsecp256k1"],
                    seconds[f"{name}_pure_python"],
                ),
            )
            for name, _, _, _ in OPERATIONS
        ],
    )
    measurement = Measurement(
        benchmark=page_of(__file__),
        run=taken_now(__file__, METHOD),
        provenance=provenance(),
        tables=[table],
        # no block saying what a timing contains: every row here is btclib
        # called through one public function, and there is no comparand to
        # have been given an advantage over
        timing_note=[],
    )
    print(rendered_provenance(measurement.provenance))
    print()
    print(rendered_table(table, width_for([row.label for row in table.rows])))
    print(f"\nsaved to {save(measurement)}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
