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
when    : 2026-08-17 15:45 CEST (13:45 UTC)
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
constructed inside the call that needs it. The BIP340 signing pair is the
exception, and holding the key is what that pair is about: table 14 is handed
the object each of the four offers a caller who will sign again, built from
table 13's own keys, so the pair prices the holding and no package is handed
something another was not.

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

One pair differs by something else. BIP340 signing is asked twice over one
encoding, under a key handed over as bytes and under the object each package
offers for signing again, which is the only question on this page whose
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

The order below is the argument rather than the operations' importance. The
parse pair comes first because every verification and every tweak repeats one
of those parses per call, so it is read isolated before being met eight more
times inside something else. Signing comes last because it parses no public
key at all.

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
  btclib_secp256k1                0.23       1.00x     0.00   (10x400,000 calls)
  coincurve                       0.24       1.04x     0.01   (10x400,000 calls)
  secp256k1                       0.65       2.80x     0.00   (10x400,000 calls)
  electrum_ecc                    1.20       5.19x     0.00   (10x400,000 calls)

2. public key parse (a 33-byte compressed key)
                               μs/call     vs best   halves
  btclib_secp256k1                2.32       1.00x     0.00   (10x100,000 calls)
  coincurve                       2.35       1.02x     0.01   (10x100,000 calls)
  secp256k1                       2.76       1.19x     0.02   (10x100,000 calls)
  electrum_ecc                    3.30       1.43x     0.02   (10x100,000 calls)
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
                               μs/call     vs best   halves
  btclib_secp256k1               13.07       1.00x     0.05   (10x10,000 calls)
  coincurve                      13.15       1.01x     0.00   (10x10,000 calls)
  secp256k1                      13.64       1.04x     0.00   (10x10,000 calls)
  electrum_ecc                   17.44       1.33x     0.01   (10x10,000 calls)

4. ECDSA verify (DER signature, a 33-byte key parsed per call)
                               μs/call     vs best   halves
  btclib_secp256k1               15.15       1.00x     0.02   (10x10,000 calls)
  coincurve                      15.42       1.02x     0.02   (10x10,000 calls)
  secp256k1                      15.93       1.05x     0.08   (10x10,000 calls)
  electrum_ecc                   19.60       1.29x     0.02   (10x10,000 calls)

5. ECDSA verify (64-byte signature, a 65-byte key parsed per call)
                               μs/call     vs best   halves
  btclib_secp256k1               13.07       1.00x     0.05   (10x10,000 calls)
  secp256k1                      13.63       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                   15.15       1.16x     0.03   (10x10,000 calls)
  coincurve                         NA

6. ECDSA verify (64-byte signature, a 33-byte key parsed per call)
                               μs/call     vs best   halves
  btclib_secp256k1               15.17       1.00x     0.04   (10x10,000 calls)
  secp256k1                      15.82       1.04x     0.01   (10x10,000 calls)
  electrum_ecc                   17.33       1.14x     0.02   (10x10,000 calls)
  coincurve                         NA
```
<!-- tables: dsa-verify: end -->

Four tables, one per combination of the two encodings. Three packages can be
read across the signature encoding at all — coincurve is not one of them, its
API carrying no compact `ecdsa_verify`, which is what tables 5 and 6 print
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
it has, tables 5 and 6 printing it `NA`. `tests/wrappers_test.py` states all of
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
7. BIP340 verify (a 65-byte key handed in, the x-only one taken from it)
                               μs/call     vs best   halves
  btclib_secp256k1               13.36       1.00x     0.27   (10x10,000 calls)
  secp256k1                      13.63       1.02x     0.06   (10x10,000 calls)
  electrum_ecc                   17.23       1.29x     0.03   (10x10,000 calls)
  coincurve                         NA

8. BIP340 verify (the x-only key handed in, parsed per call)
                               μs/call     vs best   halves
  btclib_secp256k1               15.28       1.00x     0.03   (10x10,000 calls)
  coincurve                      15.63       1.02x     0.08   (10x10,000 calls)
  secp256k1                      16.12       1.05x     0.09   (10x10,000 calls)
  electrum_ecc                   19.41       1.27x     0.26   (10x10,000 calls)
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
                               μs/call     vs best   halves
  btclib_secp256k1               10.15       1.00x     0.02   (10x10,000 calls)
  coincurve                      10.69       1.05x     0.01   (10x10,000 calls)
  secp256k1                      14.31       1.41x     0.00   (10x10,000 calls)
  electrum_ecc                   23.13       2.28x     0.18   (10x10,000 calls)

10. public key tweak by a scalar, a 33-byte key
                               μs/call     vs best   halves
  btclib_secp256k1               12.27       1.00x     0.01   (10x10,000 calls)
  coincurve                      12.83       1.05x     0.02   (10x10,000 calls)
  secp256k1                      16.47       1.34x     0.01   (10x10,000 calls)
  electrum_ecc                   25.42       2.07x     0.08   (10x10,000 calls)
```
<!-- tables: tweak: end -->

BIP32's step rather than BIP32: none of these four packages implements
derivation, and all four expose the primitive it is built from. The key
encoding costs here what it has cost everywhere else, which is the sixth
reading of the same square root.

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

### ECDSA sign

<!-- tables: dsa-sign: begin -->
```text
11. ECDSA sign (32-byte digest, DER out)
                               μs/call     vs best   halves
  btclib_secp256k1               12.12       1.00x     0.01   (10x10,000 calls)
  btclib_secp256k1_grind         24.49       2.02x     0.02   (10x10,000 calls)
  secp256k1                      26.78       2.21x     0.27   (10x10,000 calls)
  coincurve                      26.90       2.22x     0.02   (10x10,000 calls)
  btclib_secp256k1_checked       32.45       2.68x     0.06   (10x10,000 calls)
  electrum_ecc                   47.83       3.95x     0.47   (10x10,000 calls)
  electrum_ecc_grind             60.70       5.01x     0.08   (10x10,000 calls)

12. ECDSA sign (32-byte digest, 64-byte compact out)
                               μs/call     vs best   halves
  btclib_secp256k1               11.98       1.00x     0.03   (10x10,000 calls)
  btclib_secp256k1_grind         24.31       2.03x     0.07   (10x10,000 calls)
  secp256k1                      26.63       2.22x     0.01   (10x10,000 calls)
  btclib_secp256k1_checked       32.56       2.72x     0.13   (10x10,000 calls)
  electrum_ecc                   45.28       3.78x     0.03   (10x10,000 calls)
  electrum_ecc_grind             58.52       4.88x     0.35   (10x10,000 calls)
  coincurve                         NA
```
<!-- tables: dsa-sign: end -->

Signing parses no public key, so nothing above carries over and the rows of
these tables sit far further apart than any verification table's do. What
separates them is not arithmetic: every row calls one C library to make one
signature.

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
13. BIP340 sign (32-byte message, a fresh key)
                               μs/call     vs best   halves
  btclib_secp256k1               15.88       1.00x     0.21   (10x10,000 calls)
  secp256k1                      22.73       1.43x     0.16   (10x10,000 calls)
  btclib_secp256k1_checked       29.45       1.85x     0.06   (10x10,000 calls)
  coincurve                      43.45       2.74x     0.09   (10x10,000 calls)
  electrum_ecc                   49.12       3.09x     0.13   (10x10,000 calls)

14. BIP340 sign (32-byte message, the key held already)
                               μs/call     vs best   halves
  secp256k1                       7.89       1.00x     0.01   (10x10,000 calls)
  btclib_secp256k1                8.29       1.05x     0.01   (10x10,000 calls)
  btclib_secp256k1_checked       21.76       2.76x     0.06   (10x10,000 calls)
  coincurve                      28.25       3.58x     0.15   (10x10,000 calls)
  electrum_ecc                   32.39       4.10x     0.15   (10x10,000 calls)
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

What separates the rows of a signing table is therefore the wrapper's habits
and not the keypair, which is why the rows of the ECDSA tables above cover a
wider range than this one's while having no keypair in them at all.

### What holding the key is worth

Table 14 is the only place on this page where a row is handed an object a
package built, and the exception is the measurement: what a caller pays for
the *second* signature under a key is not a question the fresh-key shape can
be asked. Every other page here times one operation once, which is the right
shape for asking what an operation costs and the wrong one for asking what a
signing service pays — the same argument [the key reuse page][reuse] makes,
on the side of the signature it does not ask about.

The pair is over table 13's own keys, in table 13's order, so what it prices
is the holding and nothing else. What each row is handed is the object its own
package offers a caller who will sign again: coincurve's and secp256k1-py's
`PrivateKey`, electrum-ecc's `ECPrivkey`, btclib-secp256k1's `ssa.Signer`.

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

The btclib pages do not carry this pair. `btclib.ecc.ssa.Signer` delegates to
the one timed here, but btclib exposes no way to decline the check its fast
path now makes, so a held row there would price one policy and have nothing to
be a pair with. That is [ISS 23][i23]'s question and it is btclib's to answer
first.

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
