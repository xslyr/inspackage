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
TRY_NODES = (ast.Try, ast.TryStar) if hasattr(ast, "TryStar") else (ast.Try,)  # ast.TryStar: Python 3.11+


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
            _merge_package(root, other)
    return root


def _merge_package(target: PackageInfo, other: PackageInfo) -> None:
    """Merge ``other`` into ``target`` recursively: subpackages with the same name become a single node."""

    target.modules.extend(other.modules)
    target.errors.extend(other.errors)
    if target.docstring is None:
        target.docstring = other.docstring
    by_name = {package.name: package for package in target.packages}
    for package in other.packages:
        if package.name in by_name:
            _merge_package(by_name[package.name], package)
        else:
            target.packages.append(package)
            by_name[package.name] = package
    target.modules.sort(key=lambda m: (m.name, m.abspath))
    target.packages.sort(key=lambda p: (p.name, p.abspath))


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
        if _is_explicit_path(name) or os.path.exists(name):
            return [_resolve_path(name)], None
        raise TargetNotFoundError(name, _package_not_found(name))  # e.g. ``typing-extensions``

    paths = _spec_paths(name) if name else []
    if paths:
        return paths, name
    if name and os.path.exists(name):  # e.g. a directory in cwd that is not on sys.path
        return [_resolve_path(name)], None
    raise TargetNotFoundError(name, _package_not_found(name))


def _package_not_found(name: str) -> str:
    message = DefaultExceptions.format(DefaultExceptions.package_not_found, name)
    if "-" in name:  # distribution name typed instead of the import name
        message += DefaultExceptions.format(DefaultExceptions.did_you_mean, name.replace("-", "_"))
    return message


def _looks_like_path(name: str) -> bool:
    """
    >>> [_looks_like_path(n) for n in (".", "./pkg", "/abs", "~/x", "mod.py", "pkg.sub", "pkg", "a-b")]
    [True, True, True, True, True, False, False, True]
    """

    if _is_explicit_path(name) or name.startswith("."):
        return True
    return not all(part.isidentifier() for part in name.split("."))


def _is_explicit_path(name: str) -> bool:
    """Unambiguously a path (never a package name), even if it does not exist.

    >>> [_is_explicit_path(n) for n in ("./pkg", "a\\\\b", "~x", "mod.py", "a-b", ".")]
    [True, True, True, True, False, False]
    """

    return name.endswith(".py") or "~" in name or any(sep in name for sep in ("/", "\\", os.sep))


def _resolve_path(raw: str) -> str:
    path = os.path.abspath(os.path.expanduser(raw))
    if not os.path.exists(path):
        raise TargetNotFoundError(raw, DefaultExceptions.format(DefaultExceptions.path_not_found, raw))
    if not os.path.isdir(path) and not path.endswith(".py"):
        raise NotPythonSourceError(raw, DefaultExceptions.format(DefaultExceptions.not_python_source, raw))
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
    origin = _source_origin(spec)
    if origin:  # single-file module
        return [origin]
    raise NotPythonSourceError(  # built-in, .so, .pyc
        name, DefaultExceptions.format(DefaultExceptions.not_python_source, name)
    )


def _source_origin(spec: importlib.machinery.ModuleSpec) -> str | None:
    """``.py`` file of a single-file module; frozen stdlib modules (3.11+: ``os``, ``abc``) via ``loader_state``."""

    origin = spec.origin
    if origin == "frozen":
        origin = getattr(spec.loader_state, "filename", None)
    if isinstance(origin, str) and origin.endswith(".py") and os.path.isfile(origin):
        return os.path.abspath(origin)
    return None


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

    if entry.is_symlink() and entry.is_dir():  # symlinked directories are never followed (loops)
        if _visible(name, options):
            info.errors.append(f"Skipped symlinked directory: {name}")
    elif entry.is_dir(follow_symlinks=False):
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
        return info
    try:  # ast.unparse of pathological expressions may raise RecursionError: one file never aborts the inspection
        docstring = _first_line(ast.get_docstring(tree))
        imports = _collect_imports(tree)
        all_exports = _collect_all(tree.body)
        variables, functions, classes = _collect_body(tree.body, "function", options)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        info.errors.append(_format_error(exc))
    else:
        info.docstring, info.imports, info.all_exports = docstring, imports, all_exports
        info.variables, info.functions, info.classes = variables, functions, classes
    return info


def _visible(name: str, options: _Options) -> bool:
    return options.include_private or not is_private(name)


def _collect_body(body: list[ast.stmt], function_kind: str, options: _Options):
    """Definitions of one scope, including those inside top-level ``if``/``try`` blocks (never inside functions).

    The same name defined in several branches is kept once (first occurrence); ``@overload`` stubs are dropped
    when the implementation exists, otherwise only the first one is kept.
    """

    variables: list[VariableInfo] = []
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    statements = list(_flatten_blocks(body, False))
    implemented = {node.name for node, _ in statements if isinstance(node, FUNCTION_NODES) and not _is_overload(node)}
    seen_vars: set[str] = set()
    seen_defs: dict[str, bool] = {}  # name -> first definition was inside a conditional block
    for node, conditional in statements:
        if isinstance(node, (*FUNCTION_NODES, ast.ClassDef)):
            if not _keep_definition(node, conditional, seen_defs, implemented, options):
                continue
            if isinstance(node, ast.ClassDef):
                classes.append(_class(node, options))
            else:
                kind = function_kind if function_kind == "function" else _method_kind(node)
                functions.append(_function(node, kind))
        else:
            for var in _variables(node):
                if var.name not in seen_vars and _visible(var.name, options):
                    seen_vars.add(var.name)
                    variables.append(var)
    return variables, functions, classes


def _keep_definition(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    conditional: bool,
    seen: dict[str, bool],
    implemented: set[str],
    options: _Options,
) -> bool:
    name = node.name
    if not _visible(name, options):
        return False
    if name in seen and (conditional or seen[name]):
        return False  # same name defined in another branch of an if/try
    if isinstance(node, FUNCTION_NODES) and _is_overload(node) and (name in implemented or name in seen):
        return False
    seen.setdefault(name, conditional)
    return True


def _flatten_blocks(body: list[ast.stmt], conditional: bool) -> Iterable[tuple[ast.stmt, bool]]:
    """Yield ``(statement, inside_a_conditional_block)`` descending into ``if``/``try`` (and ``try*``) blocks."""

    for node in body:
        if isinstance(node, ast.If):
            yield from _flatten_blocks(node.body + node.orelse, True)
        elif isinstance(node, TRY_NODES):
            blocks = node.body + [stmt for handler in node.handlers for stmt in handler.body]
            yield from _flatten_blocks(blocks + node.orelse + node.finalbody, True)
        else:
            yield node, conditional


def _is_overload(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """``@overload`` / ``@typing.overload`` / ``@typing_extensions.overload``."""

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "overload":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "overload":
            return True
    return False


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
    """Literal ``__all__`` (``=``, annotated, ``+=``, ``.extend``/``.append``); ``None`` when absent or unknown.

    Once ``__all__`` receives a non-literal value its content is unknown: later ``+=``/``.extend`` are ignored
    until a new literal assignment.
    """

    exports: list[str] | None = None
    known = True
    for node in body:
        if isinstance(node, ast.Expr):
            is_call, added = _all_method_call(node.value)
            if is_call and known:
                exports = None if added is None else (exports or []) + added
                known = added is not None
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        else:
            continue
        if node.value is None or not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        values = _literal_strings(node.value)
        if isinstance(node, ast.AugAssign):
            if not known:
                continue
            if isinstance(node.op, ast.Add) and values is not None:
                exports = (exports or []) + values
            else:
                exports, known = None, False
        else:
            exports, known = values, values is not None
    return exports


def _all_method_call(node: ast.expr) -> tuple[bool, list[str] | None]:
    """``(is __all__.extend/append call, literal names added or None if not literal)``."""

    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "__all__"
        and node.func.attr in ("extend", "append")
        and len(node.args) == 1
        and not node.keywords
    ):
        return False, None
    arg = node.args[0]
    if node.func.attr == "append":
        return True, [arg.value] if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None
    return True, _literal_strings(arg)


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
