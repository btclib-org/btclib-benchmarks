# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The one thing in the renderer that refuses rather than formats.

`scripts/_results.py` is outside the coverage gate on purpose: a page is
written by a command a person runs, and putting the rewording of a heading
behind the suite is the coupling that split removes. `labelled` is the
exception worth a case of its own, because it is not formatting -- it is a
limit, and a limit whose own correctness nothing checks is the defect it was
added to fix. `LINE` widened by accident, or `>` becoming `>=`, or the
separator gaining a space, would otherwise fail nothing anywhere.

Those three are what the cases below cover, and they do not cover them the
same way. Two pin the *relationship* between the padding, the separator and
the limit, reading every term from the module, so a deliberate widening moves
them rather than breaking them. That is right for a relationship and blind to
the limit itself, which is why one case reads the width from outside the
module: `LABEL` moving is caught by `render.py --check`, since every page
shifts a column, and `LINE` moving is caught by nothing at all -- widening it
changes no rendering, only what is refused.

What is asserted is the boundary and not the rendering, so this puts no page
behind the suite: `labelled` is a pure function of a label and a string.
Importing the module costs the gate nothing, `scripts/_results.py` being in
coverage's `omit`.
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
