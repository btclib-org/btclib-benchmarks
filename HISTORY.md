# Release notes

What a user has to act on, release by release.
The record behind these notes is [CHANGELOG.md][record].

[record]: https://github.com/btclib-org/btclib-benchmarks/blob/main/CHANGELOG.md

## v2026.9 (work in progress, not released yet)

The first release: four benchmarks of
[btclib](https://github.com/btclib-org/btclib) and
[btclib_secp256k1](https://github.com/btclib-org/btclib-secp256k1), one
script to one question. README.md says what each of them measures and
how to run it.

### If you ran btclib_secp256k1's own benchmark

`scripts/benchmark.py` was part of that repository up to v0.8.0.1, with
a `bench` dependency group installing what it measured against. Both are
gone from it now, so `uv sync --group bench` there resolves nothing: the
same benchmark is `scripts/libsecp256k1_wrappers.py` here, and README.md
has the commands.

Two rows of it are not here, and are not meant to be: it timed btclib's
pure-Python arithmetic beside the bindings, which is
`scripts/pure_python.py`'s question in this repository, asked against
every pure-Python implementation instead of one. The wrapper table is
wrappers only, `electrum-ecc` among them.

### Installing needs autotools, not only pkg-config

`electrum-ecc` is a comparand of `scripts/libsecp256k1_wrappers.py` and
ships no wheel: `uv sync` compiles the libsecp256k1 in its sdist, which
runs `autogen.sh`. So `autoconf`, `automake` and `libtool` have to be
present alongside the `pkg-config` and C toolchain the other two
compiling wrappers need. Every runner image this org uses carries all of
them.
