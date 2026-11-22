import json

import pytest
from helpers import assert_snapshot

from inspackage._inspection import get_tree_map

# Rendering goes through the CLI (--static) so these tests survive refactors of the intermediate dict.


@pytest.fixture
def static_output(run_cli, samplepkg_ok):
    result = run_cli("--static", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    return result.output


def test_static_output_shows_root_modules_and_classes(static_output):
    for name in ("samplepkg", "core.py", "constants.py", "sub", "util.py", "Base", "Child", "top_level"):
        assert name in static_output, name


def test_static_output_shows_methods_params_and_return_types(static_output):
    assert "top_level" in static_output
    assert "-> int" in static_output
    assert "from_name" in static_output
    assert "static_helper" in static_output


def test_static_output_hides_private_names(static_output):
    for name in ("_private_func", "_PrivateClass", "_private_method"):
        assert name not in static_output, name


def test_static_output_is_deterministic_between_runs(run_cli, samplepkg_ok):
    first = run_cli("--static", "--dir", str(samplepkg_ok)).output
    second = run_cli("--static", "--dir", str(samplepkg_ok)).output
    assert first == second


def test_static_output_lists_properties(static_output):
    assert "prop_value" in static_output


def test_static_output_lists_method_that_calls_super_init(static_output):
    assert "reset" in static_output


def test_static_output_keeps_parameter_names_intact(static_output):
    assert "itself" in static_output
    assert "cls_name" in static_output


def test_static_output_lists_async_and_nested(static_output):
    for name in ("top_level_async", "async_method", "Inner"):
        assert name in static_output, name


def test_static_output_lists_init_py(static_output):
    assert "__init__.py" in static_output


def test_static_output_hides_private_variables_and_splits_tuples(static_output):
    assert "_PRIVATE" not in static_output
    assert "SECOND" in static_output


def test_static_snapshot_of_subpackage(run_cli, samplepkg_path):
    result = run_cli("--static", "--dir", str(samplepkg_path / "sub"))
    assert result.exit_code == 0
    assert_snapshot("static_sub.txt", result.output)


def test_json_snapshot_of_single_module(fixtures_dir):
    tree = get_tree_map(package_path=str(fixtures_dir / "single_module.py"))
    assert_snapshot("single_module.json", json.dumps(tree, indent=2, sort_keys=True) + "\n")


def test_static_output_keeps_brackets_and_does_not_crash_on_markup(run_cli, tmp_path):
    (tmp_path / "m.py").write_text(
        'def f(x: list[int], y="[/]") -> dict[str, int]: ...\n'
        'def g(y="[/x]"): ...\n'
        "class C:\n    def __init__(self, a: list[int]): ...\n    def __init__(self, b: set[str]): ...\n"
        "    @property\n    def prop_x(self): ...\n"
    )
    result = run_cli("--static", "--dir", str(tmp_path))
    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split())
    assert "list[int]" in flat
    assert "dict[str, int]" in flat
    assert "[/x]" in flat
    assert "set[str]" in flat  # every constructor is listed
    assert "prop_x" in flat


def test_static_output_prints_error_nodes_literally(run_cli, tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n")
    result = run_cli("--static", "--dir", str(tmp_path))
    assert "SyntaxError" in result.output
