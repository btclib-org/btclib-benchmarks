# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The by-hand records every benchmark reads from one place.

These tests hold the one copy to what a reader of it relies on.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from btclib_benchmarks import _releases


def test_for_each_pinned_distribution_the_pinned_builds_are_its_dated_builds() -> None:
    """A pin and a date are recorded for the same builds of a pinned one."""
    assert {
        name: set(builds) for name, builds in _releases.LIBSECP256K1_PINS.items()
    } == {
        name: set(_releases.RELEASE_DATES[name]) for name in _releases.LIBSECP256K1_PINS
    }


@pytest.fixture
def from_an_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every distribution read as installed from an index."""
    monkeypatch.setattr(_releases, "git_revision", lambda _: None)


@pytest.mark.usefixtures("from_an_index")
def test_a_recorded_release_prints_its_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """The date is read for the installed version."""
    monkeypatch.setattr(_releases, "version", lambda _: "2026.10.3")
    assert _releases.released("btclib") == "2026-10-03"


@pytest.mark.usefixtures("from_an_index")
def test_an_upgraded_release_prints_unrecorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """A version the record was not read for says so, and borrows no date."""
    monkeypatch.setattr(_releases, "version", lambda _: "9999.1")
    assert _releases.released("btclib") == "unrecorded"


@pytest.mark.usefixtures("from_an_index")
def test_a_distribution_recorded_by_artifact_prints_unrecorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Its version alone names no build, so it names no date."""
    monkeypatch.setattr(_releases, "version", lambda _: "0.14.0")
    assert _releases.released("secp256k1") == "unrecorded"
    assert _releases.released("secp256k1", "0.14.0 wheel") == "2026-01-29"


@pytest.mark.usefixtures("from_an_index")
def test_a_distribution_with_no_record_is_named_by_its_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing is dated that was never recorded."""
    monkeypatch.setattr(_releases, "origin_of", lambda _: "editable: /dev/x")
    assert _releases.released("not-recorded") == "/dev/x"


def test_a_git_install_at_a_released_version_names_its_branch_and_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A branch whose metadata carries a release's version is not that release.

    The released btclib beside it keeps its date: a default-branch run of
    one comparand leaves the others at their release.
    """
    monkeypatch.setattr(_releases, "version", lambda _: "2026.10.3")
    monkeypatch.setattr(
        _releases,
        "git_revision",
        lambda name: None if name == "btclib" else "main@8720a7df02b0",
    )
    assert _releases.build_of("ecc") == "8720a7df02b0"
    assert _releases.released("ecc") == "main@8720a7df02b0"
    assert _releases.released("not-recorded") == "main@8720a7df02b0"
    assert _releases.released("btclib") == "2026-10-03"


def test_a_git_install_at_a_recorded_commit_prints_its_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """secp256k1lab's tag is a release, and its commit is what is recorded."""
    monkeypatch.setattr(_releases, "git_revision", lambda _: "v1.0.0@44dc4bd893b8")
    assert _releases.released("secp256k1lab") == "2025-03-26"


def test_secp256k1lab_is_recorded_at_the_commit_the_lock_pins() -> None:
    """The record's key and the lock's revision are one commit.

    Bumping the tag in pyproject.toml moves the lock, and this then says
    the record was read for another build.
    """
    lock = (Path(__file__).parents[1] / "uv.lock").read_text(encoding="utf-8")
    pinned = re.findall(r"secp256k1lab\?tag=[^#\"]+#([0-9a-f]{40})", lock)
    assert pinned
    assert {commit[:12] for commit in pinned} == set(
        _releases.RELEASE_DATES["secp256k1lab"]
    )
