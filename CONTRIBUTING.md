# Contributing

What this repository holds in common with the others of the organization
— the toolchain, the lint gate, the tool tables behind it, the workflow
set and the branch rules — is stated once in the
[btclib-org repository standard](https://github.com/btclib-org/.github),
each rule with the alternative it was decided against. It binds this
repository, so a change departing from it is a divergence, and one filed
as an issue in that repository rather than here: a difference between two
repositories belongs to neither of them.

**This file is the same in every repository of the organization up to
its last section.** What is true of one tree only — the commands that
build its environment, the gates it runs, which of its workflows decide
a merge — is under that heading, and the comparison stops there.

## The issue tracker

Where an issue is filed, and what an alignment finding has to name, is
[the standard's *What this repository is*][s-what]: an issue spanning
repositories, or whose subject is the standard, goes to
[btclib-org/.github](https://github.com/btclib-org/.github/issues), and
one about this tree alone stays here.

A finding noticed while doing something else is filed, not carried.
`REVIEWING.md`'s *Every collateral finding becomes an issue* is the whole
of what to do with one, and it applies to an author as much as to a
reviewer: a pull request answering two questions cannot be accepted for
either.

## Documentation and comments

[Section 9 of the standard][s9] is the prose style, and it governs the
prose this tree ships — comments, docstrings and markdown. It is not
restated here: a second wording is the one that goes stale, which is
that section's own *One fact in one place*.

A commit message is prose this tree ships too, though section 9 does not
say so: [the only merge method the rule accepts][s11] puts it on `main`
as the landing commit's body, so what is written in one is read there
long after the branch is gone.

## Pull requests

What `main` accepts, and what it refuses to everyone, is [section 11 of
the standard][s11]. Run the gates locally before opening anything —
the last section of this file says which they are — because CI runs
exactly them, so a red run there is a local run that was not done.

What a pull request's title and description have to say about the issues
it closes, and why a manual link in the Development panel is a trap
neither of them shows, is [the standard's *What a pull request says it
is*][s-title]. Read it before opening one; it is the rule most often
found broken after the fact.

**Before it is opened, the branch's own commit subjects and bodies are
read against that same rule.** The description does not exist yet to
disagree with them, and [the standard][s-title] has the command that
scans the branch's own commit text for a verb in front of a reference.

**The two spellings are named here as well as there, against [section 9's
*One fact in one place*][s9]**, the paragraph above naming the section
and not the forms, which are the half a citation is got wrong in:
`(closes #N)` cites an issue the change closes, wherever the citation
sits — the title, the commit subject where [*Merge method*][s11] makes
that the thing that lands, and a `CHANGELOG.md` entry — and `(issue #N)`
cites, in those same places, an issue the change advances and does *not*
close. One token holds one meaning whichever file it sits in, so the
pair is chosen by what is true of the change rather than by which file
is being written, and a tree's own landed subjects are not what to copy
it from: nothing already landed is rewritten, so what a repository wrote
before the rule stays where it is.

`REVIEWING.md` is the standard a review is written against, and is this
file's other half. Read before opening a pull request, it is what the
pull request will be answered against.

`CHANGELOG.md` gets an entry for anything a reader would notice, and the
release notes move only for something a user has to *act* on, in the
repositories that publish.

### One subject, opened as soon as it is written

A pull request answers one question. Issues that share a subject are one
pull request, closing each of them; issues that do not are one pull
request each, however small either of them is.

It is opened the moment it is written and verified — not held for the
previous one to be reviewed or to land, and not batched with the next. A
batch arrives as one reviewing job with several subjects, which is the
shape that costs the most to read; a finished pull request held back is
review that could have started and did not.

Working this way stacks branches, which is fine and costs one rule: a
child whose base was amended is moved with the old base named,

```shell
git rebase --onto <new-base> <old-base-sha> <child>
```

because a plain rebase replays the base's old commit inside the child,
and the forge then shows the base's old text as additions with nothing
red anywhere. Read the child's diff afterwards rather than trusting the
rebase, and retarget each child onto `main` as its parent lands.

### The landing queue

Where more than one pull request is open against this repository, only
one is carried to `main` at a time: rebased onto the tip, reviewed on
that head, and landed, while every other one waits, untouched, for its
turn. This governs which of several *already open* pull requests reaches
`main` next; *One subject, opened as soon as it is written* above governs
the moment before that, when a finished one is opened — the two do not
conflict, since a pull request is still opened without delay and still
waits its turn once several are open.

The reason is CI throughput, not the ack a waiting pull request keeps —
`REVIEWING.md`'s *The verdict* states what an ack belongs to, and
*Landing it* below states which rebase voids one. Every rebase queues
this repository's whole check matrix against the organization's ceiling
on concurrent jobs, so rebasing every waiting pull request after each
landing spends that capacity on runs the next landing invalidates
anyway, and delays the one pull request that is actually next: work
spent on a pull request that is not next is work that delays the one
that is. The ceiling's figure is `REPOSITORY.md`'s, under *Plan-gated
settings*, beside the command that re-derives it.

Order is cheapest and least contended first, most invasive last, so that
a large change does not sit at the head blocking everything behind it.

The maintainer may declare a bounded exception — several pull requests in
flight against one repository, for a named piece of work — trading the
cost above for throughput; it is recorded as a comment in
[btclib-org/.github](https://github.com/btclib-org/.github/issues), by
*The issue tracker* above, and holds only for the work it names.

### The review

A review is given promptly and on local evidence. It does not wait for
CI, does not report a check as a finding, and does not discuss a run at
all: whether CI is green is the author's business, once, at landing time.

The exchange is anchored to a sha rather than to a branch, a branch being
free to move under a review:

- the author hands off by naming the sha pushed and the evidence run
  against it, then leaves that head alone;
- the reviewer answers with findings — where, what is wrong, how they
  know it, and whether each is blocking;
- the author accepts what is reasonable, declines the rest with a reason
  in the thread, and pushes the answer without waiting for CI;
- the reviewer resolves the threads they opened, that being what says a
  finding is closed, and re-reviews the delta rather than the branch.

**What ends the loop is the ack of record**, and the author does not
supply their own. A reading that says what it found and delivers no
verdict is a review too and ends nothing; [the standard's *Review*][s-rev]
has which is which, and `REVIEWING.md` has how each is written. A
disagreement that survives a second exchange goes to the maintainer
instead of into a third round.

### Landing it

CI is read once, and this is where. Rebase onto `main`'s tip, push that
head so the checks run on the tree that will land, and only then wait for
them: checks read before a rebase describe a tree nobody is landing. A
rebase that moved nothing but the base leaves the ack standing; one that
resolved a conflict does not, that resolution being a change no reviewer
has seen.

Then squash, [the only method the rule accepts][s11].

**The maintainer's bypass is not automatic — it has to be invoked, and
`gh pr merge` cannot invoke it**, refusing client-side before it asks
GitHub anything:

```text
Pull request is not mergeable: the base branch policy prohibits the merge
```

The merge endpoint applies it server-side, and it is the same endpoint
the merge button asks:

```shell
gh api -X PUT repos/{owner}/{repo}/pulls/<n>/merge \
  -f merge_method=squash -f sha=<the head the checks ran on>
```

**The `sha` is not optional.** Reading the ack and merging are two
calls, and the head is free to move between them — the push that would
move it comes out of the same round the verdict does. Unpinned, the
command takes whatever sits at the head when it runs; pinned, [the
endpoint answers `409` where the head has moved][gh-merge], and a round
lost that way is cheaper than a tree nobody has read reaching `main`.
*The review* above anchors the exchange to a sha and [section 11][s11]
has an ack name one: the pin is that rule reaching the call that
performs the landing.

**Verify what landed rather than trusting the answer**, the signature
[the standard asks for][s-sigs] being a valid one rather than a
particular signer's:

```shell
gh api repos/{owner}/{repo}/commits/main \
  --jq '.commit.verification | {verified, reason}'
```

**What it closed is read again here too, from the landed sha rather
than from the pull request**: [the standard's *What a pull request says
it is*][s-title] has the second read, and why the first alone does not
reach a squash subject composed after it runs.

The forge deletes the head branch itself, per the setting section 11
names. What is still yours is bringing every checkout sitting on `main`
up to date,
that being where the next session starts from and a stale one being where
a branch gets built on a base that has moved. `REPOSITORY.md` carries the
settings and why they are what they are.

[s-what]: https://github.com/btclib-org/.github#what-this-repository-is
[s11]: https://github.com/btclib-org/.github#11-github-settings
[s9]: https://github.com/btclib-org/.github#9-prose-comments-and-docstrings
[s-title]: https://github.com/btclib-org/.github#what-a-pull-request-says-it-is
[s-rev]: https://github.com/btclib-org/.github#review
[s-sigs]: https://github.com/btclib-org/.github#signatures
[gh-merge]: https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request

## This repository in particular

Everything above is the same file in every repository of the
organization; everything below is this one's, and the comparison stops at
this heading.

### The environment and the gates

uv is the only thing that has to be installed; it fetches interpreters,
linters and packaging tools itself.

```shell
uv sync --locked
```

That installs the comparands, which is most of the work: `electrum-ecc`
publishes no wheel anywhere, so it is built from its sdist, which
carries libsecp256k1 as a submodule and runs its `autogen.sh` — that is
what `autoconf`, `automake` and `libtool` have to be there for. The
other wrappers resolve to a wheel where the index serves one for the
interpreter `.python-version` pins *and* the platform in hand, and are
built from source where it does not, which is when a build of
`secp256k1` wants `pkg-config`; `os-ubuntu.yml` and `os-macos.yml` each
name a cell where that happens. The interpreter half of that is what
the pin is for, and the comment there says why. `secp256k1lab` comes
from a git tag, having no release on any index.

The gates are three commands, and CI runs exactly them: the suite,
gated at 100% coverage; every lint hook; and the documentation build.

```shell
uv run pytest
uv run pre-commit run --all-files
uv run --locked --only-group docs \
  sphinx-build -W -n -b html docs/source docs/build/html
```

The documentation build is the one a contributor used to meet by having
a pull request held: `-W` turns a sphinx warning into an error, so a
heading level skipped, a markdown link that resolves to nothing, or a
page reachable from no toctree is a red check and not a note in a log.
`-n` adds sphinx's own cross-reference resolution to what `-W` can fail
on -- a `:class:` or `:func:` role naming something that does not exist
-- which nothing under `docs/source` writes today, so the flag is ahead
of the content that will exercise it rather than catching anything here
yet; `btclib-org/.github`'s README.md "The documentation" has the
reason it is on regardless. `-W` fails at the end of the build rather
than at the first warning, so one broken page does not hide the next.

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
Passed` hides a failure, and `grep` finding nothing exits 1, which is not
the gate's answer to anything.

### What gates a merge, and what only reports

The three commands above are the three required checks, so nothing
reaches a review without having passed them or passing them beside it on
the same sha, and a reviewer may rely on that rather than establishing it
again; `REVIEWING.md` has what the reliance takes. One command names the
contexts `main` requires,

```shell
gh api repos/btclib-org/btclib-benchmarks/branches/main/protection \
  --jq '.required_status_checks.checks[].context'
```

rather than a list kept here. The suite's cell is `ubuntu-latest` on the
interpreter `.python-version` pins, which is where coverage is measured
and where the 100% ratchet is enforced.

Everything exhaustive is a scheduled workflow instead — the images and
interpreters the gate does not run, the resolution at latest, the links,
the code analysis. Which workflows those are is

```shell
ls .github/workflows/
```

rather than a list here, and each one says in its own header what it
answers for. The day each of them runs is section 10 of the repository
standard this file opens by naming: one calendar covering every
repository in the organization is one thing to remember rather than one
per tree, and a day repeated here is a day that goes stale here.

What that costs is worth stating rather than discovering. A regression
that only shows on `3.11`, on aarch64 or on macOS is not refused before
a merge; it sits on `main` until the sentinel for it runs, at most a
week (btclib-org/.github#85). What it buys is every review: the
concurrent-job ceiling `REPOSITORY.md` records belongs to the
organization rather than to this repository, and a matrix on each commit
here is a slot a reviewer elsewhere waits behind.

What a cron runs is the suite, the lint gate, the link check and the
code analysis, and never a benchmark — *What the suite can and cannot
check*, below, is where that rule and its reason live.

### Running a mutation session

The `mutation` workflow, weekly and on demand, gates nothing: it asks
whether the suite would *notice* a wrong line in the four modules and the
one script `fail_under = 100.0` already says run in full,
`src/btclib_benchmarks/_inputs.py`, `_provenance.py`, `_vectors.py` and
`scripts/artifacts.py` — where coverage says a line ran, a surviving
mutant says nothing asserted about it. `.github/mutation/` is the list,
and each file in it states what it mutates, what judges it, and what the
last session over it found; those configurations are also what a local
run reads, so there is one statement of what is mutated and what judges
it:

```shell
uv run --locked --no-default-groups --group test --group mutation \
    cosmic-ray baseline .github/mutation/inputs.toml
uv run --locked --no-default-groups --group test --group mutation \
    cosmic-ray init .github/mutation/inputs.toml inputs.sqlite
uv run --locked --no-default-groups --group test --group mutation \
    cr-filter-operators inputs.sqlite .github/mutation/inputs.toml
uv run --locked --no-default-groups --group test --group mutation \
    cosmic-ray exec .github/mutation/inputs.toml inputs.sqlite
uv run --locked --no-default-groups --group test --group mutation \
    cr-report --surviving-only --show-diff inputs.sqlite
```

`baseline` first, always: it runs the configured test command against
the unmutated tree, and without it a stale path or a renamed test file
fails every mutant identically and the session reports a perfect kill
rate, which is the one failure mode of a mutation run that looks like
good news. `cr-filter-operators` marks as skipped the mutants a
configuration excludes by operator, and is a no-op for one that excludes
none, so the same five commands run any of the three scopes —
`provenance.toml` or `vectors.toml` in place of `inputs.toml` above is
the other two. The report is `--surviving-only`, which is the whole of
what anybody acts on: a killed mutant is the suite doing its job, and
printing every one of them buries the handful that are not.

Three things to know before starting one. The session mutates the source
file in place and restores it afterwards, so nothing else may read the
tree while it runs — no second session, no `pytest` in another shell, and
a `git status` in the middle is a working tree with a mutant in it.
`exec` is resumable, running whatever the session still has pending, so
interrupting one costs only the mutant it was on. And the `.sqlite`
sessions are the artifact the workflow uploads: `cr-report`, `cr-html`
and `cr-rate` all read one, and a downloaded one can be finished locally.

For the counts, read the session with the workflow's own script rather
than `cr-rate`:

```shell
uv run --locked --no-default-groups \
    python .github/scripts/mutation_counts.py inputs.sqlite
```

`cr-rate`'s `is_killed` is `test_outcome != SURVIVED`, so a mutant the
operator filter skipped counts as a kill and the rate divides by every
result, reading a perfect 0.00% on a session nothing has run yet.
`cr-report`'s summary line is wrong the same way. The script prints
killed, survived, skipped and never-run counts, and exits non-zero for
an outcome that is no verdict at all — a worker that raised rather than
a mutant a test caught.

### Running a benchmark

Every floor in `pyproject.toml` is a minimum a comparand upgrades past
without a word, `btclib` and `btclib-secp256k1` included now that both
resolve from a released index rather than a branch: `uv sync --locked`
reinstalls the revision the lock names and never looks at whether a
newer release has shipped since. So a measurement taken without asking
for the upgrade is a measurement of whatever was current the day the
lock was last written, which is not what a page's provenance block
claims it measured. Ask for it first, every time:

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

**One script at a time, and not in a loop over the rest.** Each run
saturates the machine for minutes, and the next one started immediately
after measures a hot machine rather than the operation: measured that way,
the pure-Python columns of `02-btclib-vs-btclib.py` came out up to three
times their real cost, and a verification through the C library came out
at twice. The dispersion column beside a row is what shows it, and which
statistic it is belongs to the page. `01-libsecp256k1.py`,
`03-libraries.py`, `04-pure-python.py` and `06-silentpayments.py` save
`halves_apart`, how far the minima of the halves of a row's rounds sat
apart, so a wide one is a row whose own estimate moved while it was being
measured; `spread`, the slowest round less the quickest, is the key a run
saved before that carries, and it answers a different question. The
scripts that save neither, `02-btclib-vs-btclib.py` and
`05-key-reuse.py`, time each row once and print no such column at
all — an absent one is a page that did not measure it rather than a
row that did not move. Each page
defines the column it prints, in the prose beside its tables. Read it
before believing an ordering — and note that neither can see the machine
drifting between one run and the next, which is why the machine is given
time to cool between scripts rather than watched for it afterwards.

Drift itself is measured on one page. `01-libsecp256k1.py` times every
table twice in one invocation, idle in between, publishes the first pass
and states in its run block how far apart the two passes began, how many
rows came out quicker the second time, and by how much. It is the
cheapest of the benchmarks, which is why it is the one that pays for a
second pass; the rest state nothing, and an absent line there is a page
that did not pay for one rather than a page whose two passes agreed.

Read the count before the magnitudes. Rows moving one way in the great
majority is a difference between the two passes rather than noise between
them, and a run that shows it is one to look at twice; a count near half
the rows is an ordinary pair of passes. Which pass is published does not
move either way — it is the first, and fixed, because a rule chosen once
both passes are in hand is how a page comes to publish whichever of them
flattered it.

To measure a working tree instead of the published release:

```shell
uv run --with-editable /path/to/btclib python scripts/03-libraries.py
```

The header then says `editable: /path/to/btclib` where it otherwise says
`released`, which is the point of printing it.

### Publishing a run, which is a second command

A run writes `results/<name>.json` as it finishes: every number, the
packages block, and what the run block states — the clock, the
interpreter, the machine, the method. Nothing about the page is decided
there. With no argument every page renders from its own run; naming one
page renders only that one; `--check` names what is stale and writes
nothing.

```shell
uv run python scripts/render.py
uv run python scripts/render.py 05-key-reuse
uv run python scripts/render.py --check
```

`render.py` puts the numbers, the packages block and the run block into
the page between the markers it carries, and touches nothing else in
it. So the prose around the numbers
— the headings, the paragraph explaining a column, the analysis — is
edited and re-published without measuring again, which is the whole
reason the two are separate: a reworded heading otherwise costs either a
fresh run, whose numbers are different, or a hand-edited block, whose
numbers are nobody's.

It reads the saved run and imports no benchmark. That matters more than
it sounds: importing one derives keys, signs a message per comparand and
runs every cross-comparand assertion before it will answer anything.

### Which artifact an install resolved to, which is a third command

One line per comparand:

```shell
uv run python scripts/artifacts.py
```

A page's provenance block says what version was measured and whether it
came from an index or a branch. What no version can say is which of an
index's two artifacts answered, and for a comparand that vendors
libsecp256k1 the wheel and the sdist of one version need not carry the
same library — so this prints the tags of the wheel each install came
from, a bare `linux_*` one being a tag no index serves and therefore a
build made where it is installed.

CI runs it before every run of the suite, which is where it earns its
place: `uv.lock` carries no aarch64 wheel for one comparand, so the
weekly sentinels above assert the pages' claims against a library
compiled on the runner rather than the one an index serves. It records
and asserts nothing — an index gaining a wheel changes every line it
prints and breaks nothing.

`results/machine.toml` overrides the one line a run may get wrong, which
machine it was taken on. Edit it when that stops being true; every run
taken afterwards carries the new answer, and runs already saved keep the
one they were taken under.

`--check` says whether a page still matches the run it publishes. It is
not wired into CI, and deliberately: a page is written by a command a
person runs, not by a gate.

### A version, and no release

There is no release. Nothing here is published to an index.
Installing this project puts `src/btclib_benchmarks/` on the path, and
the scripts are still run from a checkout. So this tree carries no
`RELEASING.md` and no `RELEASE_NOTES.md`: section 2 of the standard has
why a tier-2 repository carries neither, and a file whose content is its
own absence is this paragraph instead.

What `project.version` is for, then, is the `CHANGELOG.md` heading: a
released *state of the benchmarks*, so that a table someone kept can be
placed against the versions that produced it. Cutting one is a signed
tag, as every tag in this organization is, and `REPOSITORY.md`'s
`tag-integrity` ruleset refuses an unsigned one:

```shell
git tag -s v<version> -m "v<version>"
git push origin v<version>
```

Before tagging, run every benchmark by hand, one at a time. The suite
proves the scripts load and that their comparands agree; it cannot prove
they still *measure* anything, and that is exactly what rots — a
comparand renames a method, a backend stops being found, an
implementation gets a fast path. Read each header before its numbers: a
row whose backend has silently changed is a number that means something
other than what its label says.

### What the suite can and cannot check

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

### Writing a row

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
