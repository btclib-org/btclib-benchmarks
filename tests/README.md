# Tests

This file exists for section 7 of the [organization standard][std],
which asks each repository to declare which of its conventions the suite
turns into a red test rather than leave it to be read off a directory
listing. `vectors/README.md` is the other file about what the suite
reads, and it is about the vendored vectors rather than about the suite.

## Convention tests

Section 7 lists the conventions a suite can turn into a red test, and
says a repository needs the ones its own prose states rather than all of
them. That escape clause is right and it costs something: an absent
convention test reads exactly like a convention this repository does not
have, and a `grep` over `tests/` cannot tell the two apart.

So which of them this repository tests is **declared here**, and
`conventions_test.py` asserts the declaration is true.

| convention | tested in |
| --- | --- |
| the public surface | `public_surface_test.py` |

Not tested here: the copyright header; the documentation; the import
graph; the changelog; the build system; the calling convention; input
validation.

**The public surface is tested because `src/btclib_benchmarks/` is an
importable package**, and section 7's own escape clause excepts that one
bullet from the rest: a repository publishing an importable package owes
it a test whether its prose states so or not. What the test holds true is
small, because the package is: every submodule it carries is named with a
leading underscore, which the standard's own rule excepts from the
surface, so none of them is a name the root has to re-export, and the
root's own `__all__` is the whole of what the test reads.

The other four package-only conventions in that clause — the
documentation of shipped modules, the import graph, the calling
convention, input validation — remain a choice this repository has not
been asked to make: nothing in its own prose states them, and section 7
forces only the public surface regardless of what the prose says. The
copyright header, the changelog and the build system are conventions
this repository does hold — it has a `LICENSE`, a `CHANGELOG.md` and a
declared build backend — and nothing checks any of those three either.

What the suite does check is a different set, and section 7 does not list
them because they belong to this repository alone: that every benchmark
imports without timing anything (`scripts_import_test.py`), that every
measured package answers the vendored vectors before its numbers are
believed (`vectors_test.py`, `round_trip_test.py`), that the provenance
report each benchmark prints is true (`provenance_test.py`), and that a
row claiming a pure-Python path has one (`pure_python_path_test.py`).
Section 7's closing rule is what those are: a convention worth stating is
worth a test.

[std]: https://github.com/btclib-org/.github/blob/main/README.md
