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


@pytest.mark.xfail(strict=True, reason="B12 #9")
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
