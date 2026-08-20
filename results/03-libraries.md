# Bitcoin Python libraries

## The packages downloaded from PyPI

<!-- provenance: begin -->
```text
package            version           released           arithmetic
btclib             2026.9            main@5f7ad5422544  libsecp256k1 enhanced
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
when    : 2026-08-20 09:21 CEST (07:21 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

The tables are the curve operations, BIP32 derivation, and the three
address encodings in both directions. Fastest row first, ratioed against
whichever row came out quickest, with a dispersion column beside it in the
same microseconds as the value it sits beside.

**The dispersion column is `halves`, not the `spread` earlier runs of this
page printed.** `spread` was a maximum less a minimum — a row's slowest
round against its quickest — dominated by whichever round happened to go
badly: it has enormous variance by construction, it grows as rounds are
added, and it reports the worst interruption a row happened to catch rather
than anything about the package. Whether two adjacent rows are really in the
order printed is not a question it answers. `halves` is the distance
between the minima of two halves of the row's rounds — the statistic [the
wrappers page][wrappers] prints, arriving here under a key of its own so a
number in a saved run means what its key says — and it does answer that
question: near zero, the row agreed with itself measured twice, seconds
apart; a large fraction of a neighbour's lead, and this run has not
separated the two. [ISS 47][i47] moved the script to it, and [ISS 53][i53]
is the re-measurement that carries it.

Four rounds and not more, where the wrappers page takes ten: this page's
pure-Python rows are orders of magnitude slower, which is why its loop count
is per row rather than per table, and every extra round is paid on those rows
too. Read either column as the computer and not as the library — as what else
the machine was doing while a row was measured — and neither as an error bar.
Neither can see the machine drifting between one run and the next; the
wrappers page pays for a second pass and states that size, and this page does
not, so nothing here says it.

The inputs are every BIP340 signing vector and every BIP32 chain the
vendored files publish, cycled one per call; the address rows are the
exception, one witness-v0 and one witness-v1 address being what is
vendored, so they call one input.

**BIP340 signing is two tables now, a fresh key and a key held already**, and
the split corrects a comparison as much as it adds one. A signer does not
sign one message any more than a verifier verifies one signature, and no page
in this project timed a held one on either of btclib's arms — [ISS 42][i42].
It also puts the old single table right: buidl and embit are called through an
object built from the secret, and that object was built once outside the
clock, so those rows were already the held shape while btclib's row was handed
32 octets and built everything per call. Two tables put each library in both
shapes.

What each library holds is different, and it is a reading of the source rather
than of the shape of its API. btclib's `ssa.Signer` holds the keypair that
`ssa.sign_` builds and wipes inside every call. buidl's `PrivateKey` computes
`secret * G` in its constructor and `sign_schnorr` reads the point it kept.
embit's holds the 32 secret octets and validates them, and hands those octets
to the bundled library, which builds the keypair inside every call — so a held
key object is not a held keypair, and holding embit's saves the validation and
nothing else. The pair of tables is where a reader reads that off instead of
being told it.

btclib's held rows answer with the signature's octets where its fresh rows
answer with a `Sig`, that being what the two spellings offer, so the pair
prices the change of call a caller would make rather than the keypair on its
own. buidl and embit answer with objects of their own in both tables.

**btclib's four ECDSA signing rows and its two BIP340 pairs state both flags
of the check in their name:** `grind` or `nogrind`, then `verify` or
`noverify`, in the order the call performs them. btclib verifies the
signature it has just made before answering with it, by default and on both
arms, and the grinding row pays the check once — the loop and the check
cross into the bindings together, so what is proved is the signature the
loop kept rather than every attempt discarded, the ordering [ISS 982
(btclib-org/btclib)][i982] asked for. The unchecked row of each pair is what
compares with the libraries beside it that verify nothing; the checked row
is what the guarantee costs — printing one of the two alone would make
whichever comparison it is not in wrong. [ISS 23][i23] is the shape these
rows settled on and [ISS 53][i53] the re-measurement that produced them; [the
wrappers table][wrappers] took the same shape for the same question first.

Every row states both of its flags for the same reason a library that takes
no argument is named as plainly as one that does: what a row did is a
property of the row, not a favour its API granted, and python-ecdsa having
no way to ask for a check is why its row says `noverify` rather than why it
should say nothing.

Which rows check was read out of each library rather than assumed, and the
two schemes do not answer alike. No comparand here checks an ECDSA signature
it has just made. buidl checks a BIP340 one — `sign_schnorr` verifies under
the point its key holds and raises on a failure, which is BIP340's own last
step — so in that table it is btclib's checked row that has a comparand and
its unchecked row that stands alone, and what checks in buidl's row is Python
where what checks in btclib's is libsecp256k1.

<!-- output: begin -->
```text
method  : 4 rounds per row in two halves, minimum kept; calls per row
command : uv run python scripts/03-libraries.py

what a timing contains
  one call per iteration, its answer discarded: no row checks
  itself, and no comparison is inside a measured loop
  the answers are checked in tests/vectors_test.py, and where
  each script builds its fixtures, which is before any clock

1. ECDSA sign (32-byte digest)
                                  μs/call     vs best   halves
  pycoin_nogrind_noverify           12.35        1.0x     0.00   (4x50,000 calls)
  embit_nogrind_noverify            14.12        1.1x     0.01   (4x50,000 calls)
  btclib_nogrind_noverify           15.03        1.2x     0.03   (4x50,000 calls)
  btclib_grind_noverify             27.14        2.2x     0.01   (4x20,000 calls)
  embit_grind_noverify              29.56        2.4x     0.01   (4x20,000 calls)
  btclib_nogrind_verify             35.47        2.9x     0.04   (4x20,000 calls)
  btclib_grind_verify               47.45        3.8x     0.06   (4x15,000 calls)
  bitcoinlib_nogrind_noverify      189.88       15.4x     1.06   (4x8,000 calls)
  ecdsa_nogrind_noverify           291.15       23.6x     0.40   (4x5,000 calls)
  buidl_nogrind_noverify         30226.69     2447.9x     5.61   (4x50 calls)

2. ECDSA verify (32-byte digest)
                                  μs/call     vs best   halves
  pycoin                            13.89        1.0x     0.04   (4x50,000 calls)
  btclib                            19.80        1.4x     0.04   (4x50,000 calls)
  embit                             24.16        1.7x     0.02   (4x50,000 calls)
  bitcoinlib                       221.73       16.0x     3.62   (4x7,000 calls)
  ecdsa                           1096.40       78.9x     4.70   (4x3,000 calls)
  buidl                          60066.28     4324.3x    38.31   (4x25 calls)

3. BIP340 sign (32-byte message, a fresh key)
                                  μs/call     vs best   halves
  embit_noverify                    21.55        1.0x     0.01   (4x50,000 calls)
  btclib_noverify                   22.22        1.0x     0.05   (4x50,000 calls)
  btclib_verify                     35.68        1.7x     0.02   (4x30,000 calls)
  buidl_verify                  142279.38     6601.1x  3324.25   (4x10 calls)

4. BIP340 sign (32-byte message, the key held already)
                                  μs/call     vs best   halves
  btclib_noverify                    8.61        1.0x     0.00   (4x50,000 calls)
  embit_noverify                    21.24        2.5x     0.10   (4x50,000 calls)
  btclib_verify                     21.88        2.5x     0.04   (4x30,000 calls)
  buidl_verify                  111516.39    12945.7x  1385.40   (4x20 calls)

5. BIP340 verify (32-byte message)
                                  μs/call     vs best   halves
  btclib                            21.40        1.0x     0.02   (4x50,000 calls)
  embit                             25.11        1.2x     0.01   (4x50,000 calls)
  buidl                          69000.12     3224.4x    60.76   (4x25 calls)

6. BIP32 derive, seed to child, every chain BIP32 publishes
                                  μs/call     vs best   halves
  pycoin                            47.61        1.0x     0.04   (4x30,000 calls)
  btclib                            62.04        1.3x     0.37   (4x30,000 calls)
  embit                             85.95        1.8x     0.11   (4x15,000 calls)
  buidl                         101675.45     2135.4x 10281.93   (4x12 calls)

7. base58check encode, a P2PKH address from a hash160
                                  μs/call     vs best   halves
  embit                              2.08        1.0x     0.01   (4x200,000 calls)
  buidl                              2.23        1.1x     0.01   (4x200,000 calls)
  btclib                             2.35        1.1x     0.01   (4x200,000 calls)
  bitcoinlib                         2.48        1.2x     0.00   (4x100,000 calls)
  pycoin                             3.66        1.8x     0.00   (4x200,000 calls)

8. base58check decode, a hash160 from a P2PKH address
                                  μs/call     vs best   halves
  embit                              2.18        1.0x     0.00   (4x200,000 calls)
  btclib                             2.46        1.1x     0.00   (4x200,000 calls)
  buidl                              2.88        1.3x     0.01   (4x200,000 calls)
  pycoin                             3.53        1.6x     0.01   (4x200,000 calls)
  bitcoinlib                         4.11        1.9x     0.04   (4x100,000 calls)

9. bech32 encode, a witness-v0 address from a 20-byte program
                                  μs/call     vs best   halves
  btclib                             7.89        1.0x     0.00   (4x200,000 calls)
  buidl                             11.52        1.5x     0.01   (4x100,000 calls)
  bitcoinlib                        26.25        3.3x     0.47   (4x200,000 calls)
  embit                             26.29        3.3x     0.13   (4x200,000 calls)

10. bech32 decode, a 20-byte program from a witness-v0 address
                                  μs/call     vs best   halves
  btclib                             6.95        1.0x     0.01   (4x200,000 calls)
  buidl                             10.18        1.5x     0.03   (4x100,000 calls)
  bitcoinlib                        14.42        2.1x     0.05   (4x200,000 calls)
  embit                             14.48        2.1x     0.63   (4x200,000 calls)

11. bech32m encode, a witness-v1 address from a 32-byte program
                                  μs/call     vs best   halves
  btclib                            13.11        1.0x     0.00   (4x200,000 calls)
  buidl                             16.98        1.3x     0.05   (4x100,000 calls)
  embit                             39.18        3.0x     0.10   (4x200,000 calls)

12. bech32m decode, a 32-byte program from a witness-v1 address
                                  μs/call     vs best   halves
  btclib                            11.43        1.0x     0.07   (4x200,000 calls)
  buidl                             15.17        1.3x     0.01   (4x100,000 calls)
  embit                             21.89        1.9x     0.01   (4x200,000 calls)
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

Five other sets of benchmarks are published in `results/`, each with its own
comparands:

- [the libsecp256k1 wrappers][wrappers] — four packages that wrap one C
  library, and which revision of it each vendors
- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show
- [Silent Payments][sp] — what only `btclib_secp256k1` offers of BIP352,
  which no other comparand here implements at all

[wrappers]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/01-libsecp256k1.md
[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md
[sp]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/06-silentpayments.md
[i23]: https://github.com/btclib-org/btclib-benchmarks/issues/23
[i42]: https://github.com/btclib-org/btclib-benchmarks/issues/42
[i47]: https://github.com/btclib-org/btclib-benchmarks/issues/47
[i53]: https://github.com/btclib-org/btclib-benchmarks/issues/53
[i982]: https://github.com/btclib-org/btclib/issues/982

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
