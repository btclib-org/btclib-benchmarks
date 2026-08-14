# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every measured package answers the vendored vectors, or its timings are void.

A benchmark row is a number produced by code nobody here wrote. The only
thing that makes one worth printing is that the code answered a published
question correctly first, and "it agreed with btclib" is not that question:
it cannot catch what btclib and a comparand get wrong together, and it says
nothing at all about the cases a specification publishes to be *rejected*.

So every implementation this project times is held here to BIP340's own
vectors and BIP32's, in the configuration the benchmark measures it in.
btclib is held to them too. That is redundant with btclib's own suite by
design: it is the one package whose numbers this project exists to publish,
and a table of comparands where the subject alone is unchecked would be an
odd thing to have built.

## The configurations, and why one of them is a subprocess

`scripts/bitcoin_libraries.py` and `scripts/libsecp256k1_wrappers.py` measure
these packages as installed, which is this process. `scripts/pure_python.py`
and `scripts/btclib_two_paths.py` measure two of them with their C turned
off, and neither switch can be undone: `PYCOIN_NATIVE` is read when pycoin
is imported, and btclib's dispatch flag cannot be restored once cleared
without leaving every later test measuring something it did not choose. So
the pure-Python configuration is this same file, re-run by pytest in a child
process with `BENCHMARKS_PURE_PYTHON` set -- the same vectors, the same
assertions, the other arithmetic underneath.

The negative cases are the point of the BIP340 file. Eight of its nineteen
rows carry a secret key and are signatures to reproduce; the rest are
verifications, and the ones expecting FALSE are a public key not on the
curve, an s past the order, an r that is not a field element, a signature
over another message. An implementation that answers true to all of them
passes a round-trip test and fails this one.

An implementation that *raises* on a vector it should reject counts as
rejecting it. Refusing to parse a public key off the curve is a correct
answer to the question BIP340 is asking, differently spelled.
"""

from __future__ import annotations

import csv
import hashlib
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import _vectors
import btclib_secp256k1.ssa
import buidl.hd
import buidl.pecc
import coincurve
import electrum_ecc
import embit.bip32
import embit.ec
import pycoin.symbols.btc
import pytest
import secp256k1
import secp256k1lab.bip340
from btclib.bip32 import bip32
from btclib.curves import curve
from btclib.ecc import ssa

DATA = _vectors.VECTORS

# the digests README.md publishes for the two copies. Checked on every run:
# a vendored file is only as good as the statement of where it came from, and
# a copy that has drifted from the statement should fail a test rather than
# quietly become the new question
DIGESTS = _vectors.DIGESTS

# the pure-Python configuration, as `scripts/pure_python.py` measures it: the
# environment variable pycoin reads at import, and btclib's dispatch off
PURE_PYTHON = bool(os.environ.get("BENCHMARKS_PURE_PYTHON"))
if PURE_PYTHON:  # pragma: no cover - the child process is the one that runs it
    curve._libsecp256k1_available = False


def _bip340_vectors() -> list[dict[str, str]]:
    """Return BIP340's vectors as the CSV publishes them, strings and all.

    `_vectors` decodes them for the benchmarks; the suite wants the file's own
    spelling, `verification result` included, so that a case named here is a
    case a reader can find in the file.
    """
    return list(csv.DictReader(_vectors.read("bip340_test_vectors.csv").splitlines()))


BIP340 = _bip340_vectors()
# BIP340 gained four vectors in 2022 whose messages are 0, 1, 17 and 100
# bytes, and they divide these packages: libsecp256k1's fixed-size entry
# point takes 32 and nothing else, so a wrapper exposing only that one cannot
# be asked, while btclib dispatches a message of another size to its own
# Python path and secp256k1lab has no fixed size to begin with. Which
# packages answer them is a fact about their APIs, so it is written down
# rather than discovered by a loop that skips whatever fails
FIXED_SIZE = [v for v in BIP340 if len(v["message"]) == 64]
OTHER_SIZE = [v for v in BIP340 if len(v["message"]) != 64]
SIGNING = [v for v in FIXED_SIZE if v["secret key"]]
VERIFYING = [v for v in FIXED_SIZE if v["public key"]]
OTHER_SIZE_SIGNING = [v for v in OTHER_SIZE if v["secret key"]]
OTHER_SIZE_VERIFYING = [v for v in OTHER_SIZE if v["public key"]]

# the packages whose API takes a message of any size, per operation. Signing
# is the shorter list: `schnorrsig_sign_custom` is what libsecp256k1 offers
# for it and none of the wrappers here expose it, where three of them do pass
# a length through to `schnorrsig_verify`
SIGNS_ANY_SIZE = ("btclib", "secp256k1lab")
VERIFIES_ANY_SIZE = (
    "btclib",
    "btclib_secp256k1",
    "coincurve",
    "secp256k1-py",
    "buidl.pecc",
    "secp256k1lab",
)
BIP32 = _vectors.bip32()


def _ids(vectors: list[dict[str, str]]) -> list[str]:
    """Name each case by the index BIP340 gives it, so a failure names it."""
    return [f"vector{v['index']}" for v in vectors]


@pytest.mark.parametrize("name", sorted(DIGESTS))
def test_the_vendored_file_is_the_one_the_readme_describes(name: str) -> None:
    """A copy that has drifted from its provenance is not a vector."""
    digest = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
    assert digest == DIGESTS[name]


# --- BIP340 -------------------------------------------------------------

# every implementation of BIP340 verification this project times, in the one
# spelling each of them offers. A signature over an x-only public key: what
# differs is whether the key arrives as 32 bytes or 33, and whether an
# unusable key raises rather than returning false
SSA_VERIFIERS: dict[str, Callable[[bytes, bytes, bytes], bool]] = {
    "btclib": ssa.verify_,
    "btclib_secp256k1": btclib_secp256k1.ssa.verify,
    "coincurve": lambda msg, xonly, sig: coincurve.PublicKeyXOnly(xonly).verify(
        sig, msg
    ),
    "secp256k1-py": lambda msg, xonly, sig: secp256k1.PublicKey(
        b"\x02" + xonly, raw=True
    ).schnorr_verify(msg, sig, None, raw=True),
    "electrum-ecc": lambda msg, xonly, sig: electrum_ecc.ECPubkey(
        b"\x02" + xonly
    ).schnorr_verify(sig, msg),
    "embit": lambda msg, xonly, sig: embit.ec.PublicKey.from_xonly(
        xonly
    ).schnorr_verify(embit.ec.SchnorrSig.parse(sig), msg),
    "buidl.pecc": lambda msg, xonly, sig: buidl.pecc.S256Point.parse_bip340(
        xonly
    ).verify_schnorr(msg, buidl.pecc.SchnorrSignature.parse(sig)),
    "secp256k1lab": secp256k1lab.bip340.schnorr_verify,
}

# and every implementation that can be asked for a *reproducible* signature,
# which means every one taking aux_rand. embit's `schnorr_sign` and
# secp256k1-py's take none, so their signatures are valid over a nonce of
# their own choosing and there is nothing published to compare them with
SSA_SIGNERS: dict[str, Callable[[bytes, bytes, bytes], bytes]] = {
    "btclib": lambda msg, prvkey, aux: ssa.sign_(msg, prvkey, aux=aux).serialize(),
    "btclib_secp256k1": btclib_secp256k1.ssa.sign,
    "coincurve": lambda msg, prvkey, aux: coincurve.PrivateKey(prvkey).sign_schnorr(
        msg, aux
    ),
    "electrum-ecc": lambda msg, prvkey, aux: electrum_ecc.ECPrivkey(
        prvkey
    ).schnorr_sign(msg, aux_rand32=aux),
    "buidl.pecc": lambda msg, prvkey, aux: (
        buidl.pecc.PrivateKey(int.from_bytes(prvkey, "big"))
        .sign_schnorr(msg, aux)
        .serialize()
    ),
    "secp256k1lab": secp256k1lab.bip340.schnorr_sign,
}


@pytest.mark.parametrize("package", sorted(SSA_VERIFIERS))
@pytest.mark.parametrize("vector", VERIFYING, ids=_ids(VERIFYING))
def test_bip340_verification_matches_the_vector(
    package: str, vector: dict[str, str]
) -> None:
    """Accept what BIP340 accepts and reject what it rejects, or lose the row.

    A raise counts as a rejection: an API refusing to parse a public key
    that is not on the curve has answered the question correctly.
    """
    expected = vector["verification result"] == "TRUE"
    msg = bytes.fromhex(vector["message"])
    xonly = bytes.fromhex(vector["public key"])
    sig = bytes.fromhex(vector["signature"])
    try:
        answer = SSA_VERIFIERS[package](msg, xonly, sig)
    except Exception:  # noqa: BLE001 - any refusal is a rejection
        answer = False
    assert answer == expected, vector["comment"]


@pytest.mark.parametrize("package", sorted(SSA_SIGNERS))
@pytest.mark.parametrize("vector", SIGNING, ids=_ids(SIGNING))
def test_bip340_signing_reproduces_the_vector(
    package: str, vector: dict[str, str]
) -> None:
    """With the vector's aux_rand, BIP340 signing has one right answer."""
    signature = SSA_SIGNERS[package](
        bytes.fromhex(vector["message"]),
        bytes.fromhex(vector["secret key"]),
        bytes.fromhex(vector["aux_rand"]),
    )
    assert signature.hex().upper() == vector["signature"]


@pytest.mark.parametrize("package", SIGNS_ANY_SIZE)
@pytest.mark.parametrize("vector", OTHER_SIZE_SIGNING, ids=_ids(OTHER_SIZE_SIGNING))
def test_bip340_signing_a_message_of_another_size(
    package: str, vector: dict[str, str]
) -> None:
    """The 2022 vectors, for the two packages whose API takes any size."""
    signature = SSA_SIGNERS[package](
        bytes.fromhex(vector["message"]),
        bytes.fromhex(vector["secret key"]),
        bytes.fromhex(vector["aux_rand"]),
    )
    assert signature.hex().upper() == vector["signature"]


@pytest.mark.parametrize("package", VERIFIES_ANY_SIZE)
@pytest.mark.parametrize("vector", OTHER_SIZE_VERIFYING, ids=_ids(OTHER_SIZE_VERIFYING))
def test_bip340_verifying_a_message_of_another_size(
    package: str, vector: dict[str, str]
) -> None:
    """The same four vectors, verified by the six packages that take any size.

    embit and electrum-ecc are not among them: their BIP340 verification is
    the fixed-size entry point, which is the right call for the rows that
    time them and the wrong one for a message of another length.
    """
    # no `except` around this one, where the fixed-size test has one: all
    # four of these vectors are valid, so there is no rejection to catch and
    # a raise is a failure rather than an answer
    answer = SSA_VERIFIERS[package](
        bytes.fromhex(vector["message"]),
        bytes.fromhex(vector["public key"]),
        bytes.fromhex(vector["signature"]),
    )
    assert answer == (vector["verification result"] == "TRUE"), vector["comment"]


# --- BIP32 --------------------------------------------------------------


def _pycoin_derive(seed: bytes, path: str) -> str:
    """Derive through pycoin, whose path spelling has no root to name.

    `subkey_for_path` takes the steps and not the `m`, and an empty string is
    not a path of no steps to it -- so the root is the key itself, where every
    other library's derive accepts `m` and answers.
    """
    key = pycoin.symbols.btc.network.keys.bip32_seed(seed)
    steps = path.removeprefix("m").removeprefix("/")
    if steps:
        key = key.subkey_for_path(steps)
    return str(key.hwif(as_private=True))


# each library's own spelling of "derive this path from this seed", returning
# the extended private key. The paths in the vector file are written with H
# for a hardened step, which is btclib's and pycoin's spelling; embit and
# buidl want an apostrophe
BIP32_DERIVERS: dict[str, Callable[[bytes, str], str]] = {
    "btclib": lambda seed, path: bip32.derive(bip32.rootxprv_from_seed(seed), path),
    "pycoin": _pycoin_derive,
    "embit": lambda seed, path: (
        embit.bip32.HDKey.from_seed(seed).derive(path.replace("H", "'")).to_base58()
    ),
    "buidl": lambda seed, path: (
        buidl.hd.HDPrivateKey.from_seed(seed).traverse(path.replace("H", "'")).xprv()
    ),
}


@pytest.mark.parametrize("package", sorted(BIP32_DERIVERS))
@pytest.mark.parametrize(
    "vector", BIP32, ids=[f"{v.seed.hex()[:8]}-{v.path}" for v in BIP32]
)
def test_bip32_derivation_matches_the_vector(
    package: str, vector: _vectors.Bip32
) -> None:
    """Derive the extended private key BIP32 publishes for that path."""
    assert BIP32_DERIVERS[package](vector.seed, vector.path) == vector.xprv


# --- the other configuration -------------------------------------------


@pytest.mark.skipif(
    PURE_PYTHON, reason="this is the child; running it again would not terminate"
)
def test_the_pure_python_configuration_answers_the_same_vectors() -> None:
    """Re-run this file with the C turned off, which is a second process.

    `PYCOIN_NATIVE` is read when pycoin is imported and btclib's dispatch
    flag cannot be restored, so the configuration `scripts/pure_python.py`
    measures cannot be reached from inside a suite that also measures the
    other one. What is asserted is what a reader of that benchmark needs:
    the Python arithmetic answers every vector the C arithmetic answers.
    """
    environment = dict(os.environ)
    environment["BENCHMARKS_PURE_PYTHON"] = "1"
    environment["PYCOIN_NATIVE"] = "none"
    completed = subprocess.run(  # noqa: S603
        # --no-cov because the parent's `addopts` gate a coverage percentage
        # over the whole project, which one file cannot reach and which this
        # run is not about
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-cov",
            "-p",
            "no:cacheprovider",
            __file__,
        ],
        capture_output=True,
        encoding="utf-8",
        env=environment,
        cwd=str(Path(__file__).parents[1]),
        check=False,
    )
    assert completed.returncode == 0, completed.stdout[-4000:]
