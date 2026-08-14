# Release notes

What a user has to act on, release by release.
[CHANGELOG.md](./CHANGELOG.md) is the record behind these notes.

## v2026.9 (work in progress, not released yet)

The first release: the benchmarks of
[btclib](https://github.com/btclib-org/btclib) and
[btclib_secp256k1](https://github.com/btclib-org/btclib-secp256k1),
which used to live in a `bench` dependency group inside each of those
repositories, are here instead.

### If you ran them from btclib or btclib_secp256k1

The scripts are gone from both, and `uv sync --group bench` no longer
resolves anything. Clone this repository and run them here; README.md
has the commands.

They are also renamed, one script to one question:

From btclib:

- `scripts/benchmark.py` → `scripts/btclib_two_paths.py`
- `scripts/benchmark_libraries.py` → `scripts/bitcoin_libraries.py`
- `scripts/benchmark_python.py` → `scripts/pure_python.py`

From btclib_secp256k1:

- `scripts/benchmark.py` → `scripts/libsecp256k1_wrappers.py`
