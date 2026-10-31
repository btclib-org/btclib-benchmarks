# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What every saved run under `results/` does when it is read and rendered.

The release runs are in `results/` and the default-branch runs in
`results/default-branch/`, and both are read here.

Each run is read back, written out again, and rendered into every block a
page can carry. What is asserted is that these steps hold together, not what
the blocks say: a heading reworded in `_results.py` breaks nothing here, and
`render.py --check` is what asks whether a page still matches its run.

The other cases of `_results.py` reach every line of the module without
these runs.
"""

from __future__ import annotations

import json

import pytest

from btclib_benchmarks import _results

SAVED = _results.saved_runs()


def test_there_is_a_saved_release_run_to_read() -> None:
    """The cases below are parametrized over directories, which may be empty."""
    assert any(mode == _results.RELEASE for mode, _ in SAVED)


@pytest.mark.parametrize("mode, benchmark", SAVED)
def test_a_saved_run_is_written_back_as_it_was_read(mode: str, benchmark: str) -> None:
    """Reading a run and writing it out again changes nothing in the file."""
    saved = _results.saved_run(benchmark, mode).read_text(encoding="utf-8")
    measurement = _results.load(benchmark, mode)
    assert _results.from_json(_results.as_json(measurement)) == measurement
    written = json.dumps(_results.as_json(measurement), indent=2, ensure_ascii=False)
    assert saved == written + "\n"


@pytest.mark.parametrize("mode, benchmark", SAVED)
def test_every_block_of_a_page_is_rendered(mode: str, benchmark: str) -> None:
    """A run fills each block, and the output block opens with the method."""
    measurement = _results.load(benchmark, mode)
    assert _results.rendered_run(measurement)
    assert _results.rendered_provenance(measurement.provenance)
    method = _results.rendered_method(measurement)
    assert method
    assert _results.rendered_output(measurement).startswith(method)
    for group in _results.groups_of(measurement):
        assert _results.rendered_group(measurement, group)
