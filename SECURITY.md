# Security policy

## What this project is

Benchmarks. It ships no library, exposes no API, and nothing here is
meant to be imported: the scripts are run from a checkout, by a person,
to produce a table.

It has no users in the sense that matters to a security policy — no
release on PyPI, nothing to install, and no key material of its own.
The private key every script signs with is the integer 1, published in
plain sight, because a timing must not depend on which key was drawn
and a reader has to be able to reproduce the row.

## What to report, and where

A vulnerability in the packages this project measures belongs upstream,
with the package that has it. Dependabot alerts raised here are alerts
against a comparand, which is the whole reason the benchmarks were moved
out of [btclib](https://github.com/btclib-org/btclib) and
[btclib-secp256k1](https://github.com/btclib-org/btclib-secp256k1): an
advisory should name the project the package actually belongs to.

For the two btclib-org packages themselves, report through their own
policies:

- [btclib](https://github.com/btclib-org/btclib/blob/main/SECURITY.md)
- [btclib-secp256k1](https://github.com/btclib-org/btclib-secp256k1/blob/main/SECURITY.md)

For anything genuinely about *this* repository — a script that runs
something it should not, a workflow with a permission it does not need
— open an issue, or write to <devs@btclib.org> if it should not be
public first.

## What a benchmark can get wrong

Not a vulnerability, and worth stating anyway, because it is the failure
this repository is built to avoid: **measuring something other than what
the table says**.

Every script prints the version and the provenance of each package
before any number — released, git ref, editable, or shadowed on
`sys.path` — and asserts that every comparand agrees with btclib before
timing any of them. A number produced without that header is not a
result from this project; treat it as unverified.
