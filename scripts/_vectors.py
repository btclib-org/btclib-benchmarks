# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The vendored vectors, read and checked, for the benchmarks and the suite.

Every row of every benchmark runs over a set of published inputs rather than
one input repeatedly. One input repeated measures one input: a key whose
public key is the generator, a message whose low-r grinding lands on the
first attempt, and nothing in the output says which. Cycling the set costs
one `next` per call, the same for every row, and buys a number averaged over
inputs somebody else chose.

`vectors/README.md` says where each file came from and publishes its digest.
The digests are checked here, on import, because a benchmark reading a
drifted copy would print numbers over inputs nobody can look up.

The second module in `scripts/` that is not a benchmark, after
`_provenance.py`: five scripts and the suite need one answer to "what are the
inputs", and six copies of a CSV parser is how they stop agreeing.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import NamedTuple

VECTORS = Path(__file__).parents[1] / "vectors"

# what `vectors/README.md` publishes for each file
DIGESTS = {
    "bip340_test_vectors.csv": (
        "01c8cabba63b4c9b2f44c975902990086a4fe56eee9d265b187d1e2c1d98ccfb"
    ),
    "bip32_test_vectors.json": (
        "5a0e3411f974989d9c65ee542101f175ce3847300fd5bdafdd2812ce5fb85594"
    ),
}


def read(name: str) -> str:
    """Return a vendored file's text, having checked it is the vendored file."""
    payload = (VECTORS / name).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != DIGESTS[name]:  # pragma: no cover - the suite asserts this too
        message = f"{name} is not the copy vectors/README.md describes: {digest}"
        raise ValueError(message)
    return payload.decode("utf-8")


class Bip340(NamedTuple):
    """One row of BIP340's vector file, decoded.

    `number` is what the file calls `index`, renamed because a `NamedTuple`
    inherits `tuple.index` and cannot shadow it.
    """

    number: int
    prvkey: bytes | None
    xonly_pubkey: bytes
    aux: bytes | None
    msg: bytes
    sig: bytes
    valid: bool
    comment: str


class Bip32(NamedTuple):
    """One step of one BIP32 chain, decoded."""

    seed: bytes
    path: str
    xpub: str
    xprv: str


def bip340() -> list[Bip340]:
    """Return every BIP340 vector, in the order the file publishes them."""
    return [
        Bip340(
            number=int(row["index"]),
            prvkey=bytes.fromhex(row["secret key"]) if row["secret key"] else None,
            xonly_pubkey=bytes.fromhex(row["public key"]),
            aux=bytes.fromhex(row["aux_rand"]) if row["aux_rand"] else None,
            msg=bytes.fromhex(row["message"]),
            sig=bytes.fromhex(row["signature"]),
            valid=row["verification result"] == "TRUE",
            comment=row["comment"],
        )
        for row in csv.DictReader(read("bip340_test_vectors.csv").splitlines())
    ]


def bip32() -> list[Bip32]:
    """Return every step of every BIP32 chain, seed by seed."""
    return [
        Bip32(seed=bytes.fromhex(seed), path=path, xpub=xpub, xprv=xprv)
        for seed, steps in json.loads(read("bip32_test_vectors.json")).items()
        for path, xpub, xprv in steps
    ]


class Signing(NamedTuple):
    """One BIP340 signing case, where the key and the aux_rand are not None."""

    number: int
    prvkey: bytes
    xonly_pubkey: bytes
    aux: bytes
    msg: bytes
    sig: bytes


def signing() -> list[Signing]:
    """Return the BIP340 rows that are a signature to reproduce.

    A row carries a secret key when it is a signing case, and an aux_rand
    with it, which is what makes the signature reproducible. The rows whose
    message is not 32 bytes are left out: libsecp256k1's fixed-size entry
    point is what the wrappers expose, so they are not inputs every row can
    be handed.
    """
    return [
        Signing(
            number=v.number,
            prvkey=v.prvkey,
            xonly_pubkey=v.xonly_pubkey,
            aux=v.aux or bytes(32),
            msg=v.msg,
            sig=v.sig,
        )
        for v in bip340()
        if v.prvkey is not None and len(v.msg) == 32
    ]


def verification() -> list[Bip340]:
    """Return the BIP340 rows a benchmark can time, which are the valid ones.

    The invalid rows belong to the suite: a verification that fails early has
    not done the work being timed, and mixing the two would make a row's
    number depend on how many of each it was handed.
    """
    return [v for v in bip340() if v.valid and len(v.msg) == 32]
