# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What the second signature under the same key costs, and the hundredth.

The other four benchmarks time one operation once: a key, a message, a
signature, and a row. That is the right shape for asking what an
operation costs, and the wrong shape for asking what a verifier pays,
because a verifier does not verify one signature. A node checks every
input of every transaction, a wallet checks a batch, a message checker
checks a list -- and does it, over and over, under a key it already has.

Whatever a verification derives from the key alone is the same on the
second call as on the first. This times what that is worth: the same
verification, with the key handed in raw and with it prepared, per
implementation and on both of btclib's paths.

## Reusing this state is not the usual caching trade

The objection to keeping key-derived state alive is that key material
outlives its use. It does not arise here: what is worth preparing is
derived from the *public* key, and a public key is public. There is no
secret in a decompressed point or in a table of its odd multiples, and
nothing is being kept alive that an observer of the signature does not
already have.

The private key has no counterpart to prepare. The one table a signature
leans on is the generator's, which every key shares and which btclib
already memoizes; there is no per-private-key state any of these
implementations builds. So this benchmark is about verification, and its
absence of a signing table is a result and not an omission.

## What it does not show, said before the rows say it

Preparing the key does not bring Python within reach of the C library.
The Python rows move by a small factor and the C rows move by a small
factor, and the order across the two groups is what it was: the gap is
the arithmetic, and no amount of reuse is an amount of C. A reader
hoping the reuse column is where Python catches libsecp256k1 should read
the ratio and stop hoping. What the column does show is where a caller
already has a saving available, and where btclib has none to offer.

## What each implementation lets a caller reuse

- **btclib**, on either path, accepts the public key as a parsed point
  wherever it accepts sec octets, so a caller who parses once and keeps
  the point has that saving today. It has no prepared key beyond that:
  the multiplication tables built from the point are dropped when the
  call returns and rebuilt on the next one, which is
  btclib-org/btclib#893.
- **python-ecdsa** has `VerifyingKey.precompute()`, which builds the
  table once and reuses it. On version 0.19.2 it raises `AssertionError`
  on a key built by `from_string` -- `precompute` hands the point to
  `PointJacobi.from_affine`, which does not carry the curve order over,
  and the precomputation asserts on it. A key built from the secret
  exponent works. The caller who cannot use it is therefore the verifier,
  who has the public key as bytes and nothing else, which is the caller
  the method is for; the row below uses the construction that works, so
  it measures the method rather than the defect.

The reference is the fastest row of each table, as the pure-Python
benchmark prints it, and not a row named in advance: with two paths and
two libraries in one table, naming one would be choosing.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from hashlib import sha256

import btclib
import btclib_secp256k1
import ecdsa
from _provenance import report
from btclib.curves import curve, sec_point
from btclib.ecc import dsa
from btclib.to_pub_key import pub_keyinfo_from_prv_key


def report_provenance() -> None:
    """Say which build of each package these rows are about."""
    report(
        ("btclib", btclib.__file__),
        ("btclib-secp256k1", btclib_secp256k1.__file__),
        ("ecdsa", ecdsa.__file__),
    )


# BIP340 test vector 1's secret key and message, as every other script
# here takes them: a key nobody chose, so that no row is flattered by one
PRVKEY = 0xB7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF
MSG_HASH = bytes.fromhex(
    "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89"
)
VECTOR_XONLY_PUBKEY = bytes.fromhex(
    "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"
)

# the two forms of the same key: the octets a verifier is handed, and the
# point they decompress to. Both are built here, before anything is
# timed, because which one a row passes is the whole of what it measures
SEC_OCTETS = pub_keyinfo_from_prv_key(PRVKEY)[0]
POINT = sec_point.point_from_octets(SEC_OCTETS)

# grind=False: one signature, and the same one both paths verify
DSA_SIG = dsa.sign_(MSG_HASH, PRVKEY, grind=False)

# python-ecdsa's key, built from the secret exponent rather than from the
# octets: `precompute` raises on a key built from octets, and the
# docstring above says why that is worth a sentence rather than a
# workaround nobody sees
ECDSA_SIGNING_KEY = ecdsa.SigningKey.from_secret_exponent(PRVKEY, curve=ecdsa.SECP256k1)
ECDSA_KEY = ECDSA_SIGNING_KEY.verifying_key
ECDSA_SIG = ECDSA_SIGNING_KEY.sign_digest_deterministic(MSG_HASH, hashfunc=sha256)


def _precomputed_key() -> ecdsa.VerifyingKey:
    """Return a python-ecdsa key whose multiplication table is built.

    A function rather than a constant because the preparation is itself
    a row: `main` times this call to say what the saving below costs.
    """
    key = ecdsa.SigningKey.from_secret_exponent(
        PRVKEY, curve=ecdsa.SECP256k1
    ).verifying_key
    key.precompute()
    return key


ECDSA_KEY_PREPARED = _precomputed_key()

# the specification's own public key, checked before anything is timed:
# a table of reuse timings is worth nothing if the key being reused is
# not the key the vector publishes
assert SEC_OCTETS[1:] == VECTOR_XONLY_PUBKEY
assert dsa.verify_(MSG_HASH, SEC_OCTETS, DSA_SIG)
assert dsa.verify_(MSG_HASH, POINT, DSA_SIG)
assert ECDSA_KEY.verify_digest(ECDSA_SIG, MSG_HASH)
assert ECDSA_KEY_PREPARED.verify_digest(ECDSA_SIG, MSG_HASH)
# the two libraries sign the same digest under the same key to the same
# pair, RFC6979 over sha256 being both of their nonce derivations and
# neither grinding here -- so the rows below verify one signature and not
# two, and this says so more sharply than a mutual verification would
assert DSA_SIG.r.to_bytes(32, "big") + DSA_SIG.s.to_bytes(32, "big") == ECDSA_SIG, (
    "python-ecdsa and btclib disagree on RFC6979's signature"
)
assert dsa.verify_(MSG_HASH, SEC_OCTETS, DSA_SIG)


def python_arithmetic_only() -> None:
    """Turn btclib's libsecp256k1 dispatch off, everywhere at once.

    Called once, from `main`, after every bindings row has been timed:
    the assignment cannot be undone within a process, so the order of the
    rows below is the measurement's own requirement and not a choice.
    """
    curve._libsecp256k1_available = False


def verify_octets() -> None:
    """Time a verification handed the key as sec octets."""
    dsa.assert_as_valid_(MSG_HASH, SEC_OCTETS, DSA_SIG)


def verify_point() -> None:
    """Time a verification handed the key as an already-parsed point."""
    dsa.assert_as_valid_(MSG_HASH, POINT, DSA_SIG)


def verify_ecdsa() -> None:
    """Time a python-ecdsa verification, no table prepared."""
    ECDSA_KEY.verify_digest(ECDSA_SIG, MSG_HASH)


def verify_ecdsa_prepared() -> None:
    """Time a python-ecdsa verification against a precomputed table."""
    ECDSA_KEY_PREPARED.verify_digest(ECDSA_SIG, MSG_HASH)


def parse_point() -> None:
    """Time the preparation btclib offers: decompressing the key once."""
    sec_point.point_from_octets(SEC_OCTETS)


def benchmark(func: Callable[[], None], calls: int) -> float:
    """Return microseconds per call, `calls` calls of `func`.

    Returned and not printed, as the other four scripts do it: every row
    divides by the fastest of its table, so no line can be written until
    the whole table is in hand.
    """
    # perf_counter and not time(): the wall clock can step backwards
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def prepare_once(func: Callable[[], object], calls: int) -> float:
    """Return microseconds for one preparation, `calls` of them timed.

    Separate from `benchmark` because a preparation is not a row of the
    table above: it happens once per key and is paid before the first
    verification, so what it belongs in is the break-even below.
    """
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def table(title: str, rows: dict[str, float]) -> None:
    """Print one table, fastest first, against the fastest of its rows."""
    against = min(rows.values())
    print(f"\n{title}")
    print(f"  {'':30s} {'':10s}      {'vs best':>8s}")
    for label, value in sorted(rows.items(), key=lambda row: row[1]):
        print(f"  {label:30s} {value:10.2f} μs   {value / against:8.1f}x")


def break_even(title: str, rows: tuple[tuple[str, float, float, float], ...]) -> None:
    """Print what each preparation costs and when it has paid for itself.

    The break-even is against the same implementation's own unprepared
    row and not against the fastest of the table: what a caller decides
    is whether to prepare *this* key, and the row that answers that is
    the one they would otherwise have run.
    """
    print(f"\n{title}")
    print(f"  {'':30s} {'prepare':>10s} {'saves/call':>11s} {'break-even':>11s}")
    for label, prepare, plain, prepared in rows:
        saved = plain - prepared
        calls = prepare / saved
        print(f"  {label:30s} {prepare:9.2f} μs {saved:9.2f} μs {calls:9.1f}")


def main() -> None:
    """Time every row, bindings first, and print the tables.

    The order is `python_arithmetic_only`'s requirement: it cannot be
    undone within a process, so every row that is meant to reach the
    bindings runs before it and every row that is meant to measure Python
    runs after.
    """
    report_provenance()

    bindings_octets = benchmark(verify_octets, 20_000)
    bindings_point = benchmark(verify_point, 20_000)
    bindings_parse = prepare_once(parse_point, 20_000)

    ecdsa_plain = benchmark(verify_ecdsa, 500)
    ecdsa_prepared = benchmark(verify_ecdsa_prepared, 500)
    ecdsa_prepare = prepare_once(_precomputed_key, 20)

    python_arithmetic_only()

    python_octets = benchmark(verify_octets, 500)
    python_point = benchmark(verify_point, 500)
    python_parse = prepare_once(parse_point, 2_000)

    table(
        "ECDSA verify, one key, every signature under it",
        {
            "btclib, bindings, octets": bindings_octets,
            "btclib, bindings, parsed point": bindings_point,
            "btclib, Python, octets": python_octets,
            "btclib, Python, parsed point": python_point,
            "python-ecdsa": ecdsa_plain,
            "python-ecdsa, precomputed": ecdsa_prepared,
        },
    )

    break_even(
        "what preparing the key costs, and after how many verifications it pays",
        (
            (
                "btclib, bindings, parse once",
                bindings_parse,
                bindings_octets,
                bindings_point,
            ),
            ("btclib, Python, parse once", python_parse, python_octets, python_point),
            ("python-ecdsa, precompute()", ecdsa_prepare, ecdsa_plain, ecdsa_prepared),
        ),
    )


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
