# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""What is recorded by hand about each build, once, for every benchmark.

Neither the date a build was published nor the libsecp256k1 revision it
vendors can be read from an installed package, so a person reads them from
the index and the sources and writes them down here. Each is keyed by the
build it was read for, and any other build is `unrecorded`, so an upgraded
comparand says it has outgrown its record rather than going on printing a
fact that has stopped being true. A pinned wrapper needs its date and its
pin, both here.
"""

from __future__ import annotations

from importlib.metadata import version

from btclib_benchmarks._provenance import origin_of

# When each of these builds was published, read from the index -- where
# `uv.lock` keeps it too, an `upload-time` per artifact -- and recorded
# against the build it was read for. Not available at run time: a wheel's
# METADATA carries a Version and no date, and the dist-info directory's
# mtime is when the package was installed on this machine. A comparand's
# age is worth a column, the revision a build vendors following from when
# the build was made.
#
# Keyed by build rather than by version, which for secp256k1 are not the
# same thing: its sdist and the wheels re-published under that version
# years afterwards are two builds, and a key by version would give the
# sdist's date to an installed wheel. For every other distribution the
# build is its version.
#
# secp256k1lab is on no index and is taken from a git tag, which is still a
# release someone cut on a day, so it is recorded like the rest.
RELEASE_DATES: dict[str, dict[str, str]] = {
    "base58-bech32": {"2026.10.23": "2026-10-23"},
    "btclib": {"2026.10.3": "2026-10-03", "2026.10.9": "2026-10-10"},
    "btclib-secp256k1": {"0.8.0.9": "2026-09-29"},
    "btclib-wallet": {"2026.10.9": "2026-10-08"},
    "buidl": {"0.2.36": "2022-02-28"},
    "coincurve": {"21.0.0": "2025-03-08"},
    "ecc": {"2026.10.23": "2026-10-23"},
    "ecdsa": {"0.19.2": "2026-03-26"},
    "electrum-ecc": {"0.0.7": "2026-02-25"},
    "embit": {"0.8.0": "2024-05-30"},
    "pycoin": {"0.92718.20260405": "2026-04-05"},
    "python-bitcoinlib": {"0.12.2": "2023-06-03"},
    "secp256k1": {"0.14.0 wheel": "2026-01-29", "0.14.0 sdist": "2021-11-06"},
    "secp256k1lab": {"1.0.0": "2025-03-26"},
    "starkbank-ecdsa": {"2.3.1": "2026-04-23"},
}


# Where each row's libsecp256k1 came from, read from the build named
# beside it:
#
# - btclib-secp256k1 0.8.0.9: the `secp256k1` tree in its sdist, which is
#   upstream's v0.8.0 tag, 6e2c8bc, file for file
# - coincurve: `VENDORED_UPSTREAM_REF` in its pyproject.toml, 0cdc758a,
#   which is upstream's v0.6.0
# - secp256k1: two, one per artifact, which is the whole reason these are
#   keyed the way they are. Its sdist ships a libsecp256k1 tree among its
#   own files rather than fetching one, and that tree's configure.ac still
#   calls itself 0.1: it is 9526874d, a master commit older than upstream's
#   first tagged release. The wheels come from a source that had moved
#   `LIB_TARBALL_URL` on to the v0.6.0 tag, and the installed extension is
#   what confirms it rather than the claim -- it exports the `musig` entry
#   points that release added, where the tree in the sdist has four modules
#   and neither that one nor `ellswift`
# - electrum-ecc: the libsecp256k1 tree carried in its sdist and compiled
#   at install time, whose configure.ac names 0.7.1 as a release
#
# Keyed by what identifies a build, which `01-libsecp256k1.py`'s
# `_build_of` decides and is not one thing for every wrapper: a branch install
# is its commit, a release is its version, and a release whose index serves
# two artifacts of one version is neither until the artifact is named. The
# floors in pyproject.toml are floors -- a comparand upgrades without a
# word, and a pin has to stop being claimed when the build it was read from
# is no longer the one installed. A version that stands still while its
# artifacts change is a key that cannot fire, which is why the key is the
# build.
LIBSECP256K1_PINS: dict[str, dict[str, str]] = {
    "btclib-secp256k1": {"0.8.0.9": "v0.8.0"},
    "coincurve": {"21.0.0": "v0.6.0"},
    "secp256k1": {
        "0.14.0 wheel": "v0.6.0",
        "0.14.0 sdist": "9526874d, pre-v0.1.0",
    },
    "electrum-ecc": {"0.0.7": "v0.7.1"},
}


def released(dist_name: str) -> str:
    """Say when this build was published, or where it came from instead.

    A build resolved from a branch has no publish date to report -- a
    release that has not happened cannot be dated -- so the column names
    the branch and the commit instead, which is what a reader has to look
    up to get that build again. A distribution with no entry here is treated
    as that case. The build is the installed version, so a distribution
    recorded by artifact, as `secp256k1` is, reads `unrecorded`.
    """
    if dist_name not in RELEASE_DATES:
        # the branch and the commit, without the repository the package
        # column has already named
        return origin_of(dist_name).split()[-1]
    return RELEASE_DATES[dist_name].get(version(dist_name), "unrecorded")
