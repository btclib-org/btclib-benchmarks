# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every benchmark loads, and its comparands agree, without timing anything.

This is the whole of what a test can hold a benchmark to. A measurement
cannot be asserted -- the number is a property of the machine, not of the
code -- so what is checked here is the two things that can be:

- the module imports. That covers the fixtures at its top and the block
  of assertions each of the six builds them with, holding every
  comparand to what the others answer, or to what a specification
  publishes, before any of them is timed. A table whose rows are
  computing different things is worth nothing, and importing the module
  is what runs that check.
- it did not time anything while doing so. The `main()` guard is what
  buys that, checked in the source rather than by timing a reload: a
  wall clock cannot tell a removed guard from a busy machine, the two
  reading the same from outside, and a ceiling loose enough to survive
  a busy machine is one loose enough to miss a removed guard too.

Both are what `main()` is for: a benchmark whose timings run at import
is one no suite can hold to anything.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

BENCHMARKS = [
    "01-libsecp256k1",
    "02-btclib-vs-btclib",
    "03-libraries",
    "04-pure-python",
    "05-key-reuse",
    "06-silentpayments",
]

# where conftest.py points this process's own import path, spelled again
# rather than imported from it: mypy resolves modules by path and a test
# importing its own conftest is a module it cannot find
SCRIPTS = Path(__file__).parents[1] / "scripts"


def _guards_dunder_main(node: ast.stmt) -> bool:
    """Match `if __name__ == "__main__":`, the guard every script uses."""
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], ast.Constant)
        and node.test.comparators[0].value == "__main__"
    )


def _calls_main_by_name(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "main"
    )


def _main_runs_only_behind_its_guard(source: str) -> bool:
    """Report False if main() is called at module level outside the guard.

    Only the guard's own branch may call it: every other top-level
    statement is walked whole, except a function or class definition,
    which does not call anything by merely existing.
    """
    for node in ast.parse(source).body:
        if _guards_dunder_main(node):
            continue
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        if any(_calls_main_by_name(child) for child in ast.walk(node)):
            return False
    return True


@pytest.mark.parametrize("name", BENCHMARKS)
def test_the_benchmark_imports_and_its_comparands_agree(name: str) -> None:
    """Import it, which is what runs its cross-comparand assertions."""
    assert importlib.import_module(name) is not None


@pytest.mark.parametrize("name", BENCHMARKS)
def test_main_is_never_called_outside_its_own_guard(name: str) -> None:
    """A bare module-level call would time every benchmark on import."""
    source = (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
    assert _main_runs_only_behind_its_guard(source)


def test_a_bare_module_level_call_to_main_is_detected() -> None:
    """The detector itself: none of the six is the regression it looks for."""
    source = "def main():\n    pass\n\n\nmain()\n"
    assert not _main_runs_only_behind_its_guard(source)


@pytest.mark.parametrize("name", BENCHMARKS)
def test_every_benchmark_offers_the_same_entry_point(name: str) -> None:
    """`main` and `provenance`, so the six are run and read alike."""
    module = importlib.import_module(name)
    assert callable(module.main)
    assert callable(module.provenance)
