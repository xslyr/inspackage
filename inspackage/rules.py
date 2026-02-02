import os
from enum import Enum


class Rules(Enum):
    path = {
        "DUNDER_PATHS": {"expected": False, "function": lambda x: x.startswith("_")},
        "HIDDEN_PATHS": {"expected": False, "function": lambda x: x.startswith(".")},
    }

    file = {
        "DUNDER_FILES": {"expected": False, "function": lambda x: x.startswith("_")},
        "HIDDEN_FILES": {"expected": False, "function": lambda x: x.startswith(".")},
        "PYTHON_FILES": {"expected": True, "function": lambda x: x.endswith(".py")},
        "BASH_FILES": {"expected": False, "function": lambda x: x.endswith(".sh")},
    }


def _check_allowed(path_or_file: str, rules: Rules):
    validation = []

    for k, rule in rules.value.items():
        expected = os.getenv(k) or rule["expected"]
        validation.append(rule["function"](path_or_file) == expected)

    return all(validation)


def check_path(path: str):
    p = os.path.basename(os.path.normpath(path))
    return _check_allowed(p, Rules.path)


def check_file(file: str):
    f = os.path.basename(file)
    return _check_allowed(f, Rules.file)


__all__ = ["check_path", "check_file"]
