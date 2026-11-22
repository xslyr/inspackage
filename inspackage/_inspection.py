"""Inspection engine: resolves a target (package name or path) and builds the typed model via ``ast``.

The inspected code is never imported or executed: only ``ast.parse``, ``importlib.util.find_spec`` /
``PathFinder.find_spec`` (which locate files without running them) and the filesystem are used.
"""

import ast
import copy
import fnmatch
import importlib.machinery
import importlib.util
import os
from collections.abc import Iterable
from typing import NamedTuple

from typer import Exit

from inspackage._callbacks import console
from inspackage.exception import (
    DefaultExceptions,
    InspectionTargetError,
    NotPythonSourceError,
    TargetNotFoundError,
)
from inspackage.model import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    InspectionResult,
    ModuleInfo,
    PackageInfo,
    VariableInfo,
)

SKIPPED_DIRS = frozenset({"__pycache__"})
PROPERTY_DECORATORS = frozenset({"property", "cached_property", "abstractproperty"})
PROPERTY_ACCESSORS = frozenset({"setter", "getter", "deleter"})
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
FILE_ERRORS = (OSError, SyntaxError, ValueError, RecursionError, MemoryError)


class _Options(NamedTuple):
    include_private: bool = False
    exclude: tuple[str, ...] = ()
    max_depth: int | None = None


# ---------- public API ----------


def get_tree_map(
    package_name: str | None = "",
    package_path: str = "",
    *,
    include_private: bool = False,
    exclude: Iterable[str] = (),
    max_depth: int | None = None,
) -> dict:
    """Legacy dict consumed by ``TreeBuilder``: prints a friendly error and exits with code 1 if not found."""

    try:
        info = inspect_target(
            package_name, package_path, include_private=include_private, exclude=exclude, max_depth=max_depth
        )
    except InspectionTargetError as err:
        console.print(err.message)
        raise Exit(code=1) from err
    return to_tree_map(info)


def find_package_path(package_name: str) -> str:
    """Path of the package directory (or module file) for ``package_name``; prints and exits with 1 if missing."""

    try:
        paths, _ = _resolve(package_name, None)
    except InspectionTargetError as err:
        console.print(err.message)
        raise Exit(code=1) from err
    return paths[0]


def resolve_target(package_name: str | None = None, package_path: str | None = None) -> list[str]:
    """Absolute paths to inspect for a package name or a filesystem path.

    Regular package -> its directory; single-file module -> the ``.py`` file itself; namespace package -> every
    entry of ``submodule_search_locations``. A name that looks like a path (``.``, ``./x``, ``/abs``, ``~/x``,
    ``x.py``) is treated as a path. Raises ``TargetNotFoundError`` / ``NotPythonSourceError``.
    """

    return _resolve(package_name, package_path)[0]


def inspect_target(
    package_name: str | None = None,
    package_path: str | None = None,
    *,
    include_private: bool = False,
    exclude: Iterable[str] = (),
    max_depth: int | None = None,
) -> InspectionResult:
    """Resolve the target and inspect it. Returns ``PackageInfo`` for directories or ``ModuleInfo`` for files."""

    paths, module_name = _resolve(package_name, package_path)
    options = _Options(include_private, tuple(exclude), max_depth)
    results = [_inspect_root(path, module_name, options) for path in paths]
    root = results[0]
    for other in results[1:]:  # namespace package split across several directories
        if isinstance(root, PackageInfo) and isinstance(other, PackageInfo):
            root.modules.extend(other.modules)
            root.packages.extend(other.packages)
            root.errors.extend(other.errors)
    if isinstance(root, PackageInfo):
        root.modules.sort(key=lambda m: (m.name, m.abspath))
        root.packages.sort(key=lambda p: (p.name, p.abspath))
    return root


def inspect_path(
    path: str, *, include_private: bool = False, exclude: Iterable[str] = (), max_depth: int | None = None
) -> InspectionResult:
    """Inspect a directory or a ``.py`` file."""

    return inspect_target(None, path, include_private=include_private, exclude=exclude, max_depth=max_depth)


def is_private(name: str) -> bool:
    """Leading underscore means private, except dunders.

    >>> is_private("_x"), is_private("__init__"), is_private("x"), is_private("__mangled")
    (True, False, False, True)
    """

    return name.startswith("_") and not (len(name) > 4 and name.startswith("__") and name.endswith("__"))


# ---------- target resolution ----------


def _resolve(package_name: str | None, package_path: str | None) -> tuple[list[str], str | None]:
    if package_path:
        return [_resolve_path(package_path)], None

    name = (package_name or "").strip()
    if name and _looks_like_path(name):
        return [_resolve_path(name)], None

    paths = _spec_paths(name) if name else []
    if paths:
        return paths, name
    if name and os.path.exists(name):  # e.g. a directory in cwd that is not on sys.path
        return [_resolve_path(name)], None
    raise TargetNotFoundError(name, DefaultExceptions.package_not_found.format(name))


def _looks_like_path(name: str) -> bool:
    """
    >>> [_looks_like_path(n) for n in (".", "./pkg", "/abs", "~/x", "mod.py", "pkg.sub", "pkg")]
    [True, True, True, True, True, False, False]
    """

    if name.endswith(".py") or "/" in name or os.sep in name or name.startswith(("~", ".")):
        return True
    return not all(part.isidentifier() for part in name.split("."))


def _resolve_path(raw: str) -> str:
    path = os.path.abspath(os.path.expanduser(raw))
    if not os.path.exists(path):
        raise TargetNotFoundError(raw, DefaultExceptions.path_not_found.format(raw))
    if not os.path.isdir(path) and not path.endswith(".py"):
        raise NotPythonSourceError(raw, DefaultExceptions.not_python_source.format(raw))
    return path


def _spec_paths(name: str) -> list[str]:
    """Locate ``name`` without importing it (``find_spec`` on a dotted name would import the parents)."""

    parts = name.split(".")
    try:
        spec = importlib.util.find_spec(parts[0])
    except (ImportError, ValueError):
        return []
    for index in range(1, len(parts)):
        if spec is None or spec.submodule_search_locations is None:
            return []
        spec = importlib.machinery.PathFinder.find_spec(
            ".".join(parts[: index + 1]), list(spec.submodule_search_locations)
        )
    if spec is None:
        return []

    if spec.submodule_search_locations is not None:  # regular or namespace package
        return list(dict.fromkeys(os.path.abspath(p) for p in spec.submodule_search_locations))
    if spec.origin and spec.origin.endswith(".py") and os.path.isfile(spec.origin):  # single-file module
        return [os.path.abspath(spec.origin)]
    raise NotPythonSourceError(name, DefaultExceptions.not_python_source.format(name))  # built-in, .so, .pyc


def _package_prefix(directory: str) -> str:
    """Dotted name of ``directory`` if it is a regular package (walks up while ``__init__.py`` exists)."""

    names: list[str] = []
    while os.path.isfile(os.path.join(directory, "__init__.py")):
        names.insert(0, os.path.basename(directory))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return ".".join(names)


def _join_module(prefix: str, name: str) -> str:
    if name == "__init__":
        return prefix
    return f"{prefix}.{name}" if prefix else name


# ---------- filesystem walk ----------


def _inspect_root(path: str, module_name: str | None, options: _Options) -> InspectionResult:
    name = os.path.basename(path) or path
    prefix = _package_prefix(os.path.dirname(path))
    if os.path.isdir(path):
        return _inspect_dir(path, name, module_name or _join_module(prefix, name), 0, options)
    return _inspect_file(path, name, module_name or _join_module(prefix, name[: -len(".py")]), options)


def _inspect_dir(path: str, rel: str, module: str, depth: int, options: _Options) -> PackageInfo:
    info = PackageInfo(
        name=os.path.basename(path) or path,
        module=module,
        path=rel,
        kind="package" if os.path.isfile(os.path.join(path, "__init__.py")) else "namespace",
        abspath=path,
    )
    try:
        with os.scandir(path) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
    except OSError as exc:
        info.errors.append(_format_error(exc))
        return info

    for entry in entries:
        try:
            _add_entry(info, entry, depth, options)
        except OSError as exc:
            info.errors.append(f"{entry.name}: {_format_error(exc)}")

    init = next((m for m in info.modules if m.name == "__init__.py"), None)
    info.docstring = init.docstring if init else None
    return info


def _add_entry(info: PackageInfo, entry: os.DirEntry, depth: int, options: _Options) -> None:
    name = entry.name
    if name.startswith(".") or name in SKIPPED_DIRS:
        return
    rel = f"{info.path}/{name}"
    if _is_excluded(name, rel.split("/", 1)[1], options.exclude):
        return

    if entry.is_dir(follow_symlinks=False):  # symlinked directories are never followed (loops)
        if not _visible(name, options) or (options.max_depth is not None and depth >= options.max_depth):
            return
        sub = _inspect_dir(entry.path, rel, _join_module(info.module, name), depth + 1, options)
        if sub.modules or sub.packages or sub.errors:
            info.packages.append(sub)
    elif name.endswith(".py") and entry.is_file():
        stem = name[: -len(".py")]
        if _visible(stem, options):
            info.modules.append(_inspect_file(entry.path, rel, _join_module(info.module, stem), options))


def _is_excluded(name: str, rel_to_root: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_to_root, pat) for pat in patterns)


def _format_error(exc: BaseException) -> str:
    kind = type(exc).__name__
    if isinstance(exc, SyntaxError):
        return f"{kind}: {exc.msg} (line {exc.lineno})" if exc.lineno else f"{kind}: {exc.msg}"
    if isinstance(exc, OSError) and exc.strerror:
        return f"{kind}: {exc.strerror}"
    return f"{kind}: {exc}"


# ---------- AST collection ----------


def _inspect_file(path: str, rel: str, module: str, options: _Options) -> ModuleInfo:
    """Parse one ``.py`` file; read/parse failures are recorded in ``errors`` instead of raised."""

    info = ModuleInfo(name=os.path.basename(path), module=module, path=rel, abspath=path)
    try:
        with open(path, "rb") as file:  # bytes: ast honours PEP 263 encoding cookies
            tree = ast.parse(file.read(), filename=path)
    except FILE_ERRORS as exc:
        info.errors.append(_format_error(exc))
    else:
        info.docstring = _first_line(ast.get_docstring(tree))
        info.imports = _collect_imports(tree)
        info.all_exports = _collect_all(tree.body)
        info.variables, info.functions, info.classes = _collect_body(tree.body, "function", options)
    return info


def _visible(name: str, options: _Options) -> bool:
    return options.include_private or not is_private(name)


def _collect_body(body: list[ast.stmt], function_kind: str, options: _Options):
    variables: list[VariableInfo] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    seen: set[str] = set()
    for node in body:
        if isinstance(node, (*FUNCTION_NODES, ast.ClassDef)) and not _visible(node.name, options):
            continue
        if isinstance(node, FUNCTION_NODES):
            kind = function_kind if function_kind == "function" else _method_kind(node)
            functions.append(_function(node, kind))
        elif isinstance(node, ast.ClassDef):
            classes.append(_class(node, options))
        else:
            for var in _variables(node):
                if var.name not in seen and _visible(var.name, options):
                    seen.add(var.name)
                    variables.append(var)
    return variables, functions, classes


def _class(node: ast.ClassDef, options: _Options) -> ClassInfo:
    variables, methods, classes = _collect_body(node.body, "method", options)
    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        docstring=_first_line(ast.get_docstring(node)),
        decorators=[ast.unparse(d) for d in node.decorator_list],
        bases=[ast.unparse(b) for b in node.bases],
        variables=variables,
        methods=methods,
        classes=classes,
    )


def _function(node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> FunctionInfo:
    args = node.args if kind in ("function", "staticmethod") else _drop_first_arg(node.args)
    return FunctionInfo(
        name=node.name,
        lineno=node.lineno,
        kind=kind,
        params=ast.unparse(args),
        returns=ast.unparse(node.returns) if node.returns else None,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=[ast.unparse(d) for d in node.decorator_list],
        docstring=_first_line(ast.get_docstring(node)),
    )


def _method_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name):
            if target.id in ("classmethod", "staticmethod"):
                return target.id
            if target.id in PROPERTY_DECORATORS:
                return "property"
        elif isinstance(target, ast.Attribute):
            if target.attr in PROPERTY_DECORATORS or target.attr in PROPERTY_ACCESSORS:
                return "property"
    return "method"


def _drop_first_arg(args: ast.arguments) -> ast.arguments:
    """Remove the implicit ``self``/``cls`` (first positional parameter) from the AST, never from the text."""

    new = copy.copy(args)
    if args.posonlyargs:
        new.posonlyargs = args.posonlyargs[1:]
    elif args.args:
        new.args = args.args[1:]
    else:
        return args
    positional = len(new.posonlyargs) + len(new.args)
    if len(args.defaults) > positional:
        new.defaults = args.defaults[len(args.defaults) - positional :]
    return new


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for elt in target.elts for name in _target_names(elt)]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []  # attributes/subscripts (x.y = 1, d[k] = 1) do not define names


def _variables(node: ast.stmt) -> list[VariableInfo]:
    if isinstance(node, ast.Assign):
        names = [name for target in node.targets for name in _target_names(target)]
        annotation = None
    elif isinstance(node, ast.AnnAssign):
        names = _target_names(node.target)
        annotation = ast.unparse(node.annotation)
    else:
        return []
    return [VariableInfo(name=name, lineno=node.lineno, annotation=annotation) for name in dict.fromkeys(names)]


def _collect_imports(tree: ast.Module) -> list[ImportInfo]:
    """Every import in the file (module level, conditional or local), in source order."""

    found: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(ImportInfo(module=alias.name, lineno=node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            found.append(ImportInfo(module=node.module or "", lineno=node.lineno, names=names, level=node.level))
    found.sort(key=lambda item: item.lineno)
    return found


def _collect_all(body: list[ast.stmt]) -> list[str] | None:
    """Literal ``__all__`` (``=``, annotated or ``+=``); ``None`` when absent or not a literal."""

    exports: list[str] | None = None
    for node in body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        else:
            continue
        if node.value is None or not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        values = _literal_strings(node.value)
        if values is None:
            continue
        if isinstance(node, ast.AugAssign):
            if isinstance(node.op, ast.Add):
                exports = (exports or []) + values
        else:
            exports = values
    return exports


def _literal_strings(node: ast.expr) -> list[str] | None:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return None
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _first_line(doc: str | None) -> str | None:
    if not doc:
        return None
    lines = doc.strip().splitlines()
    return lines[0].strip() if lines else None


# ---------- legacy dict (consumed by TreeBuilder and --save) ----------


def to_tree_map(info: InspectionResult) -> dict:
    """Convert the model to the legacy ``tree_map`` dict.

    Keys kept from v0.1: directory ``{name, category="directory", nodes}``, file ``{name, category="file",
    structure: {variables, methods, classes}}``, class ``{name, constructor, variables, properties, methods}``.
    Added: ``errors`` on directories/files and ``classes`` (nested) on classes.
    """

    return _legacy_module(info) if isinstance(info, ModuleInfo) else _legacy_package(info)


def _legacy_package(info: PackageInfo) -> dict:
    children = [(p.name, _legacy_package(p)) for p in info.packages] + [
        (m.name, _legacy_module(m)) for m in info.modules
    ]
    children.sort(key=lambda child: child[0])
    return {"name": info.name, "category": "directory", "nodes": [node for _, node in children], "errors": info.errors}


def _legacy_variable(var: VariableInfo) -> str:
    return f"{var.name} : {var.annotation}" if var.annotation else var.name


def _legacy_module(info: ModuleInfo) -> dict:
    groups = {
        "variables": [_legacy_variable(v) for v in info.variables],
        "methods": [(f.name, f.params, f.returns) for f in info.functions],
        "classes": [_legacy_class(c) for c in info.classes],
    }
    structure = {key: value for key, value in groups.items() if value}
    return {"name": info.name, "category": "file", "structure": structure, "errors": info.errors}


def _legacy_class(info: ClassInfo) -> dict:
    groups: dict[str, list] = {
        "constructor": [(m.name, m.params, m.returns or "") for m in info.methods if m.name == "__init__"],
        "variables": [_legacy_variable(v) for v in info.variables],
        "properties": list(dict.fromkeys(m.name for m in info.methods if m.kind == "property")),
        "methods": [
            (m.name, m.params, m.returns or "") for m in info.methods if m.name != "__init__" and m.kind != "property"
        ],
        "classes": [_legacy_class(c) for c in info.classes],
    }
    return {"name": info.name, **{key: value for key, value in groups.items() if value}}


__all__ = [
    "get_tree_map",
    "find_package_path",
    "resolve_target",
    "inspect_target",
    "inspect_path",
    "is_private",
    "to_tree_map",
]
