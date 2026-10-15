# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What `scripts/03-libraries.py`'s btclib BIP32 row times.

The row uses btclib's key-object spellings, for the reason given above
`_btclib_child_pubkey` in the script, and these tests hold that choice.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest
from btclib_wallet import bip32
from btclib_wallet.bip32 import BIP32KeyData

from btclib_benchmarks import _vectors

if TYPE_CHECKING:
    from typing import NoReturn

CHAINS = [chain for chain in _vectors.bip32() if chain.path != "m"]
IDS = [f"{chain.seed.hex()[:8]}-{chain.path}" for chain in CHAINS]


def _boom(*_: object, **__: object) -> NoReturn:
    msg = "Base58Check was touched"
    raise AssertionError(msg)


@pytest.fixture
def no_base58(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make an extended key's Base58Check encoding and decoding raise."""
    monkeypatch.setattr(BIP32KeyData, "b58encode", _boom)
    monkeypatch.setattr(BIP32KeyData, "b58decode", _boom)


@pytest.mark.usefixtures("no_base58")
def test_the_text_spellings_touch_base58check() -> None:
    """The control: the detector sees what the row is chosen not to do."""
    with pytest.raises(AssertionError, match="Base58Check"):
        bip32.derive(bip32.rootxprv_from_seed(CHAINS[0].seed), CHAINS[0].path)


@pytest.mark.usefixtures("no_base58")
def test_the_timed_row_touches_no_base58check() -> None:
    """Call the row itself once per chain."""
    module = importlib.import_module("03-libraries")
    for _ in module.DERIVATIONS:
        module.bip32_derive_btclib()


@pytest.mark.parametrize("chain", CHAINS, ids=IDS)
def test_the_row_derives_the_public_key_bip32_publishes(chain: _vectors.Bip32) -> None:
    """Dropping the text must not change the key the row answers."""
    module = importlib.import_module("03-libraries")
    published, _ = bip32.pub_keyinfo_from_xkey(chain.xpub)
    assert module._btclib_child_pubkey(chain.seed, chain.path) == published
