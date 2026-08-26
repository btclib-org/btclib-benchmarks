# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Re-check every vendored-vector pin against upstream, weekly.

`vectors/README.md` pins each vendored file to an upstream commit and the
git blob SHA-1 compared against it. The blob half is already a test:
`tests/vectors_test.py` hashes each file beside its entry on every run,
so a copy edited here fails the suite. The commit half cannot be a test
-- whether upstream has taken a newer revision of the path is a question
about another repository, and the suite runs offline. This asks it.

What it does with the answer is open an issue, never a commit. Taking a
newer revision of a vector file changes what every comparand is held to,
which is a decision, and a script that refreshed a pin would be taking it
on somebody's behalf.

Scope is narrower than the file: only entries whose `behind` already
reads 0, the ones last confirmed to be exactly at the tip of their path.
An entry documented as behind records a decision already taken, and
re-reporting the same gap every week would be noise. Every heading the
file carries that this run did not check is listed in the report, so
nothing reads as "checked and clean" that was not checked at all.

A path upstream has renamed or deleted is reported rather than raising:
it has no commit to name as a tip, and a pin standing on a file that is
not there any more is the drift nobody would otherwise notice.

    python .github/scripts/check_vendored_vectors.py vectors/README.md
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_ISSUE_TITLE = "Vendored vectors behind upstream"

# resolved once: S607 is what a bare "gh" in a subprocess list would be, a
# partial executable path relying on PATH's own search order rather than
# naming what actually runs
_GH = shutil.which("gh") or "gh"

# a vendored file's own ### heading, so a drift report -- and the
# skipped-entry list -- names the file rather than only its upstream path
_HEADING = re.compile(r"^### (.+)$", re.MULTILINE)

# a fenced block's key/value lines, in the spelling section 7 of the
# organization standard fixes
_FIELD = re.compile(r"^(repo|path|commit|blob|pulled|behind)\s+(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Entry:
    """One pin this script can re-check: a single blob, a live commit."""

    heading: str
    repo: str
    path: str
    commit: str


@dataclass(frozen=True)
class Drift:
    """A pin whose commit is no longer the tip of its own path."""

    entry: Entry
    latest_commit: str
    latest_date: str

    @property
    def path_is_gone(self) -> bool:
        """True where upstream has no commit touching the pinned path.

        The empty `latest_commit` is what says so: there is no tip to
        name, `_latest_commit` having answered None. Reading it through a
        name keeps that encoding in one place.
        """
        return not self.latest_commit


def _entries_at_tip(readme: str) -> tuple[list[Entry], list[str]]:
    """Return the checkable entries, and the headings this skips.

    A heading is skippable for either of two reasons: no repo/path/commit
    triple at all, or a `behind` already other than 0 -- a gap somebody
    decided not to close.
    """
    entries: list[Entry] = []
    skipped: list[str] = []
    heading = ""
    pos = 0
    for match in re.finditer(r"```text\n(.*?)\n```", readme, re.DOTALL):
        headings_before = _HEADING.findall(readme[pos : match.start()])
        if headings_before:
            heading = headings_before[-1]
        pos = match.end()

        fields = dict(_FIELD.findall(match.group(1)))
        repo, path, commit = (
            fields.get("repo"),
            fields.get("path"),
            fields.get("commit"),
        )
        if not (repo and path and commit):
            skipped.append(f"{heading} (no commit to check against)")
            continue
        if not fields.get("behind", "").startswith("0"):
            skipped.append(f"{heading} (already documented as behind)")
            continue
        entries.append(Entry(heading, repo, path.strip(), commit.split()[0]))
    return entries, skipped


def _latest_commit(repo: str, path: str) -> tuple[str, str] | None:
    """Return the sha and date of the most recent commit touching path.

    None where upstream has no commit touching it at all, which means the
    path has been renamed or deleted: the sharpest drift there is, a pin
    naming a file that is not there any more. Answering None rather than
    unpacking one commit out of an empty list is what lets `report` see it
    as drift with no tip to name, instead of the run going red on a bare
    `ValueError` and no issue ever opening.
    """
    result = subprocess.run(  # noqa: S603
        [
            _GH,
            "api",
            "--method",
            "GET",
            f"repos/{repo}/commits",
            "-f",
            f"path={path}",
            "-f",
            "per_page=1",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    commits = json.loads(result.stdout)
    if not commits:
        return None
    commit = commits[0]
    date: str = commit["commit"]["committer"]["date"][:10]
    sha: str = commit["sha"]
    return sha, date


def find_drift(readme_path: Path) -> tuple[list[Drift], list[str]]:
    """Return every pin no longer at upstream's tip, and what was skipped."""
    entries, skipped = _entries_at_tip(readme_path.read_text(encoding="utf-8"))
    drifted = []
    for entry in entries:
        latest = _latest_commit(entry.repo, entry.path)
        if latest is None:
            # a path upstream no longer has: drift with no tip to name
            drifted.append(Drift(entry, "", ""))
        elif latest[0] != entry.commit:
            drifted.append(Drift(entry, *latest))
    return drifted, skipped


def _issue_body(readme_path: Path, drifted: list[Drift], skipped: list[str]) -> str:
    lines = [
        f"`{readme_path}` pins below are no longer at upstream's tip.",
        "Refreshing is a decision, not a chore -- this issue only reports it.",
        "",
    ]
    for drift in drifted:
        if drift.path_is_gone:
            lines.append(
                f"- **{drift.entry.heading}**: pinned to"
                f" `{drift.entry.commit[:12]}`, and `{drift.entry.repo}` has no"
                f" commit touching `{drift.entry.path}` any more -- renamed,"
                " moved or deleted upstream"
            )
            continue
        lines.append(
            f"- **{drift.entry.heading}**: pinned to `{drift.entry.commit[:12]}`,"
            f" upstream's tip of `{drift.entry.path}` is now"
            f" `{drift.latest_commit[:12]}` ({drift.latest_date}),"
            f" `{drift.entry.repo}`"
        )
    if skipped:
        lines.extend(("", "Not checked by this run, for the reason named:"))
        lines.extend(f"- {heading}" for heading in skipped)
    return "\n".join(lines)


def _open_issue_number() -> str | None:
    result = subprocess.run(  # noqa: S603
        [
            _GH,
            "issue",
            "list",
            "--state",
            "open",
            "--search",
            f'"{_ISSUE_TITLE}" in:title',
            "--json",
            "number",
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    issues = json.loads(result.stdout)
    return str(issues[0]["number"]) if issues else None


def report(readme_path: Path, drifted: list[Drift], skipped: list[str]) -> None:
    """Open, update, or close the tracking issue, whichever applies."""
    number = _open_issue_number()
    if not drifted:
        if number is not None:
            subprocess.run(  # noqa: S603
                [
                    _GH,
                    "issue",
                    "close",
                    number,
                    "--comment",
                    "Re-checked: every pin with behind: 0 is still at upstream's tip.",
                ],
                check=True,
            )
        return
    body = _issue_body(readme_path, drifted, skipped)
    if number is None:
        subprocess.run(  # noqa: S603
            [_GH, "issue", "create", "--title", _ISSUE_TITLE, "--body", body],
            check=True,
        )
    else:
        subprocess.run(  # noqa: S603
            [_GH, "issue", "edit", number, "--body", body], check=True
        )


def main() -> int:
    """Check the README named on argv, report drift, and say so on stdout.

    --dry-run skips opening, updating or closing the issue: what the
    pull_request trigger of vendored-vectors.yml passes, so a change to
    this script or to the README is exercised without the run editing
    whatever tracking issue happens to be open at the time.
    """
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = len(args) != len(sys.argv) - 1
    if len(args) != 1:
        # a human running this by hand is the only way here, the workflow
        # passing the path every time: without this check, `args[0]` below
        # would answer with an IndexError naming a list instead
        print(
            f"usage: {Path(sys.argv[0]).name} <README path> [--dry-run]",
            file=sys.stderr,
        )
        return 2
    readme_path = Path(args[0])
    drifted, skipped = find_drift(readme_path)
    for drift in drifted:
        if drift.path_is_gone:
            print(
                f"GONE: {drift.entry.heading} pinned to"
                f" {drift.entry.commit[:12]}, and {drift.entry.repo} has no"
                f" commit touching {drift.entry.path} any more"
            )
            continue
        print(
            f"BEHIND: {drift.entry.heading} pinned to {drift.entry.commit[:12]},"
            f" tip is {drift.latest_commit[:12]} ({drift.latest_date})"
        )
    for heading in skipped:
        print(f"SKIPPED: {heading}")
    if not drifted:
        print("Every checked pin is still at upstream's tip.")
    if not dry_run:
        report(readme_path, drifted, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
