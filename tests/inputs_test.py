# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The pool every benchmark draws from, and the cache that hands it back.

`src/btclib_benchmarks/_inputs.py` is the one place a measurement gets an
input, so two of its properties are worth holding to. The first is that
the cache is a cache: what a second run reads has to be what the first
run built, or two pages that claim the same pool were measured over
different bytes. The second is that a file it cannot vouch for is
treated as absent rather than repaired -- a run interrupted mid-write
leaves a short file, and half a pool handed to a benchmark is the
failure this module exists to prevent.

Neither shows up in a timing. A pool half as long as it should be measures
perfectly well and reports a number about the wrong thing.
"""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

import btclib_secp256k1.keys
import pytest

from btclib_benchmarks import _inputs

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the module's cache at a directory this test owns.

    A directory per test rather than the repository's own: these cases
    write short and corrupt files on purpose, and the pool a developer has
    already paid to build is not something a test should be able to break.
    """
    monkeypatch.setattr(_inputs, "CACHE", tmp_path / "inputs")
    return tmp_path / "inputs"


def test_the_stream_is_the_seed_and_nothing_else() -> None:
    """Same seed, same bytes: the pool is re-derivable and not random."""
    assert _inputs._stream(4, 0) == _inputs._stream(4, 0)
    assert _inputs._stream(4, 0) != _inputs._stream(4, 4)


def test_what_the_cache_hands_back_is_what_was_built(cache: Path) -> None:
    """Build once, read twice, and the second read is off the disk.

    Counted rather than forbidden: a producer that raises when it should
    not be called says the same thing, and leaves a line in this file that
    never runs.
    """
    builds: list[int] = []

    def produce() -> list[bytes]:
        builds.append(len(builds))
        return _inputs._stream(_inputs.POOL_SIZE, 0)

    built = _inputs.cached("probe", 32, produce)
    assert len(built) == _inputs.POOL_SIZE
    assert _inputs.cached("probe", 32, produce) == built
    assert len(builds) == 1


def test_a_file_written_whole_leaves_no_partial_behind(cache: Path) -> None:
    """The temporary the write goes through is moved, not left."""
    _inputs.cached("probe", 32, lambda: _inputs._stream(_inputs.POOL_SIZE, 0))
    assert not list(cache.glob("*.partial"))
    assert len(list(cache.glob("*.bin"))) == 1


def test_a_short_file_is_absent_rather_than_half_a_pool(cache: Path) -> None:
    """Which is what an interrupted write leaves, and what must not be read."""
    name = f"{_inputs.GENERATION}-{_inputs.POOL_SIZE}-probe.bin"
    cache.mkdir(parents=True)
    (cache / name).write_bytes(b"\x00" * 32)

    rebuilt = _inputs.cached("probe", 32, lambda: _inputs._stream(_inputs.POOL_SIZE, 0))
    assert len(rebuilt) == _inputs.POOL_SIZE
    assert rebuilt[0] != b"\x00" * 32


def test_a_missing_file_reads_as_missing(cache: Path) -> None:
    """The ordinary first run, and the one case that is not an error."""
    assert _inputs._read(cache / "nothing.bin", 32) is None


def test_an_overlong_file_is_also_treated_as_absent(cache: Path) -> None:
    """A ragged file is not only a short one, and the docstring says both."""
    name = f"{_inputs.GENERATION}-{_inputs.POOL_SIZE}-probe.bin"
    cache.mkdir(parents=True)
    (cache / name).write_bytes(b"\x00" * (_inputs.POOL_SIZE * 32 + 1))
    assert _inputs._read(cache / name, 32) is None


def test_the_cache_directory_is_created_even_when_its_parent_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fixture, directly under `tmp_path`, cannot tell `True` from `False`.

    A cache path with a missing intermediate directory can.
    """
    monkeypatch.setattr(_inputs, "CACHE", tmp_path / "missing" / "inputs")
    _inputs.cached("probe", 32, lambda: _inputs._stream(4, 0))
    assert (tmp_path / "missing" / "inputs").is_dir()


def test_the_seed_folds_in_the_generation() -> None:
    """`SEED` is `%`-formatted with `GENERATION`, not repeated that often."""
    assert _inputs.SEED == b"btclib-benchmarks/inputs/%d" % _inputs.GENERATION


def test_the_stream_hashes_an_eight_byte_big_endian_counter() -> None:
    """The counter's width and byte order are part of the derivation."""
    expected = sha256(_inputs.SEED + (5).to_bytes(8, "big")).digest()
    assert _inputs._stream(1, 5) == [expected]


def test_keys_are_the_stream_from_zero(cache: Path) -> None:
    """Keys start where the stream starts, and messages start after them."""
    assert _inputs.keys()[:2] == _inputs._stream(2, 0)


def test_keys_are_read_from_the_cache_on_the_second_call(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A width `_read` cannot match rebuilds every call, unseen by value alone.

    The stream is deterministic, so a needless rebuild returns bytes
    identical to the cached ones -- only counting the rebuild sees it.
    """
    monkeypatch.setattr(_inputs, "POOL_SIZE", 4)
    calls: list[int] = []
    real_stream = _inputs._stream

    def counting(count: int, start: int) -> list[bytes]:
        calls.append(start)
        return real_stream(count, start)

    monkeypatch.setattr(_inputs, "_stream", counting)
    assert _inputs.keys() == _inputs.keys()
    assert calls == [0]


def test_messages_are_read_from_the_cache_on_the_second_call(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same property as above, for the other cached stream."""
    monkeypatch.setattr(_inputs, "POOL_SIZE", 4)
    calls: list[int] = []
    real_stream = _inputs._stream

    def counting(count: int, start: int) -> list[bytes]:
        calls.append(start)
        return real_stream(count, start)

    monkeypatch.setattr(_inputs, "_stream", counting)
    assert _inputs.messages() == _inputs.messages()
    assert calls == [4]


def test_pubkeys_65_are_read_from_the_cache_on_the_second_call(
    cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same property as the two above, for the derived public keys."""
    monkeypatch.setattr(_inputs, "POOL_SIZE", 4)
    calls: list[bytes] = []
    real_pubkey = btclib_secp256k1.keys.pubkey_from_prvkey

    def counting(prvkey: bytes, *, compressed: bool) -> bytes:
        calls.append(prvkey)
        return real_pubkey(prvkey, compressed=compressed)

    monkeypatch.setattr(btclib_secp256k1.keys, "pubkey_from_prvkey", counting)
    assert _inputs.pubkeys_65() == _inputs.pubkeys_65()
    assert len(calls) == 4


def test_the_keys_and_the_messages_are_different_bytes(cache: Path) -> None:
    """Two streams from one seed, so a key is never also a message."""
    assert _inputs.keys() != _inputs.messages()
    assert len(_inputs.keys()) == len(_inputs.messages()) == _inputs.POOL_SIZE


def test_the_compressed_key_is_the_uncompressed_one_cut(cache: Path) -> None:
    """A slice rather than a second generator multiplication."""
    uncompressed = _inputs.pubkeys_65()[:4]
    compressed = _inputs.pubkeys_33()[:4]
    xonly = _inputs.xonly()[:4]
    for full, short, x in zip(uncompressed, compressed, xonly, strict=True):
        assert full[0] == 0x04
        assert short[1:] == full[1:33] == x
        assert short[0] == 2 + (full[64] & 1)
