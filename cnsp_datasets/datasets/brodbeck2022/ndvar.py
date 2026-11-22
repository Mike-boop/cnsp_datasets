"""Read the shipped eelbrain NDVar pickles without eelbrain (restricted unpickler, whitelist only)."""
from __future__ import annotations

import pickle

import numpy as np

_NUMPY = {("numpy", "ndarray"), ("numpy", "dtype"), ("numpy.core.multiarray", "_reconstruct"),
         ("numpy.core.multiarray", "scalar"), ("numpy.core.numeric", "_frombuffer")}


class _Stub:
    """Stand-in for an eelbrain class: keeps the pickled state dict."""

    def __setstate__(self, state):
        self.state = state


_STUBS = {("eelbrain._data_obj", name): type(name, (_Stub,), {}) for name in ("NDVar", "Scalar", "UTS")}


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in _STUBS:
            return _STUBS[module, name]
        if (module.replace("numpy._core.", "numpy.core."), name) in _NUMPY:
            if module.startswith("numpy.core.") and hasattr(np, "_core"):  # numpy 2 renamed numpy.core
                module = "numpy._core." + module[len("numpy.core."):]
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"blocked {module}.{name}")


def load(path: str) -> _Stub:
    """NDVar stub: .state holds x (array), dims (Scalar/UTS stubs with their .state), name, info."""
    with open(path, "rb") as f:
        return _Unpickler(f).load()
