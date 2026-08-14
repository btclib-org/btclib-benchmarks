# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Put `scripts/` on the import path, which is the only fixture the suite needs.

The benchmark scripts are modules and not a package: nothing imports them
in ordinary use, they are run by path. A test that judges them therefore
has to reach them the way a person does, and this is the whole of what
that takes.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
