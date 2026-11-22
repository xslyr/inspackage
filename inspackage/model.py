"""Typed data model produced by the inspection engine.

Every renderer (tree, TUI, JSON, ...) consumes these dataclasses. ``to_dict()`` on a root object
(:class:`PackageInfo` or :class:`ModuleInfo`) is the public JSON contract: any change to its shape must
increment :data:`SCHEMA_VERSION`.

>>> fn = FunctionInfo(name="f", lineno=1, kind="function", params="x", returns="int")
>>> ModuleInfo(name="m.py", module="m", path="m.py", functions=[fn]).to_dict()["schema_version"]
1
"""

# pylint: disable=too-many-instance-attributes

from collections.abc import Iterator
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

SCHEMA_VERSION = 1

FUNCTION_KINDS = ("function", "method", "classmethod", "staticmethod", "property")


# Fields with this metadata stay in memory but are left out of ``to_dict()`` (e.g. machine specific absolute paths).
INTERNAL = {"export": False}


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _serialize(getattr(value, f.name)) for f in fields(value) if f.metadata.get("export", True)}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


class _Serializable:
    def to_dict(self) -> dict:
        """Plain dict (JSON serializable) with a stable key order."""
        return _serialize(self)


class _Root(_Serializable):
    TYPE = ""

    def to_dict(self) -> dict:
        """Plain dict with ``schema_version`` and ``type`` ("package" or "module") on top."""
        return {"schema_version": SCHEMA_VERSION, "type": self.TYPE, **_serialize(self)}


@dataclass
class VariableInfo(_Serializable):
    name: str
    lineno: int
    annotation: str | None = None


@dataclass
class ImportInfo(_Serializable):
    """``import a.b`` -> module="a.b", names=[]; ``from ..x import y`` -> module="x", names=["y"], level=2."""

    module: str
    lineno: int
    names: list[str] = field(default_factory=list)
    level: int = 0


@dataclass
class FunctionInfo(_Serializable):
    """Function or method. ``params`` excludes the implicit ``self``/``cls``; ``kind`` is one of FUNCTION_KINDS."""

    name: str
    lineno: int
    kind: str = "function"
    params: str = ""
    returns: str | None = None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None


@dataclass
class ClassInfo(_Serializable):
    name: str
    lineno: int
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    variables: list[VariableInfo] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    classes: list["ClassInfo"] = field(default_factory=list)


@dataclass
class ModuleInfo(_Root):
    """A ``.py`` file. ``name`` is the file name, ``module`` the dotted name and ``path`` is relative to the
    parent of the inspected root (posix separators). Read/parse failures go to ``errors``."""

    TYPE = "module"

    name: str
    module: str
    path: str
    docstring: str | None = None
    all_exports: list[str] | None = None
    imports: list[ImportInfo] = field(default_factory=list)
    variables: list[VariableInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    abspath: str = field(default="", repr=False, compare=False, metadata=INTERNAL)


@dataclass
class PackageInfo(_Root):
    """A directory. ``kind`` is "package" (has ``__init__.py``) or "namespace". Children are sorted by name;
    directory listing failures go to ``errors``."""

    TYPE = "package"

    name: str
    module: str
    path: str
    kind: str = "package"
    docstring: str | None = None
    modules: list[ModuleInfo] = field(default_factory=list)
    packages: list["PackageInfo"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    abspath: str = field(default="", repr=False, compare=False, metadata=INTERNAL)


InspectionResult = PackageInfo | ModuleInfo


def iter_modules(info: InspectionResult) -> Iterator[ModuleInfo]:
    """Every module (``.py`` file) under ``info`` (``info`` itself when it is a module)."""

    if isinstance(info, ModuleInfo):
        yield info
        return
    yield from info.modules
    for sub in info.packages:
        yield from iter_modules(sub)


def iter_errors(info: InspectionResult) -> Iterator[tuple[str, str]]:
    """``(path, message)`` for every read/parse failure under ``info``; ``path`` is absolute when known."""

    for message in info.errors:
        yield info.abspath or info.path, message
    if isinstance(info, PackageInfo):
        for module in info.modules:
            yield from iter_errors(module)
        for sub in info.packages:
            yield from iter_errors(sub)


__all__ = [
    "SCHEMA_VERSION",
    "FUNCTION_KINDS",
    "VariableInfo",
    "ImportInfo",
    "FunctionInfo",
    "ClassInfo",
    "ModuleInfo",
    "PackageInfo",
    "InspectionResult",
    "iter_modules",
    "iter_errors",
]
