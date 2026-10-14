# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every btclib Python row really has a pure-Python path.

`02-btclib-vs-btclib.py`'s whole premise is that each operation in it can be
answered twice, once in C and once in Python, and `python_arithmetic_only`
is how it asks for the second. The premise is not self-evident: an operation
whose Python arm calls the bindings anyway moves only part of its work, its
pair reads far narrower than every other, and nothing but arithmetic on the
printed table says so.

`04-pure-python.py` and `05-key-reuse.py` throw the same switch and publish
btclib's rows after it as Python. A btclib change that routed one of them to
C would turn a published Python number into a C number, so the same probe
runs over their btclib Python rows too.

What is checked here is the thing a timing cannot check: not how long the
Python path takes, but that it *is* the Python path. Every bindings entry
point is replaced with a function that raises, the switch is thrown, and
every row is called once. A row that has quietly kept a foot in C
raises instead of answering.

The predicates are left alone deliberately. `_libsecp256k1_serves` and
`is_libsecp256k1_serving` live beside the bindings imports and match the
same name, but they are the question rather than an answer: replacing them
breaks the dispatch for every row and proves nothing about any of them.

In a subprocess, because none of this can be undone in the process that
does it -- neither the switch, which `02-btclib-vs-btclib.py` documents, nor
the patching, which reaches into modules the rest of the suite imports.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from itertools import cycle
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from btclib.key import PubKeyData

# `import` cannot spell it: the six scripts are named for the pages
# they publish, which begin with a number and hold hyphens. Nothing
# imports them by statement -- a person runs `python scripts/<name>.py`
# and the suite asks `importlib` for them by string, which is indifferent
# to what a Python identifier may look like
TWO_PATHS = importlib.import_module("02-btclib-vs-btclib")

# the scripts whose btclib Python rows the probe calls. 04 and 05 are not
# imported here: 04 sets `PYCOIN_NATIVE` before pycoin's first import, and
# importing it while the suite is collected would make every other test run
# pure-Python pycoin. The probe selects the rows inside its own process
SCRIPTS_PROBED = ["02-btclib-vs-btclib", "04-pure-python", "05-key-reuse"]

# where `conftest.py` points this process's own import path, spelled again
# rather than imported from it: mypy resolves modules by path and a test
# importing its own conftest is a module it cannot find
SCRIPTS = Path(__file__).parents[1] / "scripts"

# blocks the bindings, throws the switch, and reports one line per row,
# taking the script's name. 02's operations are all btclib's and 04
# labels its btclib rows so. 05 times `verify_octets` and `verify_point` in C
# before its switch and in Python after it, so the probe throws the switch
# and calls them as the second, with `parse_point`.
# Written as a program rather than as a helper module because it has to run
# somewhere this suite is not: see the docstring
PROBE = """
import importlib, sys, types
B = importlib.import_module(sys.argv[1])


class BindingsCalled(RuntimeError):
    pass


def raiser(name):
    def f(*args, **kwargs):
        raise BindingsCalled(name)

    return f


PREDICATES = {"_libsecp256k1_serves", "is_libsecp256k1_serving"}

B.python_arithmetic_only()

# no row loads a `btclib_wallet` module, so none is patched: after every
# row has run, `sys.modules` holds none
#
# the names btclib bound at import time, `from btclib_secp256k1 import x as
# libsecp256k1_x` being a reference the module holds and not a lookup it
# repeats -- patching the bindings alone would leave every one of them live
for module in list(sys.modules.values()):
    if not isinstance(module, types.ModuleType):
        continue
    if not (module.__name__ or "").startswith(("btclib.", "btclib_ecc.")):
        continue
    for attribute in dir(module):
        if "libsecp256k1" in attribute and attribute not in PREDICATES:
            value = getattr(module, attribute)
            if callable(value) and not isinstance(value, type):
                setattr(module, attribute, raiser(module.__name__ + "." + attribute))

# and the bindings' own functions, which is what catches a call routed
# through the package at run time rather than through a name bound
# above -- "btclib_secp256k1" names both the pure-Python wrapper package
# and the compiled extension it wraps, the leading underscore in
# `_btclib_secp256k1` belonging to the distribution and not to a build
for name, module in list(sys.modules.items()):
    if not name.lstrip("_").startswith("btclib_secp256k1") or not isinstance(
        module, types.ModuleType
    ):
        continue
    for attribute in dir(module):
        if attribute.startswith("__"):
            continue
        value = getattr(module, attribute, None)
        if callable(value) and not isinstance(value, type):
            try:
                setattr(module, attribute, raiser(name + "." + attribute))
            except (AttributeError, TypeError):
                # `_btclib_secp256k1.lib` is a cffi `Lib` object whose
                # `__class__` is set to `types.ModuleType` so the check
                # above accepts it, but its C-backed attributes are not
                # a module's own `__dict__` underneath and refuse every
                # `setattr`. What decides whether this arm is reached at
                # all is the linkage: the static build the bindings
                # default to puts `lib` there, and a dynamic one -- cffi
                # ABI mode, which their `_load_lib` tells apart by
                # `hasattr(module, "lib")` -- has no such attribute and
                # nothing here to write to
                pass

if B.__name__ == "02-btclib-vs-btclib":
    names = [operation.__name__ for _, operation, _, _ in B.OPERATIONS]
elif B.__name__ == "04-pure-python":
    names = [
        function.__name__
        for _, rows in B.TABLES
        for label, function, _ in rows
        if "btclib" in label
    ]
else:
    names = ["verify_octets", "verify_point", "parse_point"]

for name in names:
    print("SELECTED " + name)
    try:
        getattr(B, name)()
    except BindingsCalled as reached:
        print("REACHED " + name + " " + str(reached))
    else:
        print("PYTHON " + name)
"""


@pytest.mark.parametrize("script", SCRIPTS_PROBED)
def test_every_row_answers_without_the_bindings(script: str) -> None:
    """Block the bindings, then call every row: each must still answer."""
    # S603 asks whether untrusted input reaches a subprocess: what reaches
    # this one is this interpreter, the constant above and a name from the
    # list above
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", PROBE, script],
        capture_output=True,
        encoding="utf-8",
        check=True,
        # the child gets `scripts/` the way `python -c` gives it, the
        # working directory: conftest puts it on *this* process's path, and
        # a path is not inherited
        cwd=str(SCRIPTS),
    )
    lines = completed.stdout.splitlines()
    reached = [line for line in lines if line.startswith("REACHED ")]
    assert not reached, "\n".join(reached)
    selected = [line.split()[1] for line in lines if line.startswith("SELECTED ")]
    answered = [line.split()[1] for line in lines if line.startswith("PYTHON ")]
    # a selection that found nothing, or a probe that fell out early, cannot
    # pass as a probe that found no row reaching C
    assert selected
    assert answered == selected


# btclib's bindings first: loading them puts libsecp256k1's symbols in the
# process, which is how pycoin finds a native library to use at all
PYCOIN_BACKEND = """
import btclib_secp256k1
import pycoin.symbols.btc
print(*(b.__qualname__ for b in type(pycoin.symbols.btc.network.generator).__mro__))
"""


def test_collecting_the_suite_leaves_pycoin_its_own_backend() -> None:
    """Importing a script at collection must not decide pycoin's backend.

    `04-pure-python.py` sets `PYCOIN_NATIVE` before pycoin's first import,
    and pycoin looks its native library up then and never again. A test
    module importing 04 would make every other test run pure-Python pycoin.
    """
    # S603: this interpreter and the constant above
    fresh = subprocess.run(  # noqa: S603
        [sys.executable, "-c", PYCOIN_BACKEND],
        capture_output=True,
        encoding="utf-8",
        check=True,
        env={k: v for k, v in os.environ.items() if k != "PYCOIN_NATIVE"},
    ).stdout.split()
    # imported here and not above: an import above would be the first, and
    # the first decides
    network = importlib.import_module("pycoin.symbols.btc").network
    generator = network.generator
    assert [b.__qualname__ for b in type(generator).__mro__] == fresh


def test_taproot_tweak_hands_each_call_a_key_with_no_cached_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Python arm caches `PubKeyData.point`; a row must not reuse a key.

    A key read twice would be lifted once, and the Python column would time
    the cache. Here one fixture is cycled twice and the call that reads it
    stands in for the Python arm, which reads `point`.
    """
    seen: list[bool] = []

    def python_arm(internal_pubkey: PubKeyData) -> tuple[bytes, int]:
        seen.append("point" in vars(internal_pubkey))
        _ = internal_pubkey.point
        return b"", 0

    monkeypatch.setattr(TWO_PATHS.taproot, "output_pubkey", python_arm)
    monkeypatch.setattr(TWO_PATHS, "TAPROOT_CYCLE", cycle([TWO_PATHS.TAPROOT_KEYS[0]]))
    TWO_PATHS.taproot_tweak()
    TWO_PATHS.taproot_tweak()
    assert seen == [False, False]
