from enum import StrEnum


class Icon(StrEnum):
    folder = "\uf07b"
    file = "\uf15b"
    obj = "\uf0e8"
    var = "\uf02b"
    method = "\uf0ad"


__all__ = ["Icon"]
