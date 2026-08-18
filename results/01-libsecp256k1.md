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
is what its pin is keyed to. Two of the others are releases whose version
identifies them. The fourth is not, and the pair of columns is why both are
here: `secp256k1` serves an sdist carrying one libsecp256k1 and wheels,
re-published under that same version years afterwards, carrying another, so
the version names a release and the date names which of its builds ran.
`uv run python scripts/artifacts.py` says which artifact each comparand here
resolved to on the machine reading it.

<!-- provenance: begin -->
```text
package           version  released           libsecp256k1 pin  bindings
btclib-secp256k1  0.8.0.3  main@52f913e706f8  v0.8.0            cffi
electrum-ecc      0.0.7    2026-02-25         v0.7.1            ctypes
secp256k1         0.14.0   2026-01-29         v0.6.0            cffi
coincurve         21.0.0   2025-03-08         v0.6.0            cffi
```
<!-- provenance: end -->

## This run

3.13 rather than 3.14 is not this page's choice: coincurve and secp256k1
publish no cp314 wheel, and neither builds from source without
`pkg-config`, so the interpreter below is the newest that runs all four
wrappers.

<!-- run: begin -->
```text
when    : 2026-08-18 09:43 CEST (07:43 UTC)
machine : Apple M5, macOS 26.6 (build 25G72), arm64
python  : 3.13.14
```
<!-- run: end -->

## The benchmarks

The tables below are grouped by operation, each sorted fastest first and
ratioed against whichever of its rows came out quickest. The numbers are an
order of magnitude, never a figure to quote.

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
constructed inside the call that needs it. The two held signing tables are
the exception, and holding the key is what they are about: tables 15 and 17
are handed the object each package offers a caller who will sign again, built
from the keys of the fresh table each is paired with and in that table's
order, so a pair prices the holding and no package is handed something another
was not.

Random rather than published, because four wrappers of one C library compute
the same arithmetic by construction: a vector proves nothing here that
another input would not, and what this page is read for is the boundary
crossing.

Most of them are one operation asked twice, differing by an encoding rather
than by any arithmetic, so what a pair prices is the encoding. Two encodings
run through the page. A signature is DER or the 64-byte compact form, which
splits signing in two and verification in two. A public key is 33 octets or
65, which splits the parse in two, verification in two again, and the tweak
in two. The members of a pair share their inputs down to the byte: the same
keys, the same signatures, one serialization of each.

Two pairs differ by something else. Signing is asked twice in each scheme,
over one encoding, under a key handed over as bytes and under the object each
package offers for signing again — the only question on this page whose
subject is what a caller kept rather than what an API costs.

Only what a package offers is measured. Where its own API has no such call
the row reads `NA` — coincurve signs and verifies ECDSA in DER alone, so it
is absent from every compact table. Reaching into the cffi or ctypes bindings
underneath would produce a number, and the number would be libsecp256k1's
rather than the wrapper's.

<!-- method: begin -->
```text
method  : 10 rounds per row in two halves, minimum kept; calls per table
command : uv run python scripts/01-libsecp256k1.py
```
<!-- method: end -->

## Results

The order below is the argument rather than the operations' importance: what
a later table contains is read before it. The parse pair comes first because
every verification and every tweak repeats one of those parses per call, so it
is read isolated before being met eight more times inside something else. The
derivation follows, because every key object on this page performs one as it
is built and nothing else on the page says how much of a constructor is the
curve. Then the tweak, whose own body is a parse and one addition, then
verification. Signing is last of the operations because it parses no public
key at all — what its tables carry instead is a constructor, and a
constructor is the derivation already read.

Two habits of reading apply throughout. A pair of tables is read by
subtracting, not by dividing — the ratio column is against the fastest row in
its own table, so one difference shows up as a large ratio where the base row
is small and a small one where it is not. And where two rows are close enough
that a round or two could reorder them, the `halves` column is how to see it
without waiting for another run: a gap smaller than the distance behind either
row is not a gap this run settled, and which of the two prints first is then
a property of the run rather than of the packages.

The column is that comparison and nothing more. The rounds behind a row are
split in half and the column is how far the two halves' minima sat apart —
which is what its heading is short for, and what the saved run keys as
`halves_apart` — so what it states is this run's agreement with itself. A row
whose distance is a large fraction of its neighbour's lead has not been
separated from that neighbour by this run; a row whose distance is near zero
has in effect been measured twice and agreed.

Agreement with another run is what it does not state. The two halves are
seconds apart and a table's rows are minutes apart, so what the column catches
is the machine's noise and not its drift — the same row measured again on
another day can differ by more than any distance on this page. That is the
reason the numbers here are an order of magnitude rather than a figure to
quote, and the reason a ratio is read instead of a difference.

It is deliberately not the slowest round less the quickest. A maximum over ten
samples reports the worst interruption a row happened to catch, has enormous
variance by construction — the same rows measured twice print minima that
agree and maxima that do not — and is read as though the package were the
erratic thing. Neither column says anything about the *variability* of an
operation, and none of these operations has any: they are the same arithmetic
every call, and what varies is the machine around them.

A maximum less a minimum is, however, still what [the libraries page][libs]
prints, under `spread`, that page not having been re-measured under the
change. The two headings are what now says the two columns are not one
number: they answer different questions and are not comparable in either
direction, this one shrinking as rounds are added and that one growing. Both
pages define the column they print where they introduce it.

### Public key parse

<!-- tables: parse: begin -->
```text
1. public key parse (a 65-byte uncompressed key)
                                        μs/call     vs best   halves
  btclib_secp256k1                         0.22       1.00x     0.00   (10x400,000 calls)
  coincurve                                0.24       1.09x     0.00   (10x400,000 calls)
  secp256k1                                0.64       2.87x     0.00   (10x400,000 calls)
  electrum_ecc                             1.19       5.33x     0.01   (10x400,000 calls)

2. public key parse (a 33-byte compressed key)
                                        μs/call     vs best   halves
  btclib_secp256k1                         2.33       1.00x     0.00   (10x100,000 calls)
  coincurve                                2.39       1.03x     0.00   (10x100,000 calls)
  secp256k1                                2.77       1.19x     0.01   (10x100,000 calls)
  electrum_ecc                             3.31       1.42x     0.02   (10x100,000 calls)
```
<!-- tables: parse: end -->

The uncompressed parse is the cheapest thing on this page: the encoding
carries y, so a parser reads two coordinates and checks they are on the
curve. The compressed parse of the same key costs many times it, and the
difference is one field square root — recovering the y that the shorter
encoding left out.

That difference is the page's recurring subject, because every table that
takes a public key parses one inside each call — which is every table below
except the derivation pair, whose input is a secret. This pair is what to
subtract from them, and the four packages agree on it closely enough that the
subtraction is worth doing.

electrum-ecc pays the most in both, and for a reason its own API states: an
`ECPubkey` holds x and y as Python integers rather than the object
libsecp256k1 read, so the constructor parses and then serializes the point
back out to get them — and every later use parses again. Its verification and
tweak rows are where that second parse is paid.

### Public key from a private key

<!-- tables: derive: begin -->
```text
3. public key from a private key (32-byte secret, 65-byte key out)
                                        μs/call     vs best   halves
  coincurve                                7.63       1.00x     0.01   (10x10,000 calls)
  btclib_secp256k1                         7.72       1.01x     0.02   (10x10,000 calls)
  secp256k1                               15.17       1.99x     0.04   (10x10,000 calls)
  electrum_ecc                            16.77       2.20x     0.00   (10x10,000 calls)

4. public key from a private key (32-byte secret, 33-byte key out)
                                        μs/call     vs best   halves
  coincurve                                7.62       1.00x     0.03   (10x10,000 calls)
  btclib_secp256k1                         7.73       1.01x     0.00   (10x10,000 calls)
  secp256k1                               15.20       1.99x     0.00   (10x10,000 calls)
  electrum_ecc                            16.80       2.20x     0.01   (10x10,000 calls)
```
<!-- tables: derive: end -->

This is the one operation on the page where the C library is most of what a
row costs, which is either the argument for the pair or the argument against
it: it prices libsecp256k1 rather than a wrapper, and it is the scale
everything else is read against. It is here as the second of those, and early
because of it — without it the held tables below price a key object at more
than a signature and nothing on the page says how much of that is the curve.

**The pair is the parse pair read the other way round.** Going in, the
compressed form is an x whose y the parser solves for and the uncompressed
form carries it, which is what tables 1 and 2 price. Coming out, the y is in
hand whichever form is asked for, and what differs is whether its octets are
written. So a package's two rows here differ by a serialization and by no
arithmetic at all, where its two rows in the parse pair differ by a square
root.

**What the pair finds is that the serialization is free**, and it is a
negative result stated rather than a table left out: every package's two rows
land inside this run's own agreement with itself, so the octets of y cost less
than the column can separate. Read against the parse pair that is the whole
asymmetry of the compressed form — it is paid for on the way in, once per
parse, and never on the way out.

**Both tables split in two, and the split is whether a package will derive
without building an object.** coincurve and btclib-secp256k1 each offer a call
that takes octets and answers octets, and those two land together — one C
library, one generator multiplication, and nothing left to do around it, which
is the same evidence the held signing tables give further down the page.
secp256k1-py and electrum-ecc have no such spelling: a public key is reached
through `PrivateKey` and through `ECPrivkey`, each deriving as it is built. So
those two rows are a constructor rather than a multiplication, and they come
out at about twice what the other two charge.

**Which puts the comparison inside one table**, where it otherwise has to be
made by subtracting a held signing row from the fresh one below. A private-key
constructor costs about twice a bare derivation, so the reading it invites —
that building
one costs a generator multiplication, because it performs one — accounts for
about half of it. The rest is not the curve at all: it is Python objects and a
crossing.

Two routes to that, independent, and both worth having. For secp256k1-py and
electrum-ecc the constructor *is* the row here, and it lands on what
subtracting the held ECDSA row below from the fresh one says their
construction costs: the same answer once by a measurement and once by a
difference.
coincurve is the third package that builds an object and the one where the two
routes are not the same number — its row here skips the object, so the
difference is where its constructor is, and that comes to about twice its own
row. Which is the ratio again, from the one package that can be read both
ways.

Both tables end at octets, as the tweak tables below do and for the same
reason: a point nobody serializes is not the operation a caller performs.

### Public key tweak by a scalar

<!-- tables: tweak: begin -->
```text
5. public key tweak by a scalar, a 65-byte key
                                        μs/call     vs best   halves
  btclib_secp256k1                        10.09       1.00x     0.00   (10x10,000 calls)
  coincurve                               10.67       1.06x     0.01   (10x10,000 calls)
  secp256k1                               14.20       1.41x     0.00   (10x10,000 calls)
  electrum_ecc                            23.12       2.29x     0.05   (10x10,000 calls)

6. public key tweak by a scalar, a 33-byte key
                                        μs/call     vs best   halves
  btclib_secp256k1                        12.21       1.00x     0.01   (10x10,000 calls)
  coincurve                               12.83       1.05x     0.00   (10x10,000 calls)
  secp256k1                               16.33       1.34x     0.01   (10x10,000 calls)
  electrum_ecc                            25.31       2.07x     0.00   (10x10,000 calls)
```
<!-- tables: tweak: end -->

BIP32's step rather than BIP32: none of these four packages implements
derivation, and all four expose the primitive it is built from. The key
encoding costs here what the parse pair says it costs, which is the first
time on the page that the same square root is met inside something else.

Octets in and octets out, in both tables. Only one of the four answers a tweak
in bytes — the other three answer with a key object of their own — so a row
timing each API's own answer would put a tweak-and-serialize beside a tweak,
and the serialization is real work three of them would never have done. Every
row therefore ends at the compressed key BIP32 stores, and pays whichever call
its API makes a caller write to get there. It is the same 33 octets out of
both tables: the pair varies the key that goes *in*, that being the difference
it exists to price, and varying the answer along with it would leave the pair
reading as neither difference.

`electrum-ecc` is the exception on this page and the row worth reading. It
has no tweak-add on `ECPubkey`, so its row multiplies the generator by the
scalar and adds the two points — two crossings into the C library where the
others make one, and a generator multiplication is not a crossing's worth of
work but an operation's. That is why its row is last by about what the whole
tweak costs the others, rather than by the small margin its other rows are
behind by.

BIP32 proper is in [the libraries table][libs], where the comparands are
python libraries rather than secp256k1 wrappers.

### ECDSA verify

<!-- tables: dsa-verify: begin -->
```text
7. ECDSA verify (DER signature, a 65-byte key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.06       1.00x     0.00   (10x10,000 calls)
  coincurve                               13.14       1.01x     0.02   (10x10,000 calls)
  secp256k1                               13.62       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                            17.36       1.33x     0.02   (10x10,000 calls)

8. ECDSA verify (DER signature, a 33-byte key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.16       1.00x     0.02   (10x10,000 calls)
  coincurve                               15.28       1.01x     0.01   (10x10,000 calls)
  secp256k1                               15.79       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                            19.55       1.29x     0.05   (10x10,000 calls)

9. ECDSA verify (64-byte signature, a 65-byte key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.04       1.00x     0.00   (10x10,000 calls)
  secp256k1                               13.61       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                            15.13       1.16x     0.02   (10x10,000 calls)
  coincurve                                  NA

10. ECDSA verify (64-byte signature, a 33-byte key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.21       1.00x     0.04   (10x10,000 calls)
  secp256k1                               15.79       1.04x     0.04   (10x10,000 calls)
  electrum_ecc                            17.28       1.14x     0.03   (10x10,000 calls)
  coincurve                                  NA
```
<!-- tables: dsa-verify: end -->

Four tables, one per combination of the two encodings. Three packages can be
read across the signature encoding at all — coincurve is not one of them, its
API carrying no compact `ecdsa_verify`, which is what tables 9 and 10 print
`NA` for — and one of the three is the exception the next paragraph is about.
So the reading is over two: for btclib-secp256k1 and secp256k1-py, DER and the
64-byte form differ by a header libsecp256k1 reads once, and a package's two
rows sit closer together than any gap the ratio column exists to show. That is
the expected answer, and it is worth having measured — the compact form is
often described as the cheap one, and for a wrapper that parses either in C it
is not.

electrum-ecc is the exception, and pays a real amount for DER. Its
`ecdsa_verify` takes the 64-byte form and nothing else, so its DER row calls
`ecdsa_sig64_from_der_sig` first, on the caller's side of the boundary. That
is not a decoder and it is not one crossing. It is two helpers, and the second
undoes what the first has just finished doing: the DER is parsed, normalized
and serialized to the 64 octets the row wants, those octets are turned into
two Python integers and back into the same 64 octets, and the result is
parsed, normalized and serialized once more. **Six** libsecp256k1 calls and
four 64-byte buffers stand between the row's input and the verification the
other rows spend their time on.

The gap between electrum-ecc's two rows is all of that, and it is the same
order as a public key's square root — so a reader subtracting them is not
performing the subtraction another package's two rows invite.

The first of the two normalizations is also the one place on this page where
reading across the signature encoding changes an answer rather than a time.
The second cannot change anything, s being low by the time it runs.
Normalizing means the malleable half of a signature arrives at `ecdsa_verify`
as the low half and is accepted —
where the same signature handed to the same method as 64 octets is refused,
that method enforcing the low half by default. So for this one package the two
rows are not one operation in two encodings, and a reader subtracting them is
subtracting a policy along with a parse. Of the other three, two refuse the
malleable half in both encodings and coincurve refuses it in the only encoding
it has, tables 9 and 10 printing it `NA`. `tests/wrappers_test.py` states all of
that as cases, over the malleable pair and over an r or an s outside the group,
which is the range check the compact form has no length field to make.

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
11. BIP340 verify (a 65-byte key handed in, the x-only one taken from it)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.55       1.00x     0.00   (10x10,000 calls)
  secp256k1                               13.98       1.03x     0.09   (10x10,000 calls)
  electrum_ecc                            17.54       1.29x     0.17   (10x10,000 calls)
  coincurve                                  NA

12. BIP340 verify (the x-only key handed in, parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.48       1.00x     0.15   (10x10,000 calls)
  coincurve                               15.60       1.01x     0.03   (10x10,000 calls)
  secp256k1                               15.92       1.03x     0.01   (10x10,000 calls)
  electrum_ecc                            19.40       1.25x     0.09   (10x10,000 calls)
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

### ECDSA sign

<!-- tables: dsa-sign: begin -->
```text
13. ECDSA sign (32-byte digest, DER out, a fresh key)
                                        μs/call     vs best   halves
  btclib_secp256k1_nogrind_noverify       11.97       1.00x     0.06   (10x10,000 calls)
  btclib_secp256k1_grind_noverify         24.09       2.01x     0.02   (10x10,000 calls)
  coincurve_nogrind_noverify              26.72       2.23x     0.01   (10x10,000 calls)
  secp256k1_nogrind_noverify              26.73       2.23x     0.03   (10x10,000 calls)
  btclib_secp256k1_nogrind_verify         32.32       2.70x     0.08   (10x10,000 calls)
  electrum_ecc_nogrind_verify             47.62       3.98x     0.07   (10x10,000 calls)
  electrum_ecc_grind_verify               60.19       5.03x     0.12   (10x10,000 calls)

14. ECDSA sign (32-byte digest, 64-byte compact out, a fresh key)
                                        μs/call     vs best   halves
  btclib_secp256k1_nogrind_noverify       11.86       1.00x     0.04   (10x10,000 calls)
  btclib_secp256k1_grind_noverify         24.08       2.03x     0.02   (10x10,000 calls)
  secp256k1_nogrind_noverify              26.55       2.24x     0.04   (10x10,000 calls)
  btclib_secp256k1_nogrind_verify         32.21       2.72x     0.03   (10x10,000 calls)
  electrum_ecc_nogrind_verify             45.23       3.81x     0.05   (10x10,000 calls)
  electrum_ecc_grind_verify               58.07       4.90x     0.03   (10x10,000 calls)
  coincurve_nogrind_noverify                 NA

15. ECDSA sign (32-byte digest, DER out, the key held already)
                                        μs/call     vs best   halves
  coincurve_nogrind_noverify              11.59       1.00x     0.01   (10x10,000 calls)
  secp256k1_nogrind_noverify              11.73       1.01x     0.01   (10x10,000 calls)
  electrum_ecc_nogrind_verify             30.85       2.66x     0.01   (10x10,000 calls)
  btclib_secp256k1_nogrind_noverify          NA
```
<!-- tables: dsa-sign: end -->

**Every row names both of its flags**, the loop first and the check second, in
the order a signing call performs them. `_grind` is the signature re-drawn
until r fits in 32 octets and `_nogrind` the signature drawn once; `_verify` is
the signature verified before it is handed back, under a public key derived
for that purpose, and `_noverify` the signature answered as made. No row is
named by what the others are not, which is what a bare name would have made it:
a reader comparing two rows reads both flags on both, and never a flag on one
against a silence on the other.

A flag says what the row did rather than what its package let it decline.
btclib-secp256k1 is the only one of the four that takes both arguments, so its
rows are the only ones whose names record a choice; the other three are named
for what their API does anyway — coincurve and secp256k1-py verify nothing
here, and
electrum-ecc's `ecdsa_sign` verifies on every call and offers nothing that
stops it, which is why it has no `_noverify` row and its grinding row is
`_grind_verify`.

Three of the four combinations carry a btclib-secp256k1 row and the fourth is
absent as a measurement rather than as a gap: the check runs once, on the
signature the loop settled on, so grinding and checking add instead of
multiplying. That row would print the sum of two the table already carries.
electrum-ecc's `_grind_verify` is that combination and not the exception to
this: its API spells no other, so the sum is what its row has to charge.

Signing parses no public key, so nothing above carries over and the rows of
these tables sit far further apart than any verification table's do. What
separates them is not arithmetic: every row calls one C library to make one
signature.

Two habits do it. Two of the four sign only through a key object of their own
— coincurve's `PrivateKey` and secp256k1-py's — and building one derives the
public key, work a signature does not need and a caller signing a fresh key
cannot decline. And three of them verify the signature they just made before
handing it back: electrum-ecc inside `ecdsa_sign`, coincurve inside
`sign_schnorr`, and btclib-secp256k1 by default. Only the last of the three
takes an argument that stops it, which is why it is the one with two rows
here.

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
less again, the DER row paying for the six-crossing conversion its own module
orchestrates. What that module writes in Python is the orchestration; the work
is libsecp256k1's, six times over, which is the verify section above.

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

**The other habit is what the held table prices.** Handed an object it built
once, coincurve signs for what secp256k1-py signs for, and both land beside
btclib-secp256k1's unchecked row above: more of what either charges for a
fresh key is the construction than is the signature. It is not work a caller
can decline — both APIs sign only through the object — but it is work paid
once and kept, and what keeping it costs is a secret in memory for longer than
the call that needed it.

btclib-secp256k1 reads `NA` there, and that is the finding rather than a gap:
`dsa.sign` takes the 32 octets, so a caller who will sign again holds what a
caller who will sign once holds, and its row above is already the held shape.
A row under another title calling the same function would print the number
beside it.

**What is left once the construction goes is the same for all three**, which
is what says these tables measure wrappers and not arithmetic: one C library
makes one signature, and three wrappers with nothing else left to do around it
charge what it costs. electrum-ecc is the one that does not join them, and
the check is why: `ecdsa_sign` verifies on every call, and that verification
parses a public key out of the coordinates its `ECPrivkey` holds — the second
parse the parse section above describes, in one more row than it names.

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
16. BIP340 sign (32-byte message, a fresh key)
                                        μs/call     vs best   halves
  btclib_secp256k1_noverify               15.73       1.00x     0.04   (10x10,000 calls)
  secp256k1_noverify                      22.62       1.44x     0.03   (10x10,000 calls)
  btclib_secp256k1_verify                 29.07       1.85x     0.02   (10x10,000 calls)
  coincurve_verify                        43.10       2.74x     0.01   (10x10,000 calls)
  electrum_ecc_verify                     48.80       3.10x     0.02   (10x10,000 calls)

17. BIP340 sign (32-byte message, the key held already)
                                        μs/call     vs best   halves
  secp256k1_noverify                       7.86       1.00x     0.03   (10x10,000 calls)
  btclib_secp256k1_noverify                8.21       1.04x     0.01   (10x10,000 calls)
  btclib_secp256k1_verify                 21.45       2.73x     0.08   (10x10,000 calls)
  coincurve_verify                        28.13       3.58x     0.12   (10x10,000 calls)
  electrum_ecc_verify                     32.11       4.09x     0.24   (10x10,000 calls)
```
<!-- tables: ssa-sign: end -->

**Here a row names the check alone**, there being no loop to name beside it:
the signature is two fixed-width halves rather than DER, so a low r saves no
octet and nothing in BIP340 grinds for one. `_verify` is BIP340's *Default
Signing* performed to its last step, `_noverify` the same signature answered
without it.

The flag is read the same way as above, as what the row did and not as what
the package allowed. coincurve and electrum-ecc verify inside `sign_schnorr`
and `schnorr_sign` and neither takes the argument that would stop it, so both
are `_verify` rows because that is what those calls do; secp256k1-py verifies
nowhere, so its row is `_noverify` for the same reason; and btclib-secp256k1,
which takes the argument, is the one comparand with a row of each.

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

The checked row is the one coincurve's and electrum-ecc's are comparable with,
both of them verifying inside the signing call and neither offering anything
that stops it; the unchecked row is secp256k1-py's comparand.

What separates the rows of a signing table is therefore the wrapper's habits
and not the keypair, which is why the rows of the ECDSA tables above cover a
wider range than this one's while having no keypair in them at all.

### What holding the key is worth

The two held tables are the only place on this page where a row is handed an
object a package built, and the exception is the measurement: what a caller
pays for the *second* signature under a key is not a question the fresh-key
shape can be asked. Every other page here times one operation once, which is
the right shape for asking what an operation costs and the wrong one for
asking what a signing service pays — the same argument [the key reuse
page][reuse] makes, on the side of the signature it does not ask about.

Each pair is over its own fresh table's keys, in that table's order, so what
it prices is the holding and nothing else. What each row is handed is the
object its own package offers a caller who will sign again: coincurve's and
secp256k1-py's `PrivateKey`, electrum-ecc's `ECPrivkey`, btclib-secp256k1's
`ssa.Signer`.

The two pairs are not one finding asked in two schemes, and what is below is
the BIP340 half. Schnorr signing starts from a keypair where ECDSA takes the
secret key as it is, so a held BIP340 row saves work the signature would
otherwise have to do again, and a held ECDSA row saves a constructor with
nothing in it the signature reads — which is the reading beside the ECDSA
tables above.

**Holding a key and holding what a signature is made from are two different
things, and an API's shape does not say which one a caller got.** Two of the
four hold the keypair: `ssa.Signer` keeps one across calls where `ssa.sign`
builds and wipes one per call, and secp256k1-py's constructor builds one that
`schnorr_sign` reuses. The other two do not — coincurve's `sign_schnorr` and
electrum-ecc's `schnorr_sign` each call `secp256k1_keypair_create` on every
call, however long the object they were reached through has been alive.

**How far a row fell is not the evidence, and one row proves it by itself.**
btclib-secp256k1's fall is the smallest of the four in microseconds and the
second largest as a fraction of what it started from: rank the table by what
each package saved and it comes last, rank it by how much of itself it gave
back and it comes second. A single row disagreeing with itself between the two
readings is enough to say that one of them is not a ranking.

Read as a *fraction* of what the fresh row cost, the four split cleanly in
two, and the split is exactly the keypair. The two packages that hold one give
back about half of a signature and more; the two that rebuild it every call
give back about a third, and what that third is is a constructor.

**And read down the held table, which is where it is plainest.** Two rows
arrive at about what one BIP340 signature costs, the keypair having gone; the
other two are still three to four times that, because each still builds one
inside the call and still verifies afterwards.

That is the finding worth having from a pair like this, and it is why both
halves were read out of each package's source before a row was written. The
timings alone support the wrong reading: a caller looking at microseconds
saved would put electrum-ecc at the top and conclude it gains most from being
held, when what it gains is a constructor and not a keypair — as coincurve's
below it gains the derivation of a full public key and an x-only one, two
point multiplications the signature never reads, before `sign_schnorr` builds
a keypair beside them anyway.

It is not a free saving, and one of the four says so. A keypair is the secret
key in libsecp256k1's own layout, so holding one is holding a secret for
longer than the call that needed it; `ssa.Signer` gives a caller `wipe` and a
`with` statement to end it, and the others hold what they hold for as long as
the object lives.

**The ratios beside the check move with it.** The checked and unchecked rows
differ by the same verification in both tables, so once the keypair leaves the
number that difference is a fraction of, the check reads as a larger share of
what a signature costs. A page that timed only the fresh-key shape would
report the friendlier of the two, and the shape a signing service actually
runs is the other one.

The btclib pages do not carry this pair yet, and what was stopping them has
gone. `btclib.ecc.ssa.Signer` delegates to the one timed here and now takes
the same argument: btclib has grown a `verify` keyword on both its signing
calls and on that signer, so a held row there prices a policy the caller
chooses rather than the only one on offer. That was [ISS 23][i23]'s question,
and what is left of it is a run of those pages rather than a decision.

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
[i23]: https://github.com/btclib-org/btclib-benchmarks/issues/23

<!-- The blocks above are rendered from the saved run beside this file,
     and their columns are sized from what is in them; rewrapping one to 80
     would make it something else. The configuration comment below has to
     open with its own keyword, so the reason for it is here rather than
     inside it. -->
<!-- markdownlint-configure-file { "MD013": { "code_blocks": false } } -->
