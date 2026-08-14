# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every benchmark loads, and its comparands agree, without timing anything.

This is the whole of what a test can hold a benchmark to. A measurement
cannot be asserted -- the number is a property of the machine, not of the
code -- so what is checked here is the two things that can be:

- the module imports. That covers the fixtures at its top and, in three
  of the four, a block of assertions comparing every comparand's answer
  against btclib's before any of them is timed. A table whose rows are
  computing different things is worth nothing, and importing the module
  is what runs that check.
- it did not time anything while doing so. The `main()` guard is what
  buys that, and a regression to bare module-level calls would turn
  every one of these tests into a benchmark run -- slow enough to notice,
  but the assertion below is what names the cause.

Both are the reason `main()` exists at all: before it, importing any of
these modules ran every timing loop in it.
"""

from __future__ import annotations

import importlib
import time

import pytest

BENCHMARKS = [
    "btclib_two_paths",
    "bitcoin_libraries",
    "pure_python",
    "libsecp256k1_wrappers",
]

# an import does fixture work -- key derivation, a signature per comparand,
# and the cross-checks over them -- so this is not a millisecond. It is,
# however, two orders of magnitude under the fastest of the timing runs,
# which take tens of seconds each. Anything near that means the guard is
# gone
_IMPORT_BUDGET_SECONDS = 10.0


@pytest.mark.parametrize("name", BENCHMARKS)
def test_the_benchmark_imports_and_its_comparands_agree(name: str) -> None:
    """Import it, which is what runs its cross-comparand assertions."""
    assert importlib.import_module(name) is not None


@pytest.mark.parametrize("name", BENCHMARKS)
def test_importing_a_benchmark_does_not_run_it(name: str) -> None:
    """A re-import is nearly free; an unguarded benchmark would not be."""
    importlib.import_module(name)  # warm, so the fixtures are not timed twice
    start = time.perf_counter()
    importlib.reload(importlib.import_module(name))
    assert time.perf_counter() - start < _IMPORT_BUDGET_SECONDS


@pytest.mark.parametrize("name", BENCHMARKS)
def test_every_benchmark_offers_the_same_entry_point(name: str) -> None:
    """`main` and `report_provenance`, so the four are run and read alike."""
    module = importlib.import_module(name)
    assert callable(module.main)
    assert callable(module.report_provenance)
