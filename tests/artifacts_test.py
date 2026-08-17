# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Tests for the command that says which artifact each comparand resolved to.

What is being defended is that the report covers the comparands -- all of
them, and only them. A list of names written out here would go stale the
day one is added, which is the failure the command reads `pyproject.toml`
to avoid, so that is what these ask about.
"""

from __future__ import annotations

import tomllib

import artifacts
import pytest


def test_every_declared_dependency_is_named_without_its_version() -> None:
    """The names are the comparands', and a requirement is not a name.

    `btclib>=2026.9` names a distribution and states a floor, and only the
    first half is something `importlib.metadata` can be asked about.
    """
    named = artifacts.declared()
    assert "btclib" in named
    assert "secp256k1" in named
    assert not [name for name in named if any(bound in name for bound in "<>=!~[; ")]


def test_the_comparands_are_read_from_the_dependencies_and_not_a_list_here() -> None:
    """A comparand added to `pyproject.toml` is reported without a second edit.

    This is the whole reason the command parses rather than declares, so it
    is asserted rather than trusted: the count comes from the file.
    """
    declared = tomllib.loads(artifacts.PYPROJECT.read_text(encoding="utf-8"))
    assert len(artifacts.declared()) == len(declared["project"]["dependencies"])


@pytest.mark.parametrize(
    "requirement, name",
    [
        ("btclib>=2026.9", "btclib"),
        ("secp256k1lab", "secp256k1lab"),
        ("coincurve[gmp]>=21.0.0", "coincurve"),
        ("embit ; python_version >= '3.11'", "embit"),
    ],
)
def test_a_requirement_string_is_cut_at_whatever_it_asks_for(
    requirement: str, name: str
) -> None:
    """Each of the four spellings a dependency can arrive in, name only."""
    assert artifacts._named(requirement) == name


def test_the_report_is_one_line_per_comparand_and_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """It records rather than judges, so no answer it can print is a failure.

    A wheel appearing on an index changes what every line says and breaks
    nothing, which is why this is a step in CI and not an assertion in it.
    """
    assert artifacts.main() == 0
    printed = capsys.readouterr().out.splitlines()
    assert len(printed) == len(artifacts.declared())
    assert [line for line in printed if line.startswith("secp256k1 ")]
    assert not [line for line in printed if line.endswith(": not installed")]
