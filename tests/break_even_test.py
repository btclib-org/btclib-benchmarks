# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What a break-even prints when the saving it divides by is not a saving.

A preparation that saves nothing never pays for itself, so the table says
`never` where the quotient would be a negative count of calls or a
`ZeroDivisionError` raised before the run is saved. The saving's own
halves' gap is saved with the row when the script measured it, and left out
of the file when it did not.
"""

from __future__ import annotations

import pytest

from btclib_benchmarks import _results

WIDTH = 8


def _table(*rows: _results.Preparation) -> _results.BreakEven:
    """Return a break-even table of the given rows."""
    return _results.BreakEven(title="t", rows=list(rows))


@pytest.mark.parametrize("prepared", [19.0, 19.5])
def test_a_saving_of_nothing_or_less_prints_never(prepared: float) -> None:
    """An equal pair and an inverted one both print `never`."""
    row = _results.Preparation("x", prepare=3.0, plain=19.0, prepared=prepared)
    line = _results.rendered_break_even(_table(row), WIDTH).splitlines()[-1]
    assert line.split()[-1] == "never"


def test_a_saving_prints_the_calls_it_takes_to_pay_back() -> None:
    """A preparation of 3 against a saving of 2 pays back in one and a half."""
    row = _results.Preparation("x", prepare=3.0, plain=19.0, prepared=17.0)
    line = _results.rendered_break_even(_table(row), WIDTH).splitlines()[-1]
    assert line.split()[-1] == "1.5"


def test_a_row_without_the_gap_is_blank_under_its_neighbours_halves_column() -> None:
    """A row without the gap is blank under the heading its neighbour has."""
    with_gap = _results.Preparation(
        "x", prepare=3.0, plain=19.0, prepared=17.0, saving_halves_apart=0.5
    )
    without = _results.Preparation("y", prepare=3.0, plain=19.0, prepared=17.0)
    lines = _results.rendered_break_even(_table(with_gap, without), WIDTH).splitlines()
    assert lines[1].split()[-2:] == ["halves", "break-even"]
    assert lines[2].split()[-2:] == ["0.50", "1.5"]
    assert lines[3].split()[-2:] == ["2.00", "1.5"]
    assert len(lines[1]) == len(lines[2]) == len(lines[3])


def test_a_table_with_no_gap_prints_no_halves_column() -> None:
    """A run saved before the gap was measured renders as it did."""
    row = _results.Preparation("x", prepare=3.0, plain=19.0, prepared=17.0)
    heading = _results.rendered_break_even(_table(row), WIDTH).splitlines()[1]
    assert "halves" not in heading


def test_the_gap_survives_a_save_and_an_absent_one_is_not_written() -> None:
    """A gap is a measurement, and zero for a missing one would claim one."""
    with_gap = _results.Preparation(
        "x", prepare=3.0, plain=19.0, prepared=17.0, saving_halves_apart=0.5
    )
    without = _results.Preparation("y", prepare=3.0, plain=19.0, prepared=17.0)
    saved = _results._table_as_json(_table(with_gap, without))
    rows = saved["rows"]
    assert isinstance(rows, list)
    assert rows[0]["saving_halves_apart"] == pytest.approx(0.5)
    assert "saving_halves_apart" not in rows[1]
    assert _results._table_from_json(saved) == _table(with_gap, without)
