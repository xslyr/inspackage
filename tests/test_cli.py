import json
import os

import pytest
from helpers import collect_strings
from typer.testing import CliRunner

from inspackage import __version__
from inspackage.cli import typer_app


def _flat(text: str) -> str:
    """Undo Rich's line wrapping (80 columns under CliRunner)."""
    return " ".join(text.split())


# ---------- behaviour that already works ----------


def test_version_option_prints_version(run_cli):
    result = run_cli("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_option_exits_zero_and_describes_tool(run_cli):
    result = run_cli("--help")
    assert result.exit_code == 0
    assert "Inspackage" in result.output


def test_no_arguments_shows_help_and_exits_zero(run_cli):
    result = run_cli()
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_name_and_dir_together_is_a_usage_error(run_cli, samplepkg_ok):
    result = run_cli("--static", "--dir", str(samplepkg_ok), "somepkg")
    assert result.exit_code == 1
    assert "Only one parameter" in result.output


def test_unknown_package_name_reports_not_found(run_cli):
    result = run_cli("--static", "xyz_package_that_does_not_exist")
    assert result.exit_code == 1
    assert "not found" in result.output


def test_static_by_name_resolves_package_on_syspath(run_cli, on_syspath):
    # samplepkg has a SyntaxError file (B05), so only resolution is checked: the error must come from parsing,
    # never from "not found".
    result = run_cli("--static", "samplepkg")
    assert "not found" not in result.output


@pytest.mark.parametrize("spelling", ["{abs}", "{abs}/", "relative"])
def test_dir_option_accepts_multiple_path_spellings(run_cli, samplepkg_ok, monkeypatch, spelling):
    if spelling == "relative":
        monkeypatch.chdir(samplepkg_ok.parent)
        path = "./samplepkg"
    else:
        path = spelling.format(abs=samplepkg_ok)
    result = run_cli("--static", "--dir", path)
    assert result.exit_code == 0
    assert "core.py" in result.output


def test_dir_option_expands_tilde(run_cli, samplepkg_ok, monkeypatch):
    monkeypatch.setenv("HOME", str(samplepkg_ok.parent))
    result = run_cli("--static", "--dir", "~/samplepkg")
    assert result.exit_code == 0
    assert "core.py" in result.output


def test_save_writes_json_named_after_the_package_dir(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    result = run_cli("--save", "--static", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    data = json.loads((out / "samplepkg.json").read_text(encoding="utf-8"))
    assert "core.py" in collect_strings(data)


# ---------- B01, B04: target handling ----------


def test_dot_means_current_directory(run_cli, samplepkg_ok, monkeypatch):
    monkeypatch.chdir(samplepkg_ok)
    result = run_cli("--static", ".")
    assert result.exit_code == 0
    assert "core.py" in result.output


def test_dir_pointing_to_a_file_renders_that_file(run_cli, samplepkg_path):
    result = run_cli("--static", "--dir", str(samplepkg_path / "core.py"))
    assert result.exit_code == 0
    assert "Base" in result.output


def test_dir_pointing_to_non_python_file_does_not_crash_with_keyerror(run_cli, tmp_path):
    target = tmp_path / "readme.txt"
    target.write_text("hello")
    result = run_cli("--static", "--dir", str(target))
    assert not isinstance(result.exception, KeyError)


def test_target_with_rich_markup_is_printed_literally(run_cli):
    result = run_cli("--static", "/nonexist[/]")
    assert result.exit_code == 1
    assert "Path '/nonexist[/]' not found!" in _flat(result.output)
    assert "MarkupError" not in repr(result.exception)


def test_dir_with_rich_markup_is_printed_literally(run_cli, tmp_path):
    result = run_cli("--static", "--dir", str(tmp_path / "[bold]missing"))
    assert result.exit_code == 1
    assert "[bold]missing' not found!" in _flat(result.output)


def test_distribution_name_suggests_import_name(run_cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_cli("--static", "typing-extensions-xyz")
    assert result.exit_code == 1
    assert "Path" not in _flat(result.output)
    assert "Package 'typing-extensions-xyz' not found" in _flat(result.output)
    assert "Did you mean 'typing_extensions_xyz'?" in _flat(result.output)


def test_cli_survives_a_file_with_syntax_error(run_cli, samplepkg_path):
    result = run_cli("--static", "--dir", str(samplepkg_path))
    assert result.exit_code == 0
    assert "core.py" in result.output


# ---------- B14: --save ----------


@pytest.mark.xfail(strict=True, reason="B14 #10")
def test_save_with_dot_does_not_create_double_dot_json(run_cli, samplepkg_ok, monkeypatch):
    monkeypatch.chdir(samplepkg_ok)
    result = run_cli("--save", "--static", "--dir", ".")
    assert result.exit_code == 0
    assert not (samplepkg_ok / "..json").exists()
    assert (samplepkg_ok / "samplepkg.json").exists()


@pytest.mark.xfail(strict=True, reason="B14 #10")
def test_save_happens_before_the_interactive_app_runs(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    seen = {}

    def fake_run(self, *args, **kwargs):
        seen["saved_before_run"] = (out / "samplepkg.json").exists()

    monkeypatch.setattr("inspackage.cli.InspackageApp.run", fake_run)
    result = run_cli("--save", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert seen["saved_before_run"]


# ---------- B15: help ----------


@pytest.mark.xfail(strict=True, reason="B15 #11")
def test_help_does_not_advertise_nonexistent_interactive_option(run_cli):
    assert "--interactive" not in run_cli("--help").output


@pytest.mark.xfail(strict=True, reason="B15 #11")
@pytest.mark.parametrize("option", ["--static", "--dir", "--env"])
def test_help_lists_real_options(run_cli, option):
    assert option in run_cli("--help").output


def test_missing_env_file_is_accepted(samplepkg_ok, tmp_path):
    result = CliRunner().invoke(
        typer_app, ["--env", str(tmp_path / "does-not-exist.rc"), "--static", "--dir", str(samplepkg_ok)]
    )
    assert result.exit_code == 0


def test_cwd_is_not_modified_by_cli(run_cli, samplepkg_ok):
    before = os.getcwd()
    run_cli("--static", "--dir", str(samplepkg_ok))
    assert os.getcwd() == before
