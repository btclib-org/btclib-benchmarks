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

from btclib_benchmarks._timing import (
    benchmark,
    estimate,
    interleaved,
    saving_apart,
)


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


def test_estimate_is_what_benchmark_returns_of_its_rounds() -> None:
    """Rounds of 8, 4, 6 and 10 microseconds halve into 4 and 6."""
    value, apart = estimate([8.0, 4.0, 6.0, 10.0])
    assert value == pytest.approx(4.0)
    assert apart == pytest.approx(2.0)


def test_estimate_refuses_rounds_that_cannot_be_halved() -> None:
    """One round has no second half."""
    with pytest.raises(ValueError, match="1 rounds cannot be halved"):
        estimate([1.0])


def test_interleaved_visits_every_function_once_a_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rounds alternate a, b, a, b: each function's list is in round order."""
    _clock_of([1e-6, 2e-6, 3e-6, 4e-6], monkeypatch)
    order: list[str] = []
    samples = interleaved(
        [lambda: order.append("a"), lambda: order.append("b")], calls=1, rounds=2
    )
    assert order == ["a", "b", "a", "b"]
    assert samples[0] == pytest.approx([1.0, 3.0])
    assert samples[1] == pytest.approx([2.0, 4.0])


def test_interleaved_calls_a_function_calls_times_a_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`calls` per round, `rounds` rounds, for each function."""
    _clock_of([1e-6] * 6, monkeypatch)
    seen: list[None] = []
    interleaved([lambda: seen.append(None)] * 2, calls=3, rounds=3)
    assert len(seen) == 18


def test_saving_apart_is_the_gap_of_the_saving_between_the_halves() -> None:
    """Plain halves at 10 and 12, prepared at 6 and 6: savings 4 and 6."""
    assert saving_apart([10.0, 12.0], [6.0, 6.0]) == pytest.approx(2.0)


def test_saving_apart_does_not_move_with_halves_that_move_together() -> None:
    """Both rows 3 slower in the second half: the saving is the same."""
    assert saving_apart([10.0, 13.0], [6.0, 9.0]) == pytest.approx(0.0)


def test_saving_apart_refuses_rows_of_unequal_round_counts() -> None:
    """Halves of different lengths are not the same rounds of a pair."""
    with pytest.raises(ValueError, match="cannot be paired"):
        saving_apart([1.0, 1.0, 1.0], [1.0, 1.0])


def test_saving_apart_refuses_rounds_that_cannot_be_halved() -> None:
    """One round of each row has no second half."""
    with pytest.raises(ValueError, match="cannot be halved"):
        saving_apart([1.0], [1.0])
