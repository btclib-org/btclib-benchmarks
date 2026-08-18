# Bitcoin Python libraries

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package            version           released           arithmetic
btclib             2026.9            main@9d85d3e61467  libsecp256k1 enhanced
pycoin             0.92718.20260405  2026-04-05         libsecp256k1 enhanced
ecdsa              0.19.2            2026-03-26         pure Python
embit              0.8.0             2024-05-30         libsecp256k1 enhanced
python-bitcoinlib  0.12.2            2023-06-03         OpenSSL's libcrypto
buidl              0.2.36            2022-02-28         pure Python
```
<!-- provenance: end -->

The last column says which arithmetic answered on the machine that ran
this, and nothing about how the package got there. That part is one
paragraph each, and none of the six is the same story:

- **btclib** requires `btclib-secp256k1`, which bundles libsecp256k1 and
  compiles it into a cffi extension at install time, so a wheel from PyPI
  is enhanced without anything further being done to it. Which revision it
  bundles is in [the wrappers table][wrappers].
- **pycoin** bundles nothing and builds nothing. `pycoin.ecdsa.native` is a
  ctypes loader that asks the machine for a library by name, and a PyPI
  install therefore gets pure Python unless one is already there. Here one
  is: btclib-secp256k1's extension has put its symbols in this process, and
  pycoin's loader finds them — through an import this script makes rather
  than anything pycoin does. On a machine where nothing else has loaded
  libsecp256k1, this row is Python, which is where the count it uses comes
  from as well. What that costs is the pycoin row of [the pure-Python
  table][pure].
- **embit** ships its own shared library in the wheel and reaches it
  through ctypes, and what it ships is secp256k1-zkp — ElementsProject's
  fork — rather than bitcoin-core/secp256k1. It is not a package anyone can
  install on its own, and the revision it carries is recorded here against
  the release it was read from.
- **buidl** has cffi bindings in `buidl.cecc`, and `pip install buidl` does
  not build them: `libsec_build.py` compiles them against a system library
  and has to be run by hand. So its rows are `buidl.pecc`, pure Python,
  unless somebody did that.
- **python-bitcoinlib** reaches C that is not libsecp256k1 at all —
  OpenSSL's libcrypto, through ctypes. It can detect a libsecp256k1 and
  does not use it for these operations.
- **ecdsa** has no bindings of any kind, bundled, built or found.

## This run

<!-- run: begin -->
```text
when    : 2026-08-16 23:33 CEST (21:33 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

The tables are the curve operations, BIP32 derivation, and the three
address encodings in both directions. Fastest row first, ratioed against
whichever row came out quickest, with the spread of a row's own three
rounds beside it — how far its slowest round ran from its quickest, in the
same microseconds as the value it sits beside.

Read it as the computer and not as the library — as what else the machine was
doing while a row was measured, rather than as anything the code under that
row does. It is the worst of three rounds less the best, so a wide one says
one round in three caught an interruption and a narrow one says none of them
did.

It is **not** a separation test. The worst of three samples is a number
dominated by whichever round happened to go badly, so it moves a great deal
from run to run while the row's own minimum barely moves at all: whether two
adjacent rows are really in the order printed is not a question it answers,
and comparing their gap against it does not make it one.

That is not the statistic the column of the same name carries on [the
wrappers page][wrappers], and the two are not comparable in either direction.
This one is a maximum less a minimum, so it grows as rounds are added and
reports the worst interruption a row happened to catch. That one is the
distance between the minima of two halves of the rounds, so it shrinks as
rounds are added and reports whether the row agreed with itself. Both are
in microseconds and neither is an error bar; a small number here and a
small number there do not mean the same thing.

The inputs are every BIP340 signing vector and every BIP32 chain the
vendored files publish, cycled one per call; the address rows are the
exception, one witness-v0 and one witness-v1 address being what is
vendored, so they call one input.

**btclib's three signing rows were measured before its signing had a check**,
and they are the only rows on this page that predate one: btclib verifies the
signature it has just made before answering with it, and the lock carries that
btclib. Each of the three understates that default by one such check — a
bare verification in BIP340, and in ECDSA a verification plus the public key
derivation verifying needs and signing did not. The grinding row pays it once
as well, the loop and the check crossing into the bindings together so that
what is proved is the signature the loop kept rather than every attempt
discarded, which is the ordering [ISS 982 (btclib-org/btclib)][i982] asked
for and the lock now carries. Every other row here is current, btclib's
verification rows included — [ISS 53][i53] re-measured this page to find that
out, and discarded the run rather than publish it.

What that re-measurement has to settle is a shape and not a number, and [the
wrappers table][wrappers] settled the same question the same way: btclib is
the only comparand here that takes the argument, the others verifying or not
as their own APIs happen to, so one row is what compares with libraries that
verify nothing and a second is what the guarantee costs. Printing one of the
two alone makes whichever comparison it is not in wrong. [ISS 23][i23] is the
order that run waits on, and [ISS 47][i47] the spread estimator that rides
with it — four rounds being affordable, and a second measurement of this page
not.

<!-- output: begin -->
```text
method  : 3 rounds per row, minimum kept; nothing else repeated
command : uv run python scripts/03-libraries.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

1. ECDSA sign (32-byte digest)
                   μs/call     vs best   spread
  pycoin             12.63        1.0x     0.50   (3x50,000 calls)
  embit              14.23        1.1x     0.03   (3x50,000 calls)
  btclib             15.24        1.2x     1.02   (3x50,000 calls)
  btclib_grind       27.99        2.2x     0.61   (3x20,000 calls)
  embit_grind        29.81        2.4x     0.20   (3x20,000 calls)
  bitcoinlib        192.10       15.2x     0.63   (3x8,000 calls)
  ecdsa             304.31       24.1x     5.30   (3x5,000 calls)
  buidl           30705.19     2431.2x   459.90   (3x50 calls)

2. ECDSA verify (32-byte digest)
                   μs/call     vs best   spread
  pycoin             13.94        1.0x     0.06   (3x50,000 calls)
  btclib             20.17        1.4x     0.10   (3x50,000 calls)
  embit              24.30        1.7x     0.44   (3x50,000 calls)
  bitcoinlib        227.14       16.3x     2.32   (3x7,000 calls)
  ecdsa            1145.09       82.1x    41.04   (3x3,000 calls)
  buidl           60505.99     4339.9x  1166.56   (3x25 calls)

3. BIP340 sign (32-byte message)
                   μs/call     vs best   spread
  embit              21.32        1.0x     0.04   (3x50,000 calls)
  btclib             22.27        1.0x     0.38   (3x50,000 calls)
  buidl          111995.92     5253.8x  4720.62   (3x20 calls)

4. BIP340 verify (32-byte message)
                   μs/call     vs best   spread
  btclib             21.33        1.0x     0.14   (3x50,000 calls)
  embit              25.07        1.2x     0.02   (3x50,000 calls)
  buidl           69173.50     3243.1x    86.47   (3x25 calls)

5. BIP32 derive, seed to child, every chain BIP32 publishes
                   μs/call     vs best   spread
  pycoin             48.21        1.0x     0.15   (3x30,000 calls)
  btclib             63.32        1.3x     0.05   (3x30,000 calls)
  embit              86.57        1.8x     0.12   (3x15,000 calls)
  buidl          103814.63     2153.4x  4959.49   (3x12 calls)

6. base58check encode, a P2PKH address from a hash160
                   μs/call     vs best   spread
  embit               2.15        1.0x     0.01   (3x200,000 calls)
  buidl               2.28        1.1x     0.01   (3x200,000 calls)
  btclib              2.41        1.1x     0.02   (3x200,000 calls)
  bitcoinlib          2.54        1.2x     0.01   (3x100,000 calls)
  pycoin              3.65        1.7x     0.02   (3x200,000 calls)

7. base58check decode, a hash160 from a P2PKH address
                   μs/call     vs best   spread
  btclib              2.50        1.0x     0.01   (3x200,000 calls)
  embit               2.59        1.0x     0.01   (3x200,000 calls)
  buidl               2.93        1.2x     0.03   (3x200,000 calls)
  pycoin              3.77        1.5x     0.01   (3x200,000 calls)
  bitcoinlib          4.30        1.7x     0.01   (3x100,000 calls)

8. bech32 encode, a witness-v0 address from a 20-byte program
                   μs/call     vs best   spread
  btclib              7.94        1.0x     0.04   (3x200,000 calls)
  buidl              11.71        1.5x     0.03   (3x100,000 calls)
  embit              26.30        3.3x     0.42   (3x200,000 calls)
  bitcoinlib         26.31        3.3x     0.03   (3x200,000 calls)

9. bech32 decode, a 20-byte program from a witness-v0 address
                   μs/call     vs best   spread
  btclib              7.00        1.0x     0.01   (3x200,000 calls)
  buidl              10.26        1.5x     0.10   (3x100,000 calls)
  bitcoinlib         14.36        2.1x     0.05   (3x200,000 calls)
  embit              14.49        2.1x     0.04   (3x200,000 calls)

10. bech32m encode, a witness-v1 address from a 32-byte program
                   μs/call     vs best   spread
  btclib             13.08        1.0x     0.02   (3x200,000 calls)
  buidl              17.54        1.3x     0.45   (3x100,000 calls)
  embit              40.28        3.1x     0.79   (3x200,000 calls)

11. bech32m decode, a 32-byte program from a witness-v1 address
                   μs/call     vs best   spread
  btclib             11.71        1.0x     0.05   (3x200,000 calls)
  buidl              15.21        1.3x     0.04   (3x100,000 calls)
  embit              21.84        1.9x     0.02   (3x200,000 calls)
```
<!-- output: end -->

## Results

The sort separates the rows into the two groups the packages table predicts:
the ones that reach C land within a small factor of one another, and the
pure-Python rows fall an order of magnitude or more behind them —
`buidl.pecc` by a great deal more than that. python-bitcoinlib's OpenSSL
path sits between the two groups. Which row is in which group is not a
property of the packages alone, which is what that table's last column is
for.

### Signing: two libraries sign more than once by default

btclib and embit both grind for a low-r signature — they sign repeatedly
until r fits in 32 bytes — so their default is not comparable per signature
with the rows that sign once. Each therefore has two rows: one signature,
which is the comparable one, and the default beside it, whose cost is that
signature times however many draws it took before r fit. Half of all draws
fit already, so two signatures is the expectation over random messages, and
the ratio between a library's two rows is where to read what this run's
messages actually cost it. That multiple is a property of the draw rather
than of either library — it is the one number on this page that moves when
the inputs do, and it is why the grinding rows sit where they do in the order
rather than beside their own one-signature rows.

### Verification: python-ecdsa's row is worth reading against its key

Handed the private key 1, python-ecdsa returns the generator *object* as the
public key — precomputed table and all — and a row verifying against it
verifies with a table no real key gets, at about half the cost. The keys here
are drawn from the shared pool, and a drawn key is not the generator, so the
row costs what verification costs. It is the sharpest reason in these five
files for drawing the input rather than choosing it: a chosen key can be
special in ways a table of timings cannot show.

### The encoding tables

base58check, bech32 and bech32m are the only tables here that are not curve
work, and they are where these libraries differ most: pure Python in all
five, so what separates them is the code and nothing else. A wrapper cannot
help an address encoder.

## What these packages get wrong

A row here is a timing and not a verdict, so where a comparand answers a
published case wrongly this page says so. None of it makes a row
meaningless — every package times the operation it is asked for, over
inputs it handles — but a reader comparing them is owed the fact that some
of them are lax about what they accept.

`python-bitcoinlib` is the one that cannot be timed at all in a table it
would otherwise appear in. It encodes a witness-v1 program with bech32's
checksum constant where BIP350 requires bech32m's, and refuses to decode
the address BIP350 publishes, so it has no bech32m row in either
direction. `tests/round_trip_test.py` holds it to both halves of that,
which is also what will fail when a release fixes it.

`pycoin` and `buidl` are lax where a DER decoder should be strict. Run
against Wycheproof, whose whole subject is adversarial encodings, both
accept signatures the file rejects: pycoin reads BER long-form lengths
where DER admits one form, lengths that are wrong or that overflow a
uint64, and signatures with bytes appended or taken away that still parse;
buidl reads the same family, plus zeros prepended to r and to s, a
truncated r, and an r larger than any verification should admit. The one
that goes the other way is buidl's, which *rejects* a valid signature
where `k*G` has a large x coordinate.

`buidl` also cannot encode the empty payload that Bitcoin Core publishes
as the first base58 case: its encoder goes through `int(s.hex(), 16)`,
which raises on the empty string rather than answering with it.

Every one of these is recorded in `tests/vectors_test.py` as an expected
failure rather than skipped, so a release that fixes one turns the suite
red and brings somebody back to this list. What none of them changes is
the timings above: the signatures and addresses these rows carry are the
ones a specification publishes, and every package answers those correctly.

The loop counts are per row and print beside their rows, sorting putting rows
orders of magnitude apart next to each other. pycoin's are picked at run time,
from the backend found, for the reason its paragraph above gives.

## More benchmarks

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[i23]: https://github.com/btclib-org/btclib-benchmarks/issues/23
[i47]: https://github.com/btclib-org/btclib-benchmarks/issues/47
[i53]: https://github.com/btclib-org/btclib-benchmarks/issues/53
[i982]: https://github.com/btclib-org/btclib/issues/982

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
