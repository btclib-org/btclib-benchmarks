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

`scripts/03-libraries.py` and `scripts/01-libsecp256k1.py` measure
these packages as installed, which is this process. `scripts/04-pure-python.py`
and `scripts/02-btclib-vs-btclib.py` measure two of them with their C turned
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
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import bitcoin.base58
import btclib.base58
import btclib_secp256k1.dsa
import btclib_secp256k1.ssa
import buidl.hd
import buidl.helper
import buidl.pecc
import coincurve
import ecdsa
import electrum_ecc
import embit.base58
import embit.bip32
import embit.ec
import pycoin.encoding.b58
import pycoin.symbols.btc
import pytest
import secp256k1
import secp256k1lab.bip340
from btclib.bip32 import bip32
from btclib.curves import curve
from btclib.ecc import dsa, ssa
from pycoin.ecdsa.secp256k1 import secp256k1_generator as pycoin_generator
from pycoin.encoding.sec import sec_to_public_pair
from pycoin.satoshi.der import sigdecode_der

from btclib_benchmarks import _vectors

if TYPE_CHECKING:
    from collections.abc import Callable

DATA = _vectors.VECTORS

# one provenance entry of README.md, matched whole rather than field by
# field. Section 7 of the organization standard fixes the block's field
# names and their spacing, and a sweep outside this repository parses it, so
# the shape is part of what a drifted file should fail on: a block that
# still carries a right blob under a wrong spelling is one nothing reads
_ENTRY = re.compile(
    r"^### `vectors/(?P<name>[^`]+)`\n\n```text\n"
    r"repo    (?P<repo>\S+)\n"
    r"path    (?P<path>\S+)\n"
    r"commit  (?P<commit>[0-9a-f]{40})  (?P<committed>\d{4}-\d\d-\d\d)\n"
    r"blob    (?P<blob>[0-9a-f]{40})\n"
    r"pulled  (?P<pulled>\d{4}-\d\d-\d\d)\n"
    r"behind  (?P<behind>.+)\n```$",
    re.MULTILINE,
)

# what README.md pins each vendored file to, parsed rather than restated:
# a vendored file is only as good as the statement of where it came from,
# and a copy that has drifted from the statement should fail a test rather
# than quietly become the new question
PINS = {
    match["name"]: match["blob"]
    for match in _ENTRY.finditer((DATA / "README.md").read_text(encoding="utf-8"))
}

# the pure-Python configuration, as `scripts/04-pure-python.py` measures it: the
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


@pytest.mark.parametrize("name", sorted(PINS))
def test_the_vendored_file_is_the_blob_the_readme_pins(name: str) -> None:
    """A copy that has drifted from its provenance is not a vector."""
    assert _vectors.blob_id((DATA / name).read_bytes()) == PINS[name]


def test_the_readme_pins_every_file_beside_it() -> None:
    """A vendored file with no entry is a file nothing says the origin of."""
    assert {path.name for path in DATA.iterdir() if path.name != "README.md"} == set(
        PINS
    )


def test_the_module_repeats_what_the_readme_pins() -> None:
    """`_vectors.BLOBS` guards what a benchmark reads, and README.md is why.

    The two are separate statements of one fact, which is what makes this
    test the thing keeping them one: a module that parsed the markdown
    instead would put a benchmark's inputs behind a prose format.
    """
    assert {name: PINS[name] for name in _vectors.BLOBS} == _vectors.BLOBS


def test_bip340_valid_matches_the_files_own_verification_result() -> None:
    """`Bip340.valid` is the CSV's own column, read by nothing below.

    Every implementation test in this file reads the raw CSV row instead,
    which is what leaves this field's own parsing otherwise unchecked.
    """
    parsed = {v.number: v.valid for v in _vectors.bip340()}
    for row in BIP340:
        expected = row["verification result"] == "TRUE"
        assert parsed[int(row["index"])] == expected


def test_signing_rows_have_a_32_byte_aux() -> None:
    """A missing `aux_rand` falls back to 32 zero bytes, not another width."""
    assert all(len(v.aux) == 32 for v in _vectors.signing())


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


# --- ECDSA verification, Wycheproof's bitcoin file ----------------------


def _secp256k1_py_verify(pubkey: bytes, digest: bytes, sig: bytes) -> bool:
    """Verify through secp256k1-py, whose API parses the two in two calls.

    A function rather than a lambda because the parsed key is wanted twice:
    once to deserialize the signature against and once to verify with.
    """
    key = secp256k1.PublicKey(pubkey, raw=True)
    return bool(key.ecdsa_verify(digest, key.ecdsa_deserialize(sig), raw=True))


# every implementation of ECDSA verification this project times, each handed
# the public key uncompressed, the SHA-256 of the message, and the signature
# in DER. Four of them convert: electrum-ecc wants 64 bytes, buidl and pycoin
# want the two integers, and the conversion is inside the entry here because
# rejecting a signature it cannot parse is one of the answers being tested
DSA_VERIFIERS: dict[str, Callable[[bytes, bytes, bytes], bool]] = {
    "btclib": lambda pubkey, digest, sig: dsa.verify_(digest, pubkey, sig),
    "btclib_secp256k1": lambda pubkey, digest, sig: btclib_secp256k1.dsa.verify(
        digest, pubkey, sig
    ),
    "coincurve": lambda pubkey, digest, sig: coincurve.PublicKey(pubkey).verify(
        sig, digest, None
    ),
    "secp256k1-py": _secp256k1_py_verify,
    "electrum-ecc": lambda pubkey, digest, sig: electrum_ecc.ECPubkey(
        pubkey
    ).ecdsa_verify(electrum_ecc.ecdsa_sig64_from_der_sig(sig), digest),
    "embit": lambda pubkey, digest, sig: embit.ec.PublicKey.parse(pubkey).verify(
        embit.ec.Signature.parse(sig), digest
    ),
    "python-ecdsa": lambda pubkey, digest, sig: ecdsa.VerifyingKey.from_string(
        pubkey, curve=ecdsa.SECP256k1
    ).verify_digest(sig, digest, sigdecode=ecdsa.util.sigdecode_der),
    "buidl.pecc": lambda pubkey, digest, sig: buidl.pecc.S256Point.parse(pubkey).verify(
        int.from_bytes(digest, "big"), buidl.pecc.Signature.parse(sig)
    ),
    "pycoin": lambda pubkey, digest, sig: pycoin_generator.verify(
        sec_to_public_pair(pubkey, pycoin_generator),
        int.from_bytes(digest, "big"),
        sigdecode_der(sig),
    ),
}

# the two cases that are bitcoin's rule rather than ECDSA's. A signature and
# its counterpart with s replaced by n-s both verify, which is what
# malleability *is*; rejecting the high one is the policy libsecp256k1 applies
# inside `secp256k1_ecdsa_verify`, and this file -- `EcdsaBitcoinVerify` --
# asks for it. So the packages that reach that C inherit the rule, and the
# ones that implement ECDSA themselves leave the policy to their caller and
# answer true. Both answers are right to a different question, which is why
# these two are expected the other way round below rather than excused: the
# assertion is still that the signature verifies, which it does.
#
# tc388 is flagged `ArithmeticError` and its comment says what it is, "edge
# case for signature malleability" -- so the pair is named by number rather
# than by flag, the file's own labels not separating these two from the
# arithmetic cases that are real
MALLEABILITY = (1, 388)
LOW_S_IS_THE_CALLER_S = (
    "btclib",
    "electrum-ecc",
    "python-ecdsa",
    "buidl.pecc",
    "pycoin",
)

# and the cases two packages answer wrongly, which is what a file of
# adversarial encodings is for. Recorded rather than excluded, and marked
# xfail rather than asserted: `xfail_strict` is on, so a release that fixes
# one of these fails the suite and somebody comes back to this table.
#
# Every one of them accepts a signature the file rejects, bar buidl's tc346,
# which rejects a valid one. pycoin's are a DER decoder that reads BER long
# forms, trailing bytes and lengths that overflow a uint64; buidl's are the
# same family, plus two where the arithmetic admits an r no verification
# should. Neither is a benchmark row that stops meaning anything -- both
# libraries verify the signatures this project times, which are the ones a
# specification publishes -- but a reader of those rows is owed the fact
# that their acceptance is wider than the arithmetic underneath.
LAX_DER_OR_WORSE = {
    "buidl.pecc": {
        79: "prepending 0's to r",
        100: "truncated r",
        123: "prepending 0's to s",
        346: "k*G has a large x-coordinate, and this one rejects a valid sig",
        347: "r too large",
    },
    "pycoin": dict.fromkeys(
        (3, 4, 62, 63, 109, 110), "a BER long-form length where DER has one form"
    )
    | dict.fromkeys(
        (5, 7, 8, 9, 10, 11, 12, 13, 20, 42, 79, 123),
        "a length that is wrong, or that overflows a uint64",
    )
    | dict.fromkeys(
        (18, 21, 50, 51, 52, 53, 54, 57, 100),
        "bytes appended to, or taken from, a signature that then still parses",
    ),
}

WYCHEPROOF = _vectors.wycheproof()


def _wycheproof_cases() -> list[pytest.param]:  # type: ignore[valid-type]
    """Pair every package with every case, marking what each is known to miss.

    One parametrize over pairs rather than two stacked over packages and
    cases, because what is known is a property of the pair: pycoin's DER
    decoder is wrong about a length, and nothing else here is.
    """
    return [
        pytest.param(
            package,
            case,
            marks=(
                pytest.mark.xfail(strict=True, reason=known[case.number])
                if (known := LAX_DER_OR_WORSE.get(package, {})).get(case.number)
                and case.number not in MALLEABILITY
                else ()
            ),
            id=f"{package}-tc{case.number}",
        )
        for package in sorted(DSA_VERIFIERS)
        for case in WYCHEPROOF
    ]


@pytest.mark.parametrize("package, case", _wycheproof_cases())
def test_ecdsa_verification_matches_wycheproof(
    package: str, case: _vectors.Wycheproof
) -> None:
    """Accept what the file accepts and reject what it rejects.

    A raise counts as a rejection, as it does for BIP340: an API that
    refuses to parse a signature whose length overflows a uint64 has
    answered correctly, differently spelled.
    """
    expected = case.valid
    if case.number in MALLEABILITY and package in LOW_S_IS_THE_CALLER_S:
        expected = True
    digest = hashlib.sha256(case.msg).digest()
    try:
        answer = DSA_VERIFIERS[package](case.pubkey, digest, case.sig)
    except Exception:  # noqa: BLE001 - any refusal is a rejection
        answer = False
    assert bool(answer) == expected, f"tc{case.number}: {case.comment}"


# --- base58, Bitcoin Core's own pairs -----------------------------------

# every library whose base58check encoding this project times, asked for the
# codec underneath it. Core's file is base58 with no checksum on it, which is
# the layer the timed rows are built from and the one where implementations
# differ: the alphabet is easy and the leading zeros are not, a zero byte
# being a `1` rather than a digit of a number.
#
# btclib spells the plain codec privately, `encode` and `decode` being the
# checksummed pair the rest of its module is about. Reaching for the private
# name is the only way to ask this question of it, and asking it of the
# public one would be asking a different question of every library here
BASE58_ENCODERS: dict[str, Callable[[bytes], str]] = {
    "btclib": lambda payload: btclib.base58._b58encode(payload).decode(),
    "pycoin": pycoin.encoding.b58.b2a_base58,
    "embit": embit.base58.encode,
    "buidl": buidl.helper.encode_base58,
    "python-bitcoinlib": bitcoin.base58.encode,
}
# buidl is not among the decoders, and cannot be: it publishes no base58
# decode without a checksum. `raw_decode_base58` verifies one and raises
# when there is none to verify, and `decode_base58` drops the version byte
# on top of that. Which packages can be asked a question is a fact about
# their APIs, so it is written down rather than discovered by a loop that
# skips whatever raises
BASE58_DECODERS: dict[str, Callable[[str], bytes]] = {
    "btclib": lambda encoded: btclib.base58._b58decode(encoded.encode()),
    "pycoin": pycoin.encoding.b58.a2b_base58,
    "embit": embit.base58.decode,
    "python-bitcoinlib": bitcoin.base58.decode,
}

# buidl's encoder cannot be handed nothing: it goes through `int(s.hex(), 16)`,
# which raises on the empty string rather than answering with it. Core
# publishes the empty payload as the first pair of the file, so this is a row
# of the benchmark answering a published case wrongly -- recorded here rather
# than dropped from the list, and `xfail_strict` turns a fixed release into a
# failing suite
EMPTY_PAYLOAD_RAISES = ("buidl",)

BASE58 = _vectors.base58()


def _base58_ids(vectors: list[_vectors.Base58]) -> list[str]:
    """Name a pair by what it encodes, the empty one included."""
    return [v.payload.hex()[:16] or "empty" for v in vectors]


@pytest.mark.parametrize("package", sorted(BASE58_ENCODERS))
@pytest.mark.parametrize("vector", BASE58, ids=_base58_ids(BASE58))
def test_base58_encoding_matches_the_vector(
    package: str, vector: _vectors.Base58
) -> None:
    """Encode the bytes Core publishes and get the string it publishes."""
    if not vector.payload and package in EMPTY_PAYLOAD_RAISES:
        pytest.xfail(f"{package} raises on the empty payload rather than encoding it")
    assert BASE58_ENCODERS[package](vector.payload) == vector.encoded


@pytest.mark.parametrize("package", sorted(BASE58_DECODERS))
@pytest.mark.parametrize("vector", BASE58, ids=_base58_ids(BASE58))
def test_base58_decoding_matches_the_vector(
    package: str, vector: _vectors.Base58
) -> None:
    """And back, which is where a leading zero is dropped or kept."""
    assert bytes(BASE58_DECODERS[package](vector.encoded)) == vector.payload


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
    flag cannot be restored, so the configuration `scripts/04-pure-python.py`
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
