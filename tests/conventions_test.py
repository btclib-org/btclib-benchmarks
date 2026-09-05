# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""The convention-test declaration in tests/README.md is true.

Section 7 of the organization standard lists the conventions a suite can
turn into a red test, and closes with the clause that makes the list
usable: a repository needs the ones its own prose states rather than all
of them. That clause is right, and its price is that an *absent*
convention test is indistinguishable from a convention this repository
does not have. Nothing anywhere recorded which of the two it was.

A filename cannot answer it either. The suites of the organization name
the same idea in as many ways as there are suites, which is the shape
section 7 asks for rather than a divergence to correct. So the audit
reads a declaration rather than a directory, and this module is what
keeps the declaration from being prose: section 7's own rule, that a
convention worth stating is worth a test, applied to section 7 itself.

The table's rows and the "Not tested here" line together carry the
declaration, which is why the assertion below is about the *section*
rather than about the rows: a table with no rows would still be making a
statement rather than failing to make one, and tests/README.md says why
each convention sits on the side it does. No count is written anywhere
-- not of either half and not of the list itself: _CONVENTIONS below is
the list, and this module asserts the two halves cover it rather than
how many fall on each side.

Section 14 asks a copy of this module to say which of its departures are
decided rather than accidental. Section 7's list is transcribed into
_CONVENTIONS below rather than read off the standard: the standard is
another repository's file, so a copy is the only form the list takes
here. The checks over the rows quantify rather than being parametrized
on them, for the reason the comment above the checks carries.

What it does not check is whether a named module tests the convention it
is named against. Nothing short of reading it can, and the four
assertions below are the ones that fail on the ways a declaration
actually rots: a convention invented here rather than taken from section
7, a module renamed or deleted with the row left behind, a module emptied
of its tests, and a bullet that quietly stops being accounted for by
either half.
"""

import ast
import re
from pathlib import Path

_TESTS = Path(__file__).parent
_README = _TESTS / "README.md"

# section 7's list, in its order and its words: the lead of each bullet,
# which is what the first column of the table repeats. This tuple is the
# standard's rather than this repository's, so a bullet added there is a
# failure here until both this and the table have caught up -- which is
# the point of naming them rather than accepting whatever the table says.
_CONVENTIONS = (
    "the public surface",
    "the copyright header",
    "the documentation",
    "the import graph",
    "the changelog",
    "the build system",
    "the calling convention",
    "input validation",
    "the suite opens no socket",
)

_HEADING = "## Convention tests"
# the sentinel for the other half of the declaration. DOTALL as well as
# MULTILINE because eighty columns wrap the list of names across lines
# and the non-greedy match then stops at the first full stop that ends
# one -- which is why no name in that list may carry a full stop of its
# own. "none" is a legal answer and the one this repository gives, and it
# fits a line; the six btclib-secp256k1 names do not, which is where the
# single-line form was found wanting. The two halves are checked against
# each other below rather than each against nothing
_NOT_TESTED = re.compile(r"^Not tested here: (.+?)\.$", re.MULTILINE | re.DOTALL)
# a table row, and the separator row is what the second group's leading
# backtick excludes: `| --- | --- |` has no backtick to match
_ROW = re.compile(
    r"^\| (?P<convention>[^|]+?) \| `(?P<module>[^`]+)` \|$", re.MULTILINE
)


def _section(text: str) -> str:
    """Return the declaration section, heading to the next one or the end.

    Read rather than the whole file: a `##` heading elsewhere in
    tests/README.md must not contribute rows. The slice ends at the next
    `## ` rather than at the end of the file, so that a section added
    after this one is not read as part of it.
    """
    if text.count(_HEADING) != 1:
        # an empty string rather than an assertion, so that a retitled or
        # duplicated heading fails the test written for it below instead
        # of raising while this module is being imported, where what a
        # reader gets is a collection error naming a line of this file
        return ""
    section = text[text.index(_HEADING) + len(_HEADING) :]
    return _HEADING + section.split("\n## ", 1)[0]


_SECTION = _section(_README.read_text(encoding="utf-8"))
_ROWS = tuple((m["convention"], m["module"]) for m in _ROW.finditer(_SECTION))


def _holds_a_test(path: Path) -> bool:
    """Return whether the module at `path` defines a test function."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return any(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def test_the_test_scan_reports_what_it_is_asked_to(tmp_path: Path) -> None:
    """The scan is exercised directly here, not only through the declared rows.

    `_holds_a_test` answers whether a module defines a function whose
    name begins with `test_`, and it is called once per declared row --
    which need not include one of each kind. Two modules written for it
    here, one of each kind, are what keeps the check below from depending
    on the declaration happening to exercise both branches of the scan.
    """
    holds = tmp_path / "holds.py"
    holds.write_text("def test_something() -> None:\n    pass\n")
    bare = tmp_path / "bare.py"
    bare.write_text("def helper() -> None:\n    pass\n")
    assert _holds_a_test(holds)
    assert not _holds_a_test(bare)


def test_the_section_reader_reports_what_it_is_asked_to() -> None:
    """The reader is exercised here, this tree giving it nothing to say.

    `_section` returns the empty string on a heading that is missing or
    duplicated, and stops at the next `## ` where there is one. On a
    correct `tests/README.md` neither branch is taken, which leaves the
    test below unable to tell a reader that works from one that returns
    whatever it is handed. So it is driven here on text written for it,
    one case per branch.
    """
    assert _section("no heading at all") == ""
    assert _section(f"{_HEADING}\none\n{_HEADING}\ntwo\n") == ""
    assert _section(f"{_HEADING}\nkept\n\n## Later\n\ndropped\n") == (
        f"{_HEADING}\nkept\n"
    )


def test_the_section_was_found() -> None:
    """A declaration that parsed to nothing is the failure that hides.

    Not "the table is not empty": whether the table has no rows or
    several, either is a repository making a statement rather than
    failing to make one. What must not parse to nothing is the section --
    retitled, or moved above another `## ` heading -- because then the
    sentinel below is missing too and the message a reader gets names the
    wrong thing.
    """
    assert _SECTION.strip() not in ("", _HEADING), (
        f"{_README.name} carries no one {_HEADING} section with anything under it"
    )


# the three checks below quantify over the rows rather than being
# parametrized by them, which matters generally: a repository is free to
# declare no rows at all, and a parametrized test over an empty set is
# skipped -- its body never runs, and the coverage gate reads that as a
# line nothing exercises. A comprehension over any number of rows still
# runs its assertion, and the message names every row that failed rather
# than one
def test_every_convention_named_is_one_of_section_sevens() -> None:
    """A convention invented here is not a convention the standard has."""
    unknown = [
        f"{module} against {convention!r}"
        for convention, module in _ROWS
        if convention not in _CONVENTIONS
    ]
    assert not unknown, (
        f"declared against a convention section 7 does not list: "
        f"{'; '.join(unknown)}. Section 7's are: {', '.join(_CONVENTIONS)}"
    )


def test_every_module_named_exists() -> None:
    """A row outliving the file it names is the ordinary way this rots."""
    missing = [
        f"{convention!r} in {module}"
        for convention, module in _ROWS
        if not (_TESTS / module).is_file()
    ]
    assert not missing, (
        f"{_README.name} names a file this directory does not have: "
        f"{'; '.join(missing)}"
    )


def test_every_module_named_holds_a_test() -> None:
    """A file emptied of its tests still satisfies the check above.

    The source is parsed rather than the suite queried: an import would
    make this module's result depend on every other module's import side
    effects, and pytest's own collection is not available to a test it
    has already collected. A row naming a file that is not there is the
    test above's to report, so it is skipped rather than read here.
    """
    empty = [
        f"{convention!r} in {module}"
        for convention, module in _ROWS
        if (_TESTS / module).is_file() and not _holds_a_test(_TESTS / module)
    ]
    assert not empty, (
        f"declared to test something and defining no test_ function: {'; '.join(empty)}"
    )


def test_the_two_halves_account_for_every_convention() -> None:
    """The table and the "Not tested here" line partition section 7's list.

    This is the assertion the declaration exists for. Either half alone
    is satisfiable by saying less: a table naming three conventions is
    true about those three and silent about the other five, and silence
    is exactly what section 7's escape clause makes unreadable. Together
    they have to name each of them once.
    """
    match = _NOT_TESTED.search(_SECTION)
    assert match, (
        f'{_README.name} has no "Not tested here: ...." line;'
        " the declaration is half of one"
    )
    listed = " ".join(match[1].split())
    # whitespace collapsed inside each name and not only around it: the
    # list wraps at eighty columns wherever the column falls, which for a
    # long one is in the middle of a name rather than at a semicolon
    absent = (
        ()
        if listed == "none"
        else tuple(" ".join(s.split()) for s in listed.split(";"))
    )
    tested = {convention for convention, _ in _ROWS}

    overlap = tested.intersection(absent)
    assert not overlap, (
        f"{', '.join(sorted(overlap))} is both declared tested and listed as not tested"
    )

    unknown = [name for name in absent if name not in _CONVENTIONS]
    assert not unknown, (
        f"{', '.join(unknown)} is listed as not tested and is not one of"
        f" section 7's: {', '.join(_CONVENTIONS)}"
    )

    unaccounted = [
        name for name in _CONVENTIONS if name not in tested and name not in absent
    ]
    assert not unaccounted, (
        f"{', '.join(unaccounted)} is neither declared tested nor listed as"
        " not tested; section 7's list is what the two halves must cover"
    )
