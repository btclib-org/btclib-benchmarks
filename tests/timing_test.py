# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The rounds-and-halves estimator, held to its arithmetic on a clock of ours.

Nothing here measures anything: the clock is replaced by a list of readings,
so what is asserted is the formula and not a machine.
"""

from __future__ import annotations

import time

import pytest

from btclib_benchmarks._timing import benchmark


def _clock_of(durations: list[float], monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `perf_counter` read the start and the end of each given duration."""
    readings = iter([t for d in durations for t in (0.0, d)])
    monkeypatch.setattr(time, "perf_counter", lambda: next(readings))


def test_the_estimate_is_the_quickest_round_and_the_gap_is_between_halves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rounds of 8, 4, 6 and 10 microseconds halve into 4 and 6."""
    _clock_of([8e-6, 4e-6, 6e-6, 10e-6], monkeypatch)
    estimate, apart = benchmark(lambda: None, 1, 4)
    assert estimate == pytest.approx(4.0)
    assert apart == pytest.approx(2.0)


def test_the_time_is_divided_by_the_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """A round of 8 microseconds over 4 calls is 2 microseconds a call."""
    _clock_of([8e-6, 8e-6], monkeypatch)
    estimate, apart = benchmark(lambda: None, 4, 2)
    assert estimate == pytest.approx(2.0)
    assert apart == pytest.approx(0.0)


def test_the_function_is_called_calls_times_in_every_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`calls` per round, `rounds` rounds."""
    _clock_of([1e-6] * 6, monkeypatch)
    seen: list[None] = []
    benchmark(lambda: seen.append(None), 5, 6)
    assert len(seen) == 30


def test_an_odd_number_of_rounds_leaves_the_larger_half_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rounds of 5, 3 and 4 microseconds halve into [5] and [3, 4]."""
    _clock_of([5e-6, 3e-6, 4e-6], monkeypatch)
    estimate, apart = benchmark(lambda: None, 1, 3)
    assert estimate == pytest.approx(3.0)
    assert apart == pytest.approx(2.0)


@pytest.mark.parametrize("rounds", [0, 1])
def test_rounds_that_cannot_be_halved_are_refused(rounds: int) -> None:
    """Half of one round is the minimum of nothing."""
    with pytest.raises(ValueError, match="cannot be halved"):
        benchmark(lambda: None, 1, rounds)
