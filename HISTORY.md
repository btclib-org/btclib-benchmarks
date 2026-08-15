# Release notes

What a user has to act on, release by release.
The record behind these notes is [CHANGELOG.md][record].

[record]: https://github.com/btclib-org/btclib-benchmarks/blob/main/CHANGELOG.md

## v2026.9 (work in progress, not released yet)

The first release: five benchmarks of
[btclib](https://github.com/btclib-org/btclib) and
[btclib_secp256k1](https://github.com/btclib-org/btclib-secp256k1), one
script to one question. README.md says what each of them measures and
how to run it.

### Running a benchmark does not publish it

A run writes `results/<name>.json` and prints its tables; the page beside
that file is written by `uv run python scripts/render.py`, which reads
the saved run and measures nothing. So the prose around a table is
rewritten and re-published without a machine, and no published number is
ever one somebody typed.

`results/machine.toml` is the one file to edit before measuring here: it
names the machine and says what else was running on it, which nothing in
a process can answer.

### If you ran btclib_secp256k1's own benchmark

`scripts/benchmark.py` was part of that repository up to v0.8.0.1, with
a `bench` dependency group installing what it measured against. Both are
gone from it now, so `uv sync --group bench` there resolves nothing: the
same benchmark is `scripts/libsecp256k1_bindings.py` here, and README.md
has the commands.

Two rows of it are not here, and are not meant to be: it timed btclib's
pure-Python arithmetic beside the bindings, which is
`scripts/pure_python.py`'s question in this repository, asked against
every pure-Python implementation instead of one. The wrapper table is
wrappers only, `electrum-ecc` among them.

### Installing needs autotools, not only pkg-config

`electrum-ecc` is a comparand of `scripts/libsecp256k1_bindings.py` and
ships no wheel: `uv sync` compiles the libsecp256k1 in its sdist, which
runs `autogen.sh`. So `autoconf`, `automake` and `libtool` have to be
present alongside the `pkg-config` and C toolchain the other two
compiling wrappers need. Every runner image this org uses carries all of
them.
