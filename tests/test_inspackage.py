import pytest
from typer.testing import CliRunner

from inspackage._inspection import get_tree_map
from inspackage.cli import app

runner = CliRunner()


def test_inspection_must_construct_tree():
    package_name = "rich"
    tree = get_tree_map(package_name)
    assert tree["name"] == package_name


def test_inspection_must_raise_error_on_wrong_package():
    package_name = "xyz"
    with pytest.raises(Exception) as err:
        get_tree_map(package_name)

        assert "not found" in str(err.value)


def test_cli_dir_options_must_accept_multiple_ways_of_path_str(): ...


def test_inspection_must_silent_jump_on_admin_paths():
    package_path = "/root"
    with pytest.raises(Exception) as err:
        result = runner.invoke(app, ["--static", "--dir", package_path])
        assert result.exit_code == 0
        assert "exception" not in str(err.value)


def test_cli_must_save_on_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    package_name = "dotenv"
    result = runner.invoke(app, ["--save", "--static", package_name])
    file = tmp_path / f"{package_name}.json"
    assert result.exit_code == 0
    assert file.exists()
    assert file.read_text() != ""
