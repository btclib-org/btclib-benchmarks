# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The pool every benchmark draws from, and the cache that hands it back.

`scripts/_inputs.py` is the one place a measurement gets an input, so two
of its properties are worth holding to. The first is that the cache is a
cache: what a second run reads has to be what the first run built, or two
pages that claim the same pool were measured over different bytes. The
second is that a file it cannot vouch for is treated as absent rather than
repaired -- a run interrupted mid-write leaves a short file, and half a
pool handed to a benchmark is the failure this module exists to prevent.

Neither shows up in a timing. A pool half as long as it should be measures
perfectly well and reports a number about the wrong thing.
"""

from __future__ import annotations

from pathlib import Path

import _inputs
import pytest


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
