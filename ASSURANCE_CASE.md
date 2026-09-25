# Assurance case

This page argues why a table this project publishes can be trusted for
what it claims to be: the threat model, the trust boundaries, how secure
design principles are applied, and how common implementation weaknesses
are countered. Each argument names the file, the test or the workflow
that supports it. The components named here are the ones
[ARCHITECTURE](./ARCHITECTURE.md) describes; this repository carries no
`SECURITY.md` of its own, and GitHub shows the one
[btclib-org/.github](https://github.com/btclib-org/.github/blob/main/SECURITY.md)
carries instead, as `README.md`'s closing section says.

## What is out of scope

This project protects nothing. It defends no secret, serves no network
request, and runs no code chosen by anyone other than whoever checks it
out and types `uv run`. What follows is proportionate to that: the claim
worth arguing is not that an attacker is kept out, but that the numbers a
table prints are the numbers the labeled build actually produced, and
that a comparand's own answers are checked before any of them is timed.

**The pool of keys `src/btclib_benchmarks/_inputs.py` derives is not a
secret in the sense any other claim on this page means.** Every key comes
from sha256 of a published constant and a counter, so it is exactly as
public as this file; `CONTRIBUTING.md`'s *Writing a row* records the one
occasion a benchmark's own choice of key mattered — the scalar 1,
whose public key is the generator itself, and whose derivation and
verification measured neither one honestly — and that is a correctness
defect in a row, not a confidentiality one. Nothing this project signs or
derives is used to protect anything after the run ends.

## What is claimed

- **A published table reports what a labeled build actually measured.**
  `scripts/artifacts.py` and every numbered script's own provenance block
  print which artifact of every comparand answered — released, an editable
  checkout, a git ref, or a wheel built where it is installed — and
  `README.md`'s *A vulnerability in a package this project measures*
  and *Measuring a working tree instead of a release* both name a number
  printed without that header as unverified.
- **Every measured package answers the published vectors it is checked
  against, in the configuration it is timed in, before any row of it is
  trusted.** `tests/vectors_test.py`'s module docstring states the
  negative cases this checks and why "it agreed with btclib" is not the
  same question.
- **A timed loop asserts nothing, and an assertion that ran is not part
  of what a row measures.** `CONTRIBUTING.md`'s *Writing a row* states
  the rule; every script's fixtures are built and checked at module
  level, ahead of `main()`.
- **A page's numbers are what its own saved run holds.** `render-check`
  (`.pre-commit-config.yaml`) fails where `results/<name>.md` and
  `results/<name>.json` disagree, on every commit.

## Threat model

The command below lists the top-level name of every module `src/`
imports, at any depth and in any spelling of the statement — the
population `src/btclib_benchmarks/` is held to, `btclib_secp256k1` beside
the standard library:

```shell
python3 - <<'EOF'
import ast, pathlib
names = set()
for p in pathlib.Path("src").rglob("*.py"):
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            names.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            names.add(n.module.split(".")[0])
print(sorted(names))
EOF
```

`scripts/` carries the wider population: every comparand `pyproject.toml`
declares — `btclib`, `bitcoin` (`python-bitcoinlib`'s import name),
`buidl`, `coincurve`, `ecdsa`, `electrum_ecc`, `ellipticcurve`
(`starkbank-ecdsa`'s import name), `embit`, `pycoin`, `secp256k1`,
`secp256k1lab` — none of which a script reaches for anything but the
operation it times.

**What is defended.** That a published table is checkable: which
artifact of which package produced each row, and that the row's own
answer was verified before it was timed. Beyond that, the correctness of
`tests/vectors_test.py`'s own verdicts, which is btclib's assurance case
one layer up for the one comparand this project also depends on for its
production code.

**The adversaries.** Two, and neither is a remote party. A comparand's
own release, which can regress a case this project has already recorded
as passing — `xfail_strict` in `pyproject.toml` turns a fixed defect into
a failing suite rather than a quietly stale `xfail`, which is the
record staying current rather than a defence against tampering. And a
session running these scripts without reading the header each one
prints, publishing a number for whichever artifact actually happened to
be installed.

**What is not defended**, each already true of the packages this project
depends on and out of its own control: a comparand's supply chain past
what Dependabot and `uv.lock` cover below; the side channels the keys and
signatures in this repository were never meant to resist, being made up
rather than secret; and the correctness of a comparand this project has
no vendored vector to check — the cross-comparand agreement
`CONTRIBUTING.md`'s *Writing a row* names as what there is instead,
weaker than a published vector and said to be.

## Trust boundaries

**The comparands and this process.** Every comparand runs inside the same
interpreter these scripts do, with the same keys and the same messages: a
benchmark holds no more of a boundary against the packages it measures
than any Python program holds against a library it imports. What crosses
deliberately is `PYCOIN_NATIVE` and `BENCHMARKS_PURE_PYTHON`
(`tests/vectors_test.py`'s docstring), read once at import to choose a
backend and never fed anything but a fixed value this project sets
itself.

**Files.** Everything read at run time is either vendored in this
repository (`vectors/`, read once by `_vectors.py`) or written by this
project's own earlier run (`.inputs/`'s cache, `results/<name>.json`,
`results/machine.toml`). No script opens a file a caller names on the
command line: `scripts/render.py` reduces each name it is given to its
stem and resolves it under `results/`, so a name with no page there ends
the run on a `FileNotFoundError` rather than reaching another path.

**The environment.** `results/machine.toml` overrides the one line
`_results.py`'s `_detected_machine` may get wrong about the host running
it; that function's own `_spoken_by` runs two fixed, absolute-path
commands (`/usr/sbin/sysctl`, `/usr/bin/sw_vers`) with no shell and no
caller-supplied argument, which is what the `# noqa: S603` beside the
`subprocess.run` call states the reason for.

## Secure design principles

Saltzer and Schroeder's principles, applied to a project whose job is
measuring rather than serving.

- **Economy of mechanism.** One provenance module (`_provenance.py`)
  answers where an artifact came from for every script that prints a
  header, rather than each script reading `direct_url.json` its own way.
- **Fail-safe defaults.** Every script's timing lives behind a `main()`
  guard; importing one runs its fixtures and its assertions and times
  nothing, which is the same property `tests/scripts_import_test.py`
  relies on to import all six under the suite. `_read`'s cache reader
  in `_inputs.py` treats a short or ragged file as absent rather than as
  a partial pool to repair, and `cached`'s writer builds a pool to a
  temporary file and renames it into place, so a run interrupted mid-write
  leaves no half-written cache for the next one to read as whole.
- **Complete mediation.** `tests/vectors_test.py` holds every measured
  package to the same vectors in the same configuration it is timed in,
  never assuming a package that passed once still does after its own
  release.
- **Open design.** `vectors/README.md` states where every vendored file
  came from; `01-libsecp256k1.py`'s `LIBSECP256K1_PINS` and
  `_provenance.artifact_of`'s docstring both say what is recorded by hand
  because nothing at run time can read it back, and a pin an upgraded
  comparand outgrows prints `unrecorded` rather than a stale number.
- **Least privilege.** `src/btclib_benchmarks/` imports nothing beyond
  the standard library and `btclib_secp256k1`, the census under *Threat
  model* above being what says so; no module opens a socket or a file
  outside `vectors/`, `.inputs/` and `results/`.
- **Psychological acceptability.** A script's own printed header is where
  a reader is told what produced the numbers below it, rather than a fact
  left to be inferred from the version pinned in `pyproject.toml`.

## Common implementation weaknesses

Weaknesses from MITRE's CWE list this project's own code is exposed to —
narrower than a library's, because nothing here parses input a remote
party supplies.

- **Weak randomness (CWE-330, CWE-338).** Not applicable to the keys
  `_inputs.py` derives, which defend nothing and are deterministic by
  design so that a table is reproducible from the seed alone; where a
  comparand's own nonce derivation matters, `tests/vectors_test.py`
  checks the signature it produces against a published vector rather than
  trusting the generator that produced the nonce.
- **Uncontrolled resource consumption (CWE-400, CWE-770).** `POOL_SIZE` in
  `_inputs.py` is a fixed constant sized for the longest row in the suite,
  documented in the module's own docstring rather than derived from
  anything a caller passes in.
- **Improper verification (CWE-347).** `tests/vectors_test.py` is the
  whole of this project's own answer, held to `xfail_strict = true`
  (`pyproject.toml`) so a comparand's release that fixes a recorded
  defect turns the suite red instead of leaving a stale exemption in
  place.
- **Type confusion (CWE-843).** mypy runs `strict = true`
  (`pyproject.toml`) over `src/` and `tests/`, as a `.pre-commit-config.yaml`
  hook.
- **Code that is wrong and still passes.** Coverage of `src/` (short of
  `_results.py`, by design — [ARCHITECTURE](./ARCHITECTURE.md)'s *The
  shared modules*) and of `tests/` is held to 100% by `fail_under` in
  `pyproject.toml`.
- **Supply chain.** `uv.lock` pins every dependency, every workflow
  installs it with `--locked`, and `.github/dependabot.yml` groups a
  weekly update per ecosystem with a seven-day cooldown. Every third-party
  action is pinned to a commit sha; `actionlint` and `zizmor` run as
  `.pre-commit-config.yaml` hooks, and `.github/workflows/codeql.yml`
  analyses the workflow files and the helpers under `scripts/` on the
  schedule and triggers that file states. A fixture holding a real-looking
  key or signature trips `detect-secrets`, and `CONTRIBUTING.md`'s *The
  environment and the gates* is where recording such a finding as
  reviewed, rather than excluding the file, is stated as the rule.
