# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Sphinx configuration.

The version is read out of pyproject.toml rather than from installed
metadata: this project installs nothing, `[tool.setuptools] packages`
being empty, so there is no distribution to ask.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"

project = "btclib-benchmarks"
author = "The btclib developers"
copyright = "The btclib developers"  # noqa: A001
release = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
version = release

extensions = ["myst_parser"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
html_theme = "sphinx_rtd_theme"
exclude_patterns: list[str] = []
