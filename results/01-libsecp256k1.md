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
when    : 2026-08-18 13:41 CEST (11:41 UTC)
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
1. public key parse (a 65-byte uncompressed key handed in, an object out)
                                        μs/call     vs best   halves
  btclib_secp256k1                         0.22       1.00x     0.00   (10x400,000 calls)
  coincurve                                0.24       1.06x     0.00   (10x400,000 calls)
  secp256k1                                0.66       2.96x     0.00   (10x400,000 calls)
  electrum_ecc                             1.18       5.34x     0.00   (10x400,000 calls)

2. public key parse (a 33-byte compressed key handed in, an object out)
                                        μs/call     vs best   halves
  btclib_secp256k1                         2.31       1.00x     0.01   (10x100,000 calls)
  coincurve                                2.36       1.02x     0.00   (10x100,000 calls)
  secp256k1                                2.77       1.20x     0.00   (10x100,000 calls)
  electrum_ecc                             3.29       1.42x     0.02   (10x100,000 calls)
```
<!-- tables: parse: end -->

The uncompressed parse is the cheapest thing on this page: the encoding
carries y, so a parser reads two coordinates and checks they are on the
curve. The compressed parse of the same key costs many times it, and the
difference is one field square root — recovering the y that the shorter
encoding left out.

Both rows end at an object, and every package has one here — btclib-secp256k1
included, whose answer is libsecp256k1's own parsed key rather than a wrapper
of its own. That is worth saying beside the tweak tables below, where its
rows answer octets because octets are what that package's *key* is: what it
has no class for is a key a caller holds, not a point the C library parsed.

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
3. public key from a private key (32-byte secret, 65-byte uncompressed key out)
                                        μs/call     vs best   halves
  coincurve_unchecked                      7.62       1.00x     0.05   (10x10,000 calls)
  btclib_secp256k1                         7.74       1.01x     0.00   (10x10,000 calls)
  coincurve                                7.75       1.02x     0.03   (10x10,000 calls)
  secp256k1                               15.27       2.00x     0.00   (10x10,000 calls)
  electrum_ecc                            16.73       2.20x     0.01   (10x10,000 calls)

4. public key from a private key (32-byte secret, 33-byte compressed key out)
                                        μs/call     vs best   halves
  coincurve_unchecked                      7.62       1.00x     0.03   (10x10,000 calls)
  coincurve                                7.76       1.02x     0.03   (10x10,000 calls)
  btclib_secp256k1                         7.77       1.02x     0.02   (10x10,000 calls)
  secp256k1                               15.27       2.00x     0.01   (10x10,000 calls)
  electrum_ecc                            16.84       2.21x     0.01   (10x10,000 calls)
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

**coincurve has two rows, and the pair prices an input check.** Its bare row
is `from_secret`, which validates the secret; `_unchecked` is
`from_valid_secret`, which says in its own docstring that it avoids input
checks. What they differ by is not the scalar's range — libsecp256k1 answers
that from the value, and every row on this page leaves it there — but the
length. The C call takes a bare pointer and reads 32 octets from it whatever
the caller passed, so a secret of 20 octets derives a public key from twelve
octets of whatever sat beside it in memory: handed the same short secret, the
unchecked spelling answers a key, and answers a different one as its
neighbours change. That is what the checked row buys, and it is why that row
is the one btclib-secp256k1's is comparable with.

Read in that order the three rows say something the table could not say
before: btclib-secp256k1 sits between coincurve's two, so its own length
check costs it less than coincurve's validation costs coincurve, and the
gap to the unchecked row is what any of them would save by not looking at
what a caller passed.

**Both tables split in two again, and that split is whether a package will
derive without building an object.** coincurve and btclib-secp256k1 each
offer a call that takes octets and answers octets, and those two land
together — one C library, one generator multiplication, and nothing left to
do around it, which is the same evidence the held signing tables give further
down the page.
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
5. public key tweak by a scalar (a 65-byte uncompressed key handed in)
                                        μs/call     vs best   halves
  btclib_secp256k1_octets                 10.13       1.00x     0.03   (10x10,000 calls)
  coincurve_object                        10.23       1.01x     0.01   (10x10,000 calls)
  coincurve_octets                        10.62       1.05x     0.04   (10x10,000 calls)
  secp256k1_object                        13.85       1.37x     0.05   (10x10,000 calls)
  secp256k1_octets                        14.32       1.41x     0.00   (10x10,000 calls)
  electrum_ecc_object                     22.84       2.26x     0.03   (10x10,000 calls)
  electrum_ecc_octets                     23.16       2.29x     0.03   (10x10,000 calls)

6. public key tweak by a scalar (a 33-byte compressed key handed in)
                                        μs/call     vs best   halves
  btclib_secp256k1_octets                 12.22       1.00x     0.03   (10x10,000 calls)
  coincurve_object                        12.35       1.01x     0.01   (10x10,000 calls)
  coincurve_octets                        12.77       1.05x     0.00   (10x10,000 calls)
  secp256k1_object                        16.00       1.31x     0.02   (10x10,000 calls)
  secp256k1_octets                        16.37       1.34x     0.03   (10x10,000 calls)
  electrum_ecc_object                     24.97       2.04x     0.01   (10x10,000 calls)
  electrum_ecc_octets                     25.29       2.07x     0.02   (10x10,000 calls)
```
<!-- tables: tweak: end -->

BIP32's step rather than BIP32: none of these four packages implements
derivation, and all four expose the primitive it is built from. The key
encoding costs here what the parse pair says it costs, which is the first
time on the page that the same square root is met inside something else.

**Each table's title names the key handed in**, that being the difference
the pair prices: the same tweak by the same scalar, reached from the two
serializations of one key. What comes out is the row's own business, and the
rows say which they answered.

`_octets` ends at the compressed key BIP32 stores, which is the comparison
every row can be held to: one of the four answers a tweak in bytes and the
other three answer with a key object, so this is the row that makes them one
question. `_object` stops where the package's own call stops. Only three
packages have one, and that is the finding rather than a gap in the fourth:
btclib-secp256k1 has no key object at all, so its octets are not a
serialization it performed but the form it works in, and its single row is
already its native answer.

Both are worth a row because they answer different questions. A caller who
stores a key wants the first; a caller in the middle of a BIP32 chain wants
the second, since a chain serializes the key it arrives at and not the ones
it passed through. And the pair of rows inside one package is what the
serialization costs it, which is a subtraction a reader makes rather than a
sentence to take on trust.

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
7. ECDSA verify (64-byte signature, a 65-byte uncompressed key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.06       1.00x     0.01   (10x10,000 calls)
  secp256k1                               13.68       1.05x     0.02   (10x10,000 calls)
  electrum_ecc                            15.24       1.17x     0.02   (10x10,000 calls)
  coincurve_nogrind_noverify                 NA

8. ECDSA verify (DER signature, a 65-byte uncompressed key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.06       1.00x     0.01   (10x10,000 calls)
  coincurve                               13.13       1.01x     0.04   (10x10,000 calls)
  secp256k1                               13.66       1.05x     0.00   (10x10,000 calls)
  electrum_ecc                            17.43       1.34x     0.04   (10x10,000 calls)

9. ECDSA verify (64-byte signature, a 33-byte compressed key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.17       1.00x     0.03   (10x10,000 calls)
  secp256k1                               15.85       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                            17.37       1.15x     0.05   (10x10,000 calls)
  coincurve_nogrind_noverify                 NA

10. ECDSA verify (DER signature, a 33-byte compressed key parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.17       1.00x     0.01   (10x10,000 calls)
  coincurve                               15.28       1.01x     0.00   (10x10,000 calls)
  secp256k1                               15.82       1.04x     0.04   (10x10,000 calls)
  electrum_ecc                            19.60       1.29x     0.00   (10x10,000 calls)
```
<!-- tables: dsa-verify: end -->

Four tables, one per combination of the two encodings, ordered by the key and
carrying the 64-byte signature first: so a package's two signature encodings
are adjacent tables, and the same signature under the two key encodings is one
table apart. Three packages can be read across the signature encoding at all —
coincurve is not one of them, its API carrying no compact `ecdsa_verify`,
which is what tables 7 and 9 print `NA` for — and one of the three is the
exception the next paragraph is about. So the reading is over two: for
btclib-secp256k1 and secp256k1-py, DER and the 64-byte form differ by a
header libsecp256k1 reads once, and a package's two
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
it has, tables 7 and 9 printing it `NA`. `tests/wrappers_test.py` states all of
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
11. BIP340 verify (a 65-byte uncompressed key handed in, x-only taken from it)
                                        μs/call     vs best   halves
  btclib_secp256k1                        13.40       1.00x     0.00   (10x10,000 calls)
  secp256k1                               13.71       1.02x     0.02   (10x10,000 calls)
  electrum_ecc                            17.27       1.29x     0.01   (10x10,000 calls)
  coincurve_nogrind_noverify                 NA

12. BIP340 verify (the x-only key handed in, parsed per call)
                                        μs/call     vs best   halves
  btclib_secp256k1                        15.24       1.00x     0.00   (10x10,000 calls)
  coincurve                               15.34       1.01x     0.02   (10x10,000 calls)
  secp256k1                               15.85       1.04x     0.00   (10x10,000 calls)
  electrum_ecc                            19.37       1.27x     0.01   (10x10,000 calls)
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
13. ECDSA sign (32-byte digest, a fresh private key handed in, DER out)
                                        μs/call     vs best   halves
  btclib_secp256k1_nogrind_noverify       12.04       1.00x     0.06   (10x10,000 calls)
  btclib_secp256k1_grind_noverify         24.13       2.01x     0.05   (10x10,000 calls)
  secp256k1_nogrind_noverify_object       26.30       2.18x     0.04   (10x10,000 calls)
  coincurve_nogrind_noverify              26.81       2.23x     0.01   (10x10,000 calls)
  secp256k1_nogrind_noverify_octets       26.83       2.23x     0.00   (10x10,000 calls)
  btclib_secp256k1_nogrind_verify         32.47       2.70x     0.05   (10x10,000 calls)
  btclib_secp256k1_grind_verify           44.61       3.71x     0.00   (10x10,000 calls)
  electrum_ecc_nogrind_verify             47.77       3.97x     0.04   (10x10,000 calls)
  electrum_ecc_grind_verify               60.52       5.03x     0.05   (10x10,000 calls)

14. ECDSA sign (32-byte digest, a fresh private key handed in, 64 octets out)
                                        μs/call     vs best   halves
  btclib_secp256k1_nogrind_noverify       11.88       1.00x     0.06   (10x10,000 calls)
  btclib_secp256k1_grind_noverify         24.16       2.03x     0.03   (10x10,000 calls)
  secp256k1_nogrind_noverify_object       26.42       2.22x     0.01   (10x10,000 calls)
  secp256k1_nogrind_noverify_octets       26.64       2.24x     0.04   (10x10,000 calls)
  btclib_secp256k1_nogrind_verify         32.45       2.73x     0.03   (10x10,000 calls)
  btclib_secp256k1_grind_verify           44.84       3.77x     0.09   (10x10,000 calls)
  electrum_ecc_nogrind_verify             45.36       3.82x     0.04   (10x10,000 calls)
  electrum_ecc_grind_verify               58.30       4.91x     0.05   (10x10,000 calls)
  coincurve_nogrind_noverify                 NA

15. ECDSA sign (32-byte digest, the public key held already, DER out)
                                        μs/call     vs best   halves
  coincurve_nogrind_noverify              11.68       1.00x     0.00   (10x10,000 calls)
  secp256k1_nogrind_noverify_octets       11.79       1.01x     0.00   (10x10,000 calls)
  btclib_secp256k1_nogrind_verify         25.25       2.16x     0.04   (10x10,000 calls)
  electrum_ecc_nogrind_verify             30.99       2.65x     0.05   (10x10,000 calls)
  btclib_secp256k1_nogrind_noverify          NA
```
<!-- tables: dsa-sign: end -->

**Every row names both flags**, in the order a call performs them: `grind` or
`nogrind` for the low-r loop, which re-draws the signature until r fits in 32
octets, and `verify` or `noverify` for the check made before the signature is
handed back, under a public key derived for the purpose. So no row is read
against a silence, and the tables carry every combination each API can be
asked for.

Which is four rows for btclib-secp256k1, the one package taking both
arguments, and fewer for the others because their APIs spell fewer: coincurve
and secp256k1-py sign once and check nothing, and electrum-ecc's `ecdsa_sign`
grinds or does not and verifies either way, which is why both of its rows say
`verify` and neither of them could be made to stop.

A flag says what happened inside the call rather than what the API let a
caller decline. electrum-ecc's rows carry `verify` though it takes no such
argument, and btclib-secp256k1's carry it because a caller passed one.

**`_octets` and `_object` are the suffixes here that are about the answer**
rather than the work, and one package needs them: secp256k1-py's `ecdsa_sign`
returns a parsed signature and no bytes, alone of the four, so its `octets`
row makes the second call that the other three are handed by their first, and
its `object` row stops where its API stops. The pair prices that
serialization inside the table that prints the encoding it serializes to, and
the two `_object` rows — one per table — are one call over two slices of the
pool, so their agreement is a check on the pool rather than a second finding.

The other three name no answer, because there is nothing to choose: their
signing calls hand back octets and have no second form. It is also why the
held table has an `octets` row and no `object` one — the same package makes
the same second call there, and the row it would be subtracted from is in the
table above.

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
takes an argument that stops it, which is why it is the one with a row on
each side of the question.

**No single one of those rows compares with all three of the others**, and
that is what they are for. Its `nogrind_noverify` row is the operation
coincurve performs in ECDSA and secp256k1-py in both schemes; its
`nogrind_verify` row is the operation
electrum-ecc performs in both of its ECDSA rows. Printing one of the two and
calling it btclib-secp256k1's signing time would make one of those comparisons
wrong, and which one would depend on which row was printed.

Read that way the tables stop being a ranking and start being a subtraction.
The unchecked row against coincurve's and secp256k1-py's leaves what their
key
object costs, and it agrees closely with the difference the same two rows show
in every other table on this page. The `_verify` row against electrum-ecc's
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

**btclib-secp256k1 answers the same question twice there, and only one of
the two is a row.** Its `nogrind_noverify` shape reads `NA`, and that is the
finding rather than a gap: `dsa.sign` takes the 32 octets, so a caller who
will sign again
holds what a caller who will sign once holds, and its fresh row is already
the held shape. A row under another title calling the same function would
print the number beside it.

Its checked shape does have something to hold, and it is exactly what the
other three keep inside their key object: the public key. The check verifies
under one, `sign` derives one per call when nobody hands it over, and
`pubkey=` is where a caller who has it puts it — so the held row is the
package's own answer to signing repeatedly under one key, reached without a
key object because octets are what this package's key is.

What it saves against the fresh `_verify` row is that derivation less the
parse of the octets handed in, which is why the saving comes out a shade
under what the derivation table near the top of the page charges for the
multiplication on its own — and that table and this subtraction are two
readings of one number, taken at opposite ends of the page and by different
routes. The parse they differ by is table 1's row for the same package, and
it accounts for the gap.

**What is left once the construction goes is the same for both rows that
sign and nothing else**, which is what says these tables measure wrappers and
not arithmetic: one C library makes one signature, and a wrapper with nothing
left to do around it charges what it costs. The other two rows of that table
verify, so neither is comparable with those two or with each other's package
— and between them the check is read again, electrum-ecc's `ecdsa_sign`
parsing a public key out of the coordinates its `ECPrivkey` holds where
btclib-secp256k1's is handed one, which is the second parse the parse section
above describes.

**Grinding is read as a difference between two rows that share a check**, and
each package supplies its own pair: btclib-secp256k1's `nogrind_noverify` row
against its `grind_noverify`, or its `nogrind_verify` against its
`grind_verify`, and electrum-ecc's
two rows, which carry the check because nothing there can put it down. Every
one of those differences is the loop and nothing else, which is why they can
be read against each other while the rows they are differences of cannot.

A grinding row is the row it is paired with plus about one extra signature,
half of all draws needing none and the tail paying for the rest — and that
comes out nearly the same for both packages and in both encodings, which is
what should happen to two Python loops around the same C call.

**The fourth btclib-secp256k1 row is what says the two costs add.** The check
runs once, on the signature the loop settled on, so grinding a checked
signature costs what grinding an unchecked one costs: what that row charges
over the checked row is what the grinding row charges over the unchecked
one.
Which is a claim two subtractions can be held to, rather than one a reader
has to accept.

Read the ratio column for any of this and none of it is visible. The ratio is
against the fastest row in the table, so btclib-secp256k1's grinding row
doubles because its base is nearly all signature, and electrum-ecc's grows by
a fraction because its base is nearly all something else.

### BIP340 sign

<!-- tables: ssa-sign: begin -->
```text
16. BIP340 sign (32-byte message, a fresh key)
                                        μs/call     vs best   halves
  btclib_secp256k1_aux_noverify           15.79       1.00x     0.03   (10x10,000 calls)
  secp256k1_noaux_noverify                22.77       1.44x     0.01   (10x10,000 calls)
  btclib_secp256k1_aux_verify             29.18       1.85x     0.10   (10x10,000 calls)
  coincurve_noaux_verify                  43.15       2.73x     0.00   (10x10,000 calls)
  coincurve_aux_verify                    43.31       2.74x     0.06   (10x10,000 calls)
  electrum_ecc_aux_verify                 48.96       3.10x     0.02   (10x10,000 calls)

17. BIP340 sign (32-byte message, the key held already)
                                        μs/call     vs best   halves
  secp256k1_noaux_noverify                 7.98       1.00x     0.02   (10x10,000 calls)
  btclib_secp256k1_aux_noverify            8.23       1.03x     0.01   (10x10,000 calls)
  btclib_secp256k1_aux_verify             21.50       2.69x     0.10   (10x10,000 calls)
  coincurve_aux_verify                    28.25       3.54x     0.29   (10x10,000 calls)
  electrum_ecc_aux_verify                 32.10       4.02x     0.05   (10x10,000 calls)
```
<!-- tables: ssa-sign: end -->

**BIP340's auxiliary randomness is a row rather than a footnote.** *Default
Signing* mixes 32 octets of it into the nonce, which blinds the nonce against
a side channel reading the secret out of it; the scheme permits signing
without and recommends against it. Three of the four are handed it here.
secp256k1-py cannot be: its `schnorr_sign` passes `NULL` and its own source
carries a note that the randomness is recommended — so its rows say `_noaux`,
that being what the call does rather than what the page chose for it.

coincurve spells both, alone of the four, so the pair of its rows in the
fresh table is what the recommendation costs, and its `_noaux_verify` row is
the one secp256k1-py's is comparable with. One pair and not two: the
difference is the same either side of a keypair, so the held table would
print it twice.

What it comes to is small — a few times the distance between either row's own
halves, which is the column to read beside it before believing the ordering —
and that is the finding rather than a disappointment. The randomness is one
tagged hash inside the nonce derivation, and a signature is a point
multiplication: a caller declining it is declining a blind on the nonce to
save a hash.

**Here the two flags are `aux` and `verify`**, there being no loop to name
beside them: the signature is two fixed-width halves rather than DER, so a low
r saves no octet and nothing in BIP340 grinds for one. `aux` is the auxiliary
randomness above, `verify` is BIP340's *Default Signing* carried to its last
step, and `noaux` and `noverify` are those two declined.

Both say what the call did rather than what its API allowed. coincurve and
electrum-ecc verify inside `sign_schnorr` and `schnorr_sign` and neither takes
the argument that would stop it, so both are `verify` rows; secp256k1-py
verifies nowhere and is handed no randomness, so its row is
`noaux_noverify`; and btclib-secp256k1, which takes the check as an argument,
is the one comparand with a row on each side of it.

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
BIP340's *Default Signing* ends with a verification, so the `verify` row is
the scheme performed as written and the `noverify` row is the shortcut. ECDSA
carries no such step, which is the whole reason one default cannot be right
for both.

The `_verify` row is the one coincurve's and electrum-ecc's are comparable with,
both of them verifying inside the signing call and neither offering anything
that stops it; the `noverify` row is secp256k1-py's comparand.

What separates the rows of a signing table is therefore the wrapper's habits
and not the keypair, which is why the rows of the ECDSA tables above cover a
wider range than this one's while having no keypair in them at all.

### What holding the key is worth

The two held tables are the only place on this page where a row is handed
something built before the clock started, and the exception is the
measurement: what a caller
pays for the *second* signature under a key is not a question the fresh-key
shape can be asked. Every other page here times one operation once, which is
the right shape for asking what an operation costs and the wrong one for
asking what a signing service pays — the same argument [the key reuse
page][reuse] makes, on the side of the signature it does not ask about.

Each pair is over its own fresh table's keys, in that table's order, so what
it prices is the holding and nothing else. What each row is handed is what
its own package offers a caller who will sign again: coincurve's and
secp256k1-py's `PrivateKey`, electrum-ecc's `ECPrivkey`, btclib-secp256k1's
`ssa.Signer` — and, in the ECDSA table, btclib-secp256k1's public key as
octets, that package having no object to keep one in.

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

**The ratios beside the check move with it.** The `verify` and `noverify`
rows
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
