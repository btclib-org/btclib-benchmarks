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
    from collections.abc import Callable


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
    if rounds < 2:
        msg = f"{rounds} rounds cannot be halved"
        raise ValueError(msg)
    # perf_counter and not time(): the wall clock can step backwards under an
    # NTP correction, and a benchmark is the one place that shows up as a
    # negative duration
    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        for _ in range(calls):
            func()
        samples.append((time.perf_counter() - start) / calls * 1e6)
    half = len(samples) // 2
    first, second = min(samples[:half]), min(samples[half:])
    return min(first, second), abs(first - second)
