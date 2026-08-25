# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Put `scripts/` on the import path, for the files that are still run by it.

`src/btclib_benchmarks/` is a package, installed into this project's own
venv, and a test of it imports it the way any caller does. What is left
under `scripts/` -- the six numbered benchmarks, `artifacts.py` and
`render.py` -- is not: a module whose name opens with a digit or carries
a hyphen is not a Python identifier, so none of the six could become a
package member as it is, and the other two were never meant to be one.
Nothing imports any of the eight in ordinary use, they are run by path,
and a test that judges them has to reach them the way a person does --
which is the whole of what this insert buys.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
