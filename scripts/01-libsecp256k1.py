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
rows repeat per call. `electrum-ecc` has no tweak-add on `ECPubkey`, so it
reaches the same point as a scalar times the generator plus an addition: two
crossings where the others make one.

Signing and verifying are two tables each, one per serialization: DER, which
is what a transaction carries, and the 64-byte compact form, which is what a
caller holds. The difference between the two is an encoding rather than an
arithmetic, so what a pair of them prices is exactly what a serialization
costs.

Every operation that takes a public key is a pair over the two
serializations of one, 65 octets against 33, because that is where the cost
of a public key lives: the compressed form is an x whose y the parser has
to solve for, and the uncompressed form carries it. The parse tables are
that difference on its own, verification is it twice over, once per
signature encoding, and so is the tweak.

BIP340 verification is a pair for the same reason, over a different
difference. It verifies against an x-only key, and a caller either holds one
already or holds a public key the x-only form has to be taken from; the two
tables are the same signatures over the same keys in those two shapes, so a
package appearing in both prices the shape and nothing else -- and the
answer is the opposite way round from the wording: holding the x-only key
is the *expensive* case, because x-only is an x and a y that has to be
recovered, where 65 octets carry the y already. Which of the two an
API asks for is not uniform -- coincurve takes the x-only key and nothing
else, secp256k1-py and electrum-ecc build their key object from a full one --
so before this pair existed one table was quietly timing both conventions at
once.

Low-r grinding is a row rather than a table, as it is in the libraries page:
two of the four offer it, so what an ECDSA signing table carries is those two
rows beside their own ungrinding ones, and not a column half `NA`.
libsecp256k1 exports no such option -- `secp256k1_ecdsa_sign` takes a nonce
function and extra entropy, and grinding is a loop over that, which
electrum-ecc and btclib_secp256k1 each write in Python. It is therefore the
one comparison on this page whose subject is Python rather than a crossing.

The two spell it opposite ways round, and the rows are named for the call
rather than for the default: electrum-ecc grinds unless a caller passes
`grind_r_value=False`, btclib_secp256k1 does not grind unless a caller passes
`grind=True`. Which default is the better one is not a timing's question.

Checking the signature before answering with it is the other row of its kind,
and it is not one package's peculiarity: electrum-ecc verifies inside
`ecdsa_sign` and inside `schnorr_sign`, coincurve inside `sign_schnorr`, and
neither offers a way to decline it, so for those rows the check is simply part
of what signing there costs. secp256k1-py does it nowhere. btclib_secp256k1 is
the only one of the four that both does it and takes `verify=False`, which is
why it is the only one that can be a pair.

What that pair is for is that no single row of it compares with all three of
the others. The checked row is the operation electrum-ecc performs in both its
ECDSA rows and coincurve in its BIP340 one; the unchecked row is the operation
coincurve performs in ECDSA and secp256k1-py in both. Printing one of the two
and calling it btclib_secp256k1's signing time would make one of those
comparisons wrong, and which one would depend on which row was printed.

The grinding rows hold the check off on both sides, because a pair prices one
difference: btclib_secp256k1's grinding pair prices the loop, and
electrum-ecc's prices the loop with the check present in both its rows, that
API offering nothing else. So the two grinding ratios are comparable while the
rows they are ratios of differ by a check. There is no fourth row grinding
with the check on, and that is a measurement rather than an omission: the
check runs once, on the signature the loop settled on, so what it costs adds
to the grinding row instead of multiplying with it -- a row that would print
the sum of two the table already carries.

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

Every ordinary signing row signs once, grinding or not being a switch its
own row throws: without that, a signature made twice on average would be
compared against signatures made once, and the table would say a library is
slow where it is doing more. Verifying what was just signed is the same
arrangement one step down: where an API takes the argument, the row passes it
explicitly rather than inheriting a default, so what a row does is read off
the call and not off the version of the package installed.

## The public key is parsed inside every timing

Two of the four leave no choice: `btclib_secp256k1` takes bytes and parses per
call, and electrum-ecc's `ECPubkey` holds x and y as Python integers and
parses a `secp256k1_pubkey` again on every verify. coincurve and secp256k1-py
could each be handed a parsed key once and are not, for the reason no row is
handed anything: a row skipping what two of the four cannot skip would be
timing a different operation. Tables 1 and 2 price that parse on its own,
ahead of the verify tables that repeat it -- so a reader meets the
subtraction before the total, and can read either against it to see how much
of a verification is the parse -- and for secp256k1-py the parse is its
`PublicKey` constructor, which derives the x-only key as it goes: preparation
for BIP340 its API performs whether the caller came for it or not.

The signature is another matter: each row takes the encoding its own API asks
for, and converting between encodings happens once, in the fixtures. What a
sign row hands back is bytes in every case: secp256k1-py's `ecdsa_sign` alone
returns its parsed signature, so its row serializes it to DER, bytes being
what the other three hand back.

A tweak hands back octets for the same reason, and only one of the four does
so on its own: `pubkey_tweak_add` answers with a serialized key where
coincurve and secp256k1-py answer with a key object of theirs and
electrum-ecc with an `ECPubkey`. Timing each API's own answer would compare a
tweak-and-serialize against a tweak, which is not one operation, so every row
ends at octets and pays the call its API makes a caller write to get them --
`.format()`, `.serialize()`, `get_public_key_bytes()`. Octets rather than the
objects because a tweak whose result is never serialized is not BIP32's step:
what derivation does with a child key is store it.

The 33 of them are the same 33 in both tweak tables, the pair varying the key
that goes *in* and nothing else. Answering each table in the encoding it was
handed would price two differences at once and leave the pair reading as
neither.

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
# How much of the pool each table reads, and each reads a different part of
# it: a key signed in the first table is not the key verified in a later
# one, so no row is quick because something before it warmed a cache with
# the same bytes.
#
# The two BIP340 verification tables are the exception, and share a slice
# on purpose: they are the same signatures over the same keys, handed over
# in the two forms BIP340 leaves a caller holding, so sharing is what makes
# their pair price the form and nothing else.
#
# Not the same thing as a row's call count, which is chosen further down
# for how long it makes a round last: a table whose count exceeds its slice
# reads the slice more than once per round, which is what the pool is sized
# to allow.
SLICE = 10_000


def _slice(table: int, of: list[bytes]) -> list[bytes]:
    """Return the `SLICE` elements table `table` reads, counting from one."""
    return of[(table - 1) * SLICE : table * SLICE]


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
# call that needs it, where the caller pays it. A cycle is exactly `SLICE`
# long, so a row's round is its table's slice once through, and the four
# rows of a table are compared over the same inputs in the same order
DSA_SIGN_DER = cycle(list(zip(_slice(1, PRVKEYS), _slice(1, MESSAGES), strict=True)))
DSA_SIGN_COMPACT = cycle(
    list(zip(_slice(2, PRVKEYS), _slice(2, MESSAGES), strict=True))
)
SSA_SIGN = cycle(list(zip(_slice(3, PRVKEYS), _slice(3, MESSAGES), strict=True)))
PARSE_COMPRESSED = cycle(_slice(4, PUBKEYS_COMPRESSED))
PARSE_UNCOMPRESSED = cycle(_slice(5, PUBKEYS))
# ECDSA verification is four tables, one per pair of encodings: the
# signature in DER or in 64 bytes, and the key in 65 or 33. Each pair over
# a key form shares its slice with the other, so what a pair prices is the
# encoding and not the input
DSA_VERIFY_DER = cycle(
    list(zip(_slice(6, PUBKEYS), _slice(6, MESSAGES), DSA_SIGS, strict=True))
)
DSA_VERIFY_DER_33 = cycle(
    list(zip(_slice(6, PUBKEYS_COMPRESSED), _slice(6, MESSAGES), DSA_SIGS, strict=True))
)
DSA_VERIFY_COMPACT = cycle(
    list(zip(_slice(7, PUBKEYS), _slice(7, MESSAGES), DSA_SIGS_COMPACT, strict=True))
)
DSA_VERIFY_COMPACT_33 = cycle(
    list(
        zip(
            _slice(7, PUBKEYS_COMPRESSED),
            _slice(7, MESSAGES),
            DSA_SIGS_COMPACT,
            strict=True,
        )
    )
)
# BIP340 verifies against an x-only key, and a caller either holds one or
# holds a public key it has to be taken from. The two cycles are the same
# signatures over the same keys in the two forms, so a package appearing in
# both prices exactly that difference
SSA_VERIFY = cycle(
    list(zip(_slice(8, XONLY), _slice(8, MESSAGES), SSA_SIGS, strict=True))
)
SSA_VERIFY_FULL = cycle(
    list(zip(_slice(8, PUBKEYS), _slice(8, MESSAGES), SSA_SIGS, strict=True))
)
# each public key tweaked by the secret key it came from
# and the tweak over the same pair of key forms, sharing its slice for the
# same reason
TWEAK = cycle(list(zip(_slice(9, PUBKEYS), _slice(9, PRVKEYS), strict=True)))
TWEAK_33 = cycle(
    list(zip(_slice(9, PUBKEYS_COMPRESSED), _slice(9, PRVKEYS), strict=True))
)


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
    "btclib-secp256k1": ("main@68657e14c47c", "v0.8.0"),
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
    """Time btclib_secp256k1's ECDSA signing, bytes in and DER out.

    `verify=False`, which is one signature and nothing else: the row this
    is comparable with is coincurve's above it and secp256k1-py's, neither
    of which checks what it made. The package's own default is the other
    way round, so this passes the argument rather than relying on it --
    the row states what it timed, and a default that moved would move a
    number without moving a word.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    btclib_secp256k1.dsa.sign(msg, prvkey, verify=False)


def dsa_sign_der_btclib_secp256k1_checked() -> None:
    """Time the same signature with the check the package defaults to.

    `verify=True`: the signature is verified under the public key of the
    key that made it before it is answered with, which costs that
    verification and the point multiplication the public key takes --
    ECDSA needing it for neither of the two things signing does, where
    BIP340 has it already. What the pair prices is exactly that.

    This is the row electrum-ecc's is comparable with, its `ecdsa_sign`
    performing the same check and offering no way to decline it. The
    signature is the same octets either way, which is why the two rows
    are one operation asked twice rather than two operations.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    btclib_secp256k1.dsa.sign(msg, prvkey, verify=True)


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


def dsa_sign_der_electrum_ecc_grind() -> None:
    """Time electrum-ecc's ECDSA signing with the low-r grinding it defaults to.

    The row above it with `grind_r_value=False` is one signature; this is
    however many the message takes before r fits in 32 bytes, half of all
    draws fitting already. The ratio between the two is what the grinding
    costs, and it is a property of the message rather than of the library.

    Two of the four offer it, and both write it themselves: libsecp256k1
    exports no such option -- `secp256k1_ecdsa_sign` takes a nonce
    function and extra entropy, and grinding is a loop over that. So the
    pair of grinding rows in each of these two tables is the one place on
    this page where what is compared is Python rather than a crossing.
    coincurve and secp256k1-py write no such loop, and a row for them
    would be this repository's rather than theirs.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
        electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=True)
    )


def dsa_sign_compact_electrum_ecc_grind() -> None:
    """Time electrum-ecc's grinding signature, in the form it answers in.

    The compact half of the pair above: the same loop, without the DER
    conversion its own module carries.
    """
    prvkey, msg = next(DSA_SIGN_COMPACT)
    electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=True)


def dsa_sign_der_btclib_secp256k1_grind() -> None:
    """Time btclib_secp256k1's ECDSA signing with low-r grinding asked for.

    `grind=True` rather than a default, which is the difference from the
    other grinding pair here: electrum-ecc grinds unless told not to, and
    this package never grinds unless told to. What each row costs is the
    same question either way, and the two defaults are a separate one.

    Core's `CKey::Sign` scheme, a counter mixed into the nonce and signed
    again until r's high bit is clear, so the signature is the one any
    other implementation of that scheme would reach.

    `verify=False` here as in the row this is a pair with, so what the
    pair prices is the loop: the check runs once whatever the loop did,
    and holding it off on both sides is what keeps the grinding the only
    difference between them.
    """
    prvkey, msg = next(DSA_SIGN_DER)
    btclib_secp256k1.dsa.sign(msg, prvkey, grind=True, verify=False)


def dsa_sign_compact_btclib_secp256k1_grind() -> None:
    """Time the same grinding signature, answered in 64 octets.

    `compact=True` is the serialization asked of the same call, not a
    conversion after it: what r's high bit saves is a DER octet, so the
    compact row grinds for a byte it does not spend, and the pair is
    what that costs in each encoding.
    """
    prvkey, msg = next(DSA_SIGN_COMPACT)
    btclib_secp256k1.dsa.sign(msg, prvkey, compact=True, grind=True, verify=False)


def dsa_sign_compact_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's ECDSA signing, bytes in and 64 bytes out.

    `verify=False`, as the DER row above says.
    """
    prvkey, msg = next(DSA_SIGN_COMPACT)
    btclib_secp256k1.dsa.sign(msg, prvkey, compact=True, verify=False)


def dsa_sign_compact_btclib_secp256k1_checked() -> None:
    """Time the same signature checked, in the form the same call answers in.

    The compact half of the pair the DER table carries, and it prices the
    same check: what is verified is the signature rather than its
    encoding, so this row and its DER twin differ by a serialization and
    by nothing the check does.
    """
    prvkey, msg = next(DSA_SIGN_COMPACT)
    btclib_secp256k1.dsa.sign(msg, prvkey, compact=True, verify=True)


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

    `verify=False`, which leaves secp256k1-py's row above as the one this
    is comparable with: BIP340's *Default Signing* ends with the check,
    and of the four only this package lets a caller stop short of it.
    """
    prvkey, msg = next(SSA_SIGN)
    btclib_secp256k1.ssa.sign(msg, prvkey, AUX, verify=False)


def ssa_sign_btclib_secp256k1_checked() -> None:
    """Time the same BIP340 signature with BIP340's own last step done.

    `verify=True`, and the pair with the row above is what that step
    costs. It is the cheaper of the two checks this page prices, and the
    reason is the keypair: BIP340 needs the public key to sign at all, so
    the point is already in hand where ECDSA has to derive it.

    This is the row coincurve's and electrum-ecc's are comparable with,
    both of them verifying inside the signing call and neither offering
    the argument that would stop it.
    """
    prvkey, msg = next(SSA_SIGN)
    btclib_secp256k1.ssa.sign(msg, prvkey, AUX, verify=True)


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


def dsa_verify_der_33_coincurve() -> None:
    """Time coincurve's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_DER_33)
    coincurve.PublicKey(pubkey).verify(sig, msg, None)


def dsa_verify_der_33_secp256k1() -> None:
    """Time secp256k1-py's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_DER_33)
    parsed = secp256k1.PublicKey(pubkey, raw=True)
    parsed.ecdsa_verify(msg, parsed.ecdsa_deserialize(sig), raw=True)


def dsa_verify_der_33_electrum_ecc() -> None:
    """Time electrum-ecc's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_DER_33)
    electrum_ecc.ECPubkey(pubkey).ecdsa_verify(
        electrum_ecc.ecdsa_sig64_from_der_sig(sig), msg
    )


def dsa_verify_der_33_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_DER_33)
    btclib_secp256k1.dsa.verify(msg, pubkey, sig)


def dsa_verify_compact_33_secp256k1() -> None:
    """Time secp256k1-py's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT_33)
    parsed = secp256k1.PublicKey(pubkey, raw=True)
    parsed.ecdsa_verify(msg, parsed.ecdsa_deserialize_compact(sig), raw=True)


def dsa_verify_compact_33_electrum_ecc() -> None:
    """Time electrum-ecc's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT_33)
    electrum_ecc.ECPubkey(pubkey).ecdsa_verify(sig, msg)


def dsa_verify_compact_33_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's, the same call over the compressed key."""
    pubkey, msg, sig = next(DSA_VERIFY_COMPACT_33)
    btclib_secp256k1.dsa.verify(msg, pubkey, sig, compact=True)


def ssa_verify_xonly_coincurve() -> None:
    """Time coincurve's BIP340 verification, over the x-only key it takes."""
    xonly, msg, sig = next(SSA_VERIFY)
    coincurve.PublicKeyXOnly(xonly).verify(sig, msg)


def ssa_verify_xonly_secp256k1() -> None:
    """Time secp256k1-py's, whose key object is built from a full key.

    Its API has no x-only constructor, so the even-y key the 32 bytes
    stand for is what it is handed: BIP340 defines the x-only form as the
    point with even y, so the prefix is the encoding rather than a choice.
    """
    xonly, msg, sig = next(SSA_VERIFY)
    secp256k1.PublicKey(b"\x02" + xonly, raw=True).schnorr_verify(
        msg, sig, None, raw=True
    )


def ssa_verify_xonly_electrum_ecc() -> None:
    """Time electrum-ecc's, its `ECPubkey` built from the same even-y key."""
    xonly, msg, sig = next(SSA_VERIFY)
    electrum_ecc.ECPubkey(b"\x02" + xonly).schnorr_verify(sig, msg)


def ssa_verify_xonly_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's, which takes the x-only key as it is."""
    xonly, msg, sig = next(SSA_VERIFY)
    btclib_secp256k1.ssa.verify(msg, xonly, sig)


def ssa_verify_derived_secp256k1() -> None:
    """Time secp256k1-py's over a full key, the x-only one taken from it.

    Its `PublicKey` constructor derives the x-only key as it parses, which
    is the work this table prices against the one above.
    """
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    secp256k1.PublicKey(pubkey, raw=True).schnorr_verify(msg, sig, None, raw=True)


def ssa_verify_derived_electrum_ecc() -> None:
    """Time electrum-ecc's over a full key, which is what `ECPubkey` takes."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    electrum_ecc.ECPubkey(pubkey).schnorr_verify(sig, msg)


def ssa_verify_derived_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's over a full key, which its API also accepts."""
    pubkey, msg, sig = next(SSA_VERIFY_FULL)
    btclib_secp256k1.ssa.verify(msg, pubkey, sig)


def tweak_coincurve() -> None:
    """Time coincurve's public key tweak, taken to the 33 octets of a key."""
    pubkey, tweak = next(TWEAK)
    coincurve.PublicKey(pubkey).add(tweak).format(compressed=True)


def tweak_secp256k1() -> None:
    """Time secp256k1-py's public key tweak, taken to 33 octets.

    Its `tweak_add` works in place on the parsed key and answers with it,
    so the serialization is a second call where two of the four make one.
    """
    pubkey, tweak = next(TWEAK)
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak).serialize(compressed=True)


def tweak_electrum_ecc() -> None:
    """Time electrum-ecc's public key tweak, which its API spells in two calls.

    There is no tweak-add on `ECPubkey`: a scalar times the generator and a
    point addition is how the same tweak is reached, both libsecp256k1 calls.
    Two crossings where the others make one is the difference this table
    exists to show, and the serialization at the end is a third.
    """
    pubkey, tweak = next(TWEAK)
    (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    ).get_public_key_bytes(compressed=True)


def tweak_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's public key tweak, bytes in and bytes out."""
    pubkey, tweak = next(TWEAK)
    btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak, compressed=True)


def tweak_33_coincurve() -> None:
    """Time coincurve's tweak over the compressed key, 33 octets out."""
    pubkey, tweak = next(TWEAK_33)
    coincurve.PublicKey(pubkey).add(tweak).format(compressed=True)


def tweak_33_secp256k1() -> None:
    """Time secp256k1-py's tweak over the compressed key, 33 octets out."""
    pubkey, tweak = next(TWEAK_33)
    secp256k1.PublicKey(pubkey, raw=True).tweak_add(tweak).serialize(compressed=True)


def tweak_33_electrum_ecc() -> None:
    """Time electrum-ecc's two-call tweak over the compressed key."""
    pubkey, tweak = next(TWEAK_33)
    (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    ).get_public_key_bytes(compressed=True)


def tweak_33_btclib_secp256k1() -> None:
    """Time btclib_secp256k1's tweak over the compressed key, 33 octets out."""
    pubkey, tweak = next(TWEAK_33)
    btclib_secp256k1.keys.pubkey_tweak_add(pubkey, tweak, compressed=True)


DSA_SIGN_DER_ROWS = (
    dsa_sign_der_coincurve,
    dsa_sign_der_secp256k1,
    dsa_sign_der_electrum_ecc,
    dsa_sign_der_electrum_ecc_grind,
    dsa_sign_der_btclib_secp256k1,
    dsa_sign_der_btclib_secp256k1_checked,
    dsa_sign_der_btclib_secp256k1_grind,
)
DSA_SIGN_COMPACT_ROWS = (
    dsa_sign_compact_secp256k1,
    dsa_sign_compact_electrum_ecc,
    dsa_sign_compact_electrum_ecc_grind,
    dsa_sign_compact_btclib_secp256k1,
    dsa_sign_compact_btclib_secp256k1_checked,
    dsa_sign_compact_btclib_secp256k1_grind,
)
SSA_SIGN_ROWS = (
    ssa_sign_coincurve,
    ssa_sign_secp256k1,
    ssa_sign_electrum_ecc,
    ssa_sign_btclib_secp256k1,
    ssa_sign_btclib_secp256k1_checked,
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
DSA_VERIFY_DER_33_ROWS = (
    dsa_verify_der_33_coincurve,
    dsa_verify_der_33_secp256k1,
    dsa_verify_der_33_electrum_ecc,
    dsa_verify_der_33_btclib_secp256k1,
)
DSA_VERIFY_COMPACT_33_ROWS = (
    dsa_verify_compact_33_secp256k1,
    dsa_verify_compact_33_electrum_ecc,
    dsa_verify_compact_33_btclib_secp256k1,
)
TWEAK_33_ROWS = (
    tweak_33_coincurve,
    tweak_33_secp256k1,
    tweak_33_electrum_ecc,
    tweak_33_btclib_secp256k1,
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
SSA_VERIFY_XONLY_ROWS = (
    ssa_verify_xonly_coincurve,
    ssa_verify_xonly_secp256k1,
    ssa_verify_xonly_electrum_ecc,
    ssa_verify_xonly_btclib_secp256k1,
)
SSA_VERIFY_DERIVED_ROWS = (
    ssa_verify_derived_secp256k1,
    ssa_verify_derived_electrum_ecc,
    ssa_verify_derived_btclib_secp256k1,
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
    + DSA_VERIFY_DER_33_ROWS
    + DSA_VERIFY_COMPACT_ROWS
    + DSA_VERIFY_COMPACT_33_ROWS
    + SSA_VERIFY_XONLY_ROWS
    + SSA_VERIFY_DERIVED_ROWS
    + TWEAK_ROWS
    + TWEAK_33_ROWS
):
    _row()

# What a row costs is `CALLS` calls, `ROUNDS` times, and the minimum of
# those rounds is the number. The two constants answer different questions
# and were chosen by measuring, not by taste.
#
# `CALLS` sets how long one round lasts, and that is what a round's
# minimum is worth: a round short enough to catch one scheduling slice
# carries it whole, where a long one leaves the interruption a smaller
# share of what it is dividing. The counts below were chosen by measuring
# that against the column as it was then -- a maximum minus a minimum,
# where a round under twenty-five milliseconds scattered by tens of
# percent on an operation whose minimum was steady to one -- and that
# measurement no longer describes the column, which is now a difference of
# two minima. The direction it argued for is unchanged and the reasoning
# under `ROUNDS` below is now the reasoning for both: more calls make each
# half's minimum better, so the counts stand and the number that chose
# them does not.
#
# What is certainly still true is why the count is per table rather than
# shared: the operations on this page are two orders of magnitude apart in
# cost, and one count for all of them would leave the parse tables
# measuring the clock.
#
# `ROUNDS` buys chances at a quiet round, and the minimum converges almost
# at once: three rounds and a hundred agree to within a percent. More of
# them cost minutes and buy little, and they no longer cost the `spread`
# anything either -- each half's minimum is the better for having more
# rounds behind it, so the two halves sit closer, where a maximum minus a
# minimum grew with every sample taken. Ten is where the minimum has
# settled, and it is even, which the halves want.
DEFAULT_CALLS = 10_000

# the two parse tables, whose operations are the cheapest on the page: a
# 65-byte parse reads two coordinates and costs a fraction of a
# microsecond, so ten thousand of them is a round of under three
# milliseconds. These counts put both rounds where the rest of the page
# already is
CALLS_PER_TABLE = {1: 400_000, 2: 100_000}

ROUNDS = 10


def benchmark(func: Callable[[], None], calls: int) -> tuple[float, float]:
    """Return the quickest round's microseconds per call, and the spread.

    `ROUNDS` rounds of `calls` calls each. The minimum is the estimate: noise
    is one-sided -- nothing on this machine makes a call quicker than it is --
    so the quickest round is the one that ran with least taken from it, and a
    mean would carry every interruption into the number.

    The spread is how far that estimate moved when the row was measured
    twice, which is what the rounds are halved for: the column is the
    distance between the two halves' minima. That is the one question the
    column is read for -- whether a gap between two adjacent rows is a gap
    this run settled -- and it answers it in the same microseconds as the
    value beside it, so the two are read against each other without
    arithmetic. Contiguous halves rather than alternate rounds, because the
    rows of a table are measured minutes apart and a machine that drifts
    over a row's rounds will drift over a table's rows.

    The column is quantized and lands on a lattice, which is worth knowing
    before reading a small value on it: a round is measured to one tick of
    `perf_counter` -- about 42 nanoseconds here -- and divided by the call
    count, so every spread this script prints is a whole number of ticks
    divided by that count. Zero is one of the lattice's points and means
    the two halves' minima fell inside one tick. It is not an unmeasured
    row: `_results.py` leaves an absent spread out of the saved run rather
    than writing it as zero.

    Two halves seconds apart say nothing about two runs a day apart, and the
    page says so where the column is explained: a row can move by more than
    any spread on it between one run and the next, which is why these
    tables are read as an order of magnitude and by ratio.

    What the column must not be is the slowest round less the quickest. That
    is an extreme-value statistic over ten samples, so it has enormous
    variance by construction and reports the worst interruption a row
    happened to catch rather than anything about the package: measured on
    this machine, the same four signing rows timed twice in one process
    printed minima agreeing to a hundredth of a microsecond and maxima
    disagreeing by a factor of forty. Nor is the garbage collector the
    mechanism, which was checked rather than assumed -- `gc.get_stats()`
    reported zero collections in every generation across those rounds, and
    the wilder of the two runs was the one taken under `gc.disable()`. More
    rounds make a maximum worse and both halves' minima better, which is the
    other reason this column is not that one.
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
    # halved on what the loop above actually produced rather than on
    # `ROUNDS`, the two being the same number until somebody changes one
    half = len(rounds) // 2
    first, second = min(rounds[:half]), min(rounds[half:])
    return min(first, second), abs(first - second)


def measured(
    title: str,
    rows: tuple[Callable[[], None], ...],
    missing: tuple[str, ...] = (),
    group: str = "",
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

    `group` is the operation the table belongs to, which the page carries
    as a section of its own: six operations, thirteen tables, and the
    renderer puts each table under the heading its group names.

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
        calls = CALLS_PER_TABLE.get(int(title.split(".", maxsplit=1)[0]), DEFAULT_CALLS)
        value, spread = benchmark(func, calls)
        timings.append(
            Timing(
                label=label,
                us_per_call=value,
                spread=spread,
                calls=calls,
                rounds=ROUNDS,
            )
        )
    # the table itself is about to be printed, so the line goes rather than
    # standing above numbers that have replaced it
    print("\r" + " " * 30 + "\r", end="", file=sys.stderr)
    return Ratios(title=title, decimals=2, rows=timings, group=group)


# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page, which is a fact about all thirteen
# tables and cannot be known while the first is being measured.
#
# The order is the page's argument rather than the operations' importance:
# the parse pair comes first because every verification and every tweak
# repeats one of those parses per call, so a reader meets it isolated before
# meeting it eight more times inside something else. Verifying, then
# tweaking, are those eight. Signing is last because it parses no public key
# at all, and BIP340 signing last of the two because what its table costs is
# read against the ECDSA one above it.
#
# Within a pair the cheaper encoding leads, so the pair reads as what the
# shorter one costs rather than as what the longer one saves
TABLES: tuple[tuple[str, tuple[Callable[[], None], ...], tuple[str, ...], str], ...] = (
    (
        "1. public key parse (a 65-byte uncompressed key)",
        PARSE_UNCOMPRESSED_ROWS,
        (),
        "parse",
    ),
    (
        "2. public key parse (a 33-byte compressed key)",
        PARSE_COMPRESSED_ROWS,
        (),
        "parse",
    ),
    (
        "3. ECDSA verify (DER signature, a 65-byte key parsed per call)",
        DSA_VERIFY_DER_ROWS,
        (),
        "dsa-verify",
    ),
    (
        "4. ECDSA verify (DER signature, a 33-byte key parsed per call)",
        DSA_VERIFY_DER_33_ROWS,
        (),
        "dsa-verify",
    ),
    (
        "5. ECDSA verify (64-byte signature, a 65-byte key parsed per call)",
        DSA_VERIFY_COMPACT_ROWS,
        ("coincurve",),
        "dsa-verify",
    ),
    (
        "6. ECDSA verify (64-byte signature, a 33-byte key parsed per call)",
        DSA_VERIFY_COMPACT_33_ROWS,
        ("coincurve",),
        "dsa-verify",
    ),
    (
        "7. BIP340 verify (a 65-byte key handed in, the x-only one taken from it)",
        SSA_VERIFY_DERIVED_ROWS,
        ("coincurve",),
        "ssa-verify",
    ),
    (
        "8. BIP340 verify (the x-only key handed in, parsed per call)",
        SSA_VERIFY_XONLY_ROWS,
        (),
        "ssa-verify",
    ),
    ("9. public key tweak by a scalar, a 65-byte key", TWEAK_ROWS, (), "tweak"),
    ("10. public key tweak by a scalar, a 33-byte key", TWEAK_33_ROWS, (), "tweak"),
    ("11. ECDSA sign (32-byte digest, DER out)", DSA_SIGN_DER_ROWS, (), "dsa-sign"),
    (
        "12. ECDSA sign (32-byte digest, 64-byte compact out)",
        DSA_SIGN_COMPACT_ROWS,
        ("coincurve",),
        "dsa-sign",
    ),
    ("13. BIP340 sign (32-byte message)", SSA_SIGN_ROWS, (), "ssa-sign"),
)

# what the run block claims about how these numbers were taken, said by
# the script that takes them: `benchmark` above is where the rounds and the
# minimum are, and the spread column is what a reader checks it by
# kept short enough that the rendered line stays inside 80 columns, the
# label it is printed under costing ten of them
METHOD = f"{ROUNDS} rounds per row in two halves, minimum kept; calls per table"


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
            for _, rows, missing, _group in TABLES
            for label in [*labels([f.__name__ for f in rows]), *missing]
        ]
    )
    tables = []
    for title, rows, missing, group in TABLES:
        table = measured(title, rows, missing, group)
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
