# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Tests for the coverage gate of conftest.

`coverage_fail_under` is one a passing suite cannot exercise on its own:
the run that reaches it with a subset selected is, by construction, not
the run that measures this file. The position of `--cov` in addopts is
here for the same reason -- it is a property of the command line no run
of that command line can report on.

The guard beside it is driven the same way, with one exception: the run
it refuses cannot be the run reporting on it either, so the case it
exists for is taken in a subprocess started from `tests/`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from conftest import (
    CoverageConfiguration,
    configuration_went_unread,
    coverage_configuration,
    coverage_fail_under,
    pytest_configure,
)

_ROOT = Path(__file__).parents[1]
# what pytest reads its own configuration from here, which the guard
# compares against what coverage read and the message names
_INIPATH = _ROOT / "pyproject.toml"
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
    three collection flags `None`, `--lf` False, `--help` and
    `--collect-only` False, and `--cov-fail-under` None. A case names
    the flag it is about and inherits the rest.
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
        "help": False,
        "collectonly": False,
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


# the pragma sits on the `def` because an exclusion on a line that
# introduces a block takes the whole block: this case's body is reachable
# only where the platform makes a symbolic link, so a floor over a
# `source` naming `tests` asks about the runner rather than about the
# suite. An exclusion on the `except` reaches the handler and the
# `pytest.skip` alone, which are the lines that do not run wherever the
# link is made, and the platform the guard is for then meets a skip and a
# floor it cannot reach in the same run. What it costs is that dead code
# inside the case stops being flagged; the case's assertions are its
# whole subject, so the trade is cheap and is still a trade.
def test_a_symlinked_spelling_of_one_tree_is_still_the_whole_suite(  # pragma: no cover -- the body needs a symlink
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
    except OSError as refused:
        pytest.skip(f"this platform will not create a symlink: {refused}")
    started_from_the_link = _threshold(
        file_or_dir=["tests"], invocation_dir=link, testpaths=[real / "tests"]
    )
    assert started_from_the_link == 100.0
    testpaths_through_the_link = _threshold(
        file_or_dir=["tests"], invocation_dir=real, testpaths=[link / "tests"]
    )
    assert testpaths_through_the_link == 100.0


def test_a_testpaths_entry_is_the_directory_its_parent_segment_reaches(
    tmp_path: Path,
) -> None:
    """`tests/../src` is `src`, which a command line naming `tests` misses.

    `pathlib` keeps a parent-directory segment where it collapses `.` and
    a trailing separator, so the join `pytest_configure` makes carries
    `..` into an entry whose parents include the directory that segment
    left: `tests` reads as above `tests/../src`, and a run collecting
    nothing of `src` is handed the whole suite's ratchet. Resolving the
    entry makes it the directory it reaches, which `tests` is not above.

    That is the `testpaths` side's second reason to resolve, and it asks
    for no symlink and no privilege, so it holds where
    `test_a_symlinked_spelling_of_one_tree_is_still_the_whole_suite` can
    only skip. A `..` that re-enters the directory it left --
    `tests/../tests` -- cannot see it: the unresolved entry then has more
    parents and the command line's path is one of them, so containment
    answers the same with the call and without it. That is
    `test_a_parent_directory_segment_names_the_whole_suite_too`, whose
    `..` re-enters and which therefore defends the call on `given`.
    """
    # both sides are spelled from the same base, so the `..` is the only
    # difference between them and the case cannot pass for a second
    # reason
    base = tmp_path.resolve()
    entry_that_leaves_the_directory = _threshold(
        file_or_dir=["tests"], invocation_dir=base, testpaths=[base / "tests/../src"]
    )
    assert entry_that_leaves_the_directory == 0


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


def _cov_config(config_file: str | None) -> CoverageConfiguration:
    """Build what the guard reads of coverage's own configuration.

    One attribute is the whole of it: the file coverage took its
    settings from, `None` where it took them from none.
    """
    return cast("CoverageConfiguration", SimpleNamespace(config_file=config_file))


def _controller(config_file: str | None) -> object:
    """Build the controller pytest-cov leaves on its plugin.

    A stand-in reachable by the attribute path `coverage_configuration`
    walks, and nothing else of one.
    """
    return SimpleNamespace(cov=SimpleNamespace(config=_cov_config(config_file)))


def _went_unread(
    config_file: str | None = None,
    *,
    inipath: Path | None = _INIPATH,
    asked: float | None = None,
    asked_for_help: bool = False,
    collect_only: bool = False,
) -> bool:
    """Ask the guard about the run the issue is about, unless told otherwise.

    Its defaults are that run -- coverage having read nothing, pytest
    having read this tree's pyproject.toml, and no flag passed -- so a
    case below names only what it changes about it, as `_threshold`
    does for the threshold beside it.
    """
    return configuration_went_unread(
        _cov_config(config_file),
        inipath,
        asked,
        asked_for_help=asked_for_help,
        collect_only=collect_only,
    )


def _config(
    controller: object | None,
    known: Namespace,
    *,
    rootpath: Path = _ROOT,
    **asked: object,
) -> pytest.Config:
    """Build what `pytest_configure` reads of a `pytest.Config`.

    Building the real thing means starting a second pytest inside this
    one, so what the hook reads of one is stood in for instead:
    `config.option` and the copy pytest-cov holds beside it,
    `testpaths`, the directory the run was invoked from, the
    configuration pytest read and the root to run from, and the plugin
    the guard walks to.
    """
    plugin = SimpleNamespace(cov_controller=controller)
    return cast(
        "pytest.Config",
        SimpleNamespace(
            known_args_namespace=known,
            option=_options(**asked),
            getini=lambda _name: ["tests"],
            invocation_params=SimpleNamespace(dir=rootpath),
            rootpath=rootpath,
            inipath=_INIPATH,
            pluginmanager=SimpleNamespace(getplugin=lambda _name: plugin),
        ),
    )


def test_a_run_coverage_read_a_configuration_for_is_not_refused() -> None:
    """The guard is silent where the configuration reached the run.

    The gate itself is this case -- `uv run pytest` from the rootdir,
    where coverage reads pyproject.toml -- so a guard firing here would
    refuse the run it exists to protect.
    """
    assert not _went_unread(str(_INIPATH))


def test_a_run_coverage_read_no_configuration_for_is_refused() -> None:
    """A run held to a floor it cannot see is refused.

    This is the defect the guard is for: coverage looks for its
    configuration in the directory the process started in, so from
    `tests/` it finds no `fail_under`, no `source` and no
    `branch = true`, which leaves the run measuring a different set of
    files against nothing (btclib-org/.github#443). pytest reads its own
    configuration all the same, and that asymmetry is what the guard
    keys on.
    """
    assert _went_unread()


def test_nothing_measuring_is_not_an_ungated_run() -> None:
    """`--no-cov` is left alone.

    Section 10 of the organization standard has a sentinel cell that
    runs the suite pass it, and the suite step of `os-macos.yml`,
    `os-ubuntu.yml` and `deps-latest.yml` is where that happens here --
    `deps-oldest.yml`'s own cell moved into `btclib-org/.github`'s
    `reusable-deps-oldest.yml` (issue btclib-org/.github#35), which
    passes the same flag by name. A run measuring no coverage has no
    configuration to be missing.
    """
    assert not configuration_went_unread(
        None, _INIPATH, None, asked_for_help=False, collect_only=False
    )


def test_an_explicit_threshold_is_not_overruled_by_the_guard() -> None:
    """`--cov-fail-under` outranks the guard as it does the threshold.

    The standard has the hook never overruling a caller who named the
    threshold, and the guard is that same hook: what it exists to catch
    is a floor going off with nobody having asked, which a named one is
    not. Zero is a threshold somebody asked for, so it has to survive
    the `is not None` test rather than be read as falsy.
    """
    assert not _went_unread(asked=0)


@pytest.mark.parametrize(
    "exempted",
    [{"asked_for_help": True}, {"collect_only": True}],
    ids=lambda exempted: next(iter(exempted)),
)
def test_a_run_no_floor_applies_to_is_not_refused(exempted: dict[str, Any]) -> None:
    """The two runs pytest-cov never gates are left alone.

    `--help` exits before a session, and pytest-cov never fails a
    `--collect-only` run on the floor whatever its report prints: its
    `pytest_runtestloop` returns on `options.collectonly` ahead of the
    comparison that raises the exit code, where `pytest_terminal_summary`
    reads the threshold alone and prints `FAIL Required test coverage of
    100.0% not reached` all the same -- which `--collect-only` from the
    rootdir here does, at exit 0. Refusing either would answer a
    question about a floor neither is held to.
    """
    assert not _went_unread(**exempted), exempted


def test_without_a_configuration_pytest_read_there_is_nothing_to_name() -> None:
    """The guard needs pytest's own answer, not only coverage's.

    What the message tells a reader is where the configuration pytest
    found is, so a run that found none leaves it with nothing to say;
    and the two tools finding none alike is no asymmetry to report.
    """
    assert not _went_unread(inipath=None)


def test_no_pytest_cov_plugin_is_nothing_measuring() -> None:
    """A run without the plugin registered reads as unmeasured.

    pytest-cov registers its plugin only where a `--cov` reached the
    parser, from addopts here rather than from a command line, and
    `getplugin` hands back `None` where none did.
    """
    config = cast(
        "pytest.Config",
        SimpleNamespace(pluginmanager=SimpleNamespace(getplugin=lambda _name: None)),
    )
    assert coverage_configuration(config) is None


def test_no_cov_leaves_the_controller_unbuilt() -> None:
    """The plugin without a controller reads as unmeasured too.

    `--no-cov` returns from `CovPlugin.__init__` before `start()`, so
    the plugin is registered and its `cov_controller` is still `None`:
    the same `getattr` default answers for that and for no plugin.
    """
    assert coverage_configuration(_config(None, Namespace(cov_fail_under=0.0))) is None


def test_the_configuration_is_the_controllers_own() -> None:
    """The attribute path to coverage's configuration is pinned.

    The hook is keyed on a path through pytest-cov it does not own: the
    plugin under `_cov`, its `cov_controller`, that controller's `cov`
    and the `config` on it. Renaming either of the first two reads as
    nothing measuring and leaves the guard silent, which is the
    direction that fails without saying so; renaming what is below them
    raises instead.
    """
    config = _config(_controller("/somewhere/setup.cfg"), Namespace(cov_fail_under=0.0))
    measuring = coverage_configuration(config)

    assert measuring is not None
    assert measuring.config_file == "/somewhere/setup.cfg"


def test_the_guards_own_names_are_ones_pytest_fills_in(
    pytestconfig: pytest.Config,
) -> None:
    """`help` and `collectonly` are still pytest's own spellings.

    The hook reads them as attributes rather than with a default, both
    being pytest's own rather than a plugin's, so a rename is an
    `AttributeError` in `pytest_configure` and not a silent refusal.
    This run's own configuration is what says they are still there, and
    `_options` above is a stand-in that could otherwise carry a name
    pytest has stopped filling in.
    """
    absent = [
        name
        for name in ("help", "collectonly")
        if not hasattr(pytestconfig.option, name)
    ]
    assert not absent, f"pytest no longer fills in {absent}"


def test_the_hook_refuses_a_run_that_cannot_see_its_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`pytest_configure` raises, and the message names all three paths.

    The function above decides; this is what wires it to a run.
    `pytest.UsageError` is what pytest prints without a traceback and
    exits `4` for, so the exit code says the run measured nothing rather
    than that something in the tree failed.

    Each path is asserted with the words around it, and the run is moved
    out of the rootdir first, because the three slots hold the same text
    otherwise: a gate run starts at the rootdir, so `Path.cwd()` and
    `rootpath` are one directory there and the configuration pytest read
    is a path under it. A message that filled a slot from the wrong one
    of the three would pass every assertion that only asked whether the
    text occurs.
    """
    monkeypatch.chdir(tmp_path)
    started_in = Path.cwd()
    known = Namespace(cov_fail_under=0.0)

    with pytest.raises(pytest.UsageError) as raised:
        pytest_configure(_config(_controller(None), known))

    message = str(raised.value)
    assert f"the directory the run started in, {started_in}," in message
    assert f"pytest read {_INIPATH}." in message
    assert f"Run from {_ROOT};" in message
    # --cov-config is named with what it does not restore and never on
    # its own: a reader sent to it alone gets a run held to the floor
    # over a different set of files, which is what this message opens by
    # naming
    assert "--cov-config restores the floor and not the file set" in message
    # the raise is ahead of the write, so the copy pytest-cov reads is
    # left holding what pytest-cov itself put there
    assert known.cov_fail_under == 0.0


def test_a_selection_does_not_excuse_the_configuration_missing() -> None:
    """Asking for less is refused the same way.

    A selective run is gated at zero by `coverage_fail_under`, so
    nothing was taken from it -- but `source`, `omit` and `branch = true`
    went unread as well, and its report is a measurement of a different
    set of files. Iterating on one module from inside `tests/` reads a
    percentage that is not about this tree, which is what the guard says
    instead. The decision above cannot see a selection at all; the hook
    is where one arrives, so this is where that is asserted.
    """
    config = _config(
        _controller(None),
        Namespace(cov_fail_under=0.0),
        file_or_dir=["inputs_test.py"],
        keyword="keys",
    )

    with pytest.raises(pytest.UsageError, match="coverage read no configuration"):
        pytest_configure(config)


def test_a_run_started_from_tests_says_it_is_ungated(tmp_path: Path) -> None:
    """The guard stops a real run started from `tests/`.

    Everything above is the decision driven as a function; this is the
    invocation the issue is about, and the only case that says the two
    are wired together -- that `tests/conftest.py` is loaded at all on
    such a run, and that what it raises reaches whoever typed it. The
    run costs no collection: `pytest_configure` is ahead of it, so the
    subprocess is refused before it imports a test module.

    `COVERAGE_FILE` is redirected because pytest-cov erases the data
    file it is pointed at as it starts, absent `--cov-append`, which
    would otherwise destroy the data file of the run reading this.
    """
    environment = dict(os.environ)
    environment.pop("PYTEST_ADDOPTS", None)
    environment["COVERAGE_FILE"] = str(tmp_path / "coverage-data")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=str(_ROOT / "tests"),
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
        # a child that hangs fails as this case rather than holding the
        # whole gate, this suite registering no per-test timeout
        timeout=120,
    )

    assert completed.returncode == pytest.ExitCode.USAGE_ERROR, completed.stderr
    # pytest writes a usage error to stderr, where nothing of the run's
    # own output is, so the assertion is on the stream that carries it
    assert "coverage read no configuration" in completed.stderr
    assert str(_ROOT) in completed.stderr
