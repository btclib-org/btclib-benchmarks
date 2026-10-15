# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""How `_results.py` takes the details of a run, and saves it.

A run is dated, placed on a machine and written beside its page. The machine
is asked of the platform and of `machine.toml`, and neither is the test
machine's to decide: the platform and the file are replaced here, so that
every branch is reached on whichever machine runs the suite.
"""

from __future__ import annotations

import platform
import sys
from typing import TYPE_CHECKING

import pytest

from btclib_benchmarks import _results

if TYPE_CHECKING:
    from pathlib import Path


def test_a_command_answers_with_its_output() -> None:
    """The output is returned without its trailing newline."""
    command = (sys.executable, "-c", "print('answer')")
    assert _results._spoken_by(command) == "answer"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(("/nonexistent/command",), id="absent"),
        pytest.param((sys.executable, "-c", "raise SystemExit(1)"), id="fails"),
    ],
)
def test_a_command_that_cannot_answer_leaves_the_line_to_the_file(
    command: tuple[str, ...],
) -> None:
    """A command that is absent, or exits non-zero, answers nothing."""
    assert not _results._spoken_by(command)


def test_a_platform_that_is_not_macos_is_named_by_what_platform_knows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Elsewhere the line is the system, its release and its architecture."""
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "release", lambda: "9.9")
    monkeypatch.setattr(platform, "machine", lambda: "riscv")
    assert _results._detected_machine() == "Linux 9.9, riscv"


@pytest.mark.parametrize(
    "chip, build, expected",
    [
        ("Chip", "B1", "Chip, macOS 99.0 (build B1), arm"),
        ("Chip", "", "Chip, macOS 99.0, arm"),
        ("", "B1", "macOS 99.0 (build B1), arm"),
        ("", "", "macOS 99.0, arm"),
    ],
)
def test_macos_names_the_chip_and_the_build_it_is_asked_for(
    monkeypatch: pytest.MonkeyPatch, chip: str, build: str, expected: str
) -> None:
    """A chip or a build the system does not answer is left out of the line."""
    answers = {
        "machdep.cpu.brand_string": chip,
        "-buildVersion": build,
    }
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm")
    monkeypatch.setattr(platform, "mac_ver", lambda: ("99.0", ("", "", ""), ""))
    monkeypatch.setattr(_results, "_spoken_by", lambda command: answers[command[-1]])
    assert _results._detected_machine() == expected


def test_a_machine_file_is_read_and_its_absence_is_no_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The file's values are strings, and a missing file answers nothing."""
    machine = tmp_path / "machine.toml"
    monkeypatch.setattr(_results, "MACHINE_FILE", machine)
    assert _results._machine_file() == {}
    machine.write_text('machine = "Somebody Else"\nthreads = 4\n', encoding="utf-8")
    assert _results._machine_file() == {"machine": "Somebody Else", "threads": "4"}


def test_a_moment_carries_its_offset() -> None:
    """An hour without an offset is an hour in whose day nobody can say."""
    assert _results.moment().utcoffset() is not None


@pytest.mark.parametrize("again", [False, True])
def test_a_run_taken_now_is_the_machine_files_when_it_names_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, again: bool
) -> None:
    """`machine.toml` overrides the detected line; a second pass is dated."""
    machine = tmp_path / "machine.toml"
    machine.write_text('machine = "Somebody Else"\n', encoding="utf-8")
    monkeypatch.setattr(_results, "MACHINE_FILE", machine)
    second = _results.moment() if again else None
    run = _results.taken_now("scripts/00-x.py", "a method", again=second)
    assert run.machine == "Somebody Else"
    assert run.command.endswith("00-x.py")
    assert (run.when_again is not None) is again


def test_a_run_taken_now_without_a_machine_file_detects_the_machine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no file the line is the detected one."""
    monkeypatch.setattr(_results, "MACHINE_FILE", tmp_path / "absent.toml")
    monkeypatch.setattr(_results, "_detected_machine", lambda: "Detected")
    assert _results.taken_now("scripts/00-x.py", "m").machine == "Detected"


def test_a_saved_run_is_loaded_back_equal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A run is written beside its page, and reading it returns the run."""
    measurement = _results.Measurement(
        benchmark="00-x",
        run=_results.taken_now("scripts/00-x.py", "m"),
        provenance=_results.Provenance(columns=[], rows=[]),
        tables=[
            _results.Pairs(
                title="p", columns=("a", "b"), rows=[_results.Pair("x", (1.0, 2.0))]
            )
        ],
    )
    monkeypatch.setattr(_results, "RESULTS", tmp_path)
    written = _results.save(measurement)
    assert written == tmp_path / "00-x.json"
    assert _results.load("00-x") == measurement
