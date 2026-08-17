# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Where the packages being timed came from, said above every number.

A released wheel, a git checkout and an editable install of the same
distribution all satisfy the same requirement, all resolve without a
word, and all land in the same `site-packages`. They do not all perform
the same, so a table that does not say which one ran is a table that
cannot be checked -- and the wrong one is not an error message, it is a
plausible number for a version nobody runs.

That is the same argument the per-comparand backend probes make one layer
down, where a package may or may not have found a C library to call: the
rule here is that nothing claims a measurement without saying what
produced it.
"""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from importlib.metadata import distribution as _distribution
from pathlib import Path

# the platform an index will not serve, so a wheel tagged for it was built
# where it is installed. PEP 600 is what makes that readable: a Linux wheel
# reaches an index as `manylinux` or `musllinux` and a bare `linux_*` one
# is refused, so on Linux the tag separates a download from a local build.
# It separates nothing on macOS or Windows, where a published wheel and one
# built here are spelled the same, which is why this is a platform and not
# a rule.
#
# Matched against the start of the platform field and not looked for
# anywhere in the tag, which is what the two accepted spellings end in:
# `manylinux_2_17_x86_64` contains this word, and a substring test called
# every downloaded Linux wheel a local build
NOT_FROM_AN_INDEX = "linux_"


def origin_of(dist_name: str) -> str:
    """Say where a distribution came from: an index, a git ref, or a path.

    PEP 610 is what makes this answerable rather than guessed: an
    installer writes a `direct_url.json` beside the metadata whenever a
    package came from anywhere *other* than an index, so the absence of
    that file is the positive statement that this is a released
    artifact.

    Reading the import path instead answers nothing, a git build and a
    PyPI wheel both sitting in `site-packages` -- which is not
    hypothetical: the first version of this file did read the path, and
    labelled a git build of btclib `released` on the very run that
    introduced it.
    """
    try:
        raw = _distribution(dist_name).read_text("direct_url.json")
    except PackageNotFoundError:  # pragma: no cover - all are installed
        return "not installed"
    if raw is None:
        return "released"
    direct = json.loads(raw)
    url = direct.get("url", "")
    if "vcs_info" in direct:
        vcs = direct["vcs_info"]
        requested = vcs.get("requested_revision")
        commit = (vcs.get("commit_id") or "")[:12]
        ref = f"{requested}@{commit}" if requested else commit
        return f"{url.removeprefix('https://github.com/')} {ref}".strip()
    if direct.get("dir_info", {}).get("editable"):
        return f"editable: {url.removeprefix('file://')}"
    return f"local: {url.removeprefix('file://')}"


def wheel_tags(dist_name: str) -> list[str] | None:
    """Return the tags of the wheel an install came from, or nothing.

    Every install goes through a wheel, an sdist being built into one
    first, and the `WHEEL` file it leaves in the metadata directory states
    what that wheel was built for. So this is the one thing at run time
    that tells the artifact from the requirement it satisfied.

    `None` is not installed and an empty list is installed with no `WHEEL`
    to read, which is a distribution laid down by something other than a
    wheel install. Two facts, and a caller reporting them as one would say
    a package is missing when what is missing is its metadata.
    """
    try:
        raw = _distribution(dist_name).read_text("WHEEL")
    except PackageNotFoundError:
        return None
    return [
        line.split(":", 1)[1].strip()
        for line in (raw or "").splitlines()
        if line.startswith("Tag:")
    ]


def _built_here(tag: str) -> bool:
    """Say whether a tag names a platform no index would have served.

    The platform is the tag's last field, and it may be several joined by
    dots -- a wheel that satisfies a compressed set of them -- so any one
    of those answering is the whole tag answering.
    """
    return any(
        platform.startswith(NOT_FROM_AN_INDEX)
        for platform in tag.rsplit("-", 1)[-1].split(".")
    )


def artifact_of(dist_name: str) -> str:
    """Say which artifact an install resolved to, where the tag can tell.

    `origin_of` above says where a distribution came from and stops there,
    which for a comparand vendoring a C library is half the answer: an
    index serves a wheel and an sdist under one version, and the two do
    not have to carry the same library. `secp256k1` is the case that
    proves it -- its wheels build against libsecp256k1 v0.6.0 and the only
    sdist of the same version downloads a pre-v0.1.0 revision, four years
    older. Which library a machine got is therefore not in the version it
    reports, and a pin keyed on that version cannot be right for both.

    The wheel's tag can say, on the platform where the question is live. A
    bare `linux_*` tag is one no index accepts, so a wheel carrying it was
    built where it is installed; a `manylinux` or `musllinux` one was not.
    On macOS and Windows the two are spelled alike, so there this reports
    the tag and stops -- which is why a caller gets a tag and a remark
    rather than a verdict, and why the revision itself is still not here.
    Nothing in an installed tree records what a build downloaded, and the
    pins in `01-libsecp256k1.py` are where that is written down by hand.
    """
    tags = wheel_tags(dist_name)
    if tags is None:
        return "not installed"
    if not tags:
        return "no WHEEL metadata"
    said = ", ".join(tags)
    if any(_built_here(tag) for tag in tags):
        return f"{said}, built where it is installed"
    return said


def _under_install_root(module_file: str) -> bool:
    """Say whether a module sits inside an install directory."""
    return any(
        parent.name in {"site-packages", "dist-packages"}
        for parent in Path(module_file).resolve().parents
    )


def from_a_declared_source(dist_name: str) -> bool:
    """Say whether an install came from an index or from a pinned revision.

    Those are the two origins that need no saying, being what a declared
    source gives: pyproject.toml names an index requirement or
    `[tool.uv.sources]` names a revision, and either way the version number
    beside the name carries it -- btclib's own says which, a release being
    dated to the day where a build off `main` is not. Printing them is a
    parenthesis that never varies.

    What is not declared is a path installed over the top, and that is
    worth a line of its own. No `PackageNotFoundError` to catch here: this
    is asked only after `version` has already answered for the same name.
    """
    raw = _distribution(dist_name).read_text("direct_url.json")
    return raw is None or "vcs_info" in json.loads(raw)


def describe(dist_name: str, module_file: str) -> str:
    """Return a line naming a package's version, and its origin if it is odd.

    `dist_name` is the name on the index and `module_file` the imported
    module's `__file__`. Both are asked for because they answer different
    halves: the metadata says how a package was installed, and only the
    file says whether what got imported is the installed copy at all --
    a directory on `sys.path` shadows an install silently, and no
    metadata can see it.

    The version alone is the line for an ordinary run. An origin appears
    only when it is one a reader has to act on, which is the point of
    reporting it at all: `editable:` and `local:` say a path was installed
    over the top, `sys.path:` says the import never reached the install,
    and a run showing any of the three is measuring something other than
    what a `uv sync` produces.
    """
    try:
        released = version(dist_name)
    except PackageNotFoundError:  # pragma: no cover - all are installed
        return f"{dist_name:<20}: not installed"
    if not _under_install_root(module_file):
        return f"{dist_name:<20}: {released:<24} (sys.path: {module_file})"
    if from_a_declared_source(dist_name):
        return f"{dist_name:<20}: {released}"
    return f"{dist_name:<20}: {released:<24} ({origin_of(dist_name)})"


# what a timing contains, said in the output rather than only in the prose
# about it. A reader looking at two rows a percent apart is entitled to know
# whether part of the difference is an assertion one row could write more
# cheaply than another. It is not: a timed function calls one API and
# discards what it comes back with, and where the answers *are* checked is
# named here, so the answer travels with the numbers rather than sitting in
# a file the numbers do not point at.
#
# Lines and not a print, because a run and a re-render both need them and
# only one of the two has a stream to write to: `_results` stores these with
# the measurement, so a page keeps the claim its own run made.
WHAT_A_TIMING_CONTAINS = (
    "what a timing contains",
    "  one call per iteration, its answer discarded: no row checks",
    "  itself, and no comparison is inside a measured loop",
    "  the answers are checked in tests/vectors_test.py, and where",
    "  each script builds its fixtures, which is before any clock",
)


def described(
    *packages: tuple[str, str], dates: dict[str, tuple[str, str]] | None = None
) -> list[str]:
    """Return one line per package, for the block above the numbers.

    `dates` maps a distribution to the release it was recorded at and the day
    that release was published. Recorded, because no installed metadata
    carries it: a wheel's METADATA has a Version and no date, and the
    dist-info directory's mtime is when the package was installed here. A date
    prints only for the release it was read at, and the version prints alone
    for any other -- the same rule the libsecp256k1 pins follow, and for the
    same reason.

    Returned rather than printed, which is what lets one run be published
    twice: the lines go into the saved measurement beside the numbers, and
    `scripts/render.py` writes both into the page without asking the
    interpreter anything. Printing them put the answer somewhere only a
    person with a terminal could reach it.

    The interpreter is not among the lines. It belongs to the run rather
    than to the packages -- as the machine and the time do, which no script
    can state either -- and the run block above the output carries all three.
    """
    lines = []
    for dist_name, module_file in packages:
        line = describe(dist_name, module_file)
        recorded = (dates or {}).get(dist_name)
        if recorded and version(dist_name) == recorded[0]:
            line = f"{line}, released {recorded[1]}"
        lines.append(line)
    return lines
