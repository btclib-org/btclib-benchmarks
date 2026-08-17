# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every operation `scripts/01-libsecp256k1.py` times, answered correctly.

That benchmark asserts nothing: a timed loop calls one wrapper API and
discards the answer, and the page says in as many words that whether these
packages answer correctly is the suite's subject. This module is the half of
that sentence which lives here, for the operations `vectors_test.py` does not
reach -- it runs BIP340 verification against the x-only key, BIP340 signing,
and ECDSA verification of a DER signature under an uncompressed key, and
those three are where its published files stop.

What is left is signing ECDSA, grinding for a low r, parsing a public key,
verifying under a compressed key or a compact signature, verifying BIP340
against a full public key, and tweaking a point. No file publishes vectors
for most of them, so what is checked instead is agreement: four
implementations of one library must answer identically, and where a property
can be stated without a second implementation -- a ground signature has a low
r, a parse round-trips, the tweak does not depend on how the key was
serialized -- it is stated.

Adversarial encodings are the gap that closes last, and only for DER.
Wycheproof's bitcoin file is where they come from and its subject is a
length field, so a case whose point is a BER long form has no compact form
to hand a verifier. What the compact rows get instead is built here, from a
signature that is valid: r or s zero, either at the group order or above it,
and the malleable half of the pair -- the ways 64 octets are wrong that
flipping a bit does not reach. The last of them is where the four stop
agreeing, and the disagreement is between one package's own two rows.

Every case goes through the same package API the benchmark times. Reaching
into the cffi or ctypes bindings underneath would test libsecp256k1, which is
not what a row of that page is about, and would pass while the wrapper around
it was broken.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

import _vectors
import btclib_secp256k1.dsa
import btclib_secp256k1.keys
import btclib_secp256k1.ssa
import coincurve
import electrum_ecc
import pytest
import secp256k1
import secp256k1lab.secp256k1

# the published BIP340 rows that carry a secret key, which is what makes them
# usable here: this module needs keys and messages rather than signatures,
# the signatures it checks being ones it makes
SIGNING = _vectors.signing()

# Wycheproof's file, whose subject is the encoding of a signature rather than
# the arithmetic under it -- the cases that separate a parser from a verifier
WYCHEPROOF = _vectors.wycheproof()

# the group order, taken from the one comparand that spells it as a number
# rather than as a compiled constant. Two cases below turn on it: a digest at
# or above it has two defensible nonces, and an r or an s at or above it is a
# signature nothing should accept
ORDER = secp256k1lab.secp256k1.Scalar.SIZE

# the rows whose message is below the group order, which is every one but a
# single published vector of thirty-two 0xff octets. RFC6979 derives its
# nonce through `bits2octets`, which reduces the digest modulo the order,
# where libsecp256k1's `nonce_function_rfc6979` is handed the thirty-two
# octets unreduced -- so for a digest at or above the order there are two
# defensible nonces and no single right signature. Both verify, and which one
# a wrapper reaches was observed to depend on the platform: the four agree on
# an Apple M5 and one of them disagrees on Linux.
#
# It is only the *agreement* cases this excludes. Every property below --
# grinding reaching a low r, a signature verifying, a parse round-tripping --
# is asked of that vector like any other
AGREEING = [vector for vector in SIGNING if int.from_bytes(vector.msg, "big") < ORDER]


def _agreeing_ids() -> list[str]:
    """Name the agreement cases for the vectors they came from."""
    return [f"bip340-{vector.number}" for vector in AGREEING]


def _ids() -> list[str]:
    """Name each case for the vector it came from."""
    return [f"bip340-{vector.number}" for vector in SIGNING]


# --- secp256k1-py, whose API takes two calls where the others take one ---


def _secp256k1_py_sign_der(msg: bytes, prvkey: bytes) -> bytes:
    """Sign through secp256k1-py, its parsed signature taken to DER.

    A named function rather than a lambda in each map below, four times
    over: `ecdsa_sign` answers a parsed signature and no octets, so the key
    object is wanted twice and there is nothing to inline.
    """
    key = secp256k1.PrivateKey(prvkey, raw=True)
    return bytes(key.ecdsa_serialize(key.ecdsa_sign(msg, raw=True)))


def _secp256k1_py_sign_compact(msg: bytes, prvkey: bytes) -> bytes:
    """Sign through secp256k1-py, answered in the 64 octets of r and s."""
    key = secp256k1.PrivateKey(prvkey, raw=True)
    return bytes(key.ecdsa_serialize_compact(key.ecdsa_sign(msg, raw=True)))


def _secp256k1_py_verify_der(msg: bytes, pubkey: bytes, sig: bytes) -> bool:
    """Verify a DER signature through secp256k1-py."""
    key = secp256k1.PublicKey(pubkey, raw=True)
    return bool(key.ecdsa_verify(msg, key.ecdsa_deserialize(sig), raw=True))


def _secp256k1_py_verify_compact(msg: bytes, pubkey: bytes, sig: bytes) -> bool:
    """Verify a 64-octet signature through secp256k1-py."""
    key = secp256k1.PublicKey(pubkey, raw=True)
    return bool(key.ecdsa_verify(msg, key.ecdsa_deserialize_compact(sig), raw=True))


# --- what each wrapper is asked, one entry per package ------------------


# `verify=False` wherever btclib_secp256k1 signs here, because that is what
# the benchmark's row passes and this module exists to check what the
# benchmark times. What the argument is worth is a case of its own below,
# and it is the case the pair of rows depends on
DSA_SIGNERS_DER: dict[str, Callable[[bytes, bytes], bytes]] = {
    "btclib_secp256k1": lambda msg, prvkey: btclib_secp256k1.dsa.sign(
        msg, prvkey, verify=False
    ),
    "coincurve": lambda msg, prvkey: coincurve.PrivateKey(prvkey).sign(
        msg, hasher=None
    ),
    "secp256k1-py": _secp256k1_py_sign_der,
    "electrum-ecc": lambda msg, prvkey: electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
        electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=False)
    ),
}

DSA_SIGNERS_COMPACT: dict[str, Callable[[bytes, bytes], bytes]] = {
    "btclib_secp256k1": lambda msg, prvkey: btclib_secp256k1.dsa.sign(
        msg, prvkey, compact=True, verify=False
    ),
    "secp256k1-py": _secp256k1_py_sign_compact,
    "electrum-ecc": lambda msg, prvkey: electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(
        msg, grind_r_value=False
    ),
}

# the two that grind, in DER and in the compact form. Core's `CKey::Sign`
# scheme in both, which is why they are compared with each other and not
# only against the property
DSA_GRINDERS_DER: dict[str, Callable[[bytes, bytes], bytes]] = {
    "btclib_secp256k1": lambda msg, prvkey: btclib_secp256k1.dsa.sign(
        msg, prvkey, grind=True, verify=False
    ),
    "electrum-ecc": lambda msg, prvkey: electrum_ecc.ecdsa_der_sig_from_ecdsa_sig64(
        electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(msg, grind_r_value=True)
    ),
}

DSA_GRINDERS_COMPACT: dict[str, Callable[[bytes, bytes], bytes]] = {
    "btclib_secp256k1": lambda msg, prvkey: btclib_secp256k1.dsa.sign(
        msg, prvkey, compact=True, grind=True, verify=False
    ),
    "electrum-ecc": lambda msg, prvkey: electrum_ecc.ECPrivkey(prvkey).ecdsa_sign(
        msg, grind_r_value=True
    ),
}

# every signing shape the benchmark times, as a call taking the one argument
# the pair of rows differs by. btclib_secp256k1 alone of the four takes it,
# so what is stated below is a property rather than an agreement -- and the
# BIP340 entry passes the vector's aux_rand, without which two calls draw
# two nonces and answer two signatures for a reason that is not the check
CHECKED_PAIRS: dict[str, Callable[[_vectors.Signing, bool], bytes]] = {
    "dsa der": lambda vector, check: btclib_secp256k1.dsa.sign(
        vector.msg, vector.prvkey, verify=check
    ),
    "dsa compact": lambda vector, check: btclib_secp256k1.dsa.sign(
        vector.msg, vector.prvkey, compact=True, verify=check
    ),
    "dsa der grind": lambda vector, check: btclib_secp256k1.dsa.sign(
        vector.msg, vector.prvkey, grind=True, verify=check
    ),
    "dsa compact grind": lambda vector, check: btclib_secp256k1.dsa.sign(
        vector.msg, vector.prvkey, compact=True, grind=True, verify=check
    ),
    "ssa": lambda vector, check: btclib_secp256k1.ssa.sign(
        vector.msg, vector.prvkey, vector.aux, verify=check
    ),
}

# parse and serialize again, which is the only way to see what a parse read:
# each wrapper's own constructor and its own encoder, never the bindings
PARSERS: dict[str, Callable[[bytes, bool], bytes]] = {
    "btclib_secp256k1": lambda pubkey, compressed: btclib_secp256k1.keys.serialize(
        btclib_secp256k1.keys.parse(pubkey), compressed=compressed
    ),
    "coincurve": lambda pubkey, compressed: coincurve.PublicKey(pubkey).format(
        compressed=compressed
    ),
    "secp256k1-py": lambda pubkey, compressed: secp256k1.PublicKey(
        pubkey, raw=True
    ).serialize(compressed=compressed),
    "electrum-ecc": lambda pubkey, compressed: electrum_ecc.ECPubkey(
        pubkey
    ).get_public_key_bytes(compressed=compressed),
}

DSA_VERIFIERS_DER: dict[str, Callable[[bytes, bytes, bytes], bool]] = {
    "btclib_secp256k1": btclib_secp256k1.dsa.verify,
    "coincurve": lambda msg, pubkey, sig: coincurve.PublicKey(pubkey).verify(
        sig, msg, None
    ),
    "secp256k1-py": _secp256k1_py_verify_der,
    "electrum-ecc": lambda msg, pubkey, sig: electrum_ecc.ECPubkey(pubkey).ecdsa_verify(
        electrum_ecc.ecdsa_sig64_from_der_sig(sig), msg
    ),
}

DSA_VERIFIERS_COMPACT: dict[str, Callable[[bytes, bytes, bytes], bool]] = {
    "btclib_secp256k1": lambda msg, pubkey, sig: btclib_secp256k1.dsa.verify(
        msg, pubkey, sig, compact=True
    ),
    "secp256k1-py": _secp256k1_py_verify_compact,
    "electrum-ecc": lambda msg, pubkey, sig: electrum_ecc.ECPubkey(pubkey).ecdsa_verify(
        sig, msg
    ),
}

# the wrapper whose DER row and compact row are not the same operation, which
# is what the case below records. `ecdsa_sig64_from_der_sig` is not a decoder:
# it parses, calls `secp256k1_ecdsa_signature_normalize` and serializes again,
# so the malleable half of a signature reaches `ecdsa_verify` as the low half
# and is accepted -- while the same signature handed over as 64 octets goes
# through no such call and is refused, `enforce_low_s` being that method's
# default. `vectors_test.py` records the acceptance as `LOW_S_IS_THE_CALLER_S`
# over the DER file; from 64 octets the same package answers the other way,
# and the page presents its two rows as one operation in two encodings
NORMALIZES_ON_THE_WAY_IN = ("electrum-ecc",)

# BIP340 verification handed the full public key rather than its x, which is
# the pair the page reads as one gap. coincurve has no such spelling: its
# x-only type is the only one carrying `verify`
SSA_VERIFIERS_FULL: dict[str, Callable[[bytes, bytes, bytes], bool]] = {
    "btclib_secp256k1": btclib_secp256k1.ssa.verify,
    "secp256k1-py": lambda msg, pubkey, sig: secp256k1.PublicKey(
        pubkey, raw=True
    ).schnorr_verify(msg, sig, None, raw=True),
    "electrum-ecc": lambda msg, pubkey, sig: electrum_ecc.ECPubkey(
        pubkey
    ).schnorr_verify(sig, msg),
}

# tweak-add, answered as the 33 octets every wrapper can serialize to, which
# is where the benchmark's tweak rows end too: these are those four calls
# rather than variants of them, the serialization included. electrum-ecc has
# no tweak-add and composes one, which is likewise what its row does
TWEAKERS: dict[str, Callable[[bytes, bytes], bytes]] = {
    "btclib_secp256k1": lambda pubkey, tweak: btclib_secp256k1.keys.pubkey_tweak_add(
        pubkey, tweak, compressed=True
    ),
    "coincurve": lambda pubkey, tweak: (
        coincurve.PublicKey(pubkey).add(tweak).format(compressed=True)
    ),
    "secp256k1-py": lambda pubkey, tweak: (
        secp256k1.PublicKey(pubkey, raw=True)
        .tweak_add(tweak)
        .serialize(compressed=True)
    ),
    "electrum-ecc": lambda pubkey, tweak: (
        electrum_ecc.ECPubkey(pubkey)
        + int.from_bytes(tweak, "big") * electrum_ecc.GENERATOR
    ).get_public_key_bytes(compressed=True),
}


def _uncompressed(prvkey: bytes) -> bytes:
    """Return the 65-octet public key, which the fixtures start from."""
    return btclib_secp256k1.keys.pubkey_from_prvkey(prvkey, compressed=False)


def _compressed(prvkey: bytes) -> bytes:
    """Return the 33-octet public key."""
    return btclib_secp256k1.keys.pubkey_from_prvkey(prvkey, compressed=True)


def _answer(
    verify: Callable[[bytes, bytes, bytes], bool],
    msg: bytes,
    pubkey: bytes,
    sig: bytes,
) -> bool:
    """Return a verifier's verdict, a refusal spelled either way being False.

    These four packages do not agree on how to decline: handed an r above
    the group order, btclib_secp256k1 raises `ValueError`, secp256k1-py's
    deserializer trips an `assert`, and electrum-ecc returns `False` from a
    length check of its own. All three are the same verdict, and the octets
    that provoke each spelling are not the same on every platform either --
    which is why every case below reads the verdict through here rather than
    asserting the shape of the refusal.
    """
    try:
        return bool(verify(msg, pubkey, sig))
    except Exception:  # noqa: BLE001 - any refusal is a rejection
        return False


def _sig64(r: int, s: int) -> bytes:
    """Return the 64 octets of r and s, whatever the two are worth."""
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


def _out_of_range(signature: bytes) -> dict[str, bytes]:
    """Return the ways 64 octets are wrong without a single bit being flipped.

    DER carries a length before each integer, so a value out of range is a
    parse error there and Wycheproof publishes hundreds of the shape. The
    compact form carries r and s and nothing else, so the same value is a
    range check a wrapper performs or does not, and no published file has a
    compact case to hand over: these are built from a signature that is
    valid, one field at a time, so that whatever a verifier refuses them for
    is the field and not the encoding.
    """
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    return {
        "r zero": _sig64(0, s),
        "s zero": _sig64(r, 0),
        "both zero": _sig64(0, 0),
        "r at the order": _sig64(ORDER, s),
        "s at the order": _sig64(r, ORDER),
        "r above the order": _sig64(2**256 - 1, s),
        "s above the order": _sig64(r, 2**256 - 1),
    }


def _malleable(signature: bytes) -> bytes:
    """Return the other signature of the malleable pair, s taken to n - s.

    Both are signatures of the same message under the same key, ECDSA being
    indifferent to which; bitcoin is not, and libsecp256k1 signs the low
    half only. So this is the one adversarial case here whose arithmetic is
    correct, and refusing it is a policy rather than a verdict.
    """
    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    return _sig64(r, ORDER - s)


def _low_r(compact: bytes) -> bool:
    """Return whether r's high bit is clear, read off the 64-octet form.

    The property grinding exists for, stated where both packages can be held
    to it: `is_low_r` is btclib_secp256k1's own and electrum-ecc has no
    counterpart, so the octet is read here rather than asked of either.
    """
    return not compact[0] & 0x80


# --- ECDSA signing, which no published file covers for these four -------


@pytest.mark.parametrize("vector", AGREEING, ids=_agreeing_ids())
def test_the_four_wrappers_produce_one_der_signature(
    vector: _vectors.Signing,
) -> None:
    """RFC6979 is a function of the key and the message, so all four agree.

    A stronger check than a round trip, and the reason ECDSA signing can be
    tested at all without a vector file: the nonce is derived rather than
    drawn, so four correct implementations have one right answer between
    them and any disagreement is a defect in whichever one is alone.
    """
    signatures = {
        package: sign(vector.msg, vector.prvkey)
        for package, sign in DSA_SIGNERS_DER.items()
    }
    assert len(set(signatures.values())) == 1, signatures


@pytest.mark.parametrize("vector", AGREEING, ids=_agreeing_ids())
def test_the_compact_signature_is_the_der_one_without_its_wrapping(
    vector: _vectors.Signing,
) -> None:
    """Same signature, two encodings: r and s are the same 64 octets.

    Which is what makes the compact tables comparable with the DER ones at
    all -- if the two encodings held different signatures, the pair would
    price two operations rather than one.
    """
    der = DSA_SIGNERS_DER["btclib_secp256k1"](vector.msg, vector.prvkey)
    compact = {
        package: sign(vector.msg, vector.prvkey)
        for package, sign in DSA_SIGNERS_COMPACT.items()
    }
    assert len(set(compact.values())) == 1, compact
    assert btclib_secp256k1.dsa.to_compact(der) == compact["btclib_secp256k1"]


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_a_signature_verifies_through_every_wrapper_that_made_one(
    vector: _vectors.Signing,
) -> None:
    """The round trip across packages, not within one.

    A package that signed and verified only its own output could be wrong in
    the same direction twice; each signature here is checked by the other
    three, under both serializations of the key.
    """
    signature = DSA_SIGNERS_DER["btclib_secp256k1"](vector.msg, vector.prvkey)
    for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
        for package, verify in DSA_VERIFIERS_DER.items():
            assert verify(vector.msg, pubkey, signature), package


# --- grinding, whose whole subject is the octet it saves ----------------


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_a_ground_signature_has_the_low_r(vector: _vectors.Signing) -> None:
    """The property the loop exists for, and the one a timing cannot show.

    A `grind=True` that ground nothing would print a row that looked like a
    fast package rather than a broken one, which is why this case is here
    and not left to the benchmark to notice.
    """
    for package, sign in DSA_GRINDERS_COMPACT.items():
        assert _low_r(sign(vector.msg, vector.prvkey)), package


@pytest.mark.parametrize("vector", AGREEING, ids=_agreeing_ids())
def test_the_two_grinding_loops_reach_the_same_signature(
    vector: _vectors.Signing,
) -> None:
    """Core's counter, so the answer is reproducible by anyone implementing it.

    Grinding is a loop each package writes in Python -- libsecp256k1 exports
    none -- so this is the one place in this file where two different bodies
    of Python are held to one answer rather than two callers of one C
    function.
    """
    der = {
        package: sign(vector.msg, vector.prvkey)
        for package, sign in DSA_GRINDERS_DER.items()
    }
    compact = {
        package: sign(vector.msg, vector.prvkey)
        for package, sign in DSA_GRINDERS_COMPACT.items()
    }
    assert len(set(der.values())) == 1, der
    assert len(set(compact.values())) == 1, compact


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_grinding_changes_nothing_where_r_was_already_low(
    vector: _vectors.Signing,
) -> None:
    """Half of all messages, and the case a broken loop would still pass.

    Stated the other way round too: where the unground r is high, grinding
    has to have produced a different signature. Both halves are here because
    a loop that always returned its first draw would satisfy one of them.
    """
    plain = DSA_SIGNERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    ground = DSA_GRINDERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    assert (plain == ground) == _low_r(plain)


# --- the check a signer makes before answering --------------------------


@pytest.mark.parametrize("shape", sorted(CHECKED_PAIRS))
@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_the_check_costs_a_row_and_changes_no_signature(
    shape: str, vector: _vectors.Signing
) -> None:
    """The equality each pair of signing rows is read as one operation on.

    `verify=True` asks the package to verify what it just made before
    answering with it, and `verify=False` stops short: the pair of rows the
    page carries is that difference and is read as the price of the check.
    Which is only what it is if the two answer the same octets -- a check
    that changed a signature would be a second operation, and the
    subtraction would be of two different things.

    A timing cannot show it, both rows being a number either way, so it is
    stated here for every shape that page times: both ECDSA encodings, both
    of them ground, and BIP340.

    Args:
        shape: the signing call, for the test id.
        vector: the key, message and aux_rand it is made with.
    """
    assert CHECKED_PAIRS[shape](vector, True) == CHECKED_PAIRS[shape](vector, False)


# --- parsing a public key -----------------------------------------------


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_a_parsed_key_serializes_back_to_what_was_parsed(
    vector: _vectors.Signing,
) -> None:
    """Both encodings in, both encodings out, and every wrapper agreeing.

    The parse tables are the page's reference pair, so a wrapper reading a
    key wrongly would move every verification and every tweak with it. What
    the round trip catches that agreement alone would not is the four of
    them being wrong together in a way the encoding shows.
    """
    uncompressed = _uncompressed(vector.prvkey)
    compressed = _compressed(vector.prvkey)
    for package, parse in PARSERS.items():
        for encoding in (uncompressed, compressed):
            assert parse(encoding, False) == uncompressed, package
            assert parse(encoding, True) == compressed, package


# --- verifying, in the encodings vectors_test.py does not hand over -----


@pytest.mark.parametrize("package", sorted(DSA_VERIFIERS_DER))
@pytest.mark.parametrize(
    "case", WYCHEPROOF, ids=[f"tc{case.number}" for case in WYCHEPROOF]
)
def test_a_compressed_key_answers_wycheproof_as_the_uncompressed_one_does(
    package: str, case: _vectors.Wycheproof
) -> None:
    """The same file, the same answers, one octet fewer of public key.

    `vectors_test.py` hands every verifier the uncompressed key the file
    publishes, which leaves the compressed tables of the benchmark measuring
    a path nothing checks. The expected answer is not read from the file
    here but from the same wrapper's answer to the uncompressed key: what is
    being tested is that the encoding does not change the verdict, and the
    verdicts themselves are that module's subject.
    """
    digest = hashlib.sha256(case.msg).digest()
    verify = DSA_VERIFIERS_DER[package]
    compressed = PARSERS[package](case.pubkey, True)
    expected = _answer(verify, digest, case.pubkey, case.sig)
    assert _answer(verify, digest, compressed, case.sig) == expected


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_a_compact_signature_verifies_and_a_tampered_one_does_not(
    vector: _vectors.Signing,
) -> None:
    """The compact tables' path, which no published file exercises.

    Wycheproof cannot serve here: its subject is DER, and a case whose point
    is a malformed length has no compact form to hand over. So the case is
    made rather than published -- accept the signature, reject the same
    signature with one octet of s changed -- and it is run under both
    serializations of the key, those being two more benchmark tables.

    The wrong values that are wrong for a reason rather than by a bit are
    the two cases below this one.
    """
    signature = DSA_SIGNERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    # a flipped octet of s, which every wrapper can parse and none should
    # accept, and 63 octets, which is not a signature at all: the second is
    # here because whether a wrapper answers False or raises on the first
    # turns out to depend on the platform, and a rejection spelled either
    # way is a rejection
    wrong = (
        signature[:-1] + bytes([signature[-1] ^ 1]),
        signature[:-1],
    )
    for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
        for package, verify in DSA_VERIFIERS_COMPACT.items():
            assert verify(vector.msg, pubkey, signature), package
            for sig in wrong:
                assert not _answer(verify, vector.msg, pubkey, sig), package


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_64_octets_outside_the_group_are_refused_by_every_compact_verifier(
    vector: _vectors.Signing,
) -> None:
    """The range check the compact encoding has no length field to make.

    Seven values that a DER parser would have refused before any arithmetic
    began, handed over in the one encoding where they parse: r or s zero,
    both zero, either at the group order, either at the largest number 32
    octets hold. What is asserted is the verdict alone, three wrappers of
    one library having to answer alike -- they do not agree on the spelling,
    two of the three raising where the third returns False, and that
    difference is `_answer`'s subject rather than this case's.

    Three and not four: coincurve has no compact `ecdsa_verify`, which is
    why tables 5 and 6 print it `NA` and why the name says verifier rather
    than wrapper.

    What keeps a case of nothing but refusals from being vacuous is the
    positive verdict two cases up, asserted over these same vectors, keys
    and verifiers: these octets are refused where the ones they were built
    from are accepted.
    """
    signature = DSA_SIGNERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
        for case, sig in _out_of_range(signature).items():
            for package, verify in DSA_VERIFIERS_COMPACT.items():
                assert not _answer(verify, vector.msg, pubkey, sig), (package, case)


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_the_malleable_half_is_refused_from_64_octets(
    vector: _vectors.Signing,
) -> None:
    """The one adversarial case whose arithmetic is right, and it is refused.

    ECDSA admits both s and n - s; bitcoin admits the low one, and
    libsecp256k1 signs it -- which the assertion below states rather than
    assumes, the case being built by subtracting from a signature this suite
    made. All three compact verifiers refuse the other half, so the low-s
    rule is under these rows and not a policy a caller is left to apply.

    Nothing here would notice if `_malleable` were wrong. An endianness slip
    or a subtraction on the wrong modulus produces octets every verifier
    refuses, and this case would pass while its own first sentence stopped
    being true. What establishes that these octets are a *signature* is the
    case below: electrum-ecc accepts them through DER, and it would not
    accept something that did not verify. So the two are one statement in
    two halves, and narrowing the second one silently unmakes this one.
    """
    signature = DSA_SIGNERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    assert 2 * int.from_bytes(signature[32:], "big") < ORDER
    for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
        for package, verify in DSA_VERIFIERS_COMPACT.items():
            assert not _answer(verify, vector.msg, pubkey, _malleable(signature)), (
                package
            )


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_one_wrapper_reads_der_and_64_octets_differently(
    vector: _vectors.Signing,
) -> None:
    """The DER pair and the compact pair are one operation, bar one row.

    The same malleable signature the case above hands over as 64 octets,
    handed over in DER instead. Two of the four answer as they did there;
    coincurve refuses it here and was never asked there, having no compact
    verification to be asked through; and the fourth accepts it, because
    what it calls a DER decoder normalizes s as it goes -- so its DER row
    and its compact row differ by a policy and not only by an encoding,
    which is the one thing the page's reading of that pair does not allow
    for.

    That acceptance is also what says the octets above are a signature at
    all rather than a construction that went wrong: this wrapper verifies
    them, and refusing them is therefore a policy the others apply and not
    an arithmetic they caught.

    Stated as an assertion rather than left to a reader: it is a property of
    a comparand's API, so a release that changes it should fail here and
    bring somebody back to `NORMALIZES_ON_THE_WAY_IN`.
    """
    signature = DSA_SIGNERS_COMPACT["btclib_secp256k1"](vector.msg, vector.prvkey)
    der = btclib_secp256k1.dsa.to_der(_malleable(signature))
    for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
        for package, verify in DSA_VERIFIERS_DER.items():
            accepted = _answer(verify, vector.msg, pubkey, der)
            assert accepted == (package in NORMALIZES_ON_THE_WAY_IN), package


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_bip340_answers_the_same_under_a_full_key_as_under_its_x(
    vector: _vectors.Signing,
) -> None:
    """The pair the page reads as one gap, held to one answer.

    BIP340 is defined over x alone, so handing a verifier the whole point
    must not change the verdict -- including where that point has the odd y
    the x-only convention discards, which half these keys do. A wrapper that
    verified against the y it was given rather than against BIP340's even
    one would pass every published vector, all of which carry x.
    """
    for package, verify in SSA_VERIFIERS_FULL.items():
        assert verify(vector.msg, _uncompressed(vector.prvkey), vector.sig), package
        assert verify(vector.msg, _compressed(vector.prvkey), vector.sig), package


# --- the tweak, which nothing else in the suite touches -----------------


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_the_tweak_is_one_point_however_the_key_arrived(
    vector: _vectors.Signing,
) -> None:
    """Four wrappers, two encodings of the key, one answer.

    Checked against `secp256k1lab` rather than only against each other: the
    four wrap one C library and could agree by sharing a mistake in how they
    call it, where the fifth is Python that computes P + tG on its own. That
    is also why electrum-ecc belongs in this table -- it has no tweak-add
    and composes the same point from a multiplication and an addition, which
    is a different claim to check than a wrong argument order.
    """
    # the secret key as the tweak, which is what the benchmark's fixture
    # does: a message is 32 octets that may be at or above the group order,
    # and one such vector is published -- a key never is
    tweak = vector.prvkey
    # secp256k1lab ships no annotations for these two, and the override in
    # pyproject.toml covers the import rather than the call
    scalar = secp256k1lab.secp256k1.Scalar(  # type: ignore[no-untyped-call]
        int.from_bytes(tweak, "big")
    )
    point = secp256k1lab.secp256k1.GE.from_bytes(  # type: ignore[no-untyped-call]
        _uncompressed(vector.prvkey)
    )
    expected = (point + scalar * secp256k1lab.secp256k1.G).to_bytes_compressed()

    for package, add in TWEAKERS.items():
        for pubkey in (_uncompressed(vector.prvkey), _compressed(vector.prvkey)):
            assert add(pubkey, tweak) == expected, package
