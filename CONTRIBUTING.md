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

btclib and btclib-secp256k1 resolve from their `main` branches until the
releases these scripts are written against are on PyPI, and **a branch in
`uv.lock` is a commit, not a branch**: `uv sync --locked` reinstalls the
revision the lock names and never looks at what `main` has become. So a
measurement taken without asking for the upgrade is a measurement of
whatever was current the day the lock was last written, which is not what a
page about `main` claims. Ask for it first, every time:

```shell
uv lock --upgrade-package btclib --upgrade-package btclib-secp256k1
uv sync --locked
```

This is not pedantry about freshness. Read the wrong way round it has
already cost a session: btclib's lock was stale while the wrapper's was
current, the two commits did not fit together, and the mismatch read
convincingly as an upstream breakage that did not exist.

Then the benchmark itself:

```shell
uv run python scripts/03-libraries.py
```

Each script prints what it is about to measure — every package's version
and where it was imported from — before any number. Read that header:
a table without it cannot be checked.

**One script at a time, and not in a loop over the five.** Each run
saturates the machine for minutes, and the next one started immediately
after measures a hot machine rather than the operation: measured that way,
the pure-Python columns of `02-btclib-vs-btclib.py` came out up to three
times their real cost, and a verification through the C library came out
at twice. The dispersion column beside a row is what shows it, and which
statistic it is belongs to the page: `03-libraries.py` saves `spread`, the
slowest round less the quickest, so a wide one is a round that caught an
interruption; `01-libsecp256k1.py` saves `halves_apart`, how far the minima
of the halves of a row's rounds sat apart, so a wide one is a row whose own
estimate moved while it was being measured. Each page defines the column it
prints, in the prose beside its tables. Read it before believing an
ordering — and note that neither can see the machine drifting between one
run and the next, which is why the machine is given time to cool between
scripts rather than watched for it afterwards.

To measure a working tree instead of the published release:

```shell
uv run --with-editable /path/to/btclib python scripts/03-libraries.py
```

The header then says `editable: /path/to/btclib` where it otherwise says
`released`, which is the point of printing it.

## Publishing a run, which is a second command

A run writes `results/<name>.json` as it finishes: every number, the
packages block, and what the run block states — the clock, the
interpreter, the machine, the method. Nothing about the page is decided
there.

```shell
uv run python scripts/render.py               # every page, from its run
uv run python scripts/render.py 05-key-reuse  # one of them
uv run python scripts/render.py --check       # name what is stale, write none
```

`render.py` puts the three blocks into the page between the markers it
carries, and touches nothing else in it. So the prose around the numbers
— the headings, the paragraph explaining a column, the analysis — is
edited and re-published without measuring again, which is the whole
reason the two are separate: a reworded heading otherwise costs either a
fresh run, whose numbers are different, or a hand-edited block, whose
numbers are nobody's.

It reads the saved run and imports no benchmark. That matters more than
it sounds: importing one derives keys, signs a message per comparand and
runs every cross-comparand assertion before it will answer anything.

## Which artifact an install resolved to, which is a third command

```shell
uv run python scripts/artifacts.py    # one line per comparand
```

A page's provenance block says what version was measured and whether it
came from an index or a branch. What no version can say is which of an
index's two artifacts answered, and for a comparand that vendors
libsecp256k1 the wheel and the sdist of one version need not carry the
same library — so this prints the tags of the wheel each install came
from, a bare `linux_*` one being a tag no index serves and therefore a
build made where it is installed.

CI runs it before the suite, on every cell, which is where it earns its
place: `uv.lock` carries no aarch64 wheel for one comparand, so three of
the six jobs assert the pages' claims against a library compiled on the
runner. It records and asserts nothing — an index gaining a wheel changes
every line it prints and breaks nothing.

`results/machine.toml` overrides the one line a run may get wrong, which
machine it was taken on. Edit it when that stops being true; every run
taken afterwards carries the new answer, and runs already saved keep the
one they were taken under.

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
  vectors, BIP32's, Wycheproof's ECDSA file and Core's base58 pairs
  against every implementation this project times,
  btclib included — redundant with btclib's own suite, deliberately, it
  being the one package these tables exist to publish. The negative cases
  are the point: an implementation that accepts a public key off the curve
  or an s past the order passes a round-trip check and fails this one. The
  pure-Python configuration is a subprocess, `PYCOIN_NATIVE` being read at
  import and btclib's dispatch flag being unrestorable.

  Where a package answers a case differently, the answer is recorded as an
  expected failure with the reason beside it, never excluded. `xfail_strict`
  is on, so a release that fixes one fails the suite instead of passing
  quietly — which is the only way a recorded defect stays current.
- that each row of `02-btclib-vs-btclib.py` has a second path at all.
  `tests/pure_python_path_test.py` blocks every libsecp256k1 entry point and
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
  it. `02-btclib-vs-btclib.py` has no grinding row at all, and that is the same
  rule: grinding multiplies both of its paths by the same number of
  attempts, so the ratio it prints does not move, and two rows saying what
  one pair already says are two rows to read.
- **loop counts are per row** wherever a table mixes Python with C: the
  two differ by orders of magnitude, and one shared count either takes
  minutes or measures the clock's own resolution. A table whose rows are
  all C can share one count, and `01-libsecp256k1.py` does. Where
  the counts differ they print beside their rows, sorting putting rows
  three orders of magnitude apart next to each other. A row whose backend
  the script does not decide carries a count *per backend* and picks
  between them at run time, as `pycoin_calls` does in
  `03-libraries.py`: one written count is either too small to measure
  the C or minutes long against the Python, and which one a machine gets
  is not this project's to choose.
- **sort on the measurement, and divide by the fastest row**, never by
  btclib's: a column against btclib prints fractions under one for
  everything quicker, which is btclib's score rather than the table's
  answer. `02-btclib-vs-btclib.py` divides each row by the quicker of its own
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

An issue is referred to as `ISS 123` and a pull request as `PR 45`, the
token itself being a link to it, and disambiguated by `owner/repo` as soon
as a second repository is in play. A bare `#123` resolves only inside the
repository it was written in, and in anything read outside the forge it
resolves to nothing. Where several are in flight the topic goes in beside
the number, a list of bare numbers being what gets confused.

One exemption, and it is mechanical: a pull request's closing keyword is
read by the forge rather than by a person, so it takes the forge's own
reference — `Closes #64` — which is what every body here carries. Where a
page written earlier still spells a reference
the other way, this paragraph is what is current and the page is what has
not caught up.

## Pull requests

`main` is the only branch, and everything lands through a pull request.
Run the two gates locally first: CI runs exactly them, so a red run there
is a local run that was not done.

CHANGELOG.md gets an entry for anything a reader would notice.
HISTORY.md moves only for something a user has to *act* on.

### One subject, opened as soon as it is written

A pull request answers one question. Issues that share a subject are one
pull request, closing each of them; issues that do not are one pull
request each, however small either of them is.

It is opened the moment it is written and verified — not held for the
previous one to be reviewed or to land, and not batched with the next. A
batch arrives as one reviewing job with several subjects, which is the
shape that costs the most to read; a finished pull request held back is
review that could have started and did not. Both have been done here, and
the second was an over-correction of the first.

Working this way stacks branches, which is fine and costs one rule: a
child whose base was amended is moved with the old base named,

```shell
git rebase --onto <new-base> <old-base-sha> <child>
```

because a plain rebase replays the base's old commit inside the child, and
the forge then shows the base's old text as additions with nothing red
anywhere — the suite passes in both worlds. Read the child's diff
afterwards rather than trusting the rebase, and retarget each child onto
`main` as its parent lands.

### The review

A review is given promptly and on local evidence. It does not wait for CI,
does not report a check as a finding, and does not discuss a run at all:
whether CI is green is the author's business, once, at landing time.

The exchange is anchored to a sha rather than to a branch, a branch being
free to move under a review:

- the author hands off by naming the sha pushed and the evidence run
  against it, then leaves that head alone;
- the reviewer answers with findings — where, what is wrong, how they know
  it, and whether each is blocking — and exactly one verdict: changes
  requested, or an ack naming that sha;
- the author accepts what is reasonable, declines the rest with a reason
  in the thread, and pushes the answer without waiting for CI;
- the reviewer resolves the threads they opened, that being what says a
  finding is closed, and re-reviews the delta rather than the branch.

An ack is formal, and it is what ends the loop: nothing else does, and the
author does not supply their own. A disagreement that survives a second
exchange goes to the maintainer instead of into a third round.

A finding that lies beside the subject becomes an issue rather than a
commit in the diff, and rather than a comment the author cannot act on: a
diff answering two questions cannot be accepted for either. Name the issue
where it came up, so nothing reads as dropped. What does not qualify is
anything the diff itself introduces, breaks or leaves half-done.

### Landing it

CI is read once, and this is where. Rebase onto `main`'s tip, push that
head so the checks run on the tree that will land, and only then wait for
them: checks read before a rebase describe a tree nobody is landing. A
rebase that moved nothing but the base leaves the ack standing; one that
resolved a conflict does not, that resolution being a change no reviewer
has seen.

Then a local squash fast-forwarded onto `main`, never a button on the
forge, which would sign the commit with the forge's own key; the signature
verified afterwards; the branch deleted, the fast-forward not being a merge
the forge cleans up after; and every checkout sitting on `main` brought up
to date, that being where the next session starts from and a stale one
being where a branch gets built on a base that has moved. `REPOSITORY.md`
carries the procedure in full, and why the branch protections permit it.
