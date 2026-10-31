# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The cases of `_results.py` the saved runs do not reach.

`saved_runs_test.py` renders every run in `results/`, which is the common
path. What is here is what a committed run happens not to hold: a row with
a deviation, a table whose rows state two dispersions, a name that shares
no prefix, a schema from the future. Each is asserted by what it does and
not by the words the page prints, so that rewording a heading breaks none
of them.
"""

from __future__ import annotations

import dataclasses
import importlib
import json

import pytest

from btclib_benchmarks import _results

WIDTH = 8
FIRST = "2026-01-01T10:00:00+00:00"
AGAIN = "2026-01-01T10:30:00+00:00"
COMMAND = (
    "uv run --with 'a @ git+https://example.org/a@main'"
    " --with 'b @ git+https://example.org/b@master' python scripts/00-x.py"
)


def _ratios(*rows: _results.Timing) -> _results.Ratios:
    """Return a table of the given rows."""
    return _results.Ratios(title="t", rows=list(rows))


def test_a_script_name_is_the_page_it_feeds() -> None:
    """The directory and the extension go, and the digits and hyphens stay."""
    assert _results.page_of("scripts/05-key-reuse.py") == "05-key-reuse"


def test_a_row_names_the_dispersion_it_states() -> None:
    """Each statistic has its key, and a row that states none has no key."""
    assert _results.Timing("x", 1.0, spread=0.1).dispersion_key == "spread"
    assert _results.Timing("x", 1.0, halves_apart=0.1).dispersion_key == "halves_apart"
    assert _results.Timing("x", 1.0).dispersion_key is None


def test_names_lose_only_the_whole_words_they_share() -> None:
    """A shared leading word goes, and a shared leading letter stays."""
    assert _results.labels(["btclib_sign", "btclib_verify"]) == ["sign", "verify"]
    assert _results.labels(["btclib", "buidl"]) == ["btclib", "buidl"]


def test_a_count_of_calls_without_rounds_is_stated_once_per_row() -> None:
    """No calls states nothing, and calls without rounds names no round."""
    assert _results.counted_calls(None, None) == ""
    assert "1,000" in _results.counted_calls(None, 1000)
    assert "5" in _results.counted_calls(5, 1000)
    assert _results.counted_calls(5, 1000) != _results.counted_calls(None, 1000)


def test_a_deviation_adds_its_column_to_the_rows_that_state_one() -> None:
    """A row with a deviation is wider than the same row without."""
    plain = _results.rendered_ratios(_ratios(_results.Timing("x", 3.0)), WIDTH)
    spread = _results.rendered_ratios(
        _ratios(_results.Timing("x", 3.0, deviation=0.5)), WIDTH
    )
    assert len(spread.splitlines()[-1]) > len(plain.splitlines()[-1])


def test_a_table_cannot_hold_two_statistics_under_one_column() -> None:
    """One row of `spread` and one of `halves_apart` are refused."""
    table = _ratios(
        _results.Timing("x", 3.0, spread=0.1),
        _results.Timing("y", 4.0, halves_apart=0.1),
    )
    with pytest.raises(ValueError, match="two statistics"):
        _results.rendered_ratios(table, WIDTH)


def test_a_group_no_table_is_in_is_refused() -> None:
    """A group the run does not declare is a mistake, not an empty block."""
    with pytest.raises(ValueError, match="no table is in the group"):
        _results.rendered_group(_full(), "a group no table is tagged with")


def test_a_schema_this_module_does_not_know_is_refused() -> None:
    """A file from another version is not rendered as if it were this one's."""
    with pytest.raises(ValueError, match="is not schema"):
        _results.from_json({"schema": _results.SCHEMA + 1})


def test_nothing_measured_prints_as_zero() -> None:
    """A value of nothing has no order of magnitude to round at, and is `0`."""
    assert _results._significant(0.0) == "0"


def _measurement(*, twice: bool) -> _results.Measurement:
    """Return a run of two rows, each measured a second time when asked."""
    rows = [
        _results.Timing("x", 10.0, us_per_call_again=11.0 if twice else None),
        _results.Timing("y", 20.0, us_per_call_again=19.0 if twice else None),
    ]
    run = _results.Run(
        when=FIRST,
        timezone="UTC",
        python="3.13",
        method="m",
        command="c",
        machine="somewhere",
        when_again=AGAIN if twice else None,
    )
    return _results.Measurement(
        benchmark="00-x",
        run=run,
        provenance=_results.Provenance(columns=[], rows=[]),
        tables=[_ratios(*rows)],
    )


def test_a_run_measured_twice_states_how_far_the_passes_were_apart() -> None:
    """A second pass adds one line to the run block, carrying what it found."""
    once = _results.rendered_run(_measurement(twice=False)).splitlines()
    twice = _results.rendered_run(_measurement(twice=True)).splitlines()
    assert twice[: len(once)] == once
    assert len(twice) == len(once) + 1
    assert "30" in twice[-1]
    assert "1/2" in twice[-1]


def test_a_run_block_names_its_commit_and_lock_or_says_it_has_none() -> None:
    """A run saved without them says so; one saved with them prints both."""
    unrecorded = _results.rendered_run(_measurement(twice=False)).splitlines()
    assert "commit  : not recorded" in unrecorded
    assert "uv.lock : not recorded" in unrecorded
    recorded = _results.rendered_run(_full()).splitlines()
    assert "commit  : c0ffee" in recorded
    assert "uv.lock : 10c4" in recorded


@pytest.mark.parametrize("title", ["t", ""])
def test_pairs_are_sorted_on_what_the_second_column_costs(title: str) -> None:
    """The row whose second column loses least is first; no title, no line."""
    table = _results.Pairs(
        title=title,
        columns=("a", "b"),
        rows=[_results.Pair("x", (1.0, 4.0)), _results.Pair("y", (2.0, 2.0))],
    )
    lines = _results.rendered_pairs(table, WIDTH).splitlines()
    assert len(lines) == (4 if title else 3)
    assert lines[-2].startswith("y")
    assert lines[-1].startswith("x")
    assert lines[-1].endswith("4.0x")


def _full() -> _results.Measurement:
    """Return a run holding every shape a page can carry.

    All three kinds of table, each in a group of its own; rows measured
    twice, with each dispersion, a deviation and an unavailable row; calls
    given with and without rounds, so that no count is shared by the page;
    a packages block with columns, beside one with notes alone; and a run at
    a default branch, its command carrying two `--with`.
    """
    ratios = _results.Ratios(
        title="r",
        group="timed",
        rows=[
            _results.Timing(
                "a_x",
                10.0,
                us_per_call_again=11.0,
                spread=0.5,
                deviation=0.1,
                calls=100,
                rounds=5,
            ),
            _results.Timing("a_y", 20.0, us_per_call_again=19.0, spread=0.7),
            _results.Unavailable("a_z"),
        ],
    )
    other = _results.Ratios(
        title="o",
        group="halves",
        decimals=2,
        rows=[
            _results.Timing(
                "b_x", 5.0, us_per_call_again=5.5, halves_apart=0.2, calls=1000
            ),
            _results.Timing("b_y", 6.0, us_per_call_again=6.0, halves_apart=0.1),
        ],
    )
    pairs = _results.Pairs(
        title="p",
        group="pairs",
        columns=("a", "b"),
        rows=[_results.Pair("x", (1.0, 4.0)), _results.Pair("y", (2.0, 2.0))],
    )
    break_even = _results.BreakEven(
        title="b",
        group="paid",
        rows=[
            _results.Preparation("x", 3.0, 19.0, 17.0, saving_halves_apart=0.1),
            _results.Preparation("y", 3.0, 19.0, 17.5),
        ],
    )
    run = _results.Run(
        when=FIRST,
        timezone="UTC",
        python="3.13",
        method="m",
        command=COMMAND,
        machine="somewhere",
        when_again=AGAIN,
        commit="c0ffee",
        lock="10c4",
        mode=_results.DEFAULT_BRANCH,
        branches="a main\nb master",
    )
    return _results.Measurement(
        benchmark="00-x",
        run=run,
        provenance=_results.Provenance(
            columns=["package", "build"], rows=[["p", "released"]], notes=["a note"]
        ),
        tables=[ratios, other, pairs, break_even],
    )


def test_a_run_of_every_shape_is_saved_and_read_back_equal() -> None:
    """Each table kind and each optional field survives the file."""
    measurement = _full()
    saved = json.loads(json.dumps(_results.as_json(measurement)))
    assert _results.from_json(saved) == measurement


def test_a_run_of_every_shape_is_rendered_in_every_block() -> None:
    """Each block is built, and the output opens with the method."""
    measurement = _full()
    assert _results.rendered_run(measurement)
    assert "released" in _results.rendered_provenance(measurement.provenance)
    method = _results.rendered_method(measurement)
    assert _results.rendered_output(measurement).startswith(method)
    for group in _results.groups_of(measurement):
        assert _results.rendered_group(measurement, group)
    assert _results.groups_of(measurement) == ["timed", "halves", "pairs", "paid"]


def test_a_run_block_opens_with_its_mode() -> None:
    """Each run names its mode first, and a branch install its branch next."""
    release = _results.rendered_run(_measurement(twice=False)).splitlines()
    assert release[0] == "mode    : release"
    lines = _results.rendered_run(_full()).splitlines()
    assert lines[:3] == [
        "mode    : default branch",
        "branch  : a main",
        "branch  : b master",
    ]


def test_a_branch_of_any_length_renders_inside_a_code_block() -> None:
    """A branch name nobody here chose is printed whole, never refused.

    Its line is in the run block's fence, which the default-branch page
    exempts from MD013 as the release pages do.
    """
    render = importlib.import_module("render")
    branch = (
        "btclib-secp256k1 feature/a-rather-long-branch-name-for-the-bindings-rework"
    )
    assert len(branch) > 70
    run = dataclasses.replace(_full().run, branches=branch)
    measurement = dataclasses.replace(_full(), run=run)
    page = render.rendered_page(
        render.DEFAULT_BRANCH_PAGE.format(benchmark="00-x"), measurement
    )
    assert '"code_blocks": false' in page
    lines = page.splitlines()
    at = lines.index(f"branch  : {branch}")
    assert len(lines[at]) > 80
    # an odd number of fences above it: the line is inside one
    assert sum(line.startswith("```") for line in lines[:at]) % 2 == 1
    assert lines[at - 2] == "```text"


def test_a_command_with_installs_is_one_line_per_install() -> None:
    """Each `--with` continues the command on a line of its own."""
    lines = _results._rendered_command(_full().run)
    assert lines[0] == "command : uv run \\"
    assert lines[1] == "  --with 'a @ git+https://example.org/a@main'\\"
    assert lines[-1] == "  python scripts/00-x.py"
    joined = " ".join(line.removesuffix("\\").strip() for line in lines)
    assert joined.removeprefix("command : ") == COMMAND


def _fails_md013(line: str) -> bool:
    """Say whether markdownlint's MD013, at its defaults, refuses a line.

    A line past 80 columns passes where nothing after column 80 is
    whitespace: a URL no width can be imposed on.
    """
    return len(line) > 80 and any(c.isspace() for c in line[80:])


def test_a_default_branch_page_passes_md013_for_the_longest_names() -> None:
    """The longest script name and a long `--with` fail no line of the page.

    The prose is checked line by line, and the command's lines too, though
    the page also switches MD013 off inside its code blocks.
    """
    render = importlib.import_module("render")
    longest = max((p.stem for p in render.SCRIPTS.glob("[0-9]*.py")), key=len)
    overlay = (
        "btclib-secp256k1 @ git+https://github.com/btclib-org/btclib-secp256k1@"
        + "c0ffee" * 6
        + "c0ff"
    )
    command = f"uv run --with '{overlay}' python scripts/{longest}.py"
    run = dataclasses.replace(_full().run, command=command)
    measurement = dataclasses.replace(_full(), benchmark=longest, run=run)
    page = render.rendered_page(
        render.DEFAULT_BRANCH_PAGE.format(benchmark=longest), measurement
    )
    assert '"code_blocks": false' in page
    fenced = False
    for line in page.splitlines():
        fenced ^= line.startswith("```")
        if not fenced or line.lstrip().startswith(("--with", "command", "branch")):
            assert not _fails_md013(line), line
    # the control: a backslash after a space, past column 80, is refused
    assert not _fails_md013(f"  --with '{overlay}'\\")
    assert _fails_md013(f"  --with '{overlay}' \\")


def test_a_command_without_installs_is_one_line() -> None:
    """A release run's command is printed as it was recorded."""
    assert _results._rendered_command(_measurement(twice=False).run) == ["command : c"]


def test_a_mode_this_module_does_not_know_is_refused() -> None:
    """A run naming another mode has no directory to be saved in."""
    run = _results.Run(
        when=FIRST,
        timezone="UTC",
        python="3.13",
        method="m",
        command="c",
        machine="somewhere",
        mode="nightly",
    )
    with pytest.raises(ValueError, match="no mode"):
        _results.Measurement(
            benchmark="00-x",
            run=run,
            provenance=_results.Provenance(columns=[], rows=[]),
            tables=[],
        )


def test_a_provenance_with_no_columns_is_its_notes() -> None:
    """A single comparand has no table of packages, only lines."""
    provenance = _results.Provenance(columns=[], rows=[], notes=["one", "two"])
    assert _results.rendered_provenance(provenance) == "one\ntwo"


def test_a_count_shared_by_every_row_is_said_once() -> None:
    """Rows agreeing on their calls hoist the count; any other mix does not."""
    same = _ratios(
        _results.Timing("x", 1.0, calls=10, rounds=2),
        _results.Timing("y", 2.0, calls=10, rounds=2),
    )
    differ = _ratios(
        _results.Timing("x", 1.0, calls=10, rounds=2),
        _results.Timing("y", 2.0, calls=20, rounds=2),
    )
    assert _results.counted_once([same]) == _results.counted_calls(2, 10)
    assert not _results.counted_once([differ])


def test_a_group_is_listed_once_and_a_table_without_one_not_at_all() -> None:
    """Groups come in the order the tables are in."""
    row = _results.Timing("x", 1.0)
    tables = [
        _results.Ratios(title="a", rows=[row], group="one"),
        _results.Ratios(title="b", rows=[row]),
        _results.Ratios(title="c", rows=[row], group="one"),
        _results.Ratios(title="d", rows=[row], group="two"),
    ]
    measurement = _results.Measurement(
        benchmark="00-x",
        run=_results.Run(
            when=FIRST,
            timezone="UTC",
            python="3.13",
            method="m",
            command="c",
            machine="somewhere",
        ),
        provenance=_results.Provenance(columns=[], rows=[]),
        tables=tables,
        timing_note=[],
    )
    assert _results.groups_of(measurement) == ["one", "two"]
    assert "\n\n" not in _results.rendered_method(measurement)


def test_a_page_without_a_provenance_region_is_refused() -> None:
    """A page whose packages block has nowhere to go is not rendered."""
    render = importlib.import_module("render")
    measurement = _measurement(twice=False)
    page = "<!-- run: begin -->\n<!-- run: end -->\n"
    page += "<!-- output: begin -->\n<!-- output: end -->\n"
    with pytest.raises(ValueError, match="provenance"):
        render.rendered_page(page, measurement)
    given = "<!-- provenance: begin -->\n<!-- provenance: end -->\n" + page
    assert "commit  : not recorded" in render.rendered_page(given, measurement)
