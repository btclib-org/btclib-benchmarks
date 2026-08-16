# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of four wrappers of one C library, side by side.

Every row calls `bitcoin-core/secp256k1`, so what separates them is the
boundary crossing rather than the arithmetic: cffi against ctypes, a signature
in DER against one in 64 bytes, a public key handed over as bytes against one
held as a Python object. There is no pure-Python row --
`scripts/04-pure-python.py` asks what staying in Python costs, and asks it with
every backend forced off rather than one switch flipped.

btclib is not imported here at all: the fixtures come from
`btclib_secp256k1` -- the module, btclib-secp256k1 being the package -- and
`hashlib`, so nothing reaches into btclib's private dispatch and importing
this module leaves the bindings on for the rest of the process.

Measured are ECDSA and BIP340 signing and verification, a public key tweaked
by a scalar, which is BIP32's step -- none of the four implements BIP32
itself, and all four expose the primitive it is built from -- and the parse
of a public key on its own, which is the step the verification and tweak
rows repeat per call -- the verification tables taking the uncompressed
65-byte key, which is the one every row of the two parses. `electrum-ecc`
has no tweak-add on `ECPubkey`, so it
reaches the same point as a scalar times the generator plus an addition: two
crossings where the others make one.

Signing and verifying are two tables each, one per serialization: DER, which
is what a transaction carries, and the 64-byte compact form, which is what a
caller holds. The difference between the two is an encoding rather than an
arithmetic, so what a pair of them prices is exactly what a serialization
costs -- and the parse tables do the same for a public key, 33 bytes against
65: the compressed form makes the parser solve for y, and the uncompressed
one hands it over.

Not every API spells both. `coincurve` signs and verifies in DER alone, so
its rows in the compact tables are `NA`; `electrum-ecc` signs in the compact
form and carries its own converter to DER, so both of its rows are its own
calls. Which encodings a wrapper offers is part of what it is, and a table
that filled the gap from the C underneath would hide exactly that.

## One input per call, and no two tables over the same ones

The inputs are `scripts/_inputs.py`': one pool, shared by every benchmark in
this repository, built once from a seed and read from `.inputs/` on every
run after the first. That module holds the seed and the pool size, and its
`GENERATION` is what asking for new inputs changes.

Each table reads a slice of that pool as long as one round, so a round is
its slice exactly once, no row measures one input repeated, and nothing a
table does can be quick because the table before it left the same key in a
cache. Every table starts from the same shapes -- the keys as 32-byte
scalars, the public keys derived from them, the signatures made once here --
and the last tweaks each public key by the secret key it came from.

Random rather than published, and that is the point of the seed. Four
wrappers of one C library compute the same arithmetic by construction, so a
published vector proves nothing here that another input would not, while what
this table is read for -- the boundary crossing -- is the same for every
input. What vectors are for is correctness, and correctness is `tests/`.

Only the package's own API is measured, and where it has no such call the
row is `NA` rather than a number: coincurve signs and verifies ECDSA in DER
alone, so it has no row in the two compact tables. Reaching into the cffi or
ctypes bindings underneath would produce a number, and the number would be
libsecp256k1's rather than the wrapper's -- what a reader comparing wrappers
asks is what each one offers.

`electrum-ecc` is the only one of the four offering low-r grinding, so its
row is `grind_r_value=False`: without it, its signing time would not be
comparable with the other three, which sign once. The tables about libraries
carry the distinction the other way, as a pair of rows, because there both
btclib and
embit grind by default -- two grinding libraries are worth comparing to each
other, and one is not.

## The public key is parsed inside every timing

Two of the four leave no choice: `btclib_secp256k1` takes bytes and parses per
call, and electrum-ecc's `ECPubkey` holds x and y as Python integers and
parses a `secp256k1_pubkey` again on every verify. coincurve and secp256k1-py
could each be handed a parsed key once and are not, for the reason no row is
handed anything: a row skipping what two of the four cannot skip would be
timing a different operation. Tables 4 and 5 price that parse on its own,
ahead of the verify tables that repeat it -- so a reader meets the
subtraction before the total, and can read either against it to see how much
of a verification is the parse -- and for
secp256k1-py the parse is its `PublicKey` constructor, which derives the
x-only key as it goes: preparation for BIP340 its API performs whether the
caller came for it or not.

The signature is another matter: each row takes the encoding its own API asks
for, and converting between encodings happens once, in the fixtures. What a
sign row hands back is bytes in every case: secp256k1-py's `ecdsa_sign` alone
returns its parsed signature, so its row serializes it to DER, bytes being
what the other three hand back.

## No row is handed an object another row's package built

Every row starts from the same bytes, so whatever an API builds before it can
work -- secp256k1-py's `PrivateKey`, coincurve's, a `secp256k1_keypair` --
is built inside the call that needs it, by the row that needs it. A fixture
holding a constructed key for one package and not for the others would price
that package's signature at what its second signature under the same key
costs, which is a different question from the one every row is being asked.

It is a toll BIP340 charges and ECDSA does not: signing a message with
Schnorr starts from a keypair, where ECDSA takes the secret key as it is,
and that is why table 2 spreads wider than table 1.

## "The same C library" is a claim about the API, not about the binary

The four vendor different revisions, so `provenance` says which is under
each row -- from a pin, because none of them can be asked. Neither
compiled artifact exports a version symbol; `btclib_secp256k1.version` is
`importlib.metadata.version` re-exported, which answers for the wrapper and
not for the library; coincurve and secp256k1-py expose only their own
`__version__`; and electrum-ecc's `version_info` returns the path of the
shared object it opened and nothing about its contents. So each pin is
recorded against the release it was read from and reported as unrecorded for
any other, and re-reading it is what a comparand's release costs.

The durable fix belongs upstream rather than here: a wrapper that recorded its
vendored revision at build time -- a constant its build script writes from the
submodule it just compiled -- would let this row read what it now asserts.

## Correctness is not measured here

A timed function calls one API and discards what it returns. It compares
nothing of its own, because a comparison inside the loop is time attributed
to the wrapper that did not spend it.

What a wrapper does inside its own call is another matter, and is measured:
coincurve's `sign_schnorr` and electrum-ecc's `schnorr_sign` and `ecdsa_sign`
each verify the signature they just made before returning it, and none of the
three lets a caller decline that. It is part of what signing through those
packages costs, so it is in their rows -- reaching past the method into the C
underneath would time something the package does not offer.

Nothing below asserts, either -- not in a timed function and not in the
fixtures. Whether these packages answer correctly is
`tests/vectors_test.py`'s subject, where BIP340's vectors, Wycheproof's and
BIP32's are run against every implementation this project times, in the
configuration it times it in, negative cases included. A benchmark that
re-checked them would be a slower copy of a test that already exists, over
inputs nobody published.

What such a check would prove here is little in any case: four wrappers of
one library agreeing with each other is the weakest evidence available, and
one of the four is where these fixtures' signatures come from.

Not part of the test suite and not run by CI: measuring is done by a person on
a machine whose state they know.

## What a run leaves behind

The numbers are written to `results/01-libsecp256k1.json` as this
finishes, and `scripts/render.py` writes the page beside it from that file
alone. So the prose around a table is rewritten and re-published
without a machine and without a number being retyped: measuring and
publishing are two commands.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from importlib.metadata import version
from itertools import cycle

import _inputs
import btclib_secp256k1.dsa
import btclib_secp256k1.keys
import btclib_secp256k1.ssa
import coincurve
import electrum_ecc
import secp256k1
from _provenance import from_a_declared_source, origin_of
from _results import (
    Measurement,
    Provenance,
    Ratios,
    Timing,
    Unavailable,
    counted_calls,
    labels,
    page_of,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)


def _built_from(dist_name: str) -> str:
    """Say when this build was published, or where it came from instead.

    btclib-secp256k1 resolves from its branch until the release these rows
    are written against is on PyPI, and a date would be a claim about a
    release that has not happened: what the column says for it is the
    branch and the commit, which is what a reader has to look up to get
    these rows again.
    """
    if not (recorded := RELEASE_DATES.get(dist_name)):
        # the branch and the commit, without the repository the package
        # column has already named
        return origin_of(dist_name).split()[-1]
    return recorded[1] if version(dist_name) == recorded[0] else "unrecorded"


def _vendored_pin(dist_name: str) -> str:
    """Return the libsecp256k1 revision this build carries, if it is known.

    Keyed by whatever identifies the build, which is not the same thing
    for all four: a released wrapper is identified by its version, and a
    wrapper resolved from a branch is not -- the version there stays put
    while the branch moves, so the key is the commit and any other prints
    `unrecorded`. Either way an upgraded comparand says it has outgrown
    its pin rather than repeating one that has quietly stopped being true.
    """
    recorded, pin = LIBSECP256K1_PINS[dist_name]
    return pin if _built_from(dist_name) == recorded else "unrecorded"


def provenance() -> Provenance:
    """Return one row per wrapper: what it is, and what is under it.

    Five columns, because the reader of this table needs all five and each
    answers a different question. The version and the release date say which
    build these rows are; the revision says which library that build carries,
    the four being four vendored trees of one project; the bindings say how
    a row crosses into it. Sorted newest build first.

    Two of the five cannot be read at run time and are recorded against the
    build they were read for, printing `unrecorded` for any other: no
    compiled artifact exports a version symbol, and no installed metadata
    carries a release date.

    A package installed from anywhere other than its declared source is named
    under the table rather than in it: `editable:` and `sys.path:` are what a
    reader has to act on, and a column of "released" repeated four times is
    not.
    """
    rows = []
    by_date = sorted(WRAPPERS, key=lambda row: _built_from(row[0]), reverse=True)
    for dist_name, bindings in by_date:
        rows.append(
            [
                dist_name,
                version(dist_name),
                _built_from(dist_name),
                _vendored_pin(dist_name),
                bindings,
            ]
        )
    return Provenance(
        columns=[
            "package",
            "version",
            "released",
            "libsecp256k1 pin",
            "bindings",
        ],
        rows=rows,
        notes=[
            f"{dist_name} is installed from {origin_of(dist_name)}"
            for dist_name, _ in WRAPPERS
            if not from_a_declared_source(dist_name)
        ],
    )


# The inputs are `_inputs`': one pool, shared by every benchmark here, built
# once and read from `.inputs/` afterwards. That module holds the seed, the
# pool size and the reason for both, and `GENERATION` there is what "new
# inputs" means.
#
# Random rather than published. Every wrapper here calls the same C library,
# so a vector proves nothing about their arithmetic that another input does
# not, and what a table of them is read for is the boundary crossing. What
# published vectors are for is correctness, and that is `tests/`: it holds
# every measured package to BIP340, to Wycheproof and to BIP32, in the
# configuration this script measures it in, so nothing below asserts.
#
# `CALLS` per row per round, out of a pool ten times that: a round is a
# tenth of the pool, and nine tables reading nine consecutive tenths of it
# leaves no two of them over the same keys -- so a key signed in table 1 is
# not the key verified in table 6, and no row is quick because something
# before it warmed a cache with the same bytes.
CALLS = 10_000

# nine, because that is how many tables are declared at the foot of this
# file: a count written twice, and the one place this file repeats itself,
# `TABLES` needing the rows and the rows needing the slices
TABLES_HERE = 9


def _slice(table: int, of: list[bytes]) -> list[bytes]:
    """Return the `CALLS` elements table `table` reads, counting from one."""
    return of[(table - 1) * CALLS : table * CALLS]


PRVKEYS = _inputs.keys()
MESSAGES = _inputs.messages()

# 65 bytes, the uncompressed form every one of the four parses, so that a
# verify row is handed the same key as every other verify row. The 33-byte
# form beside it is what tables 4 and 5 price against each other: the same
# key, one encoding carrying its y and the other making the parser solve
# for it -- cut from the uncompressed bytes rather than derived a second
# time, the parity of y and x being both already there
PUBKEYS = _inputs.pubkeys_65()
PUBKEYS_COMPRESSED = _inputs.pubkeys_33()

# BIP340 takes the x-only key, which is the uncompressed key's x: a slice
# rather than a conversion, and not a parsed object of any package's
XONLY = _inputs.xonly()

# aux_rand is 32 zero bytes throughout. secp256k1-py's `schnorr_sign` takes
# none at all, so a per-call aux would be work one row could not do
AUX = bytes(32)

# the signatures the verify tables are handed, made once, here. No file
# publishes a signature over a key nobody has seen before, so one of the
# four signs and all four verify the identical bytes -- which is what a
# comparison of verifiers wants, and one wrapper's output is the reference
# only in the sense that some bytes had to be chosen.
#
# Only the slices the verify tables read: signing every draw would be four
# fifths of a minute spent on signatures nothing verifies
DSA_SIGS = [
    btclib_secp256k1.dsa.sign(msg, prvkey)
    for msg, prvkey in zip(_slice(6, MESSAGES), _slice(6, PRVKEYS), strict=True)
]
DSA_SIGS_COMPACT = [
    btclib_secp256k1.dsa.sign(msg, prvkey, compact=True)
    for msg, prvkey in zip(_slice(7, MESSAGES), _slice(7, PRVKEYS), strict=True)
]
SSA_SIGS = [
    btclib_secp256k1.ssa.sign(msg, prvkey, AUX)
    for msg, prvkey in zip(_slice(8, MESSAGES), _slice(8, PRVKEYS), strict=True)
]

# one cycle per table, every element of it bytes: no row is handed an object
# another row's package built, so what a constructor costs is inside the
# call that needs it, where the caller pays it. A cycle is exactly `CALLS`
# long, so a row's round is its table's slice once through, and the four
# rows of a table are compared over the same inputs in the same order
DSA_SIGN_DER = cycle(list(zip(_slice(1, PRVKEYS), _slice(1, MESSAGES), strict=True)))
DSA_SIGN_COMPACT = cycle(
    list(zip(_slice(2, PRVKEYS), _slice(2, MESSAGES), strict=True))
)
SSA_SIGN = cycle(list(zip(_slice(3, PRVKEYS), _slice(3, MESSAGES), strict=True)))
PARSE_COMPRESSED = cycle(_slice(4, PUBKEYS_COMPRESSED))
PARSE_UNCOMPRESSED = cycle(_slice(5, PUBKEYS))
DSA_VERIFY_DER = cycle(
    list(zip(_slice(6, PUBKEYS), _slice(6, MESSAGES), DSA_SIGS, strict=True))
)
DSA_VERIFY_COMPACT = cycle(
    list(zip(_slice(7, PUBKEYS), _slice(7, MESSAGES), DSA_SIGS_COMPACT, strict=True))
)
SSA_VERIFY = cycle(
    list(zip(_slice(8, XONLY), _slice(8, MESSAGES), SSA_SIGS, strict=True))
)
SSA_VERIFY_FULL = cycle(
    list(zip(_slice(8, PUBKEYS), _slice(8, MESSAGES), SSA_SIGS, strict=True))
)
# each public key tweaked by the secret key it came from
TWEAK = cycle(list(zip(_slice(9, PUBKEYS), _slice(9, PRVKEYS), strict=True)))


# When each of these releases was published, read from the index and
# recorded against the release it was read for. Not available at run time:
# a wheel's METADATA carries a Version and no date, and the dist-info
# directory's mtime is when the package was installed on this machine. A
# comparand's age is worth a column here -- one of these four is years older
# than the others, and the revision it vendors follows from that.
#
# btclib-secp256k1 is absent on purpose rather than missing: it resolves
# from its branch until the release these rows call for is on PyPI, and
# there is no date to record for a release that has not happened.
# `_built_from` prints the commit for it instead, and the day the source
# entry in pyproject.toml goes, a line here is what replaces it
RELEASE_DATES = {
    "coincurve": ("21.0.0", "2025-03-08"),
    "secp256k1": ("0.14.0", "2021-11-06"),
    "electrum-ecc": ("0.0.7", "2026-02-25"),
}


# Where each row's libsecp256k1 came from, read from the build named
# beside it:
#
# - btclib-secp256k1: the `secp256k1` submodule pin at main@d9933e49e793,
#   6e2c8bc, which is upstream's v0.8.0 tag exactly -- the same commit its
#   v0.8.0, v0.8.0.1 and v0.8.0.2 tags pinned, so those releases moved and
#   the library did not
# - coincurve: `VENDORED_UPSTREAM_REF` in its pyproject.toml, 0cdc758a,
#   which is upstream's v0.6.0
# - secp256k1: `LIB_TARBALL_URL` in its setup.py, 9526874d, a master
#   commit older than upstream's first tagged release -- the configure.ac
#   of the tree it bundles still calls itself 0.1
# - electrum-ecc: the libsecp256k1 tree carried in its sdist and compiled
#   at install time, whose configure.ac names 0.7.1 as a release
#
# Keyed by whatever `_built_from` prints, because that is what identifies
# a build: a release is its version, and a branch install is the commit,
# the version there standing still while the branch moves. Either way the
# floors in pyproject.toml are floors -- a comparand upgrades without a
# word, and a pin has to stop being claimed when the build it was read
# from is no longer the one installed.
LIBSECP256K1_PINS = {
    "btclib-secp256k1": ("main@d9933e49e793", "v0.8.0"),
    "coincurve": ("2025-03-08", "v0.6.0"),
    "secp256k1": ("2021-11-06", "9526874d, pre-v0.1.0"),
    "electrum-ecc": ("2026-02-25", "v0.7.1"),
}

# how each row reaches the library, which is the difference this whole
# script is about: three link it into a cffi extension at build time,
# one opens the shared object beside the package through ctypes
WRAPPERS = (
    ("btclib-secp256k1", "cffi"),
    ("coincurve", "cffi"),
    ("secp256k1", "cffi"),
    ("electrum-ecc", "ctypes"),
)


def dsa_sign_der_coincurve() -> None:
    """Time coincurve's ECDSA signing, over a digest it is told not to hash."""
    prvkey, msg = next(DSA_SIGN_DER)
    coincurve.PrivateKey(prvkey).sign(msg, hasher=None)


def dsa_sign_der_secp256k1() -> None:
    """Time secp256k1-py's ECDSA signing, its parsed signature taken to DER.

    `ecdsa_sign` returns the parsed signature and no bytes, alone of the
    four: the serialization is a second call, made inside the timing
    because a signature nothing could store or send is not the operation
    the other three rows perform.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    key = secp256k1.PrivateKey(prvkey, raw=True)
    key.ecdsa_serialize(key.ecdsa_sign(msg, raw=True))


def dsa_sign_der_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA signing, DER through its own encoder.

    `ecdsa_sign` answers in 64 bytes, so DER is `ecdsa_der_sig_from_
    ecdsa_sig64` after it -- both electrum-ecc's, which is what this row
    is asked for. `grind_r_value=False` because the other three sign
    once, and `ecdsa_sign` verifies what it made before returning it, a
    check its API offers no way to decline and therefore part of what
    signing through electrum-ecc costs.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
        electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=False)
    )


def dsa_sign_der_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA signing, bytes in and DER out."""
    prvkey, msg = next(DSA_SIGN_DER)
    btclib_secp256k1.dsa.sign(msg, prvkey)


def dsa_sign_compact_secp256k1() -> None:
    """Time secp256k1-py's ECDSA signing, its signature taken to 64 bytes."""
    prvkey, msg = next(DSA_SIGN_COMPACT)
    key = secp256k1.PrivateKey(prvkey, raw=True)
    key.ecdsa_serialize_compact(key.ecdsa_sign(msg, raw=True))


def dsa_sign_compact_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA signing, in the 64 bytes its API answers in.

    One signature rather than a ground one, and the verification
    `ecdsa_sign` performs on its own account before returning: what
    signing through electrum-ecc costs, there being no spelling of it
    without.
    """
    prvkey, msg = next(DSA_SIGN_COMPACT)
    electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=False)


def dsa_sign_compact_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA signing, bytes in and 64 bytes out."""
    prvkey, msg = next(DSA_SIGN_COMPACT)
    btclib_secp256k1.dsa.sign(msg, prvkey, compact=True)


def ssa_sign_coincurve() -> None:
    """Time coincurve's BIP340 signing, the keypair and the check included.

    `sign_schnorr` builds the keypair fresh every call, its API caching
    none, and verifies the signature before returning it, which it offers
    no way to decline. Both are what signing through coincurve costs.
    """
    prvkey, msg = next(SSA_SIGN)
    coincurve.PrivateKey(prvkey).sign_schnorr(msg, AUX)


def ssa_sign_secp256k1() -> None:
    """Time secp256k1-py's BIP340 signing, its keypair built per call.

    `schnorr_sign` takes no key but the one its `PrivateKey` constructor
    already holds, so the constructor is inside the timing: the keypair
    every row builds, built where this API makes a caller build it. It
    takes no aux_rand either, alone of the four.
    """
    prvkey, msg = next(SSA_SIGN)
    secp256k1.PrivateKey(prvkey, raw=True).schnorr_sign(msg, None, raw=True)


def ssa_sign_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 signing, the keypair and the check included.

    `schnorr_sign` builds the keypair fresh every call and verifies the
    signature before returning it, neither of which its API lets a caller
    decline.
    """
    prvkey, msg = next(SSA_SIGN)
    electrum_ecc.ECPrivkey(prvkey).schnorr_sign(msg, aux_rand32=AUX)


def ssa_sign_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 signing, bytes in and 64 bytes out.

    Each call builds the keypair, signs, and overwrites the keypair before
    returning: the price of an API that holds no secret longer than the
    call that needed it.
    """
    prvkey, msg = next(SSA_SIGN)
    btclib_secp256k1.ssa.sign(msg, prvkey, AUX)


def parse_compressed_coincurve() -> None:
    """Time coincurve's parse of a compressed key, y recovered from x."""
    coincurve.PublicKey(next(PARSE_COMPRESSED))


def parse_compressed_secp256k1() -> None:
    """Time secp256k1-py's parse of a compressed key, x-only derived with it.

    Its constructor prepares for BIP340 as it parses, an extra the other
    three rows do not pay: its API has no parsing without it, so the row
    carries it here as it does in every verification below.
    """
    secp256k1.PublicKey(next(PARSE_COMPRESSED), raw=True)


def parse_compressed_electrum_ecc() -> None:
    """Time electrum-ecc's parse of a compressed key, out to two integers.

    `ECPubkey` holds x and y: the constructor parses the bytes and
    serializes the point back out to read them, and every later use
    parses again -- the cost its verify rows pay on top of this one.
    """
    electrum_ecc.ECPubkey(next(PARSE_COMPRESSED))


def parse_compressed_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's parse of a compressed key, bytes to object."""
    btclib_secp256k1.keys.parse(next(PARSE_COMPRESSED))


def parse_uncompressed_coincurve() -> None:
    """Time coincurve's parse of an uncompressed key, which carries its y."""
    coincurve.PublicKey(next(PARSE_UNCOMPRESSED))


def parse_uncompressed_secp256k1() -> None:
    """Time secp256k1-py's parse of an uncompressed key, x-only with it."""
    secp256k1.PublicKey(next(PARSE_UNCOMPRESSED), raw=True)


def parse_uncompressed_electrum_ecc() -> None:
    """Time electrum-ecc's parse of an uncompressed key, out to two integers."""
    electrum_ecc.ECPubkey(next(PARSE_UNCOMPRESSED))


def parse_uncompressed_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's parse of an uncompressed key, bytes to object."""
    btclib_secp256k1.keys.parse(next(PARSE_UNCOMPRESSED))


def dsa_verify_der_coincurve() -> None:
    """Time coincurve's ECDSA verification, which takes a DER signature."""
    pubkey, msg, sig = next(DSA_VERIFY_DER)
    coincurve.PublicKey(pubkey).verify(sig, msg, None)


def dsa_verify_der_secp256k1() -> None:
    """Time secp256k1-py's ECDSA verification, everything parsed per call.

    The `PublicKey` constructor is its parse, and it derives the x-only
    key as it goes -- BIP340 preparation this row never uses and cannot
    refuse.
    """
    pubkey, msg, sig = next(DSA_VERIFY_DER)
    parsed = secp256k1.PublicKey(pubkey, raw=True)
    parsed.ecdsa_verify(msg, parsed.ecdsa_deserialize(sig), raw=True)


def dsa_verify_der_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA verification of a DER signature.

    `ECPubkey.ecdsa_verify` takes the 64-byte form and nothing else, so
    the DER goes through `ecdsa_sig64_from_der_sig` first -- electrum-ecc's
    own, and the only spelling its API has for this.
    """
    pubkey, msg, sig = next(DSA_VERIFY_DER)
    electrum_ecc.ECPubkey(pubkey).ecdsa_verify(
        electrum_ecc.ecdsa_sig64_from_der_sig(sig), msg
    )


def dsa_verify_der_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA verification, bytes in every argument."""
    pubkey, msg, sig = next(DSA_VERIFY_DER)
    btclib_secp256k1.dsa.verify(msg, pubkey, sig)


def dsa_verify_compact_secp256k1() -> None:
    """Time secp256k1-py's ECDSA verification of a 64-byte signature."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT)
    parsed = secp256k1.PublicKey(pubkey, raw=True)
    parsed.ecdsa_verify(msg, parsed.ecdsa_deserialize_compact(sig), raw=True)


def dsa_verify_compact_electrum_ecc() -> None:
    """Time electrum-ecc's ECDSA verification, over the form its API takes."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT)
    electrum_ecc.ECPubkey(pubkey).ecdsa_verify(sig, msg)


def dsa_verify_compact_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA verification of a 64-byte signature."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT)
    btclib_secp256k1.dsa.verify(msg, pubkey, sig, compact=True)


def ssa_verify_coincurve() -> None:
    """Time coincurve's BIP340 verification, over an x-only public key."""
    xonly, msg, sig = next(SSA_VERIFY)
    coincurve.PublicKeyXOnly(xonly).verify(sig, msg)


def ssa_verify_secp256k1() -> None:
    """Time secp256k1-py's BIP340 verification, over a full public key."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    secp256k1.PublicKey(pubkey, raw=True).schnorr_verify(msg, sig, None, raw=True)


def ssa_verify_electrum_ecc() -> None:
    """Time electrum-ecc's BIP340 verification, x-only derived per call."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    electrum_ecc.ECPubkey(pubkey).schnorr_verify(sig, msg)


def ssa_verify_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's BIP340 verification, over an x-only key."""
    xonly, msg, sig = next(SSA_VERIFY)
    btclib_secp256k1.ssa.verify(msg, xonly, sig)


def tweak_coincurve() -> None:
    """Time coincurve's public key tweak, which returns a new PublicKey."""
    pubkey, tweak = next(TWEAK)
    coincurve.PublicKey(pubkey).add(tweak)


def tweak_secp256k1() -> None:
    """Time secp256k1-py's public key tweak, in place on a parsed key."""
    pubkey, tweak = next(TWEAK)
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak)


def tweak_electrum_ecc() -> None:
    """Time electrum-ecc's public key tweak, which its API spells in two calls.

    There is no tweak-add on `ECPubkey`: a scalar times the generator and a
    point addition is how the same tweak is reached, both libsecp256k1 calls.
    Two crossings where the others make one is the difference this table
    exists to show.
    """
    pubkey, tweak = next(TWEAK)
    (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    )


def tweak_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's public key tweak, bytes in and bytes out."""
    pubkey, tweak = next(TWEAK)
    btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak)


DSA_SIGN_DER_ROWS = (
    dsa_sign_der_coincurve,
    dsa_sign_der_secp256k1,
    dsa_sign_der_electrum_ecc,
    dsa_sign_der_btclib_secp256k1,
)
DSA_SIGN_COMPACT_ROWS = (
    dsa_sign_compact_secp256k1,
    dsa_sign_compact_electrum_ecc,
    dsa_sign_compact_btclib_secp256k1,
)
SSA_SIGN_ROWS = (
    ssa_sign_coincurve,
    ssa_sign_secp256k1,
    ssa_sign_electrum_ecc,
    ssa_sign_btclib_secp256k1,
)
PARSE_COMPRESSED_ROWS = (
    parse_compressed_coincurve,
    parse_compressed_secp256k1,
    parse_compressed_electrum_ecc,
    parse_compressed_btclib_secp256k1,
)
PARSE_UNCOMPRESSED_ROWS = (
    parse_uncompressed_coincurve,
    parse_uncompressed_secp256k1,
    parse_uncompressed_electrum_ecc,
    parse_uncompressed_btclib_secp256k1,
)
DSA_VERIFY_DER_ROWS = (
    dsa_verify_der_coincurve,
    dsa_verify_der_secp256k1,
    dsa_verify_der_electrum_ecc,
    dsa_verify_der_btclib_secp256k1,
)
DSA_VERIFY_COMPACT_ROWS = (
    dsa_verify_compact_secp256k1,
    dsa_verify_compact_electrum_ecc,
    dsa_verify_compact_btclib_secp256k1,
)
SSA_VERIFY_ROWS = (
    ssa_verify_coincurve,
    ssa_verify_secp256k1,
    ssa_verify_electrum_ecc,
    ssa_verify_btclib_secp256k1,
)
TWEAK_ROWS = (
    tweak_coincurve,
    tweak_secp256k1,
    tweak_electrum_ecc,
    tweak_btclib_secp256k1,
)

for _row in (
    DSA_SIGN_DER_ROWS
    + DSA_SIGN_COMPACT_ROWS
    + SSA_SIGN_ROWS
    + PARSE_COMPRESSED_ROWS
    + PARSE_UNCOMPRESSED_ROWS
    + DSA_VERIFY_DER_ROWS
    + DSA_VERIFY_COMPACT_ROWS
    + SSA_VERIFY_ROWS
    + TWEAK_ROWS
):
    _row()

# One count for every row, where the scripts that mix Python in need one per
# function: every row here is a call into C and they land within a factor of a
# few. Thirty rounds of it, and the row reports the *minimum*: interference on
# a shared machine only ever adds time, so the fastest round is the one least
# disturbed, and a mean would carry every interruption into the number.
#
# Thirty rather than a handful because the spread beside each row is a claim
# about how quiet the machine was, and a handful of rounds is too few to
# make one. It costs a few minutes per run, which is what a table read for
# years is worth.
ROUNDS = 30


def benchmark(func: Callable[[], None], calls: int) -> tuple[float, float]:
    """Return the quickest round's microseconds per call, and the spread.

    `ROUNDS` rounds of `calls` calls each. The minimum is the estimate: noise
    is one-sided -- nothing on this machine makes a call quicker than it is --
    so the quickest round is the one that ran with least taken from it, and a
    mean would carry every interruption into the number.

    The spread is how far the slowest round ran from the quickest, in the
    same microseconds as the value beside it, and it is printed rather than
    hidden because it is the only thing in the output that says whether the
    machine was quiet while a row was measured. Read it as the scatter of
    the rounds and not as an interval around that value: the value is the
    quickest of them and therefore sits at the low edge of what the spread
    describes, which is the price of an estimator that refuses to average
    in a machine's bad moments.
    """
    # perf_counter and not time(): the wall clock can step backwards under an
    # NTP correction, and a benchmark is the one place that shows up as a
    # negative duration
    rounds = []
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(calls):
            func()
        rounds.append((time.perf_counter() - start) / calls * 1e6)
    quickest = min(rounds)
    return quickest, max(rounds) - quickest


def measured(
    title: str,
    rows: tuple[Callable[[], None], ...],
    missing: tuple[str, ...] = (),
) -> Ratios:
    """Time every row of one operation and return them as a table.

    The sort and the ratio are the renderer's. The ratio is against the
    fastest row, whichever it turns out to be, so the top row reads 1.00x
    and every other says what it costs to use that one instead; against a
    named row the column would answer a question the reader did not ask on
    the runs where that row is not the quickest.

    Two decimals where the other scripts ask for one: every row here calls
    the same C and they land within a few percent of each other, so one
    decimal prints 1.0x for the whole column.

    `missing` names the packages whose API has no such call, and they are
    the rows that print `NA`. Reaching past one of them into the C it
    wraps would produce a number, and the number would not be the
    package's: what a reader comparing wrappers asks is what each one
    offers.

    Which row is being timed goes to stderr as it starts, and is overwritten
    by the next: a run is minutes of silence otherwise, and a reader who
    cannot tell a slow row from a hung one will reach for the interrupt. On
    stderr because stdout is the output somebody pastes, and a progress line
    in it is a line no run produced.
    """
    timings: list[Timing | Unavailable] = [Unavailable(label) for label in missing]
    for label, func in zip(labels([func.__name__ for func in rows]), rows, strict=True):
        print(
            f"\r{title.split('.', maxsplit=1)[0]:>2}. {label:<20}",
            end="",
            file=sys.stderr,
        )
        value, spread = benchmark(func, CALLS)
        timings.append(
            Timing(
                label=label,
                us_per_call=value,
                spread=spread,
                calls=CALLS,
                rounds=ROUNDS,
            )
        )
    # the table itself is about to be printed, so the line goes rather than
    # standing above numbers that have replaced it
    print("\r" + " " * 30 + "\r", end="", file=sys.stderr)
    return Ratios(title=title, decimals=2, rows=timings)


# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page, which is a fact about all nine
# tables and cannot be known while the first is being measured.
#
# Sign before verify, and the parses in between: tables 4 and 5 price on
# their own what every verification and every tweak repeats per call, so a
# reader meets that parse once before meeting it inside four more tables
TABLES: tuple[tuple[str, tuple[Callable[[], None], ...], tuple[str, ...]], ...] = (
    ("1. ECDSA sign (32-byte digest, DER out)", DSA_SIGN_DER_ROWS, ()),
    (
        "2. ECDSA sign (32-byte digest, 64-byte compact out)",
        DSA_SIGN_COMPACT_ROWS,
        ("coincurve",),
    ),
    ("3. BIP340 sign (32-byte message)", SSA_SIGN_ROWS, ()),
    ("4. public key parse (a 33-byte compressed key)", PARSE_COMPRESSED_ROWS, ()),
    ("5. public key parse (a 65-byte uncompressed key)", PARSE_UNCOMPRESSED_ROWS, ()),
    (
        "6. ECDSA verify (DER signature, the 65-byte key parsed per call)",
        DSA_VERIFY_DER_ROWS,
        (),
    ),
    (
        "7. ECDSA verify (64-byte signature, the 65-byte key parsed per call)",
        DSA_VERIFY_COMPACT_ROWS,
        ("coincurve",),
    ),
    (
        "8. BIP340 verify (32-byte message, the public key parsed per call)",
        SSA_VERIFY_ROWS,
        (),
    ),
    ("9. public key tweak by a scalar, which is BIP32's step", TWEAK_ROWS, ()),
)

# what the run block claims about how these numbers were taken, said by
# the script that takes them: `benchmark` above is where the thirty rounds
# and the minimum are, and the spread column is what a reader checks it by
METHOD = f"{counted_calls(ROUNDS, CALLS)}, minimum kept"


def main() -> None:
    """Print the six tables, one operation each, and save the run.

    No order is forced on the timing: with the pure-Python rows gone,
    nothing here changes state a later row would read. The order the rows
    are *printed* in is the measurement's own, fastest first, which is a
    property of the run rather than of this file.

    Each table is printed as it is measured, this being a run somebody
    watches, and printed through the same renderer that writes the page.
    """
    packages = provenance()
    print(rendered_provenance(packages))
    print()
    width = width_for(
        [
            label
            for _, rows, missing in TABLES
            for label in [*labels([f.__name__ for f in rows]), *missing]
        ]
    )
    tables = []
    for title, rows, missing in TABLES:
        table = measured(title, rows, missing)
        print(rendered_table(table, width, counted=True))
        print()
        tables.append(table)

    saved = save(
        Measurement(
            benchmark=page_of(__file__),
            run=taken_now(__file__, METHOD),
            provenance=packages,
            tables=tables,
            # the page says what a timing contains in its own prose, above
            # the block: the claim belongs to a reader who has not reached
            # the numbers yet, and repeating it inside them is furniture
            timing_note=[],
        )
    )
    print(f"saved to {saved}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
