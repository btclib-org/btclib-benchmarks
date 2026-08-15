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
import math
import platform
import subprocess
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

# where a machine says what it is, when the run cannot work it out well
# enough on its own. Everything else in the run block is taken where the
# run is
MACHINE_FILE = RESULTS / "machine.toml"

# two spaces between columns, everywhere. Enough to read as a gap at any
# width, and the same gap in every table of every page
GAP = 2


@dataclass(frozen=True)
class Timing:
    """One row of a table: a label, and what a call under it cost.

    `spread` and `deviation` are two answers to one question, how far the
    rounds of a row scattered, and a row carries whichever its script
    measured: the spread is how far the slowest round ran from the
    quickest, in the same microseconds as `us_per_call` so that the two
    are read against each other without arithmetic, and the deviation is
    the standard deviation over all of them, which is worth having only
    where the rounds are many. Both are optional, as `calls` is: a script
    that times each row once has no dispersion to state, and printing an
    absent one as zero would claim a quiet machine.
    """

    label: str
    us_per_call: float
    spread: float | None = None
    deviation: float | None = None
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


def page_of(script: str) -> str:
    """Return the name a benchmark's script, its run and its page share.

    One name for the three, so that none of them can be found without the
    other two. It begins with a number and holds hyphens, neither of which
    a module name may -- and neither of which a module name has to: nothing
    imports these five by an `import` statement, the suite reaching them
    through `importlib` and a person through `python scripts/<name>.py`.
    """
    return Path(script).stem


@dataclass(frozen=True)
class Measurement:
    """A whole run: what ran it, what it found, and what it can be asked.

    `benchmark` names the run's file and the page it feeds, which is the
    script's own name: `page_of` above is where that is said once.

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


def taken_now(script: str, method: str) -> Run:
    """Return the run block for a measurement being taken right now.

    Everything here is derived, `machine.toml` overriding only the machine
    itself: a detected line is the best this platform will say rather than
    the best there is, and a run on somebody else's hardware wants to name
    whose.
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
    """Return the block naming when and where a run took place.

    Local time and UTC both: a run is dated for whoever reads it next, and
    the two answers are the same instant said twice rather than a
    conversion the reader is left to make. `method` and `command` are not
    here: both are a claim about the numbers below rather than about the
    moment the clock started, so they open the output block instead, next
    to what they describe.
    """
    when = datetime.fromisoformat(run.when)
    utc = when.astimezone(UTC)
    return "\n".join(
        [
            f"when    : {when:%Y-%m-%d %H:%M} {run.timezone} ({utc:%H:%M} UTC)",
            f"machine : {run.machine}",
            f"python  : {run.python}",
        ]
    )


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


def counted_once(tables: Sequence[Table]) -> str:
    """Say how many calls every row is the average of, where they agree.

    A count repeated down a column is a column of that count, and repeated
    again in every title is that column turned sideways. So where a whole
    page shares one it is said above the tables and nowhere else.

    Where the rows differ -- which is every page whose comparands are
    orders of magnitude apart, a count sized for one measuring nothing on
    another -- there is nothing to hoist and each row keeps its own.
    """
    counts = {
        (row.rounds, row.calls)
        for table in tables
        for row in table.rows
        if isinstance(row, Timing)
    }
    if len(counts) != 1:
        return ""
    return counted_calls(*counts.pop())


def counted_calls(rounds: int | None, calls: int | None) -> str:
    """Return how many calls a row is the average of, for the method line.

    A script builds its own from its constants, and `counted_once` reads
    the same answer back out of a finished run, so what a person watched
    and what the page carries are the one sentence rather than two that
    have to be kept saying the same thing.
    """
    if calls is None:
        return ""
    if rounds is None:
        return f"{calls} calls each row"
    return f"{calls} calls each round, {rounds} rounds per row"


def rendered_ratios(table: Ratios, width: int, *, counted: bool = False) -> str:
    """Return one operation's rows, quickest first, ratioed against the best.

    `counted` says the page has already stated the call count above every
    table, which is what `counted_once` decides.
    """
    quickest = min(row.us_per_call for row in table.rows)
    spreads = any(row.spread is not None for row in table.rows)
    deviations = any(row.deviation is not None for row in table.rows)
    heading = f"  {'':<{width}}{'μs/call':>10}"
    if deviations:
        heading += f"{'sd':>10}"
    heading += f"{'vs best':>12}"
    lines = [table.title, heading + (f"{'spread':>9}" if spreads else "")]
    for row in sorted(table.rows, key=lambda row: row.us_per_call):
        ratio = row.us_per_call / quickest
        line = f"  {row.label:<{width}}{row.us_per_call:10.2f}"
        if row.deviation is not None:
            line += f"{'± ' + format(row.deviation, '.2f'):>10}"
        line += f"{ratio:11.{table.decimals}f}x"
        if row.spread is not None:
            line += f"{row.spread:9.2f}"
        lines.append((line if counted else line + _call_note(row)).rstrip())
    return "\n".join(lines)


def _significant(value: float, digits: int = 3) -> str:
    """Round to `digits` significant digits, and print without an exponent.

    `g` is the format that counts significant digits and it reaches for
    scientific notation as soon as a value outgrows the precision asked
    for -- which every Python row of the two-paths table does, so half a
    column would read `1.31e+03`. Rounding first and choosing the decimals
    afterwards says the same thing in the notation a table wants.

    Three digits: two fewer than the machine can be held to, and enough
    that two rows a percent apart are still two numbers.
    """
    if not value:  # pragma: no cover - no operation measures as free
        return "0"
    exponent = math.floor(math.log10(abs(value)))
    decimals = max(0, digits - 1 - exponent)
    return f"{round(value, digits - 1 - exponent):.{decimals}f}"


def rendered_pairs(table: Pairs, width: int) -> str:
    """Return one row per operation, sorted on what the second column costs."""
    first, second = table.columns
    heading = f"{'':<{width}}{first:>14}{second:>14}{'ratio':>10}"
    lines = [line for line in (table.title, heading) if line]
    for row in sorted(table.rows, key=lambda row: row.values[1] / row.values[0]):
        quick, slow = row.values
        lines.append(
            f"{row.label:<{width}}{_significant(quick):>14}"
            f"{_significant(slow):>14}{slow / quick:>9.1f}x"
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


def rendered_table(table: Table, width: int, *, counted: bool = False) -> str:
    """Return whichever of the three shapes a table is."""
    if isinstance(table, Ratios):
        return rendered_ratios(table, width, counted=counted)
    if isinstance(table, Pairs):
        return rendered_pairs(table, width)
    return rendered_break_even(table, width)


def rendered_output(measurement: Measurement) -> str:
    """Return the numbers block: how they were taken, then every table.

    `method` and `command` open it, ahead of what a timing contains and
    every table after that: both are a claim about the numbers below them,
    not about the run block's moment. One blank line between blocks
    otherwise, which is what the run itself prints as each table is
    measured. The two are the same text by construction -- the script
    prints these very functions' answers, over the width every label in
    the run gives them -- so what a person watched go past is what the
    page carries.
    """
    run = measurement.run
    width = width_for(labels_of(measurement.tables))
    # the count is in the method line, so a row that shares it with every
    # other row of the page says it nowhere: `counted_once` is asked
    # whether they do, not for a line to print
    counted = bool(counted_once(measurement.tables))
    blocks = [
        rendered_table(table, width, counted=counted) for table in measurement.tables
    ]
    if measurement.timing_note:
        blocks.insert(0, "\n".join(measurement.timing_note))
    blocks.insert(0, f"method  : {run.method}\ncommand : {run.command}")
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
                        ("deviation", row.deviation),
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
                    deviation=(
                        None
                        if row.get("deviation") is None
                        else float(row["deviation"])
                    ),
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
