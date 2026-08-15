# btclib-benchmarks

Timings of [btclib](https://github.com/btclib-org/btclib) and
[btclib-secp256k1](https://github.com/btclib-org/btclib-secp256k1)
against the packages they are usefully compared with.

Five benchmarks, each answering a different question:

- **`btclib_two_paths.py`** — btclib against btclib: its pure-Python
  arithmetic against the libsecp256k1 that `btclib-secp256k1` bundles and
  compiles into a cffi extension
- **`bitcoin_libraries.py`** — btclib as installed, against other Python
  bitcoin libraries, over curve operations and the address encodings
- **`pure_python.py`** — every pure-Python implementation of the same
  operation, against each other
- **`libsecp256k1_bindings.py`** — btclib-secp256k1 against the other
  wrappers of the same C library: `coincurve` and `secp256k1-py` through
  cffi, `electrum-ecc` through ctypes
- **`key_reuse.py`** — what the second signature under the same key
  costs: the other four time one verification with a fresh key, and a
  verifier never does

## Why this is its own repository

The comparands are third-party packages: `ecdsa`, `pycoin`, `buidl`,
`embit`, `python-bitcoinlib`, `coincurve`, `secp256k1`, `electrum-ecc`.
Measured from inside btclib or btclib-secp256k1 they would be resolved
into the lock of a library that never imports them — so a vulnerability
reported against a comparand would be reported against btclib, and a
reader of that alert would have to work out that the package was a
benchmark row rather than a dependency.

Here the relationship is the right way round. The comparands are what
this project is *for*, so an advisory against one names the package it is
actually about, and btclib's own lock carries nothing it does not use.

## Running them

Nothing is installed: the scripts are run from a checkout.

```shell
uv sync --locked
uv run python scripts/bitcoin_libraries.py
```

Each prints what it resolved — package versions, and which arithmetic
backend each comparand actually ran — before any number, because a timing
means nothing without them.

A run also writes itself to `results/<name>.json`, and
`scripts/render.py` is what turns that into the published page. Two
commands rather than one, for the reason under "One run of each,
published" below.

### The interpreter is 3.13, not 3.14

`coincurve` and `secp256k1` publish wheels up to `cp313` and no further,
and neither builds from source without `pkg-config` and a C toolchain. A
benchmark that cannot install its comparands measures nothing, so
`.python-version` pins 3.13 where the rest of this org pins 3.14.

Raise the pin when both publish a `cp314` wheel. Neither of the other two
wrappers holds any part of it: `btclib-secp256k1` publishes past `cp313`
already, and `electrum-ecc` has no wheel on PyPI at all — it compiles at
install time, and what it builds is tagged `py3-none`, the C being
reached through ctypes rather than linked into an extension.

The `requires-python` floor is 3.11, and that end is set by a comparand
too: `secp256k1lab` declares it, and `scripts/pure_python.py` imports it
unguarded.

### Installing the comparands needs a build toolchain

Three of them compile a libsecp256k1 of their own: `coincurve` and
`secp256k1` want `pkg-config`, and `electrum-ecc`, shipped as an sdist
carrying libsecp256k1 as a submodule, runs its `autogen.sh` — so
`autoconf`, `automake` and `libtool` have to be there as well. That cost
is what makes the wrapper rows honest: each times the build that
`pip install` produced, not whatever system library happened to be
findable.

### Measuring a working tree instead of a release

The default is deliberate: every comparand is timed at its **published
release**, btclib and btclib-secp256k1 included, because `pip install` is
what an end user gets and that is the only performance an end user has.

To time a checkout instead — an unreleased optimization, say — install it
over the top:

```shell
uv run --with-editable /path/to/btclib python scripts/bitcoin_libraries.py
```

The packages block names the version, and where an install is not the
declared one it names that too — `editable: /path/to/btclib` for the
command above, `sys.path:` for a checkout shadowing an install. So which
of the two you measured is on the screen rather than assumed, and that is
not decoration: an editable install and a released wheel of the same
package resolve silently, and the wrong one produces a plausible table.

## Reading the output

The numbers are an order of magnitude, never a figure to quote. Nothing
here repeats a measurement, discards an outlier, or controls the machine
it runs on: a shared CI runner and a laptop with a browser open disagree
by more than most of the differences being reported.

No workflow runs these. CI lints and type-checks; measuring is something
a person does, on a machine whose state they know.

### The same C library is not the same binary

`libsecp256k1_bindings.py` compares four packages that all wrap
`bitcoin-core/secp256k1`, which is true of the API and not of what is
linked: each vendors a revision of its own, and they are not the same
revision. So that script prints, per row, which one is underneath it and
how the row reaches it. Read that beside the timings — a build against a
stale one is not the comparison the table looks like, and where
`btclib-secp256k1` is the one lagging, the output is where it says so.

## One run of each, published

`results/` carries what the five scripts printed in one sitting on one
machine, each file keeping the header its script printed above the
numbers — the versions, where each package came from, and the backend
every comparand resolved to — because that header is what makes a table
checkable at all. Every table is sorted fastest row first and carries a
ratio against its fastest row, never against btclib's:

- [btclib's two paths][two-paths]
- [btclib against the other bitcoin libraries][libraries]
- [every pure-Python implementation][pure]
- [the libsecp256k1 bindings][bindings]
- [one key, every signature under it][reuse]

The machine is named in each file, and so is what else was running on it.
They are a record of one run, not a claim about anyone else's hardware:
what makes them worth publishing is that they are reproducible by one
command, not that they are authoritative.

Beside each page is the run it publishes, `results/<name>.json`: the
numbers as they were measured, and everything the page states about how.
A benchmark writes it, `scripts/render.py` writes the page from it, and
the two are separate commands on purpose — the prose around a table gets
rewritten far more often than a machine gets measured, and it must not
cost a fresh run or a hand-edited number to do it. `CONTRIBUTING.md` has
both commands.

[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/btclib-two-paths.md
[libraries]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/bitcoin-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/pure-python.md
[bindings]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/libsecp256k1-bindings.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/key-reuse.md

## Licence

MIT, as every btclib-org repository is.
