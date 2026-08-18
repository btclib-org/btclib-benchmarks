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


def test_a_recorded_release_date_is_given_beside_the_version_it_was_read_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No installed metadata carries a release date, so one is recorded.

    Recorded against a release: the date is given for that one and the
    version stands alone for any other, which is what keeps a date from
    outliving the release it describes.
    """
    monkeypatch.setattr(_provenance, "version", lambda _: "1.2.3")
    dated = _provenance.described(
        ("pytest", pytest.__file__), dates={"pytest": ("1.2.3", "2026-01-01")}
    )
    assert "released 2026-01-01" in dated[0]

    stale = _provenance.described(
        ("pytest", pytest.__file__), dates={"pytest": ("9.9.9", "2026-01-01")}
    )
    assert "released" not in stale[0]


def test_described_returns_one_line_per_package_and_nothing_else() -> None:
    """Lines and not a print, so that one run can be published twice.

    They go into the saved measurement beside the numbers, which is what
    lets a page be rewritten without a machine. One line per package and no
    others: the interpreter, the machine and the time belong to the run
    rather than to the packages, and the run block is where all three are
    stated together.
    """
    lines = _provenance.described(("pytest", pytest.__file__))
    assert len(lines) == 1
    assert lines[0].startswith("pytest")
    assert "python" not in lines[0]


def test_the_install_root_test_accepts_both_names_debian_uses(
    tmp_path: Path,
) -> None:
    """Debian installs to `dist-packages`, everyone else to `site-packages`."""
    for name in ("site-packages", "dist-packages"):
        assert _provenance._under_install_root(str(tmp_path / name / "p" / "m.py"))
    assert not _provenance._under_install_root(str(tmp_path / "src" / "m.py"))


def test_what_a_timing_contains_says_a_timing_holds_no_check() -> None:
    """The claim is in the output, not only in the prose about it.

    A reader comparing two rows a percent apart has to be able to rule out
    that one of them paid for an assertion the other wrote more cheaply, and
    the place to rule it out is the block above the numbers. This test is the
    only thing keeping that block and `tests/vectors_test.py` from drifting
    apart: it names the file the output points at.
    """
    said = "\n".join(_provenance.WHAT_A_TIMING_CONTAINS)
    assert "tests/vectors_test.py" in said
    assert Path("tests/vectors_test.py").is_file()


class _FakeWheel:
    """A distribution whose `WHEEL` file is whatever a test hands it."""

    def __init__(self, wheel: str | None) -> None:
        self.wheel = wheel

    def read_text(self, filename: str) -> str | None:
        """Answer `WHEEL` and nothing else, as importlib does."""
        assert filename == "WHEEL"
        return self.wheel


@pytest.fixture
def fake_wheel(monkeypatch: pytest.MonkeyPatch) -> Callable[[str | None], None]:
    """Return a function installing a fake `WHEEL` file to read."""

    def install(wheel: str | None) -> None:
        monkeypatch.setattr(_provenance, "_distribution", lambda _: _FakeWheel(wheel))

    return install


def test_an_index_wheel_is_reported_as_its_tag_and_nothing_more(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """A manylinux tag came from an index, so there is nothing to remark on.

    The report is what a reader has to act on and nothing else, which for
    a downloaded wheel is the tag: whoever published it built it, and the
    revision it vendors is the one recorded against its version.
    """
    fake_wheel("Wheel-Version: 1.0\nTag: cp313-cp313-manylinux_2_17_x86_64\n")
    assert _provenance.artifact_of("anything") == "cp313-cp313-manylinux_2_17_x86_64"


def test_a_bare_linux_tag_says_the_wheel_was_built_where_it_is_installed(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """The case the whole function exists for, and it is three of six CI jobs.

    No index accepts a bare `linux_*` wheel, so one installed here was
    built here -- which for a comparand vendoring libsecp256k1 means the
    revision its sdist downloads rather than the one its wheels carry.
    """
    fake_wheel("Wheel-Version: 1.0\nTag: cp311-cp311-linux_aarch64\n")
    said = _provenance.artifact_of("secp256k1")
    assert said == "cp311-cp311-linux_aarch64, built where it is installed"


def test_the_two_spellings_an_index_accepts_are_not_read_as_local_builds(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """Both accepted Linux spellings end in the word a local build starts with.

    `manylinux_2_17_x86_64` and `musllinux_1_2_aarch64` contain `linux_`,
    so a substring test called every downloaded Linux wheel a build on the
    runner -- which is the answer for three CI jobs and the wrong answer
    for the other three.
    """
    for platform in ("manylinux_2_17_x86_64", "musllinux_1_2_aarch64"):
        fake_wheel(f"Tag: cp313-cp313-{platform}\n")
        assert _provenance.artifact_of("anything") == f"cp313-cp313-{platform}"


def test_a_tag_naming_a_compressed_set_of_platforms_is_read_field_by_field(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """A platform field may be several joined by dots, and any one answers."""
    fake_wheel("Tag: cp313-cp313-manylinux1_x86_64.linux_x86_64\n")
    assert _provenance.artifact_of("anything").endswith("built where it is installed")


def test_a_wheel_of_several_tags_reports_all_of_them(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """A fat wheel satisfies several tags, and no one of them is the answer."""
    fake_wheel("Tag: cp38-abi3-macosx_10_12_x86_64\nTag: cp38-abi3-macosx_11_0_arm64\n")
    assert _provenance.wheel_tags("anything") == [
        "cp38-abi3-macosx_10_12_x86_64",
        "cp38-abi3-macosx_11_0_arm64",
    ]


def test_an_install_with_no_wheel_metadata_is_not_reported_as_missing(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """Installed with no `WHEEL` and not installed at all are two facts.

    Collapsing them would have this say a comparand is absent when what is
    absent is one metadata file, which is a different thing to go looking
    for.
    """
    fake_wheel(None)
    assert _provenance.wheel_tags("anything") == []
    assert _provenance.artifact_of("anything") == "no WHEEL metadata"


def test_an_uninstalled_distribution_has_no_tags_rather_than_none_readable() -> None:
    """`None` is the answer for a name nothing installed, and it is not `[]`."""
    assert _provenance.wheel_tags("no-such-distribution-anywhere") is None
    assert _provenance.artifact_of("no-such-distribution-anywhere") == "not installed"


def test_built_here_answers_yes_positively_and_no_only_by_default(
    fake_wheel: Callable[[str | None], None],
) -> None:
    """The asymmetry a caller keying a pin on this has to respect.

    `True` is a statement: no index would have served that tag, so the
    wheel was made where it sits and a comparand vendoring a C library
    carries whatever its sdist carries. `False` is not the opposite one --
    a macOS wheel is spelled the same whoever built it, so it means the tag
    did not say. `01-libsecp256k1.py` records the tags an index is known to
    serve for exactly that reason, and prints `unrecorded` for a tag in
    neither set rather than reading this as a download.
    """
    fake_wheel("Tag: cp311-cp311-linux_aarch64\n")
    assert _provenance.built_here("anything") is True
    fake_wheel("Tag: cp313-cp313-macosx_11_0_arm64\n")
    assert _provenance.built_here("anything") is False
    assert _provenance.built_here("no-such-distribution-anywhere") is False
