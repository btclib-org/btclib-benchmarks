# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The by-hand records every benchmark reads from one place.

These tests hold the one copy to what a reader of it relies on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from btclib_benchmarks import _releases

if TYPE_CHECKING:
    import pytest


def test_for_each_pinned_distribution_the_pinned_builds_are_its_dated_builds() -> None:
    """A pin and a date are recorded for the same builds of a pinned one."""
    assert {
        name: set(builds) for name, builds in _releases.LIBSECP256K1_PINS.items()
    } == {
        name: set(_releases.RELEASE_DATES[name]) for name in _releases.LIBSECP256K1_PINS
    }


def test_a_recorded_release_prints_its_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """The date is read for the installed version."""
    monkeypatch.setattr(_releases, "version", lambda _: "2026.10.3")
    assert _releases.released("btclib") == "2026-10-03"


def test_an_upgraded_release_prints_unrecorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """A version the record was not read for says so, and borrows no date."""
    monkeypatch.setattr(_releases, "version", lambda _: "9999.1")
    assert _releases.released("btclib") == "unrecorded"


def test_a_distribution_recorded_by_artifact_prints_unrecorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Its version alone names no build, so it names no date."""
    monkeypatch.setattr(_releases, "version", lambda _: "0.14.0")
    assert _releases.released("secp256k1") == "unrecorded"


def test_a_distribution_with_no_record_names_its_branch_and_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing is dated that was never released."""
    monkeypatch.setattr(
        _releases, "origin_of", lambda _: "btclib-org/btclib main@8720a7df02b0"
    )
    assert _releases.released("not-recorded") == "main@8720a7df02b0"
