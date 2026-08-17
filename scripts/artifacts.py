# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Say which artifact each comparand's install resolved to, measuring nothing.

    uv run python scripts/artifacts.py

One line per declared dependency: the version installed, and the tags of
the wheel it came from. A page's provenance block already says what
version was measured and whether it came from an index or a branch; what
it cannot say is which of an index's two artifacts answered, and for a
comparand that vendors libsecp256k1 that is the difference between two
libraries four years apart. `_provenance.artifact_of` has the mechanism
and the case that made it necessary.

## Where this is read, and why it is not a test

Three of the suite's six CI jobs run on `ubuntu-24.04-arm`, for which one
comparand publishes no wheel: there and only there its libsecp256k1 is
compiled on the runner. Every assertion those jobs make is therefore about
a different binary from the one the pages are measured on, and until this
command ran in them nothing said which -- a divergence found on aarch64
started from the wrapper rather than from the build. Recorded and not
asserted, because what an install resolves to is a fact about a machine
and a lock rather than a claim this repository is entitled to make: a
wheel appearing on an index changes the answer and breaks nothing.

## It reads the declared dependencies, and not the environment

`pyproject.toml`'s `dependencies` are the comparands -- that inversion is
why this repository exists, a comparand in a `bench` group having made an
advisory against it an advisory against btclib. Reading them is what keeps
this list from going stale: a comparand added there is reported here
without anybody remembering to, and the interpreter's own toolchain, which
is in a group and not a dependency, stays out of a report about comparands.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import _provenance

# where the declared dependencies are, this file sitting beside the
# scripts the project's root holds
PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"

# where a requirement's name stops and what it asks of it begins. A
# dependency is a PEP 508 string and only its name is wanted, so the name
# is what precedes the first of these rather than the product of a parser
# this has no other use for
BOUNDS = "<>=!~[; "


def _named(requirement: str) -> str:
    """Return the distribution a PEP 508 requirement string names."""
    stops = [requirement.find(bound) for bound in BOUNDS if bound in requirement]
    return requirement[: min(stops)] if stops else requirement


def declared() -> list[str]:
    """Return the distribution named by each declared dependency."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return [_named(requirement) for requirement in project["dependencies"]]


def main() -> int:
    """Print one line per comparand, and succeed whatever they say."""
    for dist_name in declared():
        print(f"{dist_name:<20}: {_provenance.artifact_of(dist_name)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - the command, not the module
    raise SystemExit(main())
