# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The address rows of 03 answer what BIP173 and BIP350 say.

A row of that script calls a library and drops what it returns, which is
right for a timing and leaves nothing to compare. So each test here runs the
row itself, with the library call it makes wrapped to keep its return value,
and holds that value to the specification. The wrapper is the only thing
added: the row is the script's own function, so a row that is edited to ask
the wrong question, or a library that answers the right one wrongly, fails.

The values are spelled out below, from the two specifications, and not read
from the script: a constant altered in the script would otherwise be both the
question and the answer. The first test holds the script's constants to them.

What a row does with the answer after the library call, the slice that cuts
the program out of a decoded tuple, is not seen here: the wrapper keeps the
whole tuple. Those slices are one index each.
"""

from __future__ import annotations

import importlib
from typing import Any

import bitcoin.bech32
import btclib.b32
import buidl.bech32
import buidl.script
import embit.bech32
import pytest

# `import` cannot spell the script's name; see `pure_python_path_test.py`
LIBRARIES = importlib.import_module("03-libraries")

# BIP173's witness-v0 test vector, and BIP350's witness-v1 one
WITNESS_V0 = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
BECH32_ADDRESS = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
WITNESS_V1 = bytes.fromhex(
    "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
)
BECH32M_ADDRESS = "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0"


def test_the_script_times_the_published_values() -> None:
    """The rows' inputs are the specifications' own, byte for byte."""
    assert LIBRARIES.WITNESS_V0 == WITNESS_V0
    assert LIBRARIES.BECH32_ADDRESS == BECH32_ADDRESS
    assert LIBRARIES.WITNESS_V1 == WITNESS_V1
    assert LIBRARIES.BECH32M_ADDRESS == BECH32M_ADDRESS


def _spy(
    patch: pytest.MonkeyPatch, owner: object, name: str
) -> list[tuple[tuple[Any, ...], Any]]:
    """Wrap `owner.name` to keep each call's arguments and answer.

    A method is wrapped on its class and called with `self`, as it is by the
    row. `monkeypatch` puts the original back whatever the test does.
    """
    original = getattr(owner, name)
    kept: list[tuple[tuple[Any, ...], Any]] = []

    def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 - any signature
        answer = original(*args, **kwargs)
        kept.append((args, answer))
        return answer

    patch.setattr(owner, name, wrapper)
    return kept


# per row: the library call it makes, and what that call must return
# for the specification's input. The decoders' returns are tuples whose
# shape differs per library, so each names its own version and program
ENCODERS: dict[str, tuple[object, str, str]] = {
    "bech32_encode_btclib": (btclib.b32, "address_from_witness", BECH32_ADDRESS),
    "bech32_encode_embit": (embit.bech32, "encode", BECH32_ADDRESS),
    "bech32_encode_buidl": (buidl.script.P2WPKHScriptPubKey, "address", BECH32_ADDRESS),
    "bech32_encode_bitcoinlib": (bitcoin.bech32, "encode", BECH32_ADDRESS),
    "bech32m_encode_btclib": (btclib.b32, "address_from_witness", BECH32M_ADDRESS),
    "bech32m_encode_embit": (embit.bech32, "encode", BECH32M_ADDRESS),
    "bech32m_encode_buidl": (buidl.script.P2TRScriptPubKey, "address", BECH32M_ADDRESS),
}


@pytest.mark.parametrize("row", sorted(ENCODERS))
def test_an_encoding_row_answers_the_published_address(
    row: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Call the row; its library returned the address the BIP publishes."""
    owner, name, address = ENCODERS[row]
    kept = _spy(monkeypatch, owner, name)
    getattr(LIBRARIES, row)()
    assert [answer for _, answer in kept] == [address]


# row -> (owner, name, address, version index, program index, version,
# program): where the library's returned tuple holds each, and what they are
DECODERS: dict[str, tuple[object, str, str, int, int, int, bytes]] = {
    "bech32_decode_btclib": (
        btclib.b32,
        "witness_from_address",
        BECH32_ADDRESS,
        0,
        1,
        0,
        WITNESS_V0,
    ),
    "bech32_decode_embit": (
        embit.bech32,
        "decode",
        BECH32_ADDRESS,
        0,
        1,
        0,
        WITNESS_V0,
    ),
    "bech32_decode_buidl": (
        buidl.bech32,
        "decode_bech32",
        BECH32_ADDRESS,
        1,
        2,
        0,
        WITNESS_V0,
    ),
    "bech32_decode_bitcoinlib": (
        bitcoin.bech32,
        "decode",
        BECH32_ADDRESS,
        0,
        1,
        0,
        WITNESS_V0,
    ),
    "bech32m_decode_btclib": (
        btclib.b32,
        "witness_from_address",
        BECH32M_ADDRESS,
        0,
        1,
        1,
        WITNESS_V1,
    ),
    "bech32m_decode_embit": (
        embit.bech32,
        "decode",
        BECH32M_ADDRESS,
        0,
        1,
        1,
        WITNESS_V1,
    ),
    "bech32m_decode_buidl": (
        buidl.bech32,
        "decode_bech32",
        BECH32M_ADDRESS,
        1,
        2,
        1,
        WITNESS_V1,
    ),
}


@pytest.mark.parametrize("row", sorted(DECODERS))
def test_a_decoding_row_answers_the_published_program(
    row: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Call the row; its library decoded the BIP's version and program.

    The address the library was handed is checked too, so a row decoding the
    other address, or a malformed one, does not pass on a lucky answer.
    """
    owner, name, address, version_at, program_at, version, program = DECODERS[row]
    kept = _spy(monkeypatch, owner, name)
    getattr(LIBRARIES, row)()
    assert len(kept) == 1
    args, answer = kept[0]
    assert args[-1] == address
    assert bytes(answer[program_at]) == program
    assert answer[version_at] == version
