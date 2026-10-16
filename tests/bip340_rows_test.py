# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""embit's BIP340 signing rows of `scripts/03-libraries.py` sign validly.

BIP340 publishes signatures made with an `aux_rand`, and embit's
`schnorr_sign` takes none, so `vectors_test.py` has nothing to compare its
signature with. What can be checked is that the signature verifies: the two
embit rows are run as the script defines them, `schnorr_sign` is wrapped to
keep what it returns and which key and message it was given, and each kept
signature is verified by a package that did not make it, `secp256k1lab`,
and by embit itself.

The wrapper is the only thing added to the rows. They are the script's own
functions, so a row signing with the wrong key or returning an invalid
signature fails here.
"""

from __future__ import annotations

import importlib
from typing import Any

import embit.ec
import pytest
import secp256k1lab.bip340
import secp256k1lab.secp256k1

# `import` cannot spell the script's name; see `pure_python_path_test.py`
LIBRARIES = importlib.import_module("03-libraries")

ROWS = ["ssa_held_embit_noverify", "ssa_sign_embit_noverify"]


@pytest.mark.parametrize("row", ROWS)
def test_an_embit_signing_row_makes_a_signature_that_verifies(
    row: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the row over its first messages; every signature must verify."""
    original = embit.ec.PrivateKey.schnorr_sign
    kept: list[tuple[embit.ec.PrivateKey, bytes, Any]] = []

    def wrapper(key: embit.ec.PrivateKey, msg: bytes) -> Any:  # noqa: ANN401
        signature = original(key, msg)
        kept.append((key, msg, signature))
        return signature

    monkeypatch.setattr(embit.ec.PrivateKey, "schnorr_sign", wrapper)
    calls = 5
    for _ in range(calls):
        getattr(LIBRARIES, row)()
    assert len(kept) == calls
    for key, msg, signature in kept:
        assert key.secret in LIBRARIES.PRVKEYS
        assert msg in LIBRARIES.MESSAGES
        scalar = int.from_bytes(key.secret, "big")
        xonly = (scalar * secp256k1lab.secp256k1.G).to_bytes_compressed()[1:]
        assert secp256k1lab.bip340.schnorr_verify(msg, xonly, signature.serialize())
        assert key.get_public_key().schnorr_verify(signature, msg)
