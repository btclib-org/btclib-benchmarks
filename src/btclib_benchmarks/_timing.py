# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The rounds-and-halves estimator, once, for every benchmark that uses it.

`_results.py` holds the shape of a run and never the arithmetic that
produces one, so the estimator is a module of its own. A script passes
its own `rounds` and its own `calls`; what is shared is the formula, and
changing it is one edit.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def benchmark(func: Callable[[], None], calls: int, rounds: int) -> tuple[float, float]:
    """Return the quickest round's microseconds per call, and the halves' gap.

    `rounds` rounds of `calls` calls each. The minimum is the estimate:
    noise is one-sided -- nothing on this machine makes a call quicker than
    it is -- so the quickest round is the one that ran with least taken from
    it, and a mean would carry every interruption into the number.

    The second number is how far that estimate moved when the row was
    measured twice, which is what the rounds are halved for: the column is
    the distance between the two halves' minima, in the same microseconds as
    the value beside it, so the two are read against each other without
    arithmetic. The column is read for one question -- whether a gap between
    two adjacent rows is a gap this run settled. Contiguous
    halves rather than alternate rounds, because the rows of a table are
    measured minutes apart and a machine that drifts over a row's rounds
    will drift over a table's rows. Two halves taken seconds apart say
    nothing about two runs taken a day apart; `CONTRIBUTING.md`'s *Running
    a benchmark* says how to read a page with that in mind.

    The scripts save it as `halves_apart`. `spread`, the slowest round less
    the quickest, is a different statistic with a key of its own: a
    definition living in this docstring is not carried by the file, so the
    two statistics are two keys and a saved number means what its key says.
    `_results.py`'s `SCHEMA` has the reasoning, that being where a format
    decision belongs.

    The column is quantized and lands on a lattice, which is worth knowing
    before reading a small value on it: a round is measured to one tick of
    `perf_counter` and divided by the call count, so every value this column
    carries is a whole number of ticks divided by that count. Zero is one of
    the lattice's points and means the two halves' minima fell inside one
    tick. It is not an unmeasured row: `_results.py` leaves an absent one out
    of the saved run rather than writing it as zero.

    What the column must not be is the slowest round less the quickest. That
    is an extreme-value statistic over a handful of samples, so it has
    enormous variance by construction and reports the worst interruption a
    row happened to catch rather than anything about the package. More rounds
    make a maximum worse and both halves' minima better, which is the other
    reason this column is not that one.

    Returned and not printed: the tables are sorted fastest to slowest and
    each row divides by the quickest, neither of which can be done a line at
    a time -- every number has to be in hand before the first line is.

    Args:
        func: The call being timed.
        calls: How many times `func` is called in a round.
        rounds: How many rounds, two at least.

    Returns:
        The quickest round's microseconds per call, and the halves' gap.

    Raises:
        ValueError: `rounds` is under two, a half of one round being the
            minimum of nothing.
    """
    return estimate(_rounds_of(func, calls, rounds))


def _round(func: Callable[[], None], calls: int) -> float:
    """Return the microseconds per call of one round of `calls` calls."""
    # perf_counter and not time(): the wall clock can step backwards under an
    # NTP correction, and a benchmark is the one place that shows up as a
    # negative duration
    start = time.perf_counter()
    for _ in range(calls):
        func()
    return (time.perf_counter() - start) / calls * 1e6


def _rounds_of(func: Callable[[], None], calls: int, rounds: int) -> list[float]:
    """Return the microseconds per call of each of `rounds` rounds."""
    return [_round(func, calls) for _ in range(rounds)]


def _halves(samples: Sequence[float]) -> tuple[Sequence[float], Sequence[float]]:
    """Split the rounds into a first half and a second, the larger one second.

    Args:
        samples: A row's rounds, in the order they were taken.

    Returns:
        The first half and the second.

    Raises:
        ValueError: There are under two rounds, a half of one round being the
            minimum of nothing.
    """
    if len(samples) < 2:
        msg = f"{len(samples)} rounds cannot be halved"
        raise ValueError(msg)
    half = len(samples) // 2
    return samples[:half], samples[half:]


def estimate(samples: Sequence[float]) -> tuple[float, float]:
    """Return the quickest round and the halves' gap of a row's rounds.

    What `benchmark` returns, for rounds that were taken some other way.

    Args:
        samples: A row's rounds, in the order they were taken.

    Returns:
        The quickest round's microseconds per call, and the halves' gap.

    Raises:
        ValueError: There are under two rounds.
    """
    first, second = (min(half) for half in _halves(samples))
    return min(first, second), abs(first - second)


def interleaved(
    funcs: Sequence[Callable[[], None]], calls: int, rounds: int
) -> list[list[float]]:
    """Return the rounds of each of `funcs`, taken one after another in turn.

    Round one of every function, then round two of every function, and so
    on, so that a machine drifting over the measurement drifts under all of
    them alike. Rows timed one after the other do not share that: the first
    ran in the machine's earlier state and the last in its later one, and a
    difference between two of them carries the drift as well as the
    functions. A script asks for this wherever it prints a difference of two
    rows, and `estimate` turns each list into the row's number.

    Args:
        funcs: The calls being timed, in the order a round visits them.
        calls: How many times a function is called in a round.
        rounds: How many rounds each function gets.

    Returns:
        One list of rounds per function, in the order of `funcs`.
    """
    samples: list[list[float]] = [[] for _ in funcs]
    for _ in range(rounds):
        for own, func in zip(samples, funcs, strict=True):
            own.append(_round(func, calls))
    return samples


def saving_apart(plain: Sequence[float], prepared: Sequence[float]) -> float:
    """Return how far the saving moved between the two halves of the rounds.

    The saving is `plain` less `prepared`, each as its half's quickest round
    gives it. This is the gap that decides whether a break-even is settled,
    and it is not the sum of the two rows' own gaps: the two rows' halves
    can move together, and a saving between interleaved rows does not move
    with them.

    Args:
        plain: The rounds of the row the saving is taken from.
        prepared: The rounds of the row it is taken to.

    Returns:
        The distance between the two halves' savings, in microseconds.

    Raises:
        ValueError: Either has under two rounds, or they differ in number.
    """
    if len(plain) != len(prepared):
        msg = f"{len(plain)} rounds against {len(prepared)} cannot be paired"
        raise ValueError(msg)
    plain_first, plain_second = (min(half) for half in _halves(plain))
    prepared_first, prepared_second = (min(half) for half in _halves(prepared))
    return abs((plain_first - prepared_first) - (plain_second - prepared_second))
