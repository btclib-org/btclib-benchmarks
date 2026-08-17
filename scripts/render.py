# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Write the published pages from the saved runs, measuring nothing.

    uv run python scripts/render.py            # every page, from its run
    uv run python scripts/render.py 05-key-reuse   # one of them
    uv run python scripts/render.py --check    # say what is stale, write none

A benchmark writes `results/<name>.json` when it is run. This reads that
file and puts its three blocks into `results/<name>.md`, between the
markers the page carries. Everything else in the page -- the headings,
the paragraph explaining what a column means, the analysis under the
numbers -- is prose somebody wrote, and this never touches it.

That separation is the point. Rewording a heading otherwise costs either
a run of the benchmark, which produces different numbers on a machine in
a different mood, or an edit to the block by hand, which produces numbers
no run ever printed. Here it costs the edit and this command, and the
numbers stay the ones the last measurement found.

## What is replaced, and what a page without a marker gets

Three regions, each opened and closed by an HTML comment:

    <!-- provenance: begin -->  which build of each package was measured
    <!-- run: begin -->         the clock, the machine, and the method
    <!-- output: begin -->      what a timing contains, and every table

Whatever lies between a pair of markers is replaced, fences and all. A
page with no `provenance` region keeps its packages block at the top of
the output block instead, which is where two of these five have always
carried it -- their prose reads around it that way, and a renderer is the
wrong thing to have opinions about that.

## It imports no benchmark, and that is not an accident

Importing one derives keys, signs a message per comparand and runs every
cross-comparand assertion before it will answer a question. That is the
right price for a measurement and an absurd one for a heading, so nothing
here can pay it: this reads JSON and writes markdown, and the only module
it shares with a benchmark is the one that defines the shape of a run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import _results
from _results import RESULTS, Measurement

# a region is named once, opened and closed with the same name: a page
# says which blocks it holds and this puts them there. The name is in
# both markers so that a page missing an end marker is a mistake with a
# line number rather than a file quietly truncated at the next one
REGIONS = ("provenance", "run", "output", "method")

# a page may carry its tables in one `output` region or split them into one
# region per operation, named for the group the run tags each table with.
# The split page carries `method` too, that block being a claim about every
# number on the page and having no single block to sit above once the
# tables are six of them
TABLES_PREFIX = "tables: "


def _fenced(block: str) -> list[str]:
    """Return one block as the fenced lines a page carries it in.

    `text` rather than a language: none of these blocks is code, and a
    highlighter guessing at a column of numbers is worse than none.
    """
    return ["```text", *block.split("\n"), "```"]


def blocks(measurement: Measurement, has_own_provenance: bool) -> dict[str, list[str]]:
    """Return the lines each region of a page is to be given.

    A page with nowhere of its own to put the packages block gets it above
    the numbers, in the same fence: that is one block for the reader
    either way, and which of the two a page wants is a property of the
    prose written around it.
    """
    provenance = _results.rendered_provenance(measurement.provenance)
    output = _results.rendered_output(measurement)
    filled = {
        "provenance": _fenced(provenance),
        "run": _fenced(_results.rendered_run(measurement.run)),
        "method": _fenced(_results.rendered_method(measurement)),
        "output": _fenced(
            output if has_own_provenance else f"{provenance}\n\n{output}"
        ),
    }
    for group in _results.groups_of(measurement):
        filled[f"{TABLES_PREFIX}{group}"] = _fenced(
            _results.rendered_group(measurement, group)
        )
    return filled


def _region_bounds(lines: list[str], name: str) -> tuple[int, int] | None:
    """Return where one region's content starts and ends, if the page has it.

    The bounds are of the content and not of the markers: the markers are
    the page's and stay where the author put them, and everything between
    them belongs to the last run.
    """
    begin = f"<!-- {name}: begin -->"
    end = f"<!-- {name}: end -->"
    opened = [number for number, line in enumerate(lines) if line.strip() == begin]
    closed = [number for number, line in enumerate(lines) if line.strip() == end]
    if not opened and not closed:
        return None
    if len(opened) != 1 or len(closed) != 1 or closed[0] < opened[0]:
        raise ValueError(f"{name}: markers are not one pair, opened then closed")
    return opened[0] + 1, closed[0]


def rendered_page(page: str, measurement: Measurement) -> str:
    """Return the page with every region it declares filled from the run."""
    lines = page.split("\n")
    names = [
        *REGIONS,
        *(f"{TABLES_PREFIX}{g}" for g in _results.groups_of(measurement)),
    ]
    bounds = {name: _region_bounds(lines, name) for name in names}
    split = [name for name in names if name.startswith(TABLES_PREFIX) and bounds[name]]
    if bounds["run"] is None or (bounds["output"] is None and not split):
        raise ValueError("a page needs a run region, and output or table regions")
    if split and len(split) != len(_results.groups_of(measurement)):
        raise ValueError("a split page carries a region for every group of the run")
    filled = blocks(measurement, has_own_provenance=bounds["provenance"] is not None)
    # last region first, so that replacing one does not move the next
    for name, where in sorted(
        ((name, where) for name, where in bounds.items() if where),
        key=lambda region: region[1][0],
        reverse=True,
    ):
        start, stop = where
        lines[start:stop] = filled[name]
    return "\n".join(lines)


def publish(benchmark: str, *, check: bool) -> bool:
    """Write one page from its saved run; return whether it had changed.

    Returned rather than announced here, so that `--check` and a real
    render are the same walk over the same pages and cannot disagree
    about what is stale.
    """
    page = RESULTS / f"{benchmark}.md"
    was = page.read_text(encoding="utf-8")
    now = rendered_page(was, _results.load(benchmark))
    if now != was and not check:
        page.write_text(now, encoding="utf-8")
    return now != was


def main(arguments: list[str]) -> int:
    """Render the pages named, or every page that has a saved run.

    A name is a benchmark's, and a path to either of its two files is
    taken as that name: `results/05-key-reuse.md` is what tab completion
    offers, and refusing it would be a puzzle rather than a rule.
    """
    check = "--check" in arguments
    named = [Path(argument).stem for argument in arguments if argument[:1] != "-"]
    benchmarks = named or sorted(path.stem for path in RESULTS.glob("*.json"))
    stale = []
    for benchmark in benchmarks:
        changed = publish(benchmark, check=check)
        if changed:
            stale.append(benchmark)
        said = ("stale" if check else "written") if changed else "up to date"
        print(f"{benchmark:<24}{said}")
    if stale and check:
        print(f"\n{len(stale)} page(s) do not match their saved run", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
