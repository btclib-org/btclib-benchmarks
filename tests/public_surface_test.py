# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""`btclib_benchmarks`'s public surface, declared and empty.

Section 7 of the organization standard asks every module and package to
declare `__all__`, a module under a private name excepted as no part of
the surface it describes. Every submodule this package holds -- the
shared inputs, the provenance report, the saved-run schema and the
vendored vectors -- is named with a leading underscore, so none of them
is a surface the root would have to re-export, and the root's own
`__all__` is legitimately empty rather than merely absent.
"""

from __future__ import annotations

from pkgutil import iter_modules

import btclib_benchmarks


def public_name(name: str) -> bool:
    """Whether a module name is public, by the standard's own exception."""
    return not name.startswith("_")


def test_the_root_declares_an_empty_all() -> None:
    """`__all__` is there to read, not merely absent."""
    assert btclib_benchmarks.__all__ == []


def test_every_submodule_is_private() -> None:
    """No direct child of the package is a name the root would re-export."""
    children = [name for _, name, _ in iter_modules(btclib_benchmarks.__path__)]
    assert children, "the package holds no submodule to check"
    public = sorted(name for name in children if public_name(name))
    assert not public, f"{', '.join(public)} is public and unexported"
