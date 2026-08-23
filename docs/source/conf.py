# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Sphinx configuration.

The version is read out of pyproject.toml rather than from installed
metadata: this project installs nothing, `[tool.setuptools] packages`
being empty, so there is no distribution to ask.
"""

from __future__ import annotations

import posixpath
import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sphinx.addnodes import pending_xref
from sphinx.transforms.post_transforms import SphinxPostTransform

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_ROOT = Path(__file__).parents[2]
_PYPROJECT = _ROOT / "pyproject.toml"

project = "btclib-benchmarks"
author = "The btclib developers"
copyright = "The btclib developers"  # noqa: A001
release = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
version = release

extensions = ["myst_parser"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
html_theme = "sphinx_rtd_theme"
exclude_patterns: list[str] = []


# -- Links out of the included root markdown files ----------------------------

# Every page of the toctree is one of this repository's root markdown
# files, pulled into a *_link.md shim by a myst {include}. A root file is
# written for the place that reads it unrendered -- the GitHub file view,
# there being no site served from this repository -- so a link in one is
# spelled relative to the repository root, and myst, resolving it relative
# to this directory, finds nothing.
#
# What myst emits for a target it cannot resolve is why this needs code
# rather than a warning filter: the link becomes an anchor on the page it
# is already on, an id nothing has, so suppressing myst.xref_missing would
# leave the link there and silence the only thing that says it goes
# nowhere.
#
# The `_link` suffix keeps a shim's own name out of the way, and it is not
# decoration: with the shim named `contributing.md`, `REVIEWING.md`'s
# link to `./CONTRIBUTING.md` resolved to the docname `CONTRIBUTING`,
# sphinx reported an unknown source document and `-W` failed the build.
# Renamed, myst finds nothing at that path, gives up, and leaves the
# target to the transform below -- which is the arrangement the sibling
# repositories' shims are named for. Both spellings were measured here.
#
# The map is read from the shims, so a page added or dropped under this
# directory needs no second edit here. A relative target no shim renders
# is left to myst, which reports it and `-W` then fails the build: what a
# root file here writes for anything this documentation does not render is
# an absolute url, which is the rule `.pre-commit-config.yaml`'s
# `local-link-prefix` hook states and measures. The sibling repositories
# send such a target to the file on GitHub instead; here that branch would
# be code nothing reaches, and
#
#     git grep -n '](\./' -- '*.md'
#
# is what says so.

# a shim is one myst include fence, and everything after the directive
# name on that line is the directive's argument: the path of the file the
# shim renders, spaces included. Options are the lines under it, never
# this one, so the path ends where the line does
_INCLUDE = re.compile(r"^```\{include\}\s+(.+?)\s*$", re.MULTILINE)


def _included(page: Path) -> tuple[str, str] | None:
    """Map the root file a page renders to that page's own docname.

    Args:
        page: a markdown file under this directory.

    Returns:
        The included file's repository-relative path and the docname, or
        None where the page includes nothing and so renders no root file.

    Raises:
        ValueError: the page holds more than one include fence, so which
            root file it renders is not a question this can answer.
    """
    paths = _INCLUDE.findall(page.read_text(encoding="utf-8"))
    if len(paths) > 1:
        err_msg = f"{page.name}: more than one include fence"
        raise ValueError(err_msg)
    if not paths:
        return None
    return str((page.parent / paths[0]).resolve().relative_to(_ROOT)), page.stem


# repository-relative path -> the docname whose page renders it
_INCLUDED = dict(
    entry
    for entry in map(_included, sorted(Path(__file__).parent.glob("*.md")))
    if entry is not None
)


class RootFileLinks(SphinxPostTransform):
    """Resolve the repository-relative links of the included root files."""

    # ahead of myst's own resolver, which runs at 9 and is what turns an
    # unresolved target into that anchor
    default_priority = 5

    def run(self, **kwargs: Any) -> None:
        """Rewrite every myst xref naming a root file a page renders.

        Args:
            kwargs: what sphinx passes a post-transform, and unused here.
        """
        for node in self.document.findall(pending_xref):
            # refdomain "doc" is a link myst has already resolved to a
            # page, and None is one it has given up on: only the second
            # can be a root file's link spelled from the repository root
            if node.get("reftype") != "myst" or node.get("refdomain") is not None:
                continue
            target, _, anchor = node["reftarget"].partition("#")
            # "./CONTRIBUTING.md" -> "CONTRIBUTING.md"; a path climbing out
            # of the repository is nothing this can answer
            target = posixpath.normpath(target)
            if target in _INCLUDED:
                # handed back to myst as the link it would have been
                # written as, so the page title is its business and not
                # this file's
                node["refdomain"] = "doc"
                node["reftarget"] = _INCLUDED[target]
                node["reftargetid"] = anchor or None


def setup(app: Sphinx) -> None:
    """Register the transform above; sphinx calls this.

    Args:
        app: the sphinx application.
    """
    app.add_post_transform(RootFileLinks)
