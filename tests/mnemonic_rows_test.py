# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every package `scripts/07-mnemonics.py` times answers what bip39-slip39 does.

Each check calls each package as its row calls it, so a package that is
fast and wrong cannot win a row. The rows discard what they return, and
this is where the answers are read.

Two sets of inputs. The published ones come first: a BIP39 vector and a
SLIP-0039 vector, spelled out below, which every package is held to
directly. Agreeing with bip39-slip39 cannot catch what it and a peer get
wrong together, and a published answer can. The script's own fixtures
follow, on which every package must answer what bip39-slip39 answers.

A split draws fresh randomness, so two packages' shares of one secret
differ. What is checked instead is that the shares each package makes
are combined back into the secret by bip39-slip39 and by
shamir-mnemonic.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest
import shamir_mnemonic
from bip39_slip39 import bip39, slip39
from embit import bip39 as embit_bip39
from embit import slip39 as embit_slip39
from mnemonic import Mnemonic

if TYPE_CHECKING:
    from collections.abc import Callable

# `import` cannot spell the script's name; see `pure_python_path_test.py`
MNEMONICS = importlib.import_module("07-mnemonics")

# enough inputs to catch a package that is wrong on some of them, few
# enough that the share rows, each a key stretch, stay quick
CASES = 20
ENTROPIES = MNEMONICS.ENTROPIES[:CASES]
SENTENCES = MNEMONICS.MNEMONICS[:CASES]
SECRETS = MNEMONICS.SECRETS[:CASES]
COMBINED = MNEMONICS.COMBINED[:CASES]
SHARES = MNEMONICS.SHARE_MNEMONICS[:CASES]

PASSPHRASE = MNEMONICS.PASSPHRASE
TREZOR = MNEMONICS.TREZOR


# the all-zero 24-word english vector of trezor's `vectors.json`, which
# btclib-org/bip39-slip39 vendors as `tests/_data/bip39_test_vectors.json`;
# every seed there is stretched with the published passphrase "TREZOR",
# which is no credential
BIP39_ENTROPY = bytes(32)
BIP39_WORDS = " ".join(["abandon"] * 23 + ["art"])
BIP39_PASSPHRASE = "TREZOR"  # noqa: S105
BIP39_SEED = bytes.fromhex(
    "bda85446c68413707090a52022edd26a1c9462295029f2e60cd7c4f2bbd30971"
    "70af7a4d73245cafa9c3cca8d561a7c3de6f5d4a10be8ed2a5e608d68f92fcc8"
)

# "4. Basic sharing 2-of-3 (128 bits)" of SLIP-0039's `vectors.json`, as
# btclib-org/bip39-slip39 vendors it in `tests/_data/`: two shares, the
# passphrase "TREZOR", and the master secret they combine into
SLIP39_SHARES = [
    (
        "shadow pistol academic always adequate wildlife fancy gross oasis "
        "cylinder mustang wrist rescue view short owner flip making coding armed"
    ),
    (
        "shadow pistol academic acid actress prayer class unknown daughter "
        "sweater depict flip twice unkind craft early superior advocate guest "
        "smoking"
    ),
]
SLIP39_PASSPHRASE = "TREZOR"  # noqa: S105
SLIP39_SECRET = bytes.fromhex("b43ceb7e57a0ea8766221624d01b0864")


def test_bip39_published_vector() -> None:
    """Every BIP39 row answers the published vector."""
    assert bip39.mnemonic_from_entropy(BIP39_ENTROPY, MNEMONICS.LANG) == BIP39_WORDS
    assert TREZOR.to_mnemonic(BIP39_ENTROPY) == BIP39_WORDS
    assert embit_bip39.mnemonic_from_bytes(BIP39_ENTROPY) == BIP39_WORDS
    assert _entropy_bytes(BIP39_WORDS) == BIP39_ENTROPY
    assert bytes(TREZOR.to_entropy(BIP39_WORDS)) == BIP39_ENTROPY
    assert embit_bip39.mnemonic_to_bytes(BIP39_WORDS) == BIP39_ENTROPY
    assert bip39.lang_from_mnemonic(BIP39_WORDS) == MNEMONICS.LANG
    assert Mnemonic.detect_language(BIP39_WORDS) == "english"
    assert bip39.seed_from_mnemonic(BIP39_WORDS, BIP39_PASSPHRASE) == BIP39_SEED
    assert (
        bip39.seed_from_mnemonic(BIP39_WORDS, BIP39_PASSPHRASE, verify_checksum=False)
        == BIP39_SEED
    )
    assert Mnemonic.to_seed(BIP39_WORDS, BIP39_PASSPHRASE) == BIP39_SEED
    assert embit_bip39.mnemonic_to_seed(BIP39_WORDS, BIP39_PASSPHRASE) == BIP39_SEED
    assert (
        embit_bip39.mnemonic_to_seed(BIP39_WORDS, BIP39_PASSPHRASE, wordlist=None)
        == BIP39_SEED
    )


def test_slip39_published_vector() -> None:
    """Every SLIP-0039 combine, parse and encode row answers the vector."""
    assert (
        slip39.master_secret_from_mnemonics(SLIP39_SHARES, SLIP39_PASSPHRASE)
        == SLIP39_SECRET
    )
    assert (
        shamir_mnemonic.combine_mnemonics(SLIP39_SHARES, SLIP39_PASSPHRASE.encode())
        == SLIP39_SECRET
    )
    parsed = [embit_slip39.Share.parse(m) for m in SLIP39_SHARES]
    assert embit_slip39.ShareSet(parsed).recover(SLIP39_PASSPHRASE.encode()) == (
        SLIP39_SECRET
    )
    for words in SLIP39_SHARES:
        assert slip39.mnemonic_from_share(slip39.share_from_mnemonic(words)) == words
        assert shamir_mnemonic.Share.from_mnemonic(words).mnemonic() == words
        assert embit_slip39.Share.parse(words).mnemonic() == words


def _entropy_bytes(sentence: str) -> bytes:
    """Return bip39-slip39's entropy as bytes, it answering 0s and 1s."""
    bits = bip39.entropy_from_mnemonic(sentence, MNEMONICS.LANG)
    return int(bits, 2).to_bytes(len(bits) // 8, "big")


@pytest.mark.parametrize("entropy", ENTROPIES, ids=range(CASES))
def test_bip39_encode(entropy: bytes) -> None:
    """The three packages spell one entropy as the same 24 words."""
    expected = bip39.mnemonic_from_entropy(entropy, MNEMONICS.LANG)
    assert len(expected.split()) == 24
    assert TREZOR.to_mnemonic(entropy) == expected
    assert embit_bip39.mnemonic_from_bytes(entropy) == expected


@pytest.mark.parametrize("sentence", SENTENCES, ids=range(CASES))
def test_bip39_decode(sentence: str) -> None:
    """The three packages read the same entropy back from the words."""
    expected = _entropy_bytes(sentence)
    assert expected in ENTROPIES
    assert bytes(TREZOR.to_entropy(sentence)) == expected
    assert embit_bip39.mnemonic_to_bytes(sentence) == expected


@pytest.mark.parametrize("sentence", SENTENCES, ids=range(CASES))
def test_bip39_language(sentence: str) -> None:
    """Both detectors name english, each in its own spelling."""
    assert bip39.lang_from_mnemonic(sentence) == MNEMONICS.LANG
    assert Mnemonic.detect_language(sentence) == "english"


@pytest.mark.parametrize("sentence", SENTENCES, ids=range(CASES))
def test_bip39_seed(sentence: str) -> None:
    """Every seed row stretches the words to the same 64 bytes."""
    expected = bip39.seed_from_mnemonic(sentence, PASSPHRASE)
    assert len(expected) == 64
    assert (
        bip39.seed_from_mnemonic(sentence, PASSPHRASE, verify_checksum=False)
        == expected
    )
    assert Mnemonic.to_seed(sentence, PASSPHRASE) == expected
    assert embit_bip39.mnemonic_to_seed(sentence, PASSPHRASE) == expected
    assert embit_bip39.mnemonic_to_seed(sentence, PASSPHRASE, wordlist=None) == expected


def _split_btclib(secret: bytes) -> list[str]:
    return slip39.mnemonics_from_master_secret(
        secret,
        MNEMONICS.GROUPS,
        MNEMONICS.GROUP_THRESHOLD,
        PASSPHRASE,
        MNEMONICS.ITERATION_EXPONENT,
        MNEMONICS.EXTENDABLE,
    )[0]


def _split_shamir(secret: bytes) -> list[str]:
    shares: list[list[str]] = shamir_mnemonic.generate_mnemonics(
        MNEMONICS.GROUP_THRESHOLD,
        MNEMONICS.GROUPS,
        secret,
        PASSPHRASE.encode(),
        MNEMONICS.EXTENDABLE,
        MNEMONICS.ITERATION_EXPONENT,
    )
    return shares[0]


@pytest.mark.parametrize("split", [_split_btclib, _split_shamir])
def test_slip39_split(split: Callable[[bytes], list[str]]) -> None:
    """Three of a package's five shares give its secret back."""
    for secret in SECRETS[:5]:
        shares = split(secret)
        assert len(shares) == 5
        assert slip39.master_secret_from_mnemonics(shares[2:], PASSPHRASE) == secret
        assert shamir_mnemonic.combine_mnemonics(shares[:3]) == secret


@pytest.mark.parametrize("index", range(CASES))
def test_slip39_combine(index: int) -> None:
    """The three packages combine the same three shares into the secret."""
    shares = COMBINED[index]
    expected = slip39.master_secret_from_mnemonics(shares, PASSPHRASE)
    assert expected == SECRETS[index]
    assert shamir_mnemonic.combine_mnemonics(shares, PASSPHRASE.encode()) == expected
    parsed = [embit_slip39.Share.parse(m) for m in shares]
    assert embit_slip39.ShareSet(parsed).recover(PASSPHRASE.encode()) == expected


@pytest.mark.parametrize("words", SHARES, ids=range(CASES))
def test_slip39_parse(words: str) -> None:
    """The three packages read the same fields out of one share."""
    share = slip39.share_from_mnemonic(words)
    shamir = shamir_mnemonic.Share.from_mnemonic(words)
    embit = embit_slip39.Share.parse(words)
    fields = (
        share.identifier,
        share.iteration_exponent,
        share.group_index,
        share.group_threshold,
        share.group_count,
        share.member_index,
        share.member_threshold,
        share.value,
    )
    assert fields == (
        shamir.identifier,
        shamir.iteration_exponent,
        shamir.group_index,
        shamir.group_threshold,
        shamir.group_count,
        shamir.index,
        shamir.member_threshold,
        shamir.value,
    )
    assert fields == (
        embit.id,
        embit.exponent,
        embit.group_index,
        embit.group_threshold,
        embit.group_count,
        embit.member_index,
        embit.member_threshold,
        embit.bytes,
    )
    assert not share.extendable
    assert not shamir.extendable


@pytest.mark.parametrize("words", SHARES, ids=range(CASES))
def test_slip39_encode(words: str) -> None:
    """Each package encodes the share it parsed back into the same words."""
    assert slip39.mnemonic_from_share(slip39.share_from_mnemonic(words)) == words
    assert shamir_mnemonic.Share.from_mnemonic(words).mnemonic() == words
    assert embit_slip39.Share.parse(words).mnemonic() == words
