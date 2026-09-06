# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What the whole suite shares: an import path, and the coverage gate.

`src/btclib_benchmarks/` is a package, installed into this project's own
venv, and a test of it imports it the way any caller does. What is left
under `scripts/` -- the six numbered benchmarks, `artifacts.py` and
`render.py` -- is not: a module whose name opens with a digit or carries
a hyphen is not a Python identifier, so none of the six could become a
package member as it is, and the other two were never meant to be one.
Nothing imports any of the eight in ordinary use, they are run by path,
and a test that judges them has to reach them the way a person does --
which is the whole of what the `sys.path` insert below buys.

`coverage_fail_under` is the other half. `--cov` is in addopts, so the
100% ratchet is what a bare `uv run pytest` measures rather than
something only CI reaches, and the price is that every partial run
reports against it too. Which invocations count as asking for less than
the suite is section 8 of the organization standard's to decide, and the
docstring below is where each of them is read.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

    import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def asks_for_everything(
    file_or_dir: list[str] | None,
    *,
    invocation_dir: Path,
    testpaths: list[Path],
) -> bool:
    """Return whether the paths named on the command line take the suite in.

    No path at all is `testpaths`, which is the suite. A path at or above
    one of those entries collects it whole, so what decides is
    containment and not equality: read as equality, `pytest tests` is a
    subset -- and it is what somebody types who means the whole suite and
    says so.

    The two bases are different directories, which `pytest .` run from
    `tests/` shows: pytest reads a positional argument against the
    directory it was invoked from, and `testpaths` against the rootdir.
    Both sides are then resolved, because a directory reached through a
    symlink -- `/tmp` on macOS -- is unequal to the same directory
    spelled without it, and either side can be the one that carries the
    link: an absolute positional keeps whatever the command line wrote,
    and `rootpath` keeps whatever `--rootdir` was given.

    A parent-directory segment is a second reason to resolve, and no
    symlink is involved in it: `pathlib` keeps `..` at construction where
    it collapses `.` and a trailing separator, so `pytest tests/../tests`
    from the rootdir spells the `testpaths` entry in a way that compares
    unequal to it. A reader checks that one in a line, for any `base`:
    `base / "tests/../tests" == base / "tests"` is False, and the same
    pair resolved is True.

    `file_or_dir` is `None` rather than `[]` on the `--help` path, the
    positional never having been parsed, and that names no path either --
    folding it in is what keeps `--help` from ending in a traceback whose
    last frame is this file.
    """
    given = [(invocation_dir / path).resolve() for path in file_or_dir or []]
    if not given:
        return True
    wanted = [path.resolve() for path in testpaths]
    if not wanted:
        # `all` over nothing is true, which would make every path named
        # here the whole suite. Nothing names the suite, so a bare run
        # collects the rootdir and anything asked for is less than it
        return False
    return all(
        any(target == path or path in target.parents for path in given)
        for target in wanted
    )


def coverage_fail_under(
    configured: float | None,
    options: Namespace,
    *,
    invocation_dir: Path,
    testpaths: list[Path],
) -> float | None:
    """Return the coverage threshold this run's selection has to meet.

    `fail_under` applies to every report coverage writes, a partial one
    included, so `uv run pytest tests/inputs_test.py` would end in
    `Required test coverage of 100.0% not reached` -- true of that run
    and saying nothing about the tree. Running one file and one test are
    documented commands, and a gate that fails them is a gate read as
    noise.

    So a run that asked for a subset is gated at zero rather than having
    coverage switched off: the report still prints, which is what makes
    it worth reading while iterating on one module. A whole run is handed
    back `configured`, the threshold pytest-cov has already read out of
    the coverage configuration, so pyproject.toml stays the one place the
    number lives.

    The threshold and the selection arrive as two arguments because by
    the time this runs the two namespaces no longer agree. pytest-cov
    fills `cov_fail_under` from the coverage configuration in
    `pytest_load_initial_conftests`, before `pytest_configure`, so "the
    option is set" has stopped meaning "somebody asked for it": what
    still means that is `options`, `config.option` itself, which carries
    only what the command line and addopts put there. An explicit
    `--cov-fail-under` is therefore `options.cov_fail_under`, and is
    handed back untouched whichever kind of run it is -- the caller
    naming the threshold is the one thing this must not overrule.

    A subset is what pytest was *asked* for, and section 8 of the
    organization standard names the set: `-k`, `-m`, `--deselect`,
    `--ignore`, `--ignore-glob`, `--lf`, and paths that leave part of the
    suite out, which is `asks_for_everything`'s question and not whether
    a path was named at all. A run that leaves tests out measures the
    same source with fewer tests, so what its report is short of is the
    tests that did not run -- a shortfall no reader can tell from one the
    tree has, which is what teaches whoever meets it to reach for
    `--no-cov`. What is read is that a flag was passed and not what it
    came down to: an `--ignore` naming a path this suite does not hold
    narrows nothing and drops the floor anyway, for the reason the next
    paragraph gives of `--lf`.

    `--lf` counts wherever it appears, rather than only where the cache
    holds a failure to rerun. What the invocation asked for is what
    decides, and the cache is a fact about the run before it: reading it
    here would be a second implementation of the cacheprovider's own rule
    for which tests `--lf` comes down to. What that costs is the `--lf`
    finding nothing to rerun, which is the whole suite ungated, and the
    bare run after it measures the tree again.

    An `-x` that stops early is outside the set: what cuts that run short
    is a failure and not what the invocation asked for.
    """
    asked: float | None = options.cov_fail_under
    if asked is not None:
        return asked
    narrowing = (
        options.keyword,
        options.markexpr,
        options.deselect,
        options.ignore,
        options.ignore_glob,
        # `-p no:cacheprovider` leaves `--lf` unregistered rather than
        # false, and a run that cannot pass the flag has not passed it
        getattr(options, "lf", False),
    )
    if any(narrowing):
        return 0
    if not asks_for_everything(
        options.file_or_dir, invocation_dir=invocation_dir, testpaths=testpaths
    ):
        return 0
    return configured


def pytest_configure(config: pytest.Config) -> None:
    """Gate a whole run at `fail_under`, and a partial one at nothing.

    The threshold is written to `known_args_namespace` and not to
    `config.option`: pytest builds the first by parsing the known
    arguments into a *copy* of the second, and pytest-cov holds on to
    that copy. Writing to `config.option` instead runs without error and
    changes nothing -- the plugin never reads it back, and the run still
    fails on the whole tree's coverage.
    """
    testpaths: list[str] = config.getini("testpaths")
    namespace = config.known_args_namespace
    namespace.cov_fail_under = coverage_fail_under(
        namespace.cov_fail_under,
        config.option,
        invocation_dir=config.invocation_params.dir,
        testpaths=[config.rootpath / path for path in testpaths],
    )
