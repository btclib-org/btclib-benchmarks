# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""One pool of inputs, shared by every benchmark and built at most once.

Every script here draws from the same `POOL_SIZE` secret keys and the same
messages, derived from a seed written below rather than from a vector file:
what a page of timings is read for is the boundary crossing, or which
arithmetic answered, and neither is a property of the input. What published
vectors are for is correctness, and correctness is `tests/`, which runs them
against every implementation this project measures. So nothing in a benchmark
asserts, and no timed loop checks what it computed.

sha256 of the seed and a counter rather than `random`, whose stream is
CPython's business and could change under a table nobody re-derived: this one
is re-derivable in any language with a hash, from the two constants below.

## The pool is a size, and the size is a decision

`POOL_SIZE` is large enough that the longest row in the suite -- the address
encodings of `03-libraries.py`, at two hundred thousand calls -- reads it
twice per round, and every other row once or twice. A row that cycled a
short pool many times would be measuring a warm cache rather than the
operation, and a pool longer than any row would leave the tail of it
unread; two passes is the compromise, and it is what makes a caching
implementation show up as one rather than hide.

## Built once, then read

Deriving a public key is a generator multiplication and signing is another,
so building what these pages need costs the better part of a minute. It is
therefore done once and written to `CACHE`, which the next run reads instead
-- the second measurement on a machine starts at the numbers.

Nothing here is versioned. The directory is in `.gitignore`, and that is the
whole of the arrangement: these bytes are re-derivable from two constants, so
committing tens of megabytes of them would be storing what the code already
says.

## Asking for new inputs

`GENERATION` is the answer to "new inputs". Bump it, and every file below is
written under a name that carries it, so the old cache is neither read nor
overwritten and a page re-measured against the new pool says which generation
it ran on. It is a constant in this file rather than state in the cache: a
number in the code is reviewable, and two machines at the same commit draw
the same bytes.
"""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from pathlib import Path

# what a benchmark reads. Two hundred thousand is the longest row in the
# suite, so this is two passes over the pool for it and one or two for
# everything else: see the module docstring for why two
POOL_SIZE = 100_000

# bump this for "new inputs", and nothing else. Every cache file is named
# for it, so the old pool is left where it is rather than overwritten
GENERATION = 1

# the base the stream is derived from, with the generation folded in: two
# constants, and the pool follows from them in any language with a hash
SEED = b"btclib-benchmarks/inputs/%d" % GENERATION

# ignored by git, and named for that: what is here is re-derivable, and
# what it buys is the second run on a machine rather than a record of
# anything
CACHE = Path(__file__).resolve().parent.parent.parent / ".inputs"


def _stream(count: int, start: int) -> list[bytes]:
    """Return `count` 32-byte blocks of the seeded stream, from `start`."""
    return [
        sha256(SEED + n.to_bytes(8, "big")).digest()
        for n in range(start, start + count)
    ]


def _read(path: Path, width: int) -> list[bytes] | None:
    """Return the fixed-width records of a cache file, or None if it has none.

    A short or ragged file is treated as absent rather than repaired: it is
    a file this module wrote and can write again, and half a pool is the
    one thing a caller must not be handed.
    """
    if not path.is_file():
        return None
    raw = path.read_bytes()
    if len(raw) != POOL_SIZE * width:
        return None
    return [raw[i : i + width] for i in range(0, len(raw), width)]


def cached(name: str, width: int, produce: Callable[[], list[bytes]]) -> list[bytes]:
    """Return one named list of records, from the cache or freshly built.

    Args:
        name: what the records are, which becomes the file name.
        width: the length of one record, every record being that long. A
            file is a concatenation and nothing else -- no header, no
            separator -- so the width has to come from the caller and the
            length of the file is what checks it.
        produce: how to build them, called only where the cache has none.

    Returns:
        `POOL_SIZE` records of `width` bytes.
    """
    path = CACHE / f"{GENERATION}-{POOL_SIZE}-{name}.bin"
    if (records := _read(path, width)) is not None:
        return records
    records = produce()
    CACHE.mkdir(parents=True, exist_ok=True)
    # written whole and then moved into place: a run interrupted while
    # writing would otherwise leave a short file that the next one reads
    # as a pool
    tmp = path.with_suffix(".partial")
    tmp.write_bytes(b"".join(records))
    tmp.replace(path)
    return records


def keys() -> list[bytes]:
    """Return the pool's secret keys.

    A 32-byte draw is a valid secret key unless it is zero or at least the
    group order, which the stream will not produce before the sun goes out.
    """
    return cached("keys", 32, lambda: _stream(POOL_SIZE, 0))


def messages() -> list[bytes]:
    """Return the pool's messages, one per key and from the same stream."""
    return cached("messages", 32, lambda: _stream(POOL_SIZE, POOL_SIZE))


def pubkeys_65() -> list[bytes]:
    """Return the pool's public keys, uncompressed.

    The form that carries both coordinates, and the one everything else
    here is cut from: parsing it is a read where parsing the compressed
    form is a field square root, so a fixture that starts from these pays
    for the derivation once and never for a lift.

    Derived through `btclib_secp256k1`, which is a fixture's business and
    not a row's: a public key is a public key, and the package that
    computed it is not something a timing can see.
    """
    import btclib_secp256k1.keys  # noqa: PLC0415

    return cached(
        "pubkeys65",
        65,
        lambda: [
            btclib_secp256k1.keys.pubkey_from_prvkey(prvkey, compressed=False)
            for prvkey in keys()
        ],
    )


def pubkeys_33() -> list[bytes]:
    """Return the pool's public keys, compressed.

    Cut from the uncompressed form rather than derived a second time: the
    x and the parity of y are both already there, so this is a slice and
    not a generator multiplication. Not cached for the same reason -- it
    is cheaper to cut than to read.
    """
    return [bytes([2 + (pubkey[64] & 1)]) + pubkey[1:33] for pubkey in pubkeys_65()]


def xonly() -> list[bytes]:
    """Return the pool's x-only public keys, which BIP340 verifies against."""
    return [pubkey[1:33] for pubkey in pubkeys_65()]
