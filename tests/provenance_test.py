# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Tests for the provenance report every benchmark prints before its numbers.

What is being defended is the one failure this project cannot afford to
have silently: measuring a build other than the one the reader will think
was measured. Each test below names the way that can happen.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import _provenance
import pytest

# what the `fake_dist` fixture hands a test: a function taking the
# payload a `direct_url.json` would hold, or None for "no such file"
InstallFake = Callable[[dict[str, object] | None], None]


class _FakeDistribution:
    """A distribution whose `direct_url.json` is whatever a test hands it."""

    def __init__(self, payload: dict[str, object] | None) -> None:
        self.payload = payload

    def read_text(self, filename: str) -> str | None:
        """Answer `direct_url.json` and nothing else, as importlib does."""
        assert filename == "direct_url.json"
        return None if self.payload is None else json.dumps(self.payload)


@pytest.fixture
def fake_dist(monkeypatch: pytest.MonkeyPatch) -> InstallFake:
    """Return a function installing a fake distribution to read."""

    def install(payload: dict[str, object] | None) -> None:
        monkeypatch.setattr(
            _provenance, "_distribution", lambda _: _FakeDistribution(payload)
        )

    return install


def test_a_package_from_an_index_is_reported_as_released(
    fake_dist: InstallFake,
) -> None:
    """No direct_url.json is PEP 610 for "this came from an index"."""
    fake_dist(None)
    assert _provenance.origin_of("anything") == "released"


def test_a_git_install_names_its_repository_and_commit(fake_dist: InstallFake) -> None:
    """The case that matters: a branch build must not read as a release.

    The requested revision *and* the commit are both reported, because a
    branch name alone dates nothing -- two runs a month apart would
    print the same `main`.
    """
    fake_dist(
        {
            "url": "https://github.com/btclib-org/btclib",
            "vcs_info": {
                "vcs": "git",
                "requested_revision": "main",
                "commit_id": "8720a7df02b05c1e14c720eaaea38d74160a86f3",
            },
        }
    )
    assert _provenance.origin_of("btclib") == "btclib-org/btclib main@8720a7df02b0"


def test_a_git_install_with_no_requested_revision_reports_the_commit(
    fake_dist: InstallFake,
) -> None:
    """A commit pinned directly has no branch or tag to name beside it."""
    fake_dist(
        {
            "url": "https://github.com/btclib-org/btclib",
            "vcs_info": {"vcs": "git", "commit_id": "0123456789abcdef"},
        }
    )
    assert _provenance.origin_of("btclib") == "btclib-org/btclib 0123456789ab"


def test_an_editable_install_is_named_as_one(fake_dist: InstallFake) -> None:
    """`--with-editable` is the documented way to measure a working tree."""
    fake_dist({"url": "file:///home/dev/btclib", "dir_info": {"editable": True}})
    assert _provenance.origin_of("btclib") == "editable: /home/dev/btclib"


def test_a_non_editable_local_install_is_distinguished_from_an_editable_one(
    fake_dist: InstallFake,
) -> None:
    """A snapshot install is not the tree it was copied from."""
    fake_dist({"url": "file:///tmp/build", "dir_info": {}})
    assert _provenance.origin_of("btclib") == "local: /tmp/build"


def test_an_uninstalled_distribution_says_so_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing comparand is a line in the report, not a traceback.

    The report runs before the numbers, so failing here would replace a
    table with a stack trace over something the reader could have fixed.
    """

    def absent(_: str) -> object:
        raise PackageNotFoundError

    monkeypatch.setattr(_provenance, "_distribution", absent)
    assert _provenance.origin_of("nowhere") == "not installed"


def test_a_module_outside_an_install_root_is_reported_as_shadowing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A checkout on `sys.path` shadows an install, unseen by metadata.

    This is the half `origin_of` cannot answer: the distribution is
    installed and its metadata says so, while the module actually
    imported came from somewhere else entirely.
    """
    monkeypatch.setattr(_provenance, "version", lambda _: "2026.9")
    line = _provenance.describe("btclib", "/home/dev/btclib/btclib/__init__.py")
    assert "sys.path: /home/dev/btclib/btclib/__init__.py" in line


INSTALLED = "/env/lib/python3.13/site-packages/pkg/__init__.py"


def test_a_declared_install_is_described_by_its_version_alone(
    monkeypatch: pytest.MonkeyPatch, fake_dist: InstallFake
) -> None:
    """The ordinary case, under which every table row is printed.

    No parenthesis: an index install and a pinned revision are what the
    declaration asks for, and a note saying so on every line of every run
    is noise a reader learns to skip -- which is the worst thing to teach
    them about this block, the one line that matters being the odd one.
    """
    fake_dist(None)
    monkeypatch.setattr(_provenance, "version", lambda _: "0.8.0.1")
    line = _provenance.describe("btclib-secp256k1", INSTALLED)
    assert line == "btclib-secp256k1    : 0.8.0.1"


def test_a_pinned_revision_is_also_described_by_its_version_alone(
    monkeypatch: pytest.MonkeyPatch, fake_dist: InstallFake
) -> None:
    """`[tool.uv.sources]` is a declaration too, and the version dates it."""
    fake_dist(
        {
            "url": "https://github.com/btclib-org/btclib",
            "vcs_info": {"vcs": "git", "commit_id": "0123456789abcdef"},
        }
    )
    monkeypatch.setattr(_provenance, "version", lambda _: "2026.9")
    assert _provenance.describe("btclib", INSTALLED) == "btclib              : 2026.9"


def test_a_path_install_is_named_in_the_line(
    monkeypatch: pytest.MonkeyPatch, fake_dist: InstallFake
) -> None:
    """The case the annotation exists for: something installed over the top.

    `--with-editable` is the documented way to measure a working tree, and
    the whole of what makes it safe is that the report says so.
    """
    fake_dist({"url": "file:///home/dev/btclib", "dir_info": {"editable": True}})
    monkeypatch.setattr(_provenance, "version", lambda _: "2026.9")
    line = _provenance.describe("btclib", INSTALLED)
    assert line.endswith("(editable: /home/dev/btclib)")


def test_a_distribution_with_no_metadata_at_all_is_named_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`describe` answers before it ever asks where the package came from."""

    def absent(_: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(_provenance, "version", absent)
    assert (
        _provenance.describe("gone", "/x.py") == "gone                : not installed"
    )


def test_report_prints_one_line_per_package_and_the_interpreter(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The report is stdout, so that a paste carries it and the numbers."""
    _provenance.report(("pytest", pytest.__file__))
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("pytest")
    assert "python              :" in out


def test_the_install_root_test_accepts_both_names_debian_uses(
    tmp_path: Path,
) -> None:
    """Debian installs to `dist-packages`, everyone else to `site-packages`."""
    for name in ("site-packages", "dist-packages"):
        assert _provenance._under_install_root(str(tmp_path / name / "p" / "m.py"))
    assert not _provenance._under_install_root(str(tmp_path / "src" / "m.py"))
