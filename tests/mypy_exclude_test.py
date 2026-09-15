# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""`[tool.mypy] exclude` is a regex, not a glob, and reaches every source file.

`mypy.modulefinder.matches_exclude` (uv.lock's pinned mypy) is
`re.search(pattern, subpath)`, unanchored unless the pattern itself
anchors -- so an unanchored `"build"` would drop any path merely
containing that substring, not only a top-level `build/` directory a
packaging tool writes. No tracked path under this tree's own mypy roots
carries it today (issue btclib-org/.github#1102), which is exactly why
nothing but this test would ever notice one arriving loose: the day
`scripts/build_report.py` or similar is added, an unanchored pattern
drops it from the type gate with no diagnostic at all.

This module reads pyproject.toml and .pre-commit-config.yaml as text
rather than importing mypy or a YAML parser. The exclude list is
`[tool.mypy]`'s own key in pyproject.toml. The roots mypy is run over
are not named in this tree's CONTRIBUTING.md the way btclib's are --
this tree's *The environment and the gates* names three gate commands,
none of them `uv run mypy` directly, and mypy runs only through the
`mypy` hook in .pre-commit-config.yaml, whose own `entry:` is what
`lint.yml` and a local `uv run pre-commit run --all-files` both run. So
the roots are read out of that hook's `entry:` line instead.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).parents[1]
_PYPROJECT = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
_PRE_COMMIT_CONFIG = (_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

# the section alone, so a `[tool.ruff.format]` or `[tool.typos.files]`
# `exclude` sitting elsewhere in the file is never read as this one
_MYPY_SECTION = re.compile(r"(?ms)^\[tool\.mypy\]\n(.*?)(?=\n\[|\Z)")
# this tree's own `exclude = [...]` sits on one line, unlike btclib's
# multi-line list -- captured non-greedily up to the first `]` either way
_EXCLUDE_LIST = re.compile(r"(?ms)^exclude = \[(?P<items>.*?)\]")
_LIST_ITEM = re.compile(r'"((?:[^"\\]|\\.)*)"')

# the roots the `mypy` pre-commit hook's own `entry:` names, read out
# rather than repeated: a root added or dropped there is a root this
# test starts or stops walking without a second edit here.
# `--explicit-package-bases` appears nowhere else in this file, so the
# line it sits on is unambiguously the mypy hook's own command
_GATE_ROOTS = re.compile(
    r"^\s*mypy --explicit-package-bases (?P<roots>\S.*)$", re.MULTILINE
)


def _mypy_exclude_patterns() -> tuple[str, ...]:
    section = _MYPY_SECTION.search(_PYPROJECT)
    assert section is not None, "[tool.mypy] is not in pyproject.toml"
    exclude_list = _EXCLUDE_LIST.search(section.group(1))
    assert exclude_list is not None, "[tool.mypy] carries no exclude list"
    return tuple(_LIST_ITEM.findall(exclude_list.group("items")))


def _gate_roots() -> tuple[str, ...]:
    match = _GATE_ROOTS.search(_PRE_COMMIT_CONFIG)
    assert match is not None, (
        "no `mypy --explicit-package-bases` line in .pre-commit-config.yaml"
    )
    return tuple(match.group("roots").split())


def _excluded(relative_posix_path: str, patterns: tuple[str, ...]) -> bool:
    """Whether mypy's own crawl would drop this path, its own way of asking.

    `re.search`, unanchored, over every pattern -- `matches_exclude`'s own
    logic, without importing the package that carries it.
    """
    return any(re.search(pattern, relative_posix_path) for pattern in patterns)


def _census(roots: tuple[str, ...]) -> tuple[str, ...]:
    """Every `.py` file under the gate's own roots, relative to the root."""
    files: list[str] = []
    for root in roots:
        files.extend(
            str(path.relative_to(_ROOT).as_posix())
            for path in sorted((_ROOT / root).rglob("*.py"))
        )
    return tuple(files)


def test_the_exclude_reaches_the_directory_it_names() -> None:
    """A real `build/` output stays out, proving the anchor has teeth."""
    patterns = _mypy_exclude_patterns()
    assert _excluded("build/lib/btclib_benchmarks/version.py", patterns)


def test_the_old_and_new_patterns_agree_on_every_tracked_path_today() -> None:
    """The anchor changes nothing here: both patterns drop the same (empty) set.

    `"build"`, the unanchored pattern this tree used to carry, and
    `"^build/"`, what `[tool.mypy] exclude` carries now, are compared
    directly rather than through `_mypy_exclude_patterns()` -- the file
    holds only the current one, and the point of this test is that its
    predecessor read no differently over the gate's actual roots today
    (issue btclib-org/.github#1102).
    """
    census = _census(_gate_roots())
    unanchored_hits = [path for path in census if _excluded(path, ("build",))]
    anchored_hits = [path for path in census if _excluded(path, ("^build/",))]
    assert unanchored_hits == []
    assert anchored_hits == []


def test_the_patterns_disagree_on_a_plausible_future_path() -> None:
    """The reason to anchor anyway: a path this tree could add would differ.

    `scripts/build_report.py` is not a path this tree has, so this is a
    control on the *pattern*, not a planted file pretending to be a
    measurement of harm this tree does not carry.
    """
    candidate = "scripts/build_report.py"
    assert _excluded(candidate, ("build",))
    assert not _excluded(candidate, ("^build/",))


def test_the_exclude_drops_nothing_the_gate_command_names() -> None:
    """Every source the documented command walks is one mypy still checks.

    An exclude entry unanchored the way `"build"` was drops any path
    carrying that substring, silently -- the census below is what makes
    that regression visible again the next time an entry is loosened.
    """
    patterns = _mypy_exclude_patterns()
    census = _census(_gate_roots())
    excluded = [path for path in census if _excluded(path, patterns)]
    assert not excluded, f"the exclude drops {excluded} from the type gate"
