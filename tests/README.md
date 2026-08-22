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

Not tested here: the public surface; the copyright header; the
documentation; the import graph; the changelog; the build system; the
calling convention; input validation.

**The table is empty, and that is the answer rather than an omission.**
This repository ships no importable package: what it publishes is the
benchmarks under `scripts/` and the results they produce under
`results/`. Five of the conventions are properties of a package — the
public surface, the documentation of shipped modules, the import graph,
the calling convention, input validation — and there is no package for
them to be properties of.

The other three could be tested here and are not. The copyright header,
the changelog and the build system are conventions this repository does
hold: it has a `LICENSE`, a `CHANGELOG.md` and a declared build backend.
Nothing checks any of them.

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
