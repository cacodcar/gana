"""Inspect bootstrap failures and native model state in a fresh interpreter."""

import json
import sys
from importlib import import_module
from importlib.abc import MetaPathFinder


class NativeImportFailure(MetaPathFinder):
    """Simulate loader failures without moving or modifying the extension."""

    def __init__(self, failure):
        """Select one failure at the extension's actual import boundary."""
        self.failure = failure

    def find_spec(self, fullname, path=None, target=None):
        """Leave other imports alone, including the Python package itself."""
        del path, target
        if fullname != "gana._native":
            return
        if self.failure == "missing":
            message = "No module named 'gana._native'"
            raise ModuleNotFoundError(message, name=fullname)
        if self.failure == "dependency":
            message = "No module named 'native_dependency'"
            raise ModuleNotFoundError(message, name="native_dependency")
        message = "Native loader rejected an incompatible binary"
        raise ImportError(message, name=fullname)


def error_record(error):
    """Expose exception identity and chaining independently of tracebacks."""
    cause = error.__cause__
    return {
        "error": type(error).__name__,
        "message": str(error),
        "name": getattr(error, "name", None),
        "cause": type(cause).__name__ if cause is not None else None,
        "cause_name": getattr(cause, "name", None),
        "cause_message": str(cause) if cause is not None else None,
    }


def native_model_record(module, namespace):
    """Check real registration and exact small-model outputs after import."""
    storage = import_module(f"{namespace}.storage.parameters")
    program = module.Prg()
    program.i = module.I("a", "b")
    program.k = module.P(program.i, _=[2, 3])
    program.x = module.V(program.i)
    program.c = program.x <= program.k
    program.o = module.inf(module.sigma(program.k * program.x))
    return {
        "backend": storage.BACKEND,
        "native": storage.NATIVE,
        "native_parameter": "_native_storage" in program.k.__dict__,
        "values": list(program.k._),
        "A": program.A,
        "B": program.B,
        "C": program.C,
    }


def main():
    """Use a fresh process so cached modules cannot conceal loader errors."""
    namespace, failure = sys.argv[1:]
    if failure != "none":
        sys.meta_path.insert(0, NativeImportFailure(failure))
    try:
        module = import_module(namespace)
    except (ImportError, ValueError) as error:
        result = error_record(error)
    else:
        result = native_model_record(module, namespace)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
