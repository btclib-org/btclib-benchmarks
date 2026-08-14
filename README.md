# btclib-benchmarks

Timings of [btclib](https://github.com/btclib-org/btclib) and
[btclib_secp256k1](https://github.com/btclib-org/btclib-secp256k1)
against the packages they are usefully compared with.

Four benchmarks, each answering a different question:

- **`btclib_two_paths.py`** — btclib's bindings path against its own
  pure-Python arithmetic
- **`bitcoin_libraries.py`** — btclib, bindings enabled, against other
  Python bitcoin libraries
- **`pure_python.py`** — every pure-Python implementation of the same
  operation, with the bindings as the reference line
- **`libsecp256k1_wrappers.py`** — btclib_secp256k1 against the other
  wrappers of the same C library

## Why this is its own repository

The comparands are third-party packages: `ecdsa`, `pycoin`, `buidl`,
`embit`, `python-bitcoinlib`, `coincurve`, `secp256k1`. Measured from
inside btclib or btclib_secp256k1 they would be resolved into the lock of
a library that never imports them — so a vulnerability reported against a
comparand would be reported against btclib, and a reader of that alert
would have to work out that the package was a benchmark row rather than a
dependency.

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

### The interpreter is 3.13, not 3.14

`coincurve` and `secp256k1` publish wheels up to `cp313` and no further,
and neither builds from source without `pkg-config` and a C toolchain. A
benchmark that cannot install its comparands measures nothing, so
`.python-version` pins 3.13 where the rest of this org pins 3.14. The
`requires-python` floor stays at 3.10, which is what the scripts
themselves need.

Raise the pin when both publish a `cp314` wheel.

### Measuring a working tree instead of a release

The default is deliberate: every comparand is timed at its **published
release**, btclib and btclib_secp256k1 included, because `pip install` is
what an end user gets and that is the only performance an end user has.

To time a checkout instead — an unreleased optimization, say — install it
over the top:

```shell
uv run --with-editable /path/to/btclib python scripts/bitcoin_libraries.py
```

The scripts print `btclib.__file__` in their setup block, so which of the
two you measured is on the screen rather than assumed. That check is not
decoration: an editable install and a released wheel of the same package
resolve silently, and the wrong one produces a plausible table.

## Reading the output

The numbers are an order of magnitude, never a figure to quote. Nothing
here repeats a measurement, discards an outlier, or controls the machine
it runs on: a shared CI runner and a laptop with a browser open disagree
by more than most of the differences being reported.

No workflow runs these. CI lints and type-checks; measuring is something
a person does, on a machine whose state they know.

## Licence

MIT, as every btclib-org repository is.
