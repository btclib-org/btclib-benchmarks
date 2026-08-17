# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The two things in the renderer that refuse rather than format.

`scripts/_results.py` is outside the coverage gate on purpose: a page is
written by a command a person runs, and putting the rewording of a heading
behind the suite is the coupling that split removes. So what earns a case here
is not the formatting but a limit, and a limit whose own correctness nothing
checks is the defect it was added to fix.

`labelled` is the first: `LINE` widened by accident, or `>` becoming `>=`, or
the separator gaining a space, would otherwise fail nothing anywhere.

Its three cases do not cover it the same way. Two pin the *relationship*
between the padding, the separator and the limit, reading every term from the
module, so a deliberate widening moves them rather than breaking them. That is
right for a relationship and blind to the limit itself, which is why one case
reads the width from outside the module: `LABEL` moving is caught by
`render.py --check`, since every page shifts a column, and `LINE` moving is
caught by nothing at all -- widening it changes no rendering, only what is
refused.

`Timing` is the second, and what it refuses is a row stating two dispersions.
Delete those two lines and nothing anywhere goes red: the row renders as
whichever field the property reads first, under a column whose page states one
definition, which is the failure two keys for two statistics exist to prevent.
Two cases, because a row arrives two ways -- built by a script, or read from a
saved run, the second being the only way a file has.

What is asserted throughout is the boundary and not the rendering, so this puts
no page behind the suite: `labelled` is a pure function of a label and a
string, and a refused row is refused before any table is built. Importing the
module costs the gate nothing, `scripts/_results.py` being in coverage's
`omit`.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import _results
import pytest

# where the same width is written down for prose, arrived at independently of
# the renderer: `ruff` holds every comment and docstring in this project to it,
# and `.markdownlint.jsonc` leaves `MD013` at its default, which is the same
# number reached from the other side
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_the_widest_line_that_fits_is_built() -> None:
    """Eight columns of label and two of separator leave seventy.

    Stated as the arithmetic rather than as the number, so that widening
    either constant moves this case with it instead of breaking it.
    """
    value = "x" * (_results.LINE - _results.LABEL - len(": "))
    line = _results.labelled("method", value)
    assert len(line) == _results.LINE
    assert line.endswith(value)


def test_one_column_wider_is_refused() -> None:
    """And refused where it is built, with the width it came to.

    A page cannot carry the line, and the renderer is the only code that
    knows both halves: the script writing the value cannot see the label it
    will print under, and `markdownlint` cannot see inside the fenced block
    it lands in.
    """
    value = "x" * (_results.LINE - _results.LABEL - len(": ") + 1)
    with pytest.raises(ValueError, match=f"wider than {_results.LINE}"):
        _results.labelled("method", value)


def test_the_limit_is_the_width_the_prose_is_held_to() -> None:
    """The one case that reads the number from outside the module it guards.

    The two cases above pin the *relationship* -- padding plus separator plus
    value reaches the limit, and one past it is refused -- which is what a
    deliberate widening should move rather than break. But every term in them
    is read from `_results`, so none of them can see `LINE` itself change:
    set it to two hundred and they build a longer value, get a wider line,
    and assert it is `LINE` wide.

    That is the mutation this file's own opening paragraph names as its
    reason for existing, and `render.py --check` cannot catch it either --
    widening the limit changes no rendering, only what is refused. So the
    limit is asserted against `max-doc-length`, which is where this project
    writes the same width down for prose and reaches it independently: a
    guard widened without the prose it protects being widened fails here.
    """
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    prose = config["tool"]["ruff"]["lint"]["pycodestyle"]["max-doc-length"]
    assert prose == _results.LINE


def test_a_row_that_states_two_dispersions_is_refused() -> None:
    """The second limit, tripped the way a script trips it.

    `spread` is the slowest round less the quickest and `halves_apart` the
    distance between two halves' minima, so a row carrying both is a script
    filling the field it used to fill and the one it moved to. Nothing
    downstream would say so: the renderer prints whichever `dispersion` reads
    first, and every page renders as it did.
    """
    with pytest.raises(ValueError, match="two dispersions"):
        _results.Timing(
            label="dsa_sign", us_per_call=15.0, spread=0.1, halves_apart=0.2
        )


def test_a_saved_row_carrying_both_keys_is_refused() -> None:
    """And the way a file trips it, which is the only way a file has.

    A saved run is read back a release after it was written, so the shape to
    refuse is not only the one a script can build today -- two keys in one row
    is what a file written across a rename would carry. Every row of every
    page reaches the renderer through here, and no other reader of a run file
    constructs a `Timing` at all.
    """
    saved: dict[str, object] = {
        "kind": "ratios",
        "title": "1. one operation",
        "decimals": 2,
        "rows": [
            {
                "label": "dsa_sign",
                "us_per_call": 15.0,
                "spread": 0.1,
                "halves_apart": 0.2,
            }
        ],
    }
    with pytest.raises(ValueError, match="two dispersions"):
        _results._table_from_json(saved)


def test_every_label_the_pages_print_is_padded_alike() -> None:
    """The five labels line up, which is what a reader reads down.

    `labelled` replaced five hand-padded literals, so what has to hold is
    that it reproduces them: every label reaches the separator at the same
    column, whatever its length.
    """
    columns = {
        _results.labelled(label, "value").index(":")
        for label in ("when", "machine", "python", "method", "command")
    }
    assert columns == {_results.LABEL}
