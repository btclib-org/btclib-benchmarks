# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What every measured package answers about its own arithmetic.

`vectors_test.py` holds each implementation to what a specification
publishes. Two claims the benchmarks depend on have nothing published to be
held to, and this is where they live instead.

The first is that a package verifies the signature it just made. No file
publishes an ECDSA signature over these keys -- RFC6979's nonce is each
implementation's own, and the ones that grind or draw entropy do not even
agree with each other -- so what is checkable is the round trip, and a
benchmark whose signing row produced something its own verifying row
rejects would be timing two unrelated operations.

The second is that the implementations agree on a public key. Deriving one
is a generator multiplication, which is the arithmetic under most of what
these pages time, and an implementation that disagreed about it would make
every row of its column a measurement of something else.

Both used to be asserted inside the benchmark scripts, where they ran at
import and cost a reader nothing to miss. A check belongs where checks are
run, and a timing script should contain no check at all.
"""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256

import bitcoin.bech32
import bitcoin.core.key as bitcoinlib_key
import btclib.ecc.dsa
import buidl.ecc
import buidl.pecc
import ecdsa
import embit.ec
import pycoin.symbols.btc
import pytest
import secp256k1lab.secp256k1
from btclib.to_pub_key import pub_keyinfo_from_prv_key

from btclib_benchmarks import _vectors

SIGNING = _vectors.signing()

PYCOIN_NETWORK = pycoin.symbols.btc.network
PYCOIN_GENERATOR = PYCOIN_NETWORK.generator
LAB_G = secp256k1lab.secp256k1.G


def _ids() -> list[str]:
    """Name each case by the key it is over, as the other suites do."""
    return [vector.prvkey.hex()[:8] for vector in SIGNING]


def _bitcoinlib_key(prvkey: bytes) -> bitcoinlib_key.CECKey:
    """Return python-bitcoinlib's key object for one secret key."""
    key = bitcoinlib_key.CECKey()
    key.set_secretbytes(prvkey)
    key.set_compressed(True)
    return key


def _btclib(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through btclib, one signature and no grinding."""
    signature = btclib.ecc.dsa.sign_(msg, prvkey, grind=False)
    return btclib.ecc.dsa.verify_(msg, pub_keyinfo_from_prv_key(prvkey)[0], signature)


def _ecdsa(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through python-ecdsa, over the digest as it is."""
    key = ecdsa.SigningKey.from_secret_exponent(
        int.from_bytes(prvkey, "big"), curve=ecdsa.SECP256k1
    )
    signature = key.sign_digest_deterministic(msg, hashfunc=sha256)
    return bool(key.verifying_key.verify_digest(signature, msg))


def _pycoin(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through pycoin, which takes the digest as an integer.

    Reduced modulo the order, which is what any implementation does with a
    digest internally and what pycoin refuses to do for a caller. A digest
    of zero it refuses outright, and BIP340's first vector has a message of
    zeros: skipped rather than asserted, because what would be recorded is
    a refusal every implementation is entitled to -- the benchmarks leave
    the same input out of their ECDSA rows for the same reason.

    Whether the refusal happens at all depends on which backend pycoin
    found, and that depends on whether anything has loaded libsecp256k1
    into the process first -- which under `pytest-randomly` is a property
    of the run. The skip is unconditional so that the outcome is not.
    """
    scalar = int.from_bytes(prvkey, "big")
    digest = int.from_bytes(msg, "big") % PYCOIN_GENERATOR.order()
    if not digest:
        pytest.skip("pycoin refuses a zero digest, and this message is zeros")
    signature = PYCOIN_GENERATOR.sign(scalar, digest)
    return bool(PYCOIN_GENERATOR.verify(PYCOIN_GENERATOR * scalar, digest, signature))


def _buidl(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through buidl, whose digest is an integer too."""
    key = buidl.ecc.PrivateKey(int.from_bytes(prvkey, "big"))
    digest = int.from_bytes(msg, "big")
    return bool(key.point.verify(digest, key.sign(digest)))


def _bitcoinlib(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through python-bitcoinlib, which is OpenSSL's."""
    key = _bitcoinlib_key(prvkey)
    pubkey = bitcoinlib_key.CPubKey(key.get_pubkey())
    return bool(pubkey.verify(msg, key.sign(msg)))


def _embit(msg: bytes, prvkey: bytes) -> bool:
    """Sign and verify through embit, one signature and no grinding."""
    key = embit.ec.PrivateKey(prvkey)
    return bool(key.get_public_key().verify(key.sign(msg, grind=False), msg))


# one entry per package that signs ECDSA in these pages, each answering
# "does this package verify what it just signed": the signature never
# leaves the package that made it, which is what makes this checkable
# where comparing two packages' signatures is not
ECDSA_ROUND_TRIPS: dict[str, Callable[[bytes, bytes], bool]] = {
    "btclib": _btclib,
    "ecdsa": _ecdsa,
    "pycoin": _pycoin,
    "buidl": _buidl,
    "python-bitcoinlib": _bitcoinlib,
    "embit": _embit,
}


@pytest.mark.parametrize("package", sorted(ECDSA_ROUND_TRIPS))
@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_a_package_verifies_the_signature_it_just_made(
    package: str, vector: _vectors.Signing
) -> None:
    """Sign and verify inside one package: the round trip has to close."""
    assert ECDSA_ROUND_TRIPS[package](vector.msg, vector.prvkey)


# and the other claim: one scalar, one public key, however it is spelled.
# Compressed SEC in every case, that being the one serialization all of
# them offer
PUBLIC_KEYS: dict[str, Callable[[int], bytes]] = {
    "btclib": lambda scalar: pub_keyinfo_from_prv_key(scalar)[0],
    "secp256k1lab": lambda scalar: (scalar * LAB_G).to_bytes_compressed(),
    "buidl.pecc": lambda scalar: buidl.pecc.PrivateKey(scalar).point.sec(),
    "ecdsa": lambda scalar: ecdsa.SigningKey.from_secret_exponent(
        scalar, curve=ecdsa.SECP256k1
    ).verifying_key.to_string("compressed"),
    "pycoin": lambda scalar: PYCOIN_NETWORK.keys.private(secret_exponent=scalar).sec(),
}


@pytest.mark.parametrize("package", sorted(set(PUBLIC_KEYS) - {"btclib"}))
@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_every_implementation_derives_the_same_public_key(
    package: str, vector: _vectors.Signing
) -> None:
    """Against btclib's, which the vector file's x-only key already pins."""
    scalar = int.from_bytes(vector.prvkey, "big")
    assert PUBLIC_KEYS[package](scalar) == PUBLIC_KEYS["btclib"](scalar)


@pytest.mark.parametrize("vector", SIGNING, ids=_ids())
def test_btclib_derives_the_public_key_the_vector_publishes(
    vector: _vectors.Signing,
) -> None:
    """The x-only half of it, which is what BIP340 publishes."""
    scalar = int.from_bytes(vector.prvkey, "big")
    assert PUBLIC_KEYS["btclib"](scalar)[1:] == vector.xonly_pubkey


# BIP350's own witness-v1 address and the program under it. Vendored here
# rather than read from a file for the reason the benchmark vendors them:
# the specification publishes this pair in its text, and no machine-readable
# file in this repository carries it
WITNESS_V1 = bytes.fromhex(
    "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
)
BECH32M_ADDRESS = "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0"


def test_python_bitcoinlib_gets_bech32m_wrong_in_both_directions() -> None:
    """Why the libraries table has no bech32m row for python-bitcoinlib.

    Its `bech32.encode` answers for a witness-v1 program with bech32's
    checksum constant where BIP350 requires bech32m's, so what comes back is
    a string no consumer should accept; and `decode` refuses the address
    BIP350 publishes. A benchmark row cannot be timed against an answer this
    project would have to record as wrong, so the row is absent and this is
    what says why -- and what would fail if a release ever fixed it, which is
    when the row should come back.
    """
    assert bitcoin.bech32.encode("bc", 1, WITNESS_V1) != BECH32M_ADDRESS
    assert bitcoin.bech32.decode("bc", BECH32M_ADDRESS) == (None, None)
