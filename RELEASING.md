# Releasing

There is no release. Nothing here is published to an index, and
`[tool.setuptools] packages = []` means an install would put nothing on
the path anyway: the scripts are run from a checkout.

What `project.version` is for, then, is the CHANGELOG heading — a
released *state of the benchmarks*, so that a table someone kept can be
placed against the versions that produced it.

## Cutting one

```shell
uv run pytest
uv run pre-commit run --all-files
git tag -s v<version> -m "v<version>"
git push origin v<version>
```

Signed, as every tag in this org is.

`gh release create` with HISTORY.md's section as the notes, if the
release is worth a page; there is no workflow that does it, because
there is no artifact for one to build.

## Before a release, run every benchmark

The suite proves the scripts load and that their comparands agree. It
cannot prove they still *measure* anything, and that is exactly what
rots: a comparand renames a method, a backend stops being found, an
implementation gets a fast path. Running all four by hand is the only
check there is, and a release is the moment to do it.

```shell
uv run python scripts/02-btclib-vs-btclib.py
uv run python scripts/03-libraries.py
uv run python scripts/04-pure-python.py
uv run python scripts/01-libsecp256k1.py
```

Read each header before its numbers: the versions, and where each
package came from. A row whose backend has silently changed is a
number that means something other than what its label says.

## The one entry with a date on it

`[tool.uv.sources]` resolves `btclib` from `main` rather than from PyPI,
because these scripts reach into a dispatch that is private and moves
between releases. `project.dependencies` already floors it at the
version that will carry those names.

Delete that entry the day the release lands, re-lock, run the six
benchmarks again and render their pages — that is the whole of the
change, and the run is what says the published wheel really does carry
what main did.
