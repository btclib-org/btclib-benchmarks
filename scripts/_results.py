# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""One run of one benchmark, kept as data rather than as a paste.

A measurement and the page about it are two different things, and only
the first of them needs a machine. So a run is kept here as data: one
JSON file per benchmark, beside the page it feeds, holding every number
as measured and everything that page states about how -- the clock, the
interpreter, the machine, what else was running on it.
`scripts/render.py` builds the page from that file, so rewording a
heading costs neither a fresh measurement, whose numbers are different,
nor a block edited by hand, whose numbers no run ever printed.

## What is stored is what was measured, and no more

Every ratio, every break-even and every sort is computed at render time
from the microseconds beside them. A derived number is not a measurement,
and storing one would let it drift from the values it came from -- and
would put a second copy of the arithmetic in the file, where the first one
could no longer be checked.

The two things stored that are *not* measurements are `method`, which says
how the run was taken, and `decimals`, which says how wide a ratio has to
print before it stops being a column of 1.0x. Both belong to the run: the
first is a claim the page makes and the second follows from how close
together that script's rows land.

## The layout is computed, so a longer name cannot break a column

Every column is sized from what is in it, and one width serves a whole
page. A width written into a format string is a floor rather than a
fence: a comparand whose name outgrows it pushes its own row out of line
with the others, and nothing anywhere says so.

## Nothing here imports a benchmark

Importing one builds its fixtures and runs its cross-comparand assertions,
which is the right price for a measurement and the wrong price for a
rewording. This module and `render.py` between them read a JSON file and
write text, and that is the whole of what publishing costs.
"""

from __future__ import annotations

import json
import platform
import subprocess
import textwrap
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from _provenance import WHAT_A_TIMING_CONTAINS

# what `render.py` refuses to read rather than misread. A saved run is a
# file this project writes and reads back a release apart, so the one
# thing it must not do is answer plausibly to a shape it does not know
SCHEMA = 1

# where a run is saved and where the page it feeds lives, which are one
# directory: a measurement nobody can find beside its page is a
# measurement that gets taken again
RESULTS = Path(__file__).resolve().parent.parent / "results"

# the two lines of the run block that nothing in a process can answer.
# `state` above all: what else was running on the machine is a fact about
# the room, and the honest place for it is a file its owner edits when it
# stops being true
MACHINE_FILE = RESULTS / "machine.toml"

# two spaces between columns, everywhere. Enough to read as a gap at any
# width, and the same gap in every table of every page
GAP = 2


@dataclass(frozen=True)
class Timing:
    """One row of a table: a label, and what a call under it cost.

    `spread` and `calls` are optional because not every script has one to
    report -- a script that times each row once has no spread to state,
    and printing an absent one as zero would claim a quiet machine.
    """

    label: str
    us_per_call: float
    spread: float | None = None
    calls: int | None = None
    rounds: int | None = None


@dataclass(frozen=True)
class Ratios:
    """Rows of one operation, to be printed fastest first.

    The ratio is against the quickest row of the table, whichever that
    turns out to be, and it is computed here rather than stored: against
    a row named in advance the column would read as that row's score
    instead of as the table's answer.

    `decimals` is the script's, and the reason is the run's: where every
    row calls the same C library they land within a few percent of each
    other, and one decimal prints 1.0x down the whole column.
    """

    title: str
    rows: list[Timing]
    decimals: int = 1


@dataclass(frozen=True)
class Pair:
    """One operation, timed through two arithmetics."""

    label: str
    values: tuple[float, float]


@dataclass(frozen=True)
class Pairs:
    """One row per operation, the two arithmetics beside each other.

    Sorted on the ratio the row divides its own two numbers into, and the
    ratio divides the second column by the first so that its direction
    carries information: under 1.0x is a pair where the first column
    lost, which no absolute value would say.
    """

    title: str
    columns: tuple[str, str]
    rows: list[Pair]


@dataclass(frozen=True)
class Preparation:
    """What preparing a key costs, and the two verifications it sits between.

    `plain` and `prepared` are the same implementation's own rows, not the
    table's fastest: what a caller decides is whether to prepare *this*
    key, and the row they would otherwise have run is the one to answer
    against.
    """

    label: str
    prepare: float
    plain: float
    prepared: float


@dataclass(frozen=True)
class BreakEven:
    """A preparation per row, and after how many calls it has paid."""

    title: str
    rows: list[Preparation]


Table = Ratios | Pairs | BreakEven


@dataclass(frozen=True)
class Provenance:
    """Which build of each package the rows below are about.

    A released wheel, a git checkout and an editable install of one
    distribution satisfy the same requirement, resolve in silence and do
    not perform alike, so this block is what makes a table checkable at
    all. `notes` are the lines printed under it: an install that is not
    the declared one is what a reader has to act on, and a column
    repeating "released" four times is not.
    """

    columns: list[str]
    rows: list[list[str]]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Run:
    """The facts about a run that no table of numbers carries.

    `when` is an ISO timestamp with its offset and `timezone` is the name
    that offset went by locally: an offset alone dates a run, and a reader
    on another continent reading `+02:00` has to work out which hour of
    whose day that was.
    """

    when: str
    timezone: str
    python: str
    method: str
    command: str
    machine: str
    state: str


@dataclass(frozen=True)
class Measurement:
    """A whole run: what ran it, what it found, and what it can be asked.

    `benchmark` names the run's file and the page it feeds, and each
    script declares its own rather than having it derived from the script's
    name. A page ordered among its siblings carries a number, and no
    module name may begin with one -- so the two names are free to differ,
    and the script says which page is its.

    `timing_note` is the block saying a timed call checks nothing, stored
    with the numbers rather than written by the renderer: a page is a
    record of one run, and a claim about what that run contained must not
    be answered by whatever this repository believes today.
    """

    benchmark: str
    run: Run
    provenance: Provenance
    tables: Sequence[Table]
    timing_note: list[str] = field(default_factory=lambda: list(WHAT_A_TIMING_CONTAINS))


# --- taking the run's own details ---------------------------------------


def _spoken_by(command: tuple[str, ...]) -> str:
    """Return a system command's one-line answer, or nothing if it has none.

    Absolute paths and a fixed argv, no shell and no input: what S603
    guards against is a command assembled from something a caller
    supplied, and there is nothing here for anyone to supply. A machine
    that answers differently -- or not at all, this being asked on any
    platform -- leaves the line to `machine.toml`.

    The encoding is named rather than left to the locale: these answers
    are a chip's name and a build number, and a machine whose locale
    decodes them differently would put the difference in a published
    page.
    """
    try:
        answered = subprocess.run(  # noqa: S603
            command, capture_output=True, check=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return answered.stdout.decode("utf-8", errors="replace").strip()


def _detected_machine() -> str:
    """Name the machine as precisely as this platform will say it.

    The processor is the part that matters and the part `platform` will
    not give: `platform.processor()` answers `arm` on the machine whose
    rows these are, where what a reader needs is which chip. macOS knows,
    and is asked; anywhere else this falls back to what `platform` has,
    and `machine.toml` is where a better line goes.
    """
    architecture = platform.machine()
    if platform.system() != "Darwin":
        return f"{platform.system()} {platform.release()}, {architecture}"
    chip = _spoken_by(("/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"))
    build = _spoken_by(("/usr/bin/sw_vers", "-buildVersion"))
    release = platform.mac_ver()[0]
    named = f"macOS {release} (build {build})" if build else f"macOS {release}"
    return f"{chip}, {named}, {architecture}" if chip else f"{named}, {architecture}"


def _machine_file() -> dict[str, str]:
    """Read the two lines a process cannot answer, or say there are none."""
    if not MACHINE_FILE.is_file():
        return {}
    read = tomllib.loads(MACHINE_FILE.read_text(encoding="utf-8"))
    return {key: str(value) for key, value in read.items()}


NO_STATE = "unrecorded: results/machine.toml says nothing about this run"


def taken_now(script: str, method: str) -> Run:
    """Return the run block for a measurement being taken right now.

    Everything derivable is derived, so that the one line a person
    maintains is the one nothing could have derived: what else the machine
    was doing. `machine.toml` may override the detected machine too, a
    detected line being the best this platform would say rather than the
    best there is.
    """
    recorded = _machine_file()
    now = datetime.now().astimezone()
    return Run(
        when=now.isoformat(timespec="seconds"),
        timezone=now.tzname() or "local",
        python=platform.python_version(),
        method=method,
        command=f"uv run python scripts/{Path(script).name}",
        machine=recorded.get("machine") or _detected_machine(),
        state=recorded.get("state") or NO_STATE,
    )


# --- rendering, which both the run and a re-render go through -----------


def _columns(rows: list[list[str]], headings: list[str]) -> str:
    """Return one block of left-aligned columns, sized from what is in them.

    The last column is not padded: a trailing run of spaces is invisible
    and every file in this repository is checked for it.
    """
    widths = [
        max(len(heading), *(len(row[column]) for row in rows)) + GAP
        for column, heading in enumerate(headings)
    ]
    lines = []
    for cells in [headings, *rows]:
        padded = [f"{cell:<{width}}" for cell, width in zip(cells, widths, strict=True)]
        lines.append("".join(padded[:-1]) + cells[-1])
    return "\n".join(lines)


def rendered_provenance(provenance: Provenance) -> str:
    """Return the packages block, its notes under it.

    Two of the five benchmarks have no table to print here: one compares
    btclib with btclib and the other three packages, and a column of two
    or three cells is a table only in the sense that it has edges. Those
    say what they have to say in lines, which is what `notes` are, and a
    Provenance with no columns is that rather than an empty one.
    """
    lines = provenance.notes
    if provenance.columns:
        lines = [_columns(provenance.rows, provenance.columns), *lines]
    return "\n".join(lines)


def rendered_run(run: Run) -> str:
    """Return the block naming the run, which no number in it can.

    Local time and UTC both: a run is dated for whoever reads it next, and
    the two answers are the same instant said twice rather than a
    conversion the reader is left to make.
    """
    when = datetime.fromisoformat(run.when)
    utc = when.astimezone(UTC)
    lines = [
        f"when    : {when:%Y-%m-%d %H:%M} {run.timezone} ({utc:%H:%M} UTC)",
        f"python  : {run.python}",
        f"method  : {run.method}",
        f"command : {run.command}",
        f"machine : {run.machine}",
    ]
    state = textwrap.wrap(
        run.state, width=70, initial_indent="state   : ", subsequent_indent=" " * 10
    )
    return "\n".join(lines + state)


def labels(names: list[str]) -> list[str]:
    """Drop the operation from each row's name, the title having said it.

    Every function in a table is named `<operation>_<comparand>`, so the
    operation is the leading run of underscore-separated words they all
    share: printing it on every row is the same prefix repeated down a
    column, and what a reader compares is what is left of the name. Whole
    words rather than characters, or three rows reading `btclib`, `embit`
    and `buidl` would lose a `b` to what they happen to share.
    """
    split = [name.split("_") for name in names]
    shared = 0
    while len({parts[shared] for parts in split}) == 1 and all(
        len(parts) > shared + 1 for parts in split
    ):
        shared += 1
    return ["_".join(parts[shared:]) for parts in split]


def labels_of(tables: Sequence[Table]) -> list[str]:
    """Return every label in a run, whichever shape of table holds it."""
    return [row.label for table in tables for row in table.rows]


def width_for(labels: list[str]) -> int:
    """Return the width the label column takes, given everything in it.

    One width for a whole page rather than one per table: the tables of a
    page are read down the screen, and a column that steps in and out
    between them reads as tables about different things. Computed and not
    written down, so that a comparand with a longer name widens the column
    instead of overflowing a number somebody chose in 2026.

    Both the run and a re-render call this over the same labels, so a
    person watching a table go past is watching the line the page will
    carry -- which is only true while nothing between the two rounds it
    off differently.
    """
    return max(len(label) for label in labels) + GAP


def _call_note(row: Timing) -> str:
    """Say how many calls a row is the average of, where a script says.

    Beside the row and not above the table, because the count is part of
    what a row is: the counts within one table differ by orders of
    magnitude, and sorting puts those rows next to each other.
    """
    if row.calls is None:
        return ""
    counted = f"{row.rounds}x{row.calls}" if row.rounds else f"{row.calls}"
    return f"   ({counted} calls)"


def rendered_ratios(table: Ratios, width: int) -> str:
    """Return one operation's rows, quickest first, ratioed against the best."""
    quickest = min(row.us_per_call for row in table.rows)
    spreads = any(row.spread is not None for row in table.rows)
    heading = f"  {'':<{width}}{'μs/call':>10}{'vs best':>12}"
    lines = [table.title, heading + (f"{'spread':>9}" if spreads else "")]
    for row in sorted(table.rows, key=lambda row: row.us_per_call):
        ratio = row.us_per_call / quickest
        line = f"  {row.label:<{width}}{row.us_per_call:10.2f}"
        line += f"{ratio:11.{table.decimals}f}x"
        if row.spread is not None:
            line += f"{row.spread:8.1%}"
        lines.append((line + _call_note(row)).rstrip())
    return "\n".join(lines)


def rendered_pairs(table: Pairs, width: int) -> str:
    """Return one row per operation, sorted on what the second column costs.

    Five significant digits, which is four more than the machine can be
    held to and enough that two rows within a percent of each other are
    still two numbers.
    """
    first, second = table.columns
    heading = f"{'':<{width}}{first:>14}{second:>14}{'ratio':>10}"
    lines = [line for line in (table.title, heading) if line]
    for row in sorted(table.rows, key=lambda row: row.values[1] / row.values[0]):
        quick, slow = row.values
        lines.append(
            f"{row.label:<{width}}{quick:>#14.5g}{slow:>#14.5g}{slow / quick:>9.1f}x"
        )
    return "\n".join(lines)


def rendered_break_even(table: BreakEven, width: int) -> str:
    """Return what each preparation costs and when it has paid for itself."""
    lines = [
        table.title,
        f"  {'':<{width}}{'prepare':>10}{'saves/call':>13}{'break-even':>13}",
    ]
    for row in table.rows:
        saved = row.plain - row.prepared
        lines.append(
            f"  {row.label:<{width}}{row.prepare:10.2f}"
            f"{saved:13.2f}{row.prepare / saved:13.1f}"
        )
    return "\n".join(lines)


def rendered_table(table: Table, width: int) -> str:
    """Return whichever of the three shapes a table is."""
    if isinstance(table, Ratios):
        return rendered_ratios(table, width)
    if isinstance(table, Pairs):
        return rendered_pairs(table, width)
    return rendered_break_even(table, width)


def rendered_output(measurement: Measurement) -> str:
    """Return the numbers block: what a timing contains, then every table.

    One blank line between blocks, which is what the run itself prints as
    each table is measured. The two are the same text by construction --
    the script prints these very functions' answers, over the width every
    label in the run gives them -- so what a person watched go past is
    what the page carries.
    """
    width = width_for(labels_of(measurement.tables))
    blocks = [rendered_table(table, width) for table in measurement.tables]
    if measurement.timing_note:
        blocks.insert(0, "\n".join(measurement.timing_note))
    return "\n\n".join(blocks)


# --- the file itself ----------------------------------------------------


def _table_as_json(table: Table) -> dict[str, object]:
    """Return one table as the mapping saved for it, tagged by shape."""
    if isinstance(table, Ratios):
        return {
            "kind": "ratios",
            "title": table.title,
            "decimals": table.decimals,
            "rows": [
                {
                    key: value
                    for key, value in (
                        ("label", row.label),
                        ("us_per_call", row.us_per_call),
                        ("spread", row.spread),
                        ("rounds", row.rounds),
                        ("calls", row.calls),
                    )
                    if value is not None
                }
                for row in table.rows
            ],
        }
    if isinstance(table, Pairs):
        return {
            "kind": "pairs",
            "title": table.title,
            "columns": list(table.columns),
            "rows": [
                {"label": row.label, "values": list(row.values)} for row in table.rows
            ],
        }
    return {
        "kind": "break-even",
        "title": table.title,
        "rows": [
            {
                "label": row.label,
                "prepare": row.prepare,
                "plain": row.plain,
                "prepared": row.prepared,
            }
            for row in table.rows
        ],
    }


def _table_from_json(saved: dict[str, object]) -> Table:
    """Return the table one saved mapping describes."""
    kind = saved["kind"]
    title = str(saved["title"])
    rows = saved["rows"]
    assert isinstance(rows, list)
    if kind == "ratios":
        return Ratios(
            title=title,
            decimals=int(str(saved["decimals"])),
            rows=[
                Timing(
                    label=str(row["label"]),
                    us_per_call=float(row["us_per_call"]),
                    spread=None if row.get("spread") is None else float(row["spread"]),
                    calls=None if row.get("calls") is None else int(row["calls"]),
                    rounds=None if row.get("rounds") is None else int(row["rounds"]),
                )
                for row in rows
            ],
        )
    if kind == "pairs":
        columns = saved["columns"]
        assert isinstance(columns, list)
        return Pairs(
            title=title,
            columns=(str(columns[0]), str(columns[1])),
            rows=[
                Pair(
                    label=str(row["label"]),
                    values=(float(row["values"][0]), float(row["values"][1])),
                )
                for row in rows
            ],
        )
    assert kind == "break-even"
    return BreakEven(
        title=title,
        rows=[
            Preparation(
                label=str(row["label"]),
                prepare=float(row["prepare"]),
                plain=float(row["plain"]),
                prepared=float(row["prepared"]),
            )
            for row in rows
        ],
    )


def as_json(measurement: Measurement) -> dict[str, object]:
    """Return the whole run as the mapping written to disk."""
    run = measurement.run
    return {
        "schema": SCHEMA,
        "benchmark": measurement.benchmark,
        "run": {
            "when": run.when,
            "timezone": run.timezone,
            "python": run.python,
            "method": run.method,
            "command": run.command,
            "machine": run.machine,
            "state": run.state,
        },
        "provenance": {
            "columns": measurement.provenance.columns,
            "rows": measurement.provenance.rows,
            "notes": measurement.provenance.notes,
        },
        "timing_note": measurement.timing_note,
        "tables": [_table_as_json(table) for table in measurement.tables],
    }


def from_json(saved: dict[str, object]) -> Measurement:
    """Return the run one saved file describes, or refuse to guess.

    A schema this module does not know is a file written by a version of
    it that knew something this one does not, and rendering it would
    publish that difference as a table.
    """
    if saved.get("schema") != SCHEMA:
        raise ValueError(f"{saved.get('schema')} is not schema {SCHEMA}")
    run = saved["run"]
    provenance = saved["provenance"]
    tables = saved["tables"]
    assert isinstance(run, dict)
    assert isinstance(provenance, dict)
    assert isinstance(tables, list)
    note = saved.get("timing_note") or []
    assert isinstance(note, list)
    return Measurement(
        benchmark=str(saved["benchmark"]),
        run=Run(**{key: str(value) for key, value in run.items()}),
        provenance=Provenance(
            columns=[str(column) for column in provenance["columns"]],
            rows=[[str(cell) for cell in row] for row in provenance["rows"]],
            notes=[str(line) for line in provenance.get("notes", [])],
        ),
        tables=[_table_from_json(table) for table in tables],
        timing_note=[str(line) for line in note],
    )


def saved_run(benchmark: str) -> Path:
    """Return where one benchmark's run is written and read back."""
    return RESULTS / f"{benchmark}.json"


def save(measurement: Measurement) -> Path:
    """Write the run beside the page it feeds, and return where it went."""
    path = saved_run(measurement.benchmark)
    path.write_text(
        json.dumps(as_json(measurement), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load(benchmark: str) -> Measurement:
    """Read back one saved run, which is all a re-render is given."""
    path = saved_run(benchmark)
    return from_json(json.loads(path.read_text(encoding="utf-8")))
