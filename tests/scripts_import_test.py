# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every benchmark loads, and its comparands agree, without timing anything.

This is the whole of what a test can hold a benchmark to. A measurement
cannot be asserted -- the number is a property of the machine, not of the
code -- so what is checked here is the two things that can be:

- the module imports. That covers the fixtures at its top and the block
  of assertions each of the five builds them with, holding every
  comparand to what the others answer, or to what a specification
  publishes, before any of them is timed. A table whose rows are
  computing different things is worth nothing, and importing the module
  is what runs that check.
- it did not time anything while doing so. The `main()` guard is what
  buys that, and a regression to bare module-level calls would turn
  every one of these tests into a benchmark run -- slow enough to notice,
  but the assertion below is what names the cause.

Both are what `main()` is for: a benchmark whose timings run at import
is one no suite can hold to anything.
"""

from __future__ import annotations

import importlib
import time

import pytest

BENCHMARKS = [
    "01-libsecp256k1",
    "02-btclib-vs-btclib",
    "03-libraries",
    "04-pure-python",
    "05-key-reuse",
]

# an import does fixture work, and since the five scripts draw from one
# shared pool that work is no longer a handful of vectors: `03-libraries.py`
# builds key objects and signatures for six packages, two of which sign in
# pure Python at tens of milliseconds a signature. What the pool caches --
# the keys, the messages, the public keys -- is read from disk after the
# first run; what it cannot cache is a package's own object.
#
# So this is tens of seconds rather than milliseconds, and the number is
# chosen against what it guards rather than against what a quiet machine
# manages: a benchmark that timed on import would spend minutes, every one
# of the five timing runs being minutes long. It is deliberately loose,
# because the machine running this suite may have just run one of those --
# `03-libraries.py` built its fixtures in thirteen seconds cold and
# twenty-six warm, and a budget tight enough to catch the difference would
# be a test that fails for the temperature of a laptop rather than for
# anything in the code. Anything near a minute means the
# `if __name__ == "__main__"` guard is gone
_IMPORT_BUDGET_SECONDS = 60.0


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
    """`main` and `provenance`, so the five are run and read alike."""
    module = importlib.import_module(name)
    assert callable(module.main)
    assert callable(module.provenance)
