# The libsecp256k1 wrappers

## The packages downloaded from PyPI

The `libsecp256k1 pin` column is the premise of the table below: four
wrappers of one library, not four libraries — four vendored trees of one
project, at different revisions.

None of the four can be asked for its revision at run time: no compiled
artifact exports a version symbol, and each package's version attribute
answers for the package rather than for the library. So each pin below is
recorded rather than read, keyed to the build it was read from, and prints
`unrecorded` for any other — an upgraded comparand says it has outgrown its
pin rather than repeating one that has quietly stopped being true. A wrapper
recording its own vendored revision at build time would end the recording
here.

`btclib-secp256k1` is the one row with a commit where the others have a
date: it resolves from its branch until the release these rows are written
against is published, so what identifies that build is the commit, and that
is what its pin is keyed to. The others are releases, and their version is
what identifies them.

<!-- provenance: begin -->
```text
package           version  released           libsecp256k1 pin      bindings
btclib-secp256k1  0.8.0.3  main@68657e14c47c  v0.8.0                cffi
electrum-ecc      0.0.7    2026-02-25         v0.7.1                ctypes
coincurve         21.0.0   2025-03-08         v0.6.0                cffi
secp256k1         0.14.0   2021-11-06         9526874d, pre-v0.1.0  cffi
```
<!-- provenance: end -->

## This run

3.13 rather than 3.14 is not this page's choice: coincurve and secp256k1
publish no cp314 wheel, and neither builds from source without
`pkg-config`, so the interpreter below is the newest that runs all four
wrappers.

<!-- run: begin -->
```text
when    : 2026-08-17 12:17 CEST (10:17 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

Thirteen tables over six operations, each sorted fastest first and ratioed
against whichever of its rows came out quickest. The numbers are an order of
magnitude, never a figure to quote.

What a timing contains is one call per iteration and its answer thrown away.
Nothing is compared, verified or asserted anywhere in this benchmark —
whether these packages answer correctly is the suite's subject:
`tests/vectors_test.py` for the operations a published file covers, and
`tests/wrappers_test.py` for the rest, which is most of this page.

The inputs are drawn from a seed written into the script: a secret key and a
message per call, and as many of each as every table together has calls, so
each table reads a slice of its own. A round consumes that slice exactly once,
no row measures one input repeated, and no table is quick because the one
before it left the same key in a cache. Every table starts from the same
shapes — the keys as 32-byte scalars, the public keys derived from them, the
signatures made once in the fixtures — and no row is handed an object a
package built: whatever an API makes a caller construct before it can work is
constructed inside the call that needs it.

Random rather than published, because four wrappers of one C library compute
the same arithmetic by construction: a vector proves nothing here that
another input would not, and what this page is read for is the boundary
crossing.

Most of the thirteen are one operation asked twice, differing by an encoding
rather than by any arithmetic, so what a pair prices is the encoding. Two
encodings run through the page. A signature is DER or the 64-byte compact
form, which splits signing in two and verification in two. A public key is
33 octets or 65, which splits the parse in two, verification in two again,
and the tweak in two. The members of a pair share their inputs down to the
byte: the same keys, the same signatures, one serialization of each.

Only what a package offers is measured. Where its own API has no such call
the row reads `NA` — coincurve signs and verifies ECDSA in DER alone, so it
is absent from every compact table. Reaching into the cffi or ctypes bindings
underneath would produce a number, and the number would be libsecp256k1's
rather than the wrapper's.

<!-- method: begin -->
```text
method  : 10 rounds per row, minimum kept; the call count is per table
command : uv run python scripts/01-libsecp256k1.py
```
<!-- method: end -->

## Results

The order below is the argument rather than the operations' importance. The
parse pair comes first because every verification and every tweak repeats one
of those parses per call, so it is read isolated before being met eight more
times inside something else. Signing comes last because it parses no public
key at all.

Two habits of reading apply throughout. A pair of tables is read by
subtracting, not by dividing — the ratio column is against the fastest row in
its own table, so one difference shows up as a large ratio where the base row
is small and a small one where it is not. And where two rows are close enough
that a round or two could reorder them, the `spread` column is how to see it
without waiting for another run: a gap smaller than the scatter behind either
row is not a gap this run settled, and which of the two prints first is then
a property of the run rather than of the packages.

What the spread is not is a property of the row. It is the slowest of ten
rounds less the quickest, so it reports the worst interruption a row happened
to catch, and the same row measured twice will print a tenth of a microsecond
once and a couple of microseconds the next time while its minimum does not
move. A wide spread beside a stable minimum says the machine was busy for one
round out of ten, not that the package is erratic — which is why the minimum
is what the other column carries.

### Public key parse

<!-- tables: parse: begin -->
```text
1. public key parse (a 65-byte uncompressed key)
                               μs/call     vs best   spread
  btclib_secp256k1                0.22       1.00x     0.01   (10x400,000 calls)
  coincurve                       0.24       1.07x     0.01   (10x400,000 calls)
  secp256k1                       0.64       2.85x     0.02   (10x400,000 calls)
  electrum_ecc                    1.17       5.20x     0.02   (10x400,000 calls)

2. public key parse (a 33-byte compressed key)
                               μs/call     vs best   spread
  btclib_secp256k1                2.35       1.00x     0.08   (10x100,000 calls)
  coincurve                       2.38       1.01x     0.02   (10x100,000 calls)
  secp256k1                       2.77       1.18x     0.19   (10x100,000 calls)
  electrum_ecc                    3.32       1.41x     0.49   (10x100,000 calls)
```
<!-- tables: parse: end -->

The uncompressed parse is the cheapest thing on this page: the encoding
carries y, so a parser reads two coordinates and checks they are on the
curve. The compressed parse of the same key costs many times it, and the
difference is one field square root — recovering the y that the shorter
encoding left out.

That difference is the page's recurring subject, because every table after
this one parses a public key inside each call. This pair is what to subtract
from them, and the four packages agree on it closely enough that the
subtraction is worth doing.

electrum-ecc pays the most in both, and for a reason its own API states: an
`ECPubkey` holds x and y as Python integers rather than the object
libsecp256k1 read, so the constructor parses and then serializes the point
back out to get them — and every later use parses again. Its verification and
tweak rows are where that second parse is paid.

### ECDSA verify

<!-- tables: dsa-verify: begin -->
```text
3. ECDSA verify (DER signature, a 65-byte key parsed per call)
                               μs/call     vs best   spread
  btclib_secp256k1               13.14       1.00x     1.10   (10x10,000 calls)
  coincurve                      13.48       1.03x     0.59   (10x10,000 calls)
  secp256k1                      14.01       1.07x     0.32   (10x10,000 calls)
  electrum_ecc                   17.58       1.34x     0.44   (10x10,000 calls)

4. ECDSA verify (DER signature, a 33-byte key parsed per call)
                               μs/call     vs best   spread
  btclib_secp256k1               15.17       1.00x     2.11   (10x10,000 calls)
  coincurve                      15.32       1.01x     2.99   (10x10,000 calls)
  secp256k1                      15.95       1.05x     9.29   (10x10,000 calls)
  electrum_ecc                   19.62       1.29x     0.39   (10x10,000 calls)

5. ECDSA verify (64-byte signature, a 65-byte key parsed per call)
                               μs/call     vs best   spread
  btclib_secp256k1               13.08       1.00x     0.32   (10x10,000 calls)
  secp256k1                      13.87       1.06x     0.61   (10x10,000 calls)
  electrum_ecc                   15.25       1.17x     0.59   (10x10,000 calls)
  coincurve                         NA

6. ECDSA verify (64-byte signature, a 33-byte key parsed per call)
                               μs/call     vs best   spread
  btclib_secp256k1               15.22       1.00x     0.15   (10x10,000 calls)
  secp256k1                      15.85       1.04x     0.73   (10x10,000 calls)
  electrum_ecc                   17.38       1.14x     0.20   (10x10,000 calls)
  coincurve                         NA
```
<!-- tables: dsa-verify: end -->

Four tables, one per combination of the two encodings. Read across the
signature encoding and, for three of the four, nothing happens at all: DER
and the 64-byte form differ by a header libsecp256k1 reads once, and the rows
land on the same number to the second decimal. That is the expected answer,
and it is worth having measured — the compact form is often described as the
cheap one, and for a wrapper that parses either in C it is not.

electrum-ecc is the exception, and pays a real amount for DER. Its
`ecdsa_verify` takes the 64-byte form and nothing else, so its DER row calls
`ecdsa_sig64_from_der_sig` first — a conversion written in Python, on the
caller's side of the boundary. The gap between its two rows is that
conversion, and it is the same order as a public key's square root.

Read across the key encoding and the parse pair reappears. Verification under
a 33-byte key is dearer than under the same key in 65 octets, in both
signature encodings, by close to what tables 1 and 2 charge for exactly that
difference. Nothing else changed between the two tables: the same keys, the
same signatures, one serialization of each.

Within a table the four land close together, which is what a table of one C
library should look like. What little separates them is what a wrapper makes
a caller do around the call, not the verification itself.

### BIP340 verify

<!-- tables: ssa-verify: begin -->
```text
7. BIP340 verify (a 65-byte key handed in, the x-only one taken from it)
                               μs/call     vs best   spread
  btclib_secp256k1               13.42       1.00x     0.22   (10x10,000 calls)
  secp256k1                      13.69       1.02x     3.74   (10x10,000 calls)
  electrum_ecc                   17.30       1.29x     0.12   (10x10,000 calls)
  coincurve                         NA

8. BIP340 verify (the x-only key handed in, parsed per call)
                               μs/call     vs best   spread
  btclib_secp256k1               15.28       1.00x     0.14   (10x10,000 calls)
  coincurve                      15.36       1.01x     0.39   (10x10,000 calls)
  secp256k1                      15.86       1.04x     0.20   (10x10,000 calls)
  electrum_ecc                   19.42       1.27x     0.16   (10x10,000 calls)
```
<!-- tables: ssa-verify: end -->

The same question a third way, and the pair comes out the opposite way round
from how the tables are usually described. The x-only key is the compressed
form with even the parity byte gone, and handing a verifier that is *dearer*
than handing it the whole 65-byte point — again by about what the parse pair
charges, because an x is an x whose y has to be recovered.

Taken with the four ECDSA tables above, that is five independent readings of
one square root, agreeing across packages that share no Python. So a caller
holding a full public key should not shorten it before verifying, and
BIP340's x-only convention is a saving in what a transaction carries rather
than in what verifying costs.

coincurve is absent from the 65-byte table because its API has no such
spelling: `PublicKeyXOnly` is the only type of its that carries a Schnorr
`verify`.

### Public key tweak by a scalar

<!-- tables: tweak: begin -->
```text
9. public key tweak by a scalar, a 65-byte key
                               μs/call     vs best   spread
  btclib_secp256k1               10.16       1.00x     0.73   (10x10,000 calls)
  coincurve                      10.25       1.01x     0.21   (10x10,000 calls)
  secp256k1                      13.84       1.36x     0.09   (10x10,000 calls)
  electrum_ecc                   22.71       2.24x     1.10   (10x10,000 calls)

10. public key tweak by a scalar, a 33-byte key
                               μs/call     vs best   spread
  btclib_secp256k1               12.26       1.00x     0.31   (10x10,000 calls)
  coincurve                      12.50       1.02x     0.28   (10x10,000 calls)
  secp256k1                      16.11       1.31x     0.53   (10x10,000 calls)
  electrum_ecc                   25.08       2.05x     0.76   (10x10,000 calls)
```
<!-- tables: tweak: end -->

BIP32's step rather than BIP32: none of these four packages implements
derivation, and all four expose the primitive it is built from. The key
encoding costs here what it has cost everywhere else, which is the sixth
reading of the same square root.

`electrum-ecc` is the exception on this page and the row worth reading. It
has no tweak-add on `ECPubkey`, so its row multiplies the generator by the
scalar and adds the two points — two crossings into the C library where the
others make one, and a generator multiplication is not a crossing's worth of
work but an operation's. That is why its row is last by about what the whole
tweak costs the others, rather than by the small margin its other rows are
behind by.

BIP32 proper is in [the libraries table][libs], where the comparands are
python libraries rather than secp256k1 wrappers.

### ECDSA sign

<!-- tables: dsa-sign: begin -->
```text
11. ECDSA sign (32-byte digest, DER out)
                               μs/call     vs best   spread
  btclib_secp256k1               12.09       1.00x     0.84   (10x10,000 calls)
  btclib_secp256k1_grind         24.14       2.00x     4.67   (10x10,000 calls)
  secp256k1                      26.97       2.23x     6.87   (10x10,000 calls)
  coincurve                      26.97       2.23x     0.21   (10x10,000 calls)
  btclib_secp256k1_checked       32.54       2.69x     0.99   (10x10,000 calls)
  electrum_ecc                   47.97       3.97x     0.52   (10x10,000 calls)
  electrum_ecc_grind             60.88       5.03x     1.62   (10x10,000 calls)

12. ECDSA sign (32-byte digest, 64-byte compact out)
                               μs/call     vs best   spread
  btclib_secp256k1               11.89       1.00x     0.16   (10x10,000 calls)
  btclib_secp256k1_grind         24.25       2.04x     0.10   (10x10,000 calls)
  secp256k1                      26.59       2.24x     2.36   (10x10,000 calls)
  btclib_secp256k1_checked       32.38       2.72x     0.91   (10x10,000 calls)
  electrum_ecc                   45.40       3.82x     0.70   (10x10,000 calls)
  electrum_ecc_grind             58.32       4.90x     9.79   (10x10,000 calls)
  coincurve                         NA
```
<!-- tables: dsa-sign: end -->

Signing parses no public key, so nothing above carries over and these tables
spread far wider than any verification table does. What spreads them is not
arithmetic: every row calls one C library to make one signature.

Two habits do it. Two of the four sign only through a key object of their own
— coincurve's `PrivateKey` and secp256k1-py's — and building one derives the
public key, work a signature does not need and a caller cannot decline. And
three of them verify the signature they just made before handing it back:
electrum-ecc inside `ecdsa_sign`, coincurve inside `sign_schnorr`, and
btclib-secp256k1 by default. Only the last of the three takes an argument that
stops it, which is why it is the one with two rows here.

**No single row of that pair compares with all three of the others**, and that
is what the pair is for. The unchecked row is the operation coincurve performs
in ECDSA and secp256k1-py in both schemes; the checked row is the operation
electrum-ecc performs in both its ECDSA rows. Printing one of the two and
calling it btclib-secp256k1's signing time would make one of those comparisons
wrong, and which one would depend on which row was printed.

Read that way the tables stop being a ranking and start being a subtraction.
The unchecked row against coincurve's and secp256k1-py's leaves what their key
object costs, and it agrees closely with the difference the same two rows show
in every other table on this page. The checked row against electrum-ecc's
leaves what remains of electrum-ecc's own overhead once the check is on both
sides — much less than the ordinary rows suggest, and in the compact table
less again, the DER row paying for a conversion its own module writes in
Python.

**What the check costs is not the same in the two schemes**, and the ECDSA
tables are the expensive half. Verifying needs the public key and signing did
not, so the check has to derive one first: the gap between the checked and
unchecked rows here is a verification plus that derivation, and it is larger
than the same gap in the BIP340 table by about a generator multiplication.
That multiplication is not on this page — [the two-paths table][two-paths]
times it — but its size is what the difference between the two schemes'
checks comes to. Which makes this the one row on the page that prices a
default rather than an operation — the argument exists, and a caller who does
not pass it pays for a proof that libsecp256k1 already gave.

The grinding rows hold the check off on **both** sides, and they have to.
A pair prices one difference: btclib-secp256k1's grinding pair prices the
loop, electrum-ecc's prices the loop with the check present in both of its
rows, and each ratio is therefore about grinding alone. So the two ratios are
comparable while the rows they are ratios of are not. A grinding row is the
ordinary row with about one extra signature in it, half of all draws needing
none and the tail paying for the rest — and that difference comes out nearly
the same for both packages, in both encodings, which is what should happen to
two Python loops around the same C call.

Read the ratio column for any of this and none of it is visible. The ratio is
against the fastest row in the table, so btclib-secp256k1's grinding row
doubles because its base is nearly all signature, and electrum-ecc's grows by
a fraction because its base is nearly all something else.

### BIP340 sign

<!-- tables: ssa-sign: begin -->
```text
13. BIP340 sign (32-byte message)
                               μs/call     vs best   spread
  btclib_secp256k1               15.88       1.00x     0.70   (10x10,000 calls)
  secp256k1                      22.89       1.44x     0.12   (10x10,000 calls)
  btclib_secp256k1_checked       29.46       1.86x     0.85   (10x10,000 calls)
  coincurve                      43.24       2.72x     1.07   (10x10,000 calls)
  electrum_ecc                   49.25       3.10x     0.60   (10x10,000 calls)
```
<!-- tables: ssa-sign: end -->

This is the one operation where a keypair has to be built no matter what:
ECDSA takes the secret key as it is, and Schnorr does not. That toll is not
read across the table — every row pays it, so it moves them all together —
but down a column against the ECDSA table above: three of the four sign a
Schnorr message for more than they sign an ECDSA digest, and the keypair is
the difference.

secp256k1-py is the exception, and it is one because its ECDSA row was
already paying a toll of its own: the key object it signs through derives the
public key too, which is the same work under a different name. Where a
package pays for a keypair twice, asking for BIP340 costs it nothing extra.

**The check is cheaper here than in ECDSA, and the keypair is why.** Schnorr
needs the public key to sign at all, so verifying afterwards has the point
already in hand where ECDSA has to go and get it. What is left is a bare
verification, and it comes out close to what this page's own BIP340 verify
table charges for one — which is the arithmetic agreeing with itself across
two operations that were measured independently.

It is also the one place where the check is what a specification asks for.
BIP340's *Default Signing* ends with a verification, so the checked row is the
scheme performed as written and the unchecked row is the shortcut. ECDSA
carries no such step, which is the whole reason one default cannot be right
for both.

The checked row is the one coincurve's is comparable with, `sign_schnorr`
verifying and offering nothing that stops it; the unchecked row is
secp256k1-py's comparand.

What spreads a signing table is therefore the wrapper's habits and not the
keypair, which is why the ECDSA table above spreads more widely than this one
while having no keypair in it at all.

## What the rows leave out

Nothing is measured that a package does not offer. A row is either its own
API's call or `NA`, and no gap is filled from the C underneath: a wrapper
that leaves an encoding to its caller is a wrapper that leaves an encoding to
its caller, and a table that hid it would be a table about libsecp256k1.

Low-r grinding is offered by two of the four, `electrum-ecc` and
`btclib-secp256k1`, so each ECDSA signing table carries their grinding rows
beside their ordinary ones rather than a column half `NA`. A row that is
retried until r fits in 32 octets is a multiple of one that is not, and every
other row on this page signs once, so keeping the two apart is what makes
either comparable. What the pair prices is an octet saved in every
transaction that spends, paid for at signing time.

It is also the one comparison here whose subject is not a crossing.
libsecp256k1 exports no grinding option, so both packages write the loop
themselves in Python, and the two rows are those two loops. They spell it
opposite ways round — electrum-ecc grinds unless told not to, and
btclib-secp256k1 does not grind unless told to — and the rows are named for
the call rather than for the default, a default being a decision about
callers rather than a cost.

Nothing here says whether any of the four is correct. That is deliberate and
it is not a gap, but it is a debt the suite has to carry rather than one
nobody pays. `tests/vectors_test.py` runs BIP340's vectors, Wycheproof's and
BIP32's against every implementation this project measures, in the
configuration it measures it in, negative cases included — which reaches
three of the operations timed here, those being the ones somebody published
a file for.

`tests/wrappers_test.py` is the other ten, and it is a different kind of
test because there is nothing to compare against. Signing ECDSA is checked
by RFC6979 being a function of the key and the message, so four correct
wrappers have one answer between them; grinding by the octet it exists to
save; parsing by the round trip; the compressed key and the compact
signature by giving the same verdict as the encodings a file does publish;
BIP340's full key by agreeing with its own x; and the tweak against
`secp256k1lab`, which computes the point in Python and shares no C with any
of them. Every case goes through the same API a row here times, never the
bindings under it — a test that reached those would pass while the wrapper
around them was broken, which is the whole subject of this page.

A benchmark that re-checked any of it would be a slower copy of a test that
already exists, over inputs nobody published.

## More benchmarks

Four other sets of benchmarks are published in `results/`, each with its own
comparands:

- [btclib's two paths][two-paths] — btclib against itself, its pure-Python
  arithmetic against the wrappers measured here
- [python libraries][libs] — where a wrapper, if there is one, is just one
  component of a python library
- [every pure-Python implementation][pure] — the same operations with no
  bindings anywhere
- [one key, every signature under it][reuse] — what the second verification
  under a key costs, which a table of fresh keys cannot show

[two-paths]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/02-btclib-vs-btclib.md
[libs]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/03-libraries.md
[pure]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/04-pure-python.md
[reuse]: https://github.com/btclib-org/btclib-benchmarks/blob/main/results/05-key-reuse.md

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
