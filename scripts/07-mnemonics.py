# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Timings of BIP39 and SLIP-0039, bip39-slip39 against its peers.

The peers are Trezor's `mnemonic` for BIP39, Trezor's `shamir-mnemonic`
for SLIP-0039, and `embit`, which implements both. `results/07-mnemonics.md`
says what each table asks, and why a package has an `NA` row in one.

The entropy and the master secrets are read from the top of `_inputs`'
pool. `tests/mnemonic_rows_test.py` checks every package's answers on
these fixtures: no row checks what it returns.

The numbers are saved as this finishes, where CONTRIBUTING.md's
*Publishing a run, which is a second command* says, and
`scripts/render.py` writes the page beside them from that file alone.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from importlib.metadata import version
from itertools import cycle
from typing import TYPE_CHECKING

import shamir_mnemonic
from bip39_slip39 import bip39, slip39
from embit import bip39 as embit_bip39
from embit import slip39 as embit_slip39
from mnemonic import Mnemonic

from btclib_benchmarks import _inputs
from btclib_benchmarks._provenance import WHAT_A_TIMING_CONTAINS, undeclared
from btclib_benchmarks._releases import released
from btclib_benchmarks._results import (
    Measurement,
    Provenance,
    Ratios,
    Timing,
    Unavailable,
    page_of,
    rendered_provenance,
    rendered_table,
    save,
    taken_now,
    width_for,
)
from btclib_benchmarks._timing import benchmark

if TYPE_CHECKING:
    from bip39_slip39.slip39 import Share


def provenance() -> Provenance:
    """Return one row per package: its version and the day it was released.

    Above every number, because a released wheel and a working tree satisfy
    the same requirement and resolve in silence. Every row runs Python code
    over the standard library alone, each seed and each share encryption
    through `hashlib.pbkdf2_hmac`, so no column names a backend. Sorted
    newest release first; an install that is not the declared one goes
    under the table.
    """
    packages = ("bip39-slip39", "mnemonic", "shamir-mnemonic", "embit")
    return Provenance(
        columns=["package", "version", "released"],
        rows=[
            [dist_name, version(dist_name), released(dist_name)]
            for dist_name in sorted(packages, key=released, reverse=True)
        ],
        notes=undeclared(*packages),
    )


# how many inputs each scheme reads from the pool. Every row cycles its
# own list, so a row longer than its list reads it more than once: what
# these packages compute depends on no earlier call, and none of them
# caches an answer
BIP39_INPUTS = 2_000
SLIP39_INPUTS = 200

_KEYS = _inputs.keys()
ENTROPIES = _KEYS[:BIP39_INPUTS]
# a key is 32 bytes any entropy may be: the BIP39 entropy is a whole key,
# and a SLIP-0039 master secret the first 16 bytes of one
SECRETS = [key[:16] for key in _KEYS[BIP39_INPUTS : BIP39_INPUTS + SLIP39_INPUTS]]

# the language every BIP39 row names, in each package's own spelling
LANG = "en"
TREZOR = Mnemonic("english")

MNEMONICS = [bip39.mnemonic_from_entropy(entropy, LANG) for entropy in ENTROPIES]

# one group of five members, three of them needed, and not extendable:
# embit reads no extendable flag, and the same shares then serve every
# package
GROUPS = ((3, 5),)
GROUP_THRESHOLD = 1
MEMBER_THRESHOLD = 3
ITERATION_EXPONENT = 0
EXTENDABLE = False
PASSPHRASE = ""

SHARE_SETS = [
    slip39.mnemonics_from_master_secret(
        secret, GROUPS, GROUP_THRESHOLD, PASSPHRASE, ITERATION_EXPONENT, EXTENDABLE
    )[0]
    for secret in SECRETS
]
# what combine is handed: the first three members of each set
COMBINED = [shares[:MEMBER_THRESHOLD] for shares in SHARE_SETS]
SHARE_MNEMONICS = [share for shares in SHARE_SETS for share in shares]

BIP39_SLIP39_SHARES: list[Share] = [
    slip39.share_from_mnemonic(m) for m in SHARE_MNEMONICS
]
SHAMIR_SHARES = [shamir_mnemonic.Share.from_mnemonic(m) for m in SHARE_MNEMONICS]
EMBIT_SHARES = [embit_slip39.Share.parse(m) for m in SHARE_MNEMONICS]

# one cycle per row
ENCODE_BIP39_SLIP39 = cycle(ENTROPIES)
ENCODE_MNEMONIC = cycle(ENTROPIES)
ENCODE_EMBIT = cycle(ENTROPIES)
DECODE_BIP39_SLIP39 = cycle(MNEMONICS)
DECODE_MNEMONIC = cycle(MNEMONICS)
DECODE_EMBIT = cycle(MNEMONICS)
LANG_BIP39_SLIP39 = cycle(MNEMONICS)
LANG_MNEMONIC = cycle(MNEMONICS)
SEED_BIP39_SLIP39_VERIFY = cycle(MNEMONICS)
SEED_BIP39_SLIP39_NOVERIFY = cycle(MNEMONICS)
SEED_MNEMONIC = cycle(MNEMONICS)
SEED_EMBIT_VERIFY = cycle(MNEMONICS)
SEED_EMBIT_NOVERIFY = cycle(MNEMONICS)
SPLIT_BIP39_SLIP39 = cycle(SECRETS)
SPLIT_SHAMIR = cycle(SECRETS)
COMBINE_BIP39_SLIP39 = cycle(COMBINED)
COMBINE_SHAMIR = cycle(COMBINED)
COMBINE_EMBIT = cycle(COMBINED)
PARSE_BIP39_SLIP39 = cycle(SHARE_MNEMONICS)
PARSE_SHAMIR = cycle(SHARE_MNEMONICS)
PARSE_EMBIT = cycle(SHARE_MNEMONICS)
SHARE_BIP39_SLIP39 = cycle(BIP39_SLIP39_SHARES)
SHARE_SHAMIR = cycle(SHAMIR_SHARES)
SHARE_EMBIT = cycle(EMBIT_SHARES)


def bip39_encode_bip39_slip39() -> None:
    """Time encoding 256 bits of entropy as 24 words."""
    bip39.mnemonic_from_entropy(next(ENCODE_BIP39_SLIP39), LANG)


def bip39_encode_mnemonic() -> None:
    """Time encoding 256 bits of entropy as 24 words."""
    TREZOR.to_mnemonic(next(ENCODE_MNEMONIC))


def bip39_encode_embit() -> None:
    """Time encoding 256 bits of entropy as 24 words."""
    embit_bip39.mnemonic_from_bytes(next(ENCODE_EMBIT))


def bip39_decode_bip39_slip39() -> None:
    """Time decoding 24 words to their entropy, the language given."""
    bip39.entropy_from_mnemonic(next(DECODE_BIP39_SLIP39), LANG)


def bip39_decode_mnemonic() -> None:
    """Time decoding 24 words to their entropy, the language given."""
    TREZOR.to_entropy(next(DECODE_MNEMONIC))


def bip39_decode_embit() -> None:
    """Time decoding 24 words to their entropy, english being its default."""
    embit_bip39.mnemonic_to_bytes(next(DECODE_EMBIT))


def bip39_lang_bip39_slip39() -> None:
    """Time detecting the language of 24 words."""
    bip39.lang_from_mnemonic(next(LANG_BIP39_SLIP39))


def bip39_lang_mnemonic() -> None:
    """Time detecting the language of 24 words."""
    Mnemonic.detect_language(next(LANG_MNEMONIC))


def bip39_seed_bip39_slip39_verify() -> None:
    """Time stretching 24 words to a seed, the checksum verified first."""
    bip39.seed_from_mnemonic(next(SEED_BIP39_SLIP39_VERIFY), PASSPHRASE)


def bip39_seed_bip39_slip39_noverify() -> None:
    """Time stretching 24 words to a seed, the checksum not verified."""
    bip39.seed_from_mnemonic(
        next(SEED_BIP39_SLIP39_NOVERIFY), PASSPHRASE, verify_checksum=False
    )


def bip39_seed_mnemonic() -> None:
    """Time stretching 24 words to a seed, which verifies no checksum."""
    Mnemonic.to_seed(next(SEED_MNEMONIC), PASSPHRASE)


def bip39_seed_embit_verify() -> None:
    """Time stretching 24 words to a seed, the checksum verified first."""
    embit_bip39.mnemonic_to_seed(next(SEED_EMBIT_VERIFY), PASSPHRASE)


def bip39_seed_embit_noverify() -> None:
    """Time stretching 24 words to a seed, no word-list to verify against."""
    embit_bip39.mnemonic_to_seed(next(SEED_EMBIT_NOVERIFY), PASSPHRASE, wordlist=None)


def slip39_split_bip39_slip39() -> None:
    """Time splitting a 128-bit master secret into three-of-five shares."""
    slip39.mnemonics_from_master_secret(
        next(SPLIT_BIP39_SLIP39),
        GROUPS,
        GROUP_THRESHOLD,
        PASSPHRASE,
        ITERATION_EXPONENT,
        EXTENDABLE,
    )


def slip39_split_shamir() -> None:
    """Time splitting a 128-bit master secret into three-of-five shares."""
    shamir_mnemonic.generate_mnemonics(
        GROUP_THRESHOLD,
        GROUPS,
        next(SPLIT_SHAMIR),
        PASSPHRASE.encode(),
        EXTENDABLE,
        ITERATION_EXPONENT,
    )


def slip39_combine_bip39_slip39() -> None:
    """Time combining three shares into the master secret."""
    slip39.master_secret_from_mnemonics(next(COMBINE_BIP39_SLIP39), PASSPHRASE)


def slip39_combine_shamir() -> None:
    """Time combining three shares into the master secret."""
    shamir_mnemonic.combine_mnemonics(next(COMBINE_SHAMIR), PASSPHRASE.encode())


def slip39_combine_embit() -> None:
    """Time parsing three shares and combining them into the master secret."""
    shares = [embit_slip39.Share.parse(m) for m in next(COMBINE_EMBIT)]
    embit_slip39.ShareSet(shares).recover(PASSPHRASE.encode())


def slip39_parse_bip39_slip39() -> None:
    """Time parsing a share's 20 words."""
    slip39.share_from_mnemonic(next(PARSE_BIP39_SLIP39))


def slip39_parse_shamir() -> None:
    """Time parsing a share's 20 words."""
    shamir_mnemonic.Share.from_mnemonic(next(PARSE_SHAMIR))


def slip39_parse_embit() -> None:
    """Time parsing a share's 20 words."""
    embit_slip39.Share.parse(next(PARSE_EMBIT))


def slip39_encode_bip39_slip39() -> None:
    """Time encoding a share as its 20 words."""
    slip39.mnemonic_from_share(next(SHARE_BIP39_SLIP39))


def slip39_encode_shamir() -> None:
    """Time encoding a share as its 20 words."""
    next(SHARE_SHAMIR).mnemonic()


def slip39_encode_embit() -> None:
    """Time encoding a share as its 20 words."""
    next(SHARE_EMBIT).mnemonic()


# the label a row prints, its function, and its call count. Each count puts
# a round near one common duration, the rows of one table being up to
# orders of magnitude apart
Rows = tuple[tuple[str, Callable[[], None], int], ...]

# every table of this benchmark, declared rather than called: the label
# column is one width for the whole page. The third entry is the packages
# that implement the scheme and not the operation, printed as `NA`: embit
# ships the english word-list alone, and its `generate_shares` splits a
# BIP39 sentence rather than a master secret, into one-member groups
TABLES: tuple[tuple[str, Rows, tuple[str, ...]], ...] = (
    (
        "1. BIP39 encode: 256 bits of entropy to 24 words",
        (
            ("bip39-slip39", bip39_encode_bip39_slip39, 10_000),
            ("mnemonic", bip39_encode_mnemonic, 50_000),
            ("embit", bip39_encode_embit, 10_000),
        ),
        (),
    ),
    (
        "2. BIP39 decode: 24 words to their entropy, the language given",
        (
            ("bip39-slip39", bip39_decode_bip39_slip39, 8_000),
            ("mnemonic", bip39_decode_mnemonic, 1_500),
            ("embit", bip39_decode_embit, 1_000),
        ),
        (),
    ),
    (
        "3. BIP39 language detection: 24 words",
        (
            ("bip39-slip39", bip39_lang_bip39_slip39, 25_000),
            ("mnemonic", bip39_lang_mnemonic, 70),
        ),
        ("embit",),
    ),
    (
        "4. BIP39 seed: 24 words, an empty passphrase",
        (
            ("bip39-slip39, verify", bip39_seed_bip39_slip39_verify, 400),
            ("bip39-slip39, noverify", bip39_seed_bip39_slip39_noverify, 400),
            ("mnemonic, noverify", bip39_seed_mnemonic, 400),
            ("embit, verify", bip39_seed_embit_verify, 400),
            ("embit, noverify", bip39_seed_embit_noverify, 400),
        ),
        (),
    ),
    (
        "5. SLIP-0039 split: a 128-bit master secret into three-of-five shares",
        (
            ("bip39-slip39", slip39_split_bip39_slip39, 200),
            ("shamir-mnemonic", slip39_split_shamir, 200),
        ),
        ("embit",),
    ),
    (
        "6. SLIP-0039 combine: three of five shares into the master secret",
        (
            ("bip39-slip39", slip39_combine_bip39_slip39, 200),
            ("shamir-mnemonic", slip39_combine_shamir, 200),
            ("embit", slip39_combine_embit, 200),
        ),
        (),
    ),
    (
        "7. SLIP-0039 share parse: 20 words to a share",
        (
            ("bip39-slip39", slip39_parse_bip39_slip39, 8_000),
            ("shamir-mnemonic", slip39_parse_shamir, 15_000),
            ("embit", slip39_parse_embit, 3_000),
        ),
        (),
    ),
    (
        "8. SLIP-0039 share encode: a share to 20 words",
        (
            ("bip39-slip39", slip39_encode_bip39_slip39, 10_000),
            ("shamir-mnemonic", slip39_encode_shamir, 15_000),
            ("embit", slip39_encode_embit, 15_000),
        ),
        (),
    ),
)

# every row is called once before anything is timed: a fixture built wrong
# would otherwise be timed rather than reported, and a word-list a package
# loads on its first call is not charged to the first round
for _title, _rows, _missing in TABLES:
    for _label, _row, _calls in _rows:
        _row()

ROUNDS = 10

# what the run block claims about how these numbers were taken
METHOD = f"{ROUNDS} rounds per row in two halves, minimum kept; calls per row"


def measured(title: str, rows: Rows, missing: tuple[str, ...]) -> Ratios:
    """Time one operation's rows and return them as a table.

    The sort and the ratio are the renderer's: one ratio, against whichever
    row came out quickest. A package in `missing` gets an `NA` row, which
    the renderer sorts last.
    """
    timings: list[Timing | Unavailable] = [Unavailable(label) for label in missing]
    for label, func, calls in rows:
        print(f"\r{label:<32}", end="", file=sys.stderr)
        value, apart = benchmark(func, calls, ROUNDS)
        timings.append(
            Timing(
                label=label,
                us_per_call=value,
                halves_apart=apart,
                calls=calls,
                rounds=ROUNDS,
            )
        )
    print("\r" + " " * 32 + "\r", end="", file=sys.stderr)
    return Ratios(title=title, decimals=2, rows=timings)


def main() -> None:
    """Print a table per operation and save the run."""
    packages = provenance()
    print(rendered_provenance(packages))
    print()
    print("\n".join(WHAT_A_TIMING_CONTAINS))
    print()

    width = width_for(
        [
            label
            for _, rows, missing in TABLES
            for label in [*(label for label, _, _ in rows), *missing]
        ]
    )
    tables = []
    for title, rows, missing in TABLES:
        table = measured(title, rows, missing)
        print(rendered_table(table, width))
        print()
        tables.append(table)

    saved = save(
        Measurement(
            benchmark=page_of(__file__),
            run=taken_now(__file__, METHOD),
            provenance=packages,
            tables=tables,
        )
    )
    print(f"saved to {saved}", file=sys.stderr)


# a guard rather than bare module-level calls: the helpers above are
# imported by the suite, and a bare call would time every one of them on
# the import. A measurement is the one thing a test must not do
if __name__ == "__main__":
    main()
