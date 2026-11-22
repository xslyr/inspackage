import json
import sys
import textwrap

import pytest
from helpers import assert_snapshot, tree_has

from inspackage._inspection import get_tree_map, inspect_path, inspect_target, resolve_target, to_tree_map
from inspackage.exception import NotPythonSourceError, TargetNotFoundError
from inspackage.model import SCHEMA_VERSION, ClassInfo, FunctionInfo, ModuleInfo, PackageInfo


def _write(path, source: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def _module(path, **kwargs) -> ModuleInfo:
    info = inspect_path(str(path), **kwargs)
    assert isinstance(info, ModuleInfo)
    return info


def _by_name(items, name):
    return next(item for item in items if item.name == name)


@pytest.fixture
def core(samplepkg_path) -> ModuleInfo:
    return _module(samplepkg_path / "core.py")


# ---------- to_dict / schema ----------


def test_root_to_dict_has_schema_version_and_type(samplepkg_ok):
    data = inspect_path(str(samplepkg_ok)).to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["type"] == "package"
    assert "schema_version" not in data["modules"][0]
    assert json.loads(json.dumps(data)) == data


def test_module_to_dict_has_type_module(fixtures_dir):
    data = inspect_path(str(fixtures_dir / "single_module.py")).to_dict()
    assert (data["type"], data["name"], data["module"], data["path"]) == (
        "module",
        "single_module.py",
        "single_module",
        "single_module.py",
    )


def test_to_dict_has_no_absolute_paths(samplepkg_ok):
    text = json.dumps(inspect_path(str(samplepkg_ok)).to_dict())
    assert str(samplepkg_ok) not in text
    assert "abspath" not in text


def test_model_json_contract_snapshot(samplepkg_ok):
    data = inspect_path(str(samplepkg_ok)).to_dict()
    assert_snapshot("samplepkg_model.json", json.dumps(data, indent=2) + "\n")


# ---------- functions, classes, kinds ----------


def test_method_kinds_come_from_decorators(core):
    base = _by_name(core.classes, "Base")
    kinds = {m.name: m.kind for m in base.methods}
    assert kinds["prop_value"] == "property"
    assert kinds["from_name"] == "classmethod"
    assert kinds["static_helper"] == "staticmethod"
    assert kinds["public_method"] == "method"
    assert kinds["__init__"] == "method"
    assert _by_name(base.methods, "prop_value").decorators == ["property"]


def test_self_and_cls_are_removed_via_ast(core):
    base = _by_name(core.classes, "Base")
    assert _by_name(base.methods, "from_name").params == "cls_name"
    assert _by_name(base.methods, "public_method").params == "itself, other: int=1"
    assert _by_name(base.methods, "public_method").returns == "str"
    assert _by_name(base.methods, "static_helper").params == "value"


def test_async_flag_and_linenos(core):
    func = _by_name(core.functions, "top_level_async")
    assert func.is_async and func.kind == "function" and func.lineno == 69
    base = _by_name(core.classes, "Base")
    assert _by_name(base.methods, "async_method").is_async
    assert not _by_name(base.methods, "public_method").is_async
    assert base.lineno == 4


def test_docstrings_bases_and_nested_classes(core):
    base = _by_name(core.classes, "Base")
    assert core.docstring == "Core module."
    assert base.docstring == "Base class."
    inner = _by_name(base.classes, "Inner")
    assert isinstance(inner, ClassInfo)
    assert inner.docstring == "Nested class."
    assert [m.name for m in inner.methods] == ["inner_method"]
    assert _by_name(core.classes, "Child").bases == ["Base"]


def test_private_members_hidden_by_default_and_included_on_request(samplepkg_path):
    hidden = _module(samplepkg_path / "core.py")
    shown = _module(samplepkg_path / "core.py", include_private=True)
    assert "_private_func" not in [f.name for f in hidden.functions]
    assert "_private_func" in [f.name for f in shown.functions]
    assert "_PrivateClass" in [c.name for c in shown.classes]
    assert "_hidden_var" in [v.name for v in _by_name(shown.classes, "Base").variables]


def test_dunder_methods_are_public(tmp_path):
    info = _module(_write(tmp_path / "m.py", "class A:\n    def __repr__(self):\n        return ''\n"))
    assert [m.name for m in info.classes[0].methods] == ["__repr__"]


def test_edge_case_signatures_and_decorators(tmp_path):
    source = '''
        """First line.

        More text.
        """
        import os, os.path as osp
        from . import sibling
        from ..parent import a as b, c

        __all__ = ["f"]
        __all__ += ["C"]

        class C(Base, metaclass=Meta):
            @property
            def value(self):
                """Value doc.

                Details."""
            @value.setter
            def value(self, new):
                pass
            @functools.cached_property
            def cached(self):
                pass
            def posonly(self, /, x, *args, y=1, **kw):
                pass
            def defaulted(self=None, other=2):
                pass
            @staticmethod
            def static(self_like):
                pass
    '''
    path = _write(tmp_path / "edge.py", source)
    info = _module(path)
    assert info.docstring == "First line."
    assert info.all_exports == ["f", "C"]
    assert [(i.module, i.names, i.level) for i in info.imports] == [
        ("os", [], 0),
        ("os.path", [], 0),
        ("", ["sibling"], 1),
        ("parent", ["a", "c"], 2),
    ]
    cls = info.classes[0]
    assert cls.bases == ["Base"]
    methods = {(m.name, m.kind, m.params) for m in cls.methods}
    assert ("value", "property", "") in methods
    assert ("value", "property", "new") in methods
    assert ("cached", "property", "") in methods
    assert ("posonly", "method", "x, *args, y=1, **kw") in methods
    assert ("defaulted", "method", "other=2") in methods
    assert ("static", "staticmethod", "self_like") in methods
    assert _by_name(cls.methods, "value").docstring == "Value doc."
    legacy_class = to_tree_map(info)["structure"]["classes"][0]
    assert legacy_class["properties"] == ["value", "cached"]


def test_dynamic_all_is_none_and_variables_dedupe(tmp_path):
    info = _module(_write(tmp_path / "m.py", "__all__ = list(x)\nX: int\nX = 1\nY, *REST = 1, 2, 3\nobj.attr = 1\n"))
    assert info.all_exports is None
    assert [(v.name, v.annotation) for v in info.variables] == [
        ("__all__", None),
        ("X", "int"),
        ("Y", None),
        ("REST", None),
    ]


# ---------- errors ----------


def test_parse_errors_are_recorded_in_module_errors(samplepkg_path):
    pkg = inspect_path(str(samplepkg_path))
    assert isinstance(pkg, PackageInfo)
    broken = _by_name(pkg.modules, "broken.py")
    assert broken.errors and broken.errors[0].startswith("SyntaxError")
    assert not _by_name(pkg.modules, "core.py").errors


def test_undecodable_file_error_is_recorded(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "bad.py").write_bytes(b"X = '\xff\xfe'\n")
    pkg = inspect_path(str(tmp_path / "pkg"))
    assert _by_name(pkg.modules, "bad.py").errors


# ---------- filesystem walk ----------


def test_private_and_cache_directories_are_skipped(tmp_path):
    pkg = tmp_path / "pkg"
    _write(pkg / "_private" / "hidden.py", "H = 1\n")
    _write(pkg / "_internal.py", "I = 1\n")
    _write(pkg / "__pycache__" / "x.py", "C = 1\n")
    _write(pkg / "data" / "readme.txt", "no python here\n")
    _write(pkg / "ok.py", "OK = 1\n")
    info = inspect_path(str(pkg))
    assert [m.name for m in info.modules] == ["ok.py"]
    assert info.packages == []
    private = inspect_path(str(pkg), include_private=True)
    assert [m.name for m in private.modules] == ["_internal.py", "ok.py"]
    assert [p.name for p in private.packages] == ["_private"]


def test_exclude_and_max_depth(tmp_path):
    pkg = tmp_path / "pkg"
    _write(pkg / "a.py", "A = 1\n")
    _write(pkg / "test_a.py", "T = 1\n")
    _write(pkg / "sub" / "b.py", "B = 1\n")
    _write(pkg / "sub" / "deep" / "c.py", "C = 1\n")
    assert [m.name for m in inspect_path(str(pkg), exclude=["test_*"]).modules] == ["a.py"]
    assert inspect_path(str(pkg), exclude=["sub/deep"]).packages[0].packages == []
    assert inspect_path(str(pkg), max_depth=0).packages == []
    shallow = inspect_path(str(pkg), max_depth=1)
    assert [p.name for p in shallow.packages] == ["sub"]
    assert shallow.packages[0].packages == []


def test_dotted_module_names_follow_init_files(samplepkg_path):
    sub = inspect_path(str(samplepkg_path / "sub"))
    assert sub.module == "samplepkg.sub"
    assert sub.kind == "package"
    assert [m.module for m in sub.modules] == ["samplepkg.sub", "samplepkg.sub.util"]
    assert _module(samplepkg_path / "core.py").module == "samplepkg.core"


# ---------- target resolution ----------


def test_dotted_name_is_resolved_without_importing(on_syspath, samplepkg_path):
    assert resolve_target("samplepkg.sub") == [str(samplepkg_path / "sub")]
    assert resolve_target("samplepkg.core") == [str(samplepkg_path / "core.py")]
    assert "samplepkg" not in sys.modules
    assert inspect_target("samplepkg.sub").module == "samplepkg.sub"


def test_namespace_package_split_across_directories_is_merged(tmp_path, monkeypatch):
    _write(tmp_path / "one" / "splitns" / "a.py", "A = 1\n")
    _write(tmp_path / "two" / "splitns" / "b.py", "B = 1\n")
    monkeypatch.syspath_prepend(str(tmp_path / "two"))
    monkeypatch.syspath_prepend(str(tmp_path / "one"))
    info = inspect_target("splitns")
    assert info.kind == "namespace"
    assert [m.name for m in info.modules] == ["a.py", "b.py"]


def test_dot_and_path_like_names_are_paths(samplepkg_ok, monkeypatch):
    monkeypatch.chdir(samplepkg_ok)
    assert tree_has(get_tree_map("."), "core.py")
    assert get_tree_map("./core.py")["name"] == "core.py"


def test_builtin_module_is_not_python_source():
    with pytest.raises(NotPythonSourceError):
        resolve_target("sys")


def test_missing_path_and_non_python_file(tmp_path):
    with pytest.raises(TargetNotFoundError):
        resolve_target(package_path=str(tmp_path / "missing"))
    (tmp_path / "notes.txt").write_text("x")
    with pytest.raises(NotPythonSourceError):
        resolve_target(package_path=str(tmp_path / "notes.txt"))


def test_function_info_defaults_are_serializable():
    data = FunctionInfo(name="f", lineno=1).to_dict()
    assert data == {
        "name": "f",
        "lineno": 1,
        "kind": "function",
        "params": "",
        "returns": None,
        "is_async": False,
        "decorators": [],
        "docstring": None,
    }
