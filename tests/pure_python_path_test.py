# Copyright (c) The btclib developers
# Distributed under the MIT software license, see the accompanying
# LICENSE file or https://opensource.org/license/mit for the full text.

"""Every row of `02-btclib-vs-btclib.py` really has a pure-Python path.

That script's whole premise is that each operation in it can be answered
twice, once in C and once in Python, and `python_arithmetic_only` is how it
asks for the second. The premise is not self-evident and it has already
been wrong once: BIP32 derivation was a row until this check was written,
and it never had a Python path at all -- `bip32._prv_key_derivation` calls
`btclib_secp256k1.keys.prvkey_tweak_add` whatever the dispatch says, btclib
saying why beside the call, so the switch moved only the public key derived
for the fingerprint. Its pair read far narrower than every other, and nothing
but arithmetic on the printed table said so.

What is checked here is the thing a timing cannot check: not how long the
Python path takes, but that it *is* the Python path. Every bindings entry
point is replaced with a function that raises, the switch is thrown, and
every operation is called once. A row that has quietly kept a foot in C
raises instead of answering.

The predicate is left alone deliberately. `_libsecp256k1_serves` lives
beside the bindings imports and matches the same name, but it is the
question rather than an answer: replacing it breaks the dispatch for every
row and proves nothing about any of them.

In a subprocess, because none of this can be undone in the process that
does it -- neither the switch, which `02-btclib-vs-btclib.py` documents, nor
the patching, which reaches into modules the rest of the suite imports.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

# `import` cannot spell it: the six scripts are named for the pages
# they publish, which begin with a number and hold hyphens. Nothing
# imports them by statement -- a person runs `python scripts/<name>.py`
# and the suite asks `importlib` for them by string, which is indifferent
# to what a Python identifier may look like
TWO_PATHS = importlib.import_module("02-btclib-vs-btclib")

# where `conftest.py` points this process's own import path, spelled again
# rather than imported from it: mypy resolves modules by path and a test
# importing its own conftest is a module it cannot find
SCRIPTS = Path(__file__).parents[1] / "scripts"

# blocks the bindings, throws the switch, and reports one line per
# operation. Written as a program rather than as a helper module because it
# has to run somewhere this suite is not: see the docstring
PROBE = """
import importlib, sys, types
B = importlib.import_module("02-btclib-vs-btclib")


class BindingsCalled(RuntimeError):
    pass


def raiser(name):
    def f(*args, **kwargs):
        raise BindingsCalled(name)

    return f


B.python_arithmetic_only()

# the names btclib bound at import time, `from btclib_secp256k1 import x as
# libsecp256k1_x` being a reference the module holds and not a lookup it
# repeats -- patching the bindings alone would leave every one of them live
for module in list(sys.modules.values()):
    if not isinstance(module, types.ModuleType):
        continue
    if not (module.__name__ or "").startswith("btclib."):
        continue
    for attribute in dir(module):
        if "libsecp256k1" in attribute and attribute != "_libsecp256k1_serves":
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

for name, operation, _, _ in B.OPERATIONS:
    try:
        operation()
    except BindingsCalled as reached:
        print("REACHED " + name + " " + str(reached))
    else:
        print("PYTHON " + name)
"""


def test_every_operation_answers_without_the_bindings() -> None:
    """Block the bindings, then call every row: each must still answer."""
    # S603 asks whether untrusted input reaches a subprocess: what reaches
    # this one is this interpreter and the constant above, both written here
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", PROBE],
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
    # every row reported, so a probe that fell out early cannot pass as a
    # probe that found nothing
    answered = [line for line in lines if line.startswith("PYTHON ")]
    assert len(answered) == len(TWO_PATHS.OPERATIONS)
