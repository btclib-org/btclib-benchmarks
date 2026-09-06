# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Tests for the coverage gate of conftest.

`coverage_fail_under` is one a passing suite cannot exercise on its own:
the run that reaches it with a subset selected is, by construction, not
the run that measures this file. The position of `--cov` in addopts is
here for the same reason -- it is a property of the command line no run
of that command line can report on.
"""

from __future__ import annotations

import re
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
from conftest import coverage_fail_under

_ROOT = Path(__file__).parents[1]
# what `[tool.pytest.ini_options]` testpaths names, joined onto the
# rootdir the way tests/conftest.py's pytest_configure joins it
_TESTPATHS = [_ROOT / "tests"]
# a nodeid for the cases that need one, out of the module whose path the
# cases below also select on
_ONE_TEST = "tests/inputs_test.py::test_keys_are_the_stream_from_zero"


def _options(**asked_for: object) -> Namespace:
    """Return a `config.option` carrying what a command line asked for.

    The defaults are what pytest leaves on that namespace for a command
    line that passed none of these: `-k` and `-m` empty strings, the
    three collection flags `None`, `--lf` False, and `--cov-fail-under`
    None. A case names the flag it is about and inherits the rest.
    """
    defaults: dict[str, object] = {
        "cov_fail_under": None,
        "file_or_dir": [],
        "keyword": "",
        "markexpr": "",
        "deselect": None,
        "ignore": None,
        "ignore_glob": None,
        "lf": False,
    }
    return Namespace(**(defaults | asked_for))


def _threshold(
    configured: float | None = 100.0,
    *,
    testpaths: list[Path] | None = None,
    invocation_dir: Path | None = None,
    **asked_for: object,
) -> float | None:
    """Ask `coverage_fail_under` from the rootdir, unless told otherwise.

    Most cases below are run from the rootdir, and naming that in each
    assertion would bury what the case is about. Two are not: a tree that
    configures no `testpaths`, and a run started from a subdirectory,
    which is the only case that tells `invocation_dir` from the rootdir.
    """
    return coverage_fail_under(
        configured,
        _options(**asked_for),
        invocation_dir=_ROOT if invocation_dir is None else invocation_dir,
        testpaths=_TESTPATHS if testpaths is None else testpaths,
    )


def test_a_whole_run_is_gated_at_what_pyproject_configured() -> None:
    """No selection: the ratchet applies, and it is not restated here.

    The number comes back as it was handed in, which is the property
    worth pinning: pyproject.toml is where 100 is decided, and a copy of
    it in this file would be a second place to change it.
    """
    assert _threshold() == 100.0
    assert _threshold(42.0) == 42.0


def test_naming_the_suite_is_not_selecting_from_it() -> None:
    """A path that takes `testpaths` in is gated at the full ratchet.

    `uv run pytest tests` collects what a bare run collects, `testpaths`
    being `tests`, so the spelling that says out loud which suite is
    meant is the one that must not drop the floor. The trailing slash,
    the `./` and the absolute path are that same directory; the rootdir
    is above it, and a path above `testpaths` collects it whole too.
    """
    for path in ("tests", "./tests", "tests/", str(_ROOT / "tests"), str(_ROOT)):
        assert _threshold(file_or_dir=[path]) == 100.0, path


def test_a_path_is_read_against_where_pytest_was_started() -> None:
    """`tests` means one directory from the rootdir and another from `tests/`.

    pytest reads a positional argument against the directory it was
    invoked from and `testpaths` against the rootdir, so the two bases
    are what `invocation_dir` exists to keep apart. Without this case
    nothing here would fail if the rootdir were substituted back for it:
    every other assertion starts from the rootdir, where the two
    coincide, so the suite would stay green at a 100% floor while the
    parameter had stopped meaning anything.

    From `tests/`, `pytest tests` names `tests/tests`, which collects
    none of the suite and is therefore a selection.
    """
    assert _threshold(file_or_dir=["tests"], invocation_dir=_ROOT / "tests") == 0
    assert _threshold(file_or_dir=["tests"]) == 100.0


def test_a_parent_directory_segment_names_the_whole_suite_too() -> None:
    """`..` survives into the path object, so the spelling has to resolve.

    `.` and the trailing separator are collapsed when the path is built,
    which is why they sit in
    `test_naming_the_suite_is_not_selecting_from_it` and this is its own
    case: a `..` segment is kept instead, so `tests/../tests` and `tests`
    are two objects that compare unequal until each side is resolved.
    Both commands here collect the suite, and without `given`'s call each
    reads as a selection and is gated at nothing.
    """
    assert _threshold(file_or_dir=["tests/../tests"]) == 100.0
    from_the_tests_directory = _threshold(
        file_or_dir=["../tests"], invocation_dir=_ROOT / "tests"
    )
    assert from_the_tests_directory == 100.0


def test_a_symlinked_spelling_of_one_tree_is_still_the_whole_suite(
    tmp_path: Path,
) -> None:
    """Both sides are resolved, so one directory named two ways compares equal.

    A positional argument is joined onto the directory pytest was invoked
    from and `testpaths` onto the rootdir, and either can be spelled
    through a symlink -- `/tmp` is one on macOS, and a checkout under a
    linked home is another. Resolved on one side only, the two spellings
    of one directory compare unequal, `pytest tests` reads as a subset of
    itself, and the run that measures the whole suite is gated at
    nothing. Each assertion below spells one side through the link, so
    each fails without a different one of the two calls.

    The link is made here rather than taken from the machine, so what the
    case is about is the comparison and not which directories an
    operating system happens to link. Creating one on Windows takes a
    privilege a runner need not hold, so a platform that refuses says so
    as a skip, which `-ra` reports.
    """
    base = tmp_path.resolve()
    real = base / "real"
    (real / "tests").mkdir(parents=True)
    link = base / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError as refused:  # pragma: no cover -- Windows without the privilege
        pytest.skip(f"this platform will not create a symlink: {refused}")
    started_from_the_link = _threshold(
        file_or_dir=["tests"], invocation_dir=link, testpaths=[real / "tests"]
    )
    assert started_from_the_link == 100.0
    testpaths_through_the_link = _threshold(
        file_or_dir=["tests"], invocation_dir=real, testpaths=[link / "tests"]
    )
    assert testpaths_through_the_link == 100.0


def test_the_help_path_is_no_selection_either() -> None:
    """`--help` leaves `file_or_dir` at `None` rather than at `[]`.

    pytest abandons the parse before the positional is consumed, and
    `pytest_configure` fires anyway, so this is what reaches the hook on
    a command line that named no path at all.
    """
    assert _threshold(file_or_dir=None) == 100.0


def test_a_tree_naming_no_testpaths_treats_every_path_as_a_subset() -> None:
    """With `testpaths` empty, nothing on the command line is the suite.

    A bare run collects the rootdir, which no named path can be more than
    -- and `all` over an empty `testpaths` would answer the opposite,
    calling every path the whole suite.
    """
    assert _threshold(file_or_dir=["tests"], testpaths=[]) == 0


@pytest.mark.parametrize(
    "asked_for",
    [
        {"keyword": "stream"},
        {"markexpr": "slow"},
        {"deselect": [_ONE_TEST]},
        {"ignore": ["tests/inputs_test.py"]},
        {"ignore_glob": ["*inputs_test.py"]},
        {"lf": True},
    ],
    ids=lambda asked_for: next(iter(asked_for)),
)
def test_every_flag_that_narrows_a_run_drops_the_threshold(
    asked_for: dict[str, Any],
) -> None:
    """Section 8's set, one flag at a time, with the paths saying nothing.

    A flag missing from this list is one the hook can stop reading with
    nothing turning red. Such a run measures the same source with fewer
    tests against the whole suite's threshold, so it fails on the tests
    it did not run and prints what a shortfall of the tree prints.

    What the hook reads is that the flag was passed: `-m slow` selects
    against a marker this suite does not register, and it drops the floor
    all the same, for the reason `coverage_fail_under`'s docstring gives
    of an `--ignore` naming a path the suite does not hold.
    """
    assert _threshold(**asked_for) == 0, asked_for


def test_a_selected_subset_is_gated_at_nothing() -> None:
    """A partial path drops the threshold to zero, and so does a mixture.

    Zero and not None: None is what pytest-cov reads the configured
    threshold into, so it would restore the very gate this removes. The
    cases naming the whole suite beside a flag are what say that a run
    which also asked for less is a selection whatever its paths say.
    """
    one_file = ["tests/inputs_test.py"]
    cases: tuple[dict[str, Any], ...] = (
        {"file_or_dir": one_file},
        {"file_or_dir": one_file, "keyword": "stream", "markexpr": "slow"},
        {"file_or_dir": ["tests"], "keyword": "stream"},
        {"file_or_dir": ["tests"], "lf": True},
    )
    for asked_for in cases:
        assert _threshold(**asked_for) == 0, asked_for


def test_a_run_that_disabled_the_cache_plugin_is_gated_rather_than_crashed() -> None:
    """`-p no:cacheprovider` leaves `--lf` off the namespace altogether.

    The option is that plugin's, so without it there is no attribute to
    read, and a command line that could not pass `--lf` did not pass it.
    Reading it with a default is what keeps such a run gated at the
    ratchet rather than ending in an AttributeError raised from
    `pytest_configure`.
    """
    options = _options()
    del options.lf
    threshold = coverage_fail_under(
        100.0, options, invocation_dir=_ROOT, testpaths=_TESTPATHS
    )
    assert threshold == 100.0


def test_cov_is_not_the_last_token_of_addopts() -> None:
    """`--cov` last in addopts eats the first argument of the command.

    It takes an optional value, so as the final token it is handed
    whatever the command line goes on to say: `uv run pytest
    tests/inputs_test.py` becomes `--cov=tests/inputs_test.py`, leaving
    no path to select on. Moving it there with `-o addopts=` is what
    re-derives the damage: the whole suite collects, coverage warns that
    no data was collected, and the run reports 0.00% against a
    `fail_under` of 100.

    `pytest -q tests/...` hides it, a token starting with `-` not being
    consumed, so the habitual spelling is green and the documented one is
    not. Nothing about a run reports its own addopts, which is why this
    reads the file: anywhere but last is safe, and the assertion is that
    weak on purpose -- the order of the rest is nobody's business here.
    """
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^addopts = "(.*)"$', text, re.MULTILINE)
    assert match, "pyproject.toml has no single-line 'addopts = \"...\"'"

    addopts = match.group(1).split()
    assert "--cov" in addopts, "the local coverage gate is --cov in addopts"
    assert addopts[-1] != "--cov", (
        "--cov is the last token of addopts, so it will swallow the first "
        "positional argument of any command line that has one"
    )


def test_an_explicit_threshold_survives_either_kind_of_run() -> None:
    """`--cov-fail-under` is the caller's, and outranks both branches."""
    partial = ["tests/inputs_test.py"]
    assert _threshold(file_or_dir=partial, cov_fail_under=90.0) == 90.0
    assert _threshold(cov_fail_under=90.0) == 90.0
    # zero is a threshold somebody asked for, not a missing answer: it
    # has to survive the `is not None` test rather than be falsy
    assert _threshold(cov_fail_under=0) == 0
