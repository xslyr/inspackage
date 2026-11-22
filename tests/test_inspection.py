import os

import pytest
from helpers import collect_strings, tree_contains, tree_has
from typer import Exit

from inspackage._inspection import find_package_path, get_tree_map, inspect_path

# ---------- behaviour that already works ----------


def test_find_package_path_resolves_regular_package_by_name(on_syspath, samplepkg_path):
    assert find_package_path("samplepkg") == str(samplepkg_path)


def test_unknown_package_name_exits_with_code_1():
    with pytest.raises(Exit) as err:
        get_tree_map("xyz_package_that_does_not_exist")
    assert err.value.exit_code == 1


def test_directory_map_lists_modules_and_subpackages(samplepkg_ok):
    tree = get_tree_map(package_path=str(samplepkg_ok))
    assert tree["name"] == "samplepkg"
    for name in ("core.py", "constants.py", "sub", "util.py"):
        assert tree_has(tree, name), name


def test_relative_and_absolute_paths_give_same_result(samplepkg_ok, monkeypatch):
    monkeypatch.chdir(samplepkg_ok.parent)
    assert get_tree_map(package_path="samplepkg") == get_tree_map(package_path=str(samplepkg_ok))
    assert get_tree_map(package_path="./samplepkg/") == get_tree_map(package_path=str(samplepkg_ok))


def test_empty_directory_gives_node_without_children(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    tree = get_tree_map(package_path=str(empty))
    assert tree_has(tree, "empty")
    assert not tree_contains(tree, ".py")


def test_public_classes_and_functions_are_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    for name in ("Base", "Child", "top_level", "from_name", "static_helper", "public_method"):
        assert tree_has(tree, name), name


def test_private_functions_classes_and_methods_are_hidden(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    for name in ("_private_func", "_PrivateClass", "_private_method"):
        assert not tree_has(tree, name), name


def test_constructor_is_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "__init__")


def test_class_level_annotated_and_plain_variables_are_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "class_var")
    assert tree_contains(tree, "typed_var")


def test_module_level_annotated_assignment_is_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "constants.py"))
    assert tree_has(tree, "PUBLIC")
    assert tree_contains(tree, "TYPED")


def test_dotted_names_and_hidden_directories_are_ignored(tmp_path):
    pkg = tmp_path / "pkg"
    (pkg / ".hidden").mkdir(parents=True)
    (pkg / ".hidden" / "secret.py").write_text("X = 1\n")
    (pkg / "ok.py").write_text("Y = 1\n")
    tree = get_tree_map(package_path=str(pkg))
    assert tree_has(tree, "ok.py")
    assert not tree_has(tree, "secret.py")


# ---------- B01-B03: resolving the target ----------


def test_single_module_by_name_inspects_only_that_module(on_syspath):
    tree = get_tree_map("single_module")
    assert tree_has(tree, "single_func")
    assert not tree_contains(tree, "samplepkg")


def test_namespace_package_by_name_is_resolved(on_syspath):
    tree = get_tree_map("nspkg")
    assert tree_has(tree, "mod.py")
    assert tree_has(tree, "ns_func")


# ---------- B05, B16: robustness and determinism ----------


def test_syntax_error_in_one_file_does_not_abort_inspection(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path))
    assert tree_has(tree, "core.py")
    assert tree_has(tree, "util.py")


def test_undecodable_file_does_not_abort_inspection(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "bad.py").write_bytes(b"\xff\xfe\x00 not utf-8")
    (pkg / "good.py").write_text("GOOD = 1\n")
    tree = get_tree_map(package_path=str(pkg))
    assert tree_has(tree, "good.py")


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unreadable_directory_error_is_recorded(tmp_path):
    pkg = tmp_path / "pkg"
    locked = pkg / "locked"
    locked.mkdir(parents=True)
    (pkg / "ok.py").write_text("OK = 1\n")
    locked.chmod(0o000)
    try:
        tree = get_tree_map(package_path=str(pkg))
    finally:
        locked.chmod(0o755)
    assert tree_has(tree, "ok.py")
    locked_node = next(node for node in tree["nodes"] if node["name"] == "locked")
    assert locked_node["errors"] == ["PermissionError: Permission denied"]


def test_children_are_sorted_deterministically(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    names = [f"mod_{i:02d}.py" for i in range(30)]
    for name in reversed(names):
        (pkg / name).write_text("X = 1\n")
    tree = get_tree_map(package_path=str(pkg))
    assert [node["name"] for node in tree["nodes"]] == names


def test_symlink_loops_are_not_followed(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("A = 1\n")
    (pkg / "loop").symlink_to(pkg, target_is_directory=True)
    tree = get_tree_map(package_path=str(pkg))
    assert tree_has(tree, "a.py")
    assert collect_strings(tree).count("a.py") == 1
    assert tree["errors"] == ["Skipped symlinked directory: loop"]


def test_symlinked_directory_is_reported_in_parent_errors(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "inner.py").write_text("INNER = 1\n")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "inner_link").symlink_to(real, target_is_directory=True)
    (pkg / "_private_link").symlink_to(real, target_is_directory=True)
    info = inspect_path(str(pkg))
    assert info.packages == []
    assert info.errors == ["Skipped symlinked directory: inner_link"]


# ---------- B06, B07: which files are inspected ----------


def test_only_dot_py_files_are_inspected(samplepkg_ok):
    (samplepkg_ok / "compiled.pyc").write_text("PYC_MARKER = 1\n")
    tree = get_tree_map(package_path=str(samplepkg_ok))
    assert tree_has(tree, "core.py")
    for name in ("stubs_only.pyi", "notes.python.txt", "compiled.pyc"):
        assert not tree_has(tree, name), name


def test_init_py_is_inspected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "sub"))
    assert tree_has(tree, "__init__.py")
    assert tree_has(tree, "SUB_EXPORT")


def test_main_py_is_inspected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "__main__.py"))
    assert tree_has(tree, "ENTRY")


def test_package_init_with_reexports_is_listed(samplepkg_ok):
    tree = get_tree_map(package_path=str(samplepkg_ok))
    assert tree_has(tree, "__init__.py")
    assert tree_has(tree, "__main__.py")


# ---------- B08: variables ----------


def test_private_module_variables_are_hidden(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "constants.py"))
    assert not tree_contains(tree, "_PRIVATE")


def test_private_class_variables_are_hidden(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert not tree_contains(tree, "_hidden_var")


def test_tuple_assignment_yields_each_name(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "constants.py"))
    assert tree_has(tree, "FIRST")
    assert tree_has(tree, "SECOND")


def test_chained_assignment_yields_every_target(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "constants.py"))
    assert tree_has(tree, "A")
    assert tree_has(tree, "B")


# ---------- B09: async and nested ----------


def test_async_top_level_function_is_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "top_level_async")


def test_async_method_is_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "async_method")


def test_nested_class_is_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "Inner")
    assert tree_has(tree, "inner_method")


# ---------- B10, B11: classification and parameters ----------


def test_method_calling_super_init_is_not_a_constructor(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    child = _find_class(tree, "Child")
    assert [m[0] if isinstance(m, tuple) else m for m in child.get("constructor", [])] == ["__init__"]


def test_method_with_inner_private_def_is_still_collected(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_has(tree, "uses_inner_def")


def test_parameter_named_itself_is_not_corrupted(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_contains(tree, "itself")


def test_parameter_named_cls_name_is_not_corrupted(samplepkg_path):
    tree = get_tree_map(package_path=str(samplepkg_path / "core.py"))
    assert tree_contains(tree, "cls_name")


def _find_class(tree, name):
    """Find the class dict called name inside a single-file map (format agnostic about the outer layout)."""
    stack = [tree]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            if obj.get("name") == name and "category" not in obj:
                return obj
            stack.extend(obj.values())
        elif isinstance(obj, list):
            stack.extend(obj)
    raise AssertionError(f"class {name} not found")
