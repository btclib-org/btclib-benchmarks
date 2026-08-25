# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The four shared modules the benchmarks and the suite both import.

Every submodule of this package is named with a leading underscore --
`_inputs`, `_provenance`, `_results`, `_vectors` -- so none of them is
part of the public surface the organization standard's section 7 asks a
package to declare, and the root re-exports nothing.
"""

from __future__ import annotations

__all__: list[str] = []
