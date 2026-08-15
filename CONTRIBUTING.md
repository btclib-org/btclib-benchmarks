# Contributing

## The environment

uv is the only thing that has to be installed; it fetches interpreters,
linters and packaging tools itself.

```shell
uv sync --locked
```

That installs the comparands, which is most of the work: `coincurve`,
`secp256k1` and `electrum-ecc` each compile a libsecp256k1 of their own,
so a C toolchain has to be present — `pkg-config` for the first two, and
`autoconf`, `automake` and `libtool` for the third, which ships as an
sdist and runs libsecp256k1's `autogen.sh`. `secp256k1lab` comes from a
git tag, having no release on any index.

## Running a benchmark

```shell
uv run python scripts/bitcoin_libraries.py
```

Each script prints what it is about to measure — every package's version
and where it was imported from — before any number. Read that header:
a table without it cannot be checked.

To measure a working tree instead of the published release:

```shell
uv run --with-editable /path/to/btclib python scripts/bitcoin_libraries.py
```

The header then says `editable: /path/to/btclib` where it otherwise says
`released`, which is the point of printing it.

## Publishing a run, which is a second command

A run writes `results/<name>.json` as it finishes: every number, the
packages block, and what the run block states — the clock, the
interpreter, the machine, the method. Nothing about the page is decided
there.

```shell
uv run python scripts/render.py            # every page, from its saved run
uv run python scripts/render.py key-reuse  # one of them
uv run python scripts/render.py --check    # name what is stale, write none
```

`render.py` puts the three blocks into the page between the markers it
carries, and touches nothing else in it. So the prose around the numbers
— the headings, the paragraph explaining a column, the analysis — is
edited and re-published without measuring again, which is the whole
reason the two are separate: a reworded heading used to mean either a
fresh run, whose numbers are different, or a hand-edited block, whose
numbers are nobody's.

It reads the saved run and imports no benchmark. That matters more than
it sounds: importing one derives keys, signs a message per comparand and
runs every cross-comparand assertion before it will answer anything.

The two lines no process can answer are in `results/machine.toml` —
which machine, and what else was running on it. Edit that file when
either stops being true; every run taken afterwards carries the new
answer, and runs already saved keep the one they were taken under.

`--check` says whether a page still matches the run it publishes. It is
not wired into CI, and deliberately: a page is written by a command a
person runs, not by a gate.

## The gates

```shell
uv run pytest                      # the suite, gated at 100% coverage
uv run pre-commit run --all-files  # every lint hook, which is what CI runs
```

A fixture that is a key or a signature trips detect-secrets, correctly: it
cannot tell a private key published in a BIP from a credential. Record the
finding as reviewed rather than excluding the file, which would make it
blind for good, and stage the result — the hook refuses an unstaged
baseline:

```shell
uvx detect-secrets@1.5.0 scan --baseline .secrets.baseline
git add .secrets.baseline
```

`.pre-commit-config.yaml` **is** the lint gate: `lint.yml` runs that file
and nothing else, so a commit and CI enforce the same list. Never add a
second copy of the same tools to a workflow.

Check exit codes rather than filtered output — `pre-commit run | grep -v
Passed` hides a failure.

## What the suite can and cannot check

It cannot check a measurement. A timing is a property of the machine, not
of the code, so no test here asserts one, and **no workflow runs a
benchmark**: a shared CI runner disagrees with a laptop by more than most
of the differences being reported.

What it does check is what survives being automated:

- that every measured package answers the vendored vectors, in the
  configuration it is measured in. `tests/vectors_test.py` runs BIP340's
  own vectors and BIP32's against every implementation this project times,
  btclib included — redundant with btclib's own suite, deliberately, it
  being the one package these tables exist to publish. The negative cases
  are the point: an implementation that accepts a public key off the curve
  or an s past the order passes a round-trip check and fails this one. The
  pure-Python configuration is a subprocess, `PYCOIN_NATIVE` being read at
  import and btclib's dispatch flag being unrestorable.
- that each row of `btclib_two_paths.py` has a second path at all.
  `tests/pure_python_path_test.py` blocks every bindings entry point and
  calls every operation: a row that has kept a foot in C raises instead of
  answering. BIP32 derivation was such a row.
- that every script *loads*, which runs the fixtures at its top and the
  assertions comparing each comparand's answer against btclib's. A table
  whose rows compute different things is worth nothing, and importing the
  module is what catches it.
- that loading one times nothing. Every script keeps its timing behind
  `main()`; before that guard existed, importing any of them ran every
  loop in it, which is why none could be tested at all.

## Writing a row

- **assert where the fixtures are built, never inside a timing.** A timed
  function calls one API and discards what it returns: a comparison in the
  loop is time attributed to a comparand that did not spend it, and a row
  that checks itself is measuring the check. The assertions live at module
  level, where each comparand's answer is checked against btclib's — or,
  where btclib is not a row, against the package the script is about — so
  one that is merely fast and wrong cannot win a row, and the suite
  importing the module is what runs them.

  Correctness itself belongs to the suite rather than to any of this.
  `tests/vectors_test.py` runs the vendored vectors against every
  implementation these scripts time, in the configuration each is timed
  in, including the negative cases no benchmark row can express.
- **take the input from a published test vector.** The fixtures are
  BIP340's first vector and BIP32's first, transcribed from btclib's
  vendored copies — the values, not the files, each row timing one input.
  The timings do not turn on it: a valid key measures like any other valid
  key, which was checked. The assertions do. Checked against btclib, a
  comparand can only disagree with btclib; checked against what the
  specification publishes, both can be wrong and still fail, which is the
  failure worth being able to have. Where no vector fixes the answer —
  ECDSA's nonce is btclib's own RFC6979 — the cross-comparand check is
  what there is, and that is worth writing down beside the row.

  A made-up key is not merely weaker, it can be actively wrong, and the
  key this project signed with for a while — 1 — was wrong in two ways.
  Deriving a public key from it costs a pure-Python implementation one
  ladder step rather than a full-width scalar's worth. And its public key
  *is* the generator: python-ecdsa hands back the generator object itself,
  precomputed table and all, so every row verifying against that key
  verified with a table no real key gets, and measured about half what it
  should. That row was published before anybody noticed. A key nobody chose
  cannot flatter a row on purpose, which is the whole argument.
- **say which backend actually ran.** `pycoin`, `buidl` and
  `python-bitcoinlib` each reach for a C library at import if they find
  one, and quietly fall back to Python if they do not. A row that does
  not name what it resolved to is not a measurement of anything in
  particular.
- **two rows where a library grinds, and none where grinding says
  nothing.** btclib and embit grind for a low-r signature by default, and
  `electrum-ecc` offers it; each gets a `grind=False` row, which is the one
  comparable with libraries that sign once, and a row of its default beside
  it. `btclib_two_paths.py` has no grinding row at all, and that is the same
  rule: grinding multiplies both of its paths by the same number of
  attempts, so the ratio it prints does not move, and two rows saying what
  one pair already says are two rows to read.
- **loop counts are per row** wherever a table mixes Python with C: the
  two differ by orders of magnitude, and one shared count either takes
  minutes or measures the clock's own resolution. A table whose rows are
  all C can share one count, and `libsecp256k1_wrappers.py` does. Where
  the counts differ they print beside their rows, sorting putting rows
  three orders of magnitude apart next to each other. A row whose backend
  the script does not decide carries a count *per backend* and picks
  between them at run time, as `pycoin_calls` does in
  `bitcoin_libraries.py`: one written count is either too small to measure
  the C or minutes long against the Python, and which one a machine gets
  is not this project's to choose.
- **sort on the measurement, and divide by the fastest row**, never by
  btclib's: a column against btclib prints fractions under one for
  everything quicker, which is btclib's score rather than the table's
  answer. `btclib_two_paths.py` divides each row by the quicker of its own
  *pair* instead, its rows being one operation through two arithmetics.

  An order written by hand is an opinion about the result, and a reader
  dividing two numbers to get the ratio is doing arithmetic the table
  should have done. It follows that a row cannot print as it is timed:
  every number has to be in hand before the first line, which is why each
  script's `benchmark` returns rather than prints.
- **never state a number in prose.** Not in a comment, not in a
  docstring, not in the README. The tables are produced by running the
  scripts; a figure written down anywhere else is a claim nothing
  re-derives, and it will be wrong by the next release of something.

## Documentation and comments

The house style of btclib-org, in one line: a comment says *why*, never
*how it got here*. Present-tense reasoning, including the negative
results — what was tried, what it measured, why it was not taken — is
what makes a file reviewable. History belongs in CHANGELOG.md.

Markdown wraps at 80 columns, tables included; a line holding nothing but
an unbreakable URL is exempt.

## Pull requests

`main` is the only branch, and everything lands through a pull request.
Run the two gates locally first: CI runs exactly them, so a red run there
is a local run that was not done.

CHANGELOG.md gets an entry for anything a reader would notice.
HISTORY.md moves only for something a user has to *act* on.
