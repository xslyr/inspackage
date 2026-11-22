import json
import os
import subprocess
import sys

import pytest
from helpers import assert_snapshot, collect_strings
from typer.testing import CliRunner

from inspackage import __version__
from inspackage.cli import typer_app
from inspackage.render import FORMATS, OutputFormat


def _flat(text: str) -> str:
    """Undo Rich's line wrapping (80 columns under CliRunner)."""
    return " ".join(text.split())


# ---------- behaviour that already works ----------


def test_version_option_prints_version(run_cli):
    result = run_cli("--version")
    assert result.exit_code == 0
    assert __version__ in result.output
    assert "0.0.0+unknown" not in result.output


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
    assert result.exit_code == 2
    assert "not found" in result.output


def test_static_by_name_resolves_package_on_syspath(run_cli, on_syspath):
    result = run_cli("--static", "samplepkg")
    assert result.exit_code == 0
    assert "core.py" in result.stdout


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
    assert result.exit_code == 2
    assert "is not a Python source file" in _flat(result.output)
    assert "readme.txt" in _flat(result.output)


def test_target_with_rich_markup_is_printed_literally(run_cli):
    result = run_cli("--static", "/nonexist[/]")
    assert result.exit_code == 2
    assert "Path '/nonexist[/]' not found!" in _flat(result.output)
    assert "MarkupError" not in repr(result.exception)


def test_dir_with_rich_markup_is_printed_literally(run_cli, tmp_path):
    result = run_cli("--static", "--dir", str(tmp_path / "[bold]missing"))
    assert result.exit_code == 2
    assert "[bold]missing' not found!" in _flat(result.output)


def test_distribution_name_suggests_import_name(run_cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_cli("--static", "typing-extensions-xyz")
    assert result.exit_code == 2
    assert "Path" not in _flat(result.output)
    assert "Package 'typing-extensions-xyz' not found" in _flat(result.output)
    assert "Did you mean 'typing_extensions_xyz'?" in _flat(result.output)


def test_cli_survives_a_file_with_syntax_error(run_cli, samplepkg_path):
    result = run_cli("--static", "--dir", str(samplepkg_path))
    assert result.exit_code == 0
    assert "core.py" in result.output


# ---------- B14: --save ----------


def test_save_with_dot_does_not_create_double_dot_json(run_cli, samplepkg_ok, monkeypatch):
    monkeypatch.chdir(samplepkg_ok)
    result = run_cli("--save", "--static", "--dir", ".")
    assert result.exit_code == 0
    assert not (samplepkg_ok / "..json").exists()
    assert json.loads((samplepkg_ok / "samplepkg.json").read_text(encoding="utf-8"))["schema_version"] == 1


def test_save_alone_writes_json_without_opening_the_tui(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    called = []
    monkeypatch.setattr("inspackage.render.InspackageApp.run", lambda self, *a, **k: called.append(1))
    result = run_cli("--save", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert not called
    assert json.loads((out / "samplepkg.json").read_text(encoding="utf-8"))["name"] == "samplepkg"
    assert "deprecated" in result.stderr


def test_save_with_tui_happens_before_the_interactive_app_runs(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    seen = {}

    def fake_run(self, *args, **kwargs):
        seen["saved_before_run"] = (out / "samplepkg.json").exists()

    monkeypatch.setattr("inspackage.render.InspackageApp.run", fake_run)
    result = run_cli("--save", "--format", "tui", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert seen["saved_before_run"]


def test_save_name_comes_from_resolved_module_not_from_the_argument(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    result = run_cli("--save", "--dir", str(samplepkg_ok / "core.py"))
    assert result.exit_code == 0
    assert (out / "core.json").exists()


def test_save_with_static_prints_tree_and_writes_json(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    result = run_cli("--static", "--save", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert "core.py" in result.stdout
    assert (out / "samplepkg.json").exists()


# ---------- B15: help ----------


def test_help_does_not_advertise_nonexistent_interactive_option(run_cli):
    assert "--interactive" not in run_cli("--help").output


@pytest.mark.parametrize("option", ["--static", "--dir", "--env", "--format", "--output", "--include-private"])
def test_help_lists_real_options(run_cli, option):
    assert option in run_cli("--help").output


def test_short_help_flag_works(run_cli):
    result = run_cli("-h")
    assert result.exit_code == 0
    assert "--format" in result.output


def test_verbose_reports_resolved_path_and_counts_on_stderr(run_cli, samplepkg_path):
    result = run_cli("--format", "tree", "--verbose", "--dir", str(samplepkg_path))
    assert result.exit_code == 0
    assert "Resolved:" in result.stderr and "samplepkg" in result.stderr
    assert "errors: 1" in result.stderr
    assert str(samplepkg_path / "broken.py") in result.stderr  # absolute path, not relative to the parent dir


def test_without_verbose_stderr_is_quiet(run_cli, samplepkg_path):
    result = run_cli("--format", "tree", "--dir", str(samplepkg_path))
    assert result.stderr == ""


def test_unexpected_error_hides_traceback_unless_verbose(run_cli, samplepkg_ok, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("inspackage.cli.inspect_target", boom)
    quiet = run_cli("--format", "tree", "--dir", str(samplepkg_ok))
    assert quiet.exit_code == 2
    assert "kaboom" in quiet.stderr and "Traceback" not in quiet.stderr
    loud = run_cli("--format", "tree", "--verbose", "--dir", str(samplepkg_ok))
    assert loud.exit_code == 2
    assert "Traceback" in loud.stderr


# ---------- F2: --format / -o / filters / exit codes ----------


def test_format_json_goes_to_stdout_uncolored_with_schema_version(run_cli, samplepkg_ok):
    result = run_cli("--format", "json", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["schema_version"] == 1 and data["type"] == "package" and data["name"] == "samplepkg"
    assert "\x1b" not in result.stdout
    assert result.stderr == ""


def test_format_json_with_output_writes_file(run_cli, samplepkg_ok, tmp_path):
    target = tmp_path / "out.json"
    result = run_cli("--format", "json", "-o", str(target), "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert result.stdout == ""
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 1


def test_format_tree_with_output_writes_plain_text(run_cli, samplepkg_ok, tmp_path):
    target = tmp_path / "tree.txt"
    result = run_cli("--format", "tree", "--output", str(target), "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    text = target.read_text(encoding="utf-8")
    assert "core.py" in text and "\x1b" not in text
    assert text.splitlines()[0] == "samplepkg"


def test_static_is_alias_of_format_tree_with_deprecation_warning(run_cli, samplepkg_ok):
    legacy = run_cli("--static", "--dir", str(samplepkg_ok))
    new = run_cli("--format", "tree", "--dir", str(samplepkg_ok))
    assert legacy.stdout == new.stdout
    assert "--static is deprecated" in legacy.stderr
    assert new.stderr == ""


def test_static_with_other_format_is_a_usage_error(run_cli, samplepkg_ok):
    result = run_cli("--static", "--format", "json", "--dir", str(samplepkg_ok))
    assert result.exit_code == 1


def test_output_with_tui_is_a_usage_error(run_cli, samplepkg_ok, tmp_path):
    result = run_cli("--format", "tui", "-o", str(tmp_path / "x"), "--dir", str(samplepkg_ok))
    assert result.exit_code == 1
    assert "--output" in result.stderr
    result = run_cli("-o", str(tmp_path / "x"), "--dir", str(samplepkg_ok))  # default format is tui
    assert result.exit_code == 1


def test_invalid_format_is_a_usage_error_without_traceback(run_cli, samplepkg_ok):
    result = run_cli("--format", "yaml", "--dir", str(samplepkg_ok))
    assert result.exit_code == 1
    assert "Invalid format 'yaml'" in _flat(result.stderr)
    assert "Traceback" not in result.output


@pytest.mark.parametrize("fmt", ["html", "md", "llm", "graph"])
def test_planned_formats_report_not_available(run_cli, samplepkg_ok, fmt):
    result = run_cli("--format", fmt, "--dir", str(samplepkg_ok))
    assert result.exit_code == 1
    assert "not available in this version" in _flat(result.stderr)


def test_click_usage_errors_exit_with_1(run_cli):
    assert run_cli("--no-such-option").exit_code == 1
    assert run_cli("--max-depth", "abc", ".").exit_code == 1


def test_unwritable_output_is_a_friendly_error(run_cli, samplepkg_ok, tmp_path):
    result = run_cli("--format", "json", "-o", str(tmp_path / "missing" / "x.json"), "--dir", str(samplepkg_ok))
    assert result.exit_code == 1
    assert "Could not write" in result.stderr and "Traceback" not in result.output


def test_include_private_option(run_cli, samplepkg_ok):
    hidden = run_cli("--format", "tree", "--dir", str(samplepkg_ok)).stdout
    shown = run_cli("--format", "tree", "--include-private", "--dir", str(samplepkg_ok)).stdout
    assert "_private_func" not in hidden
    assert "_private_func" in shown


def test_exclude_option_is_repeatable(run_cli, samplepkg_ok):
    result = run_cli("--format", "tree", "--exclude", "core.py", "--exclude", "sub", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert "core.py" not in result.stdout and "util.py" not in result.stdout
    assert "constants.py" in result.stdout


def test_max_depth_option(run_cli, samplepkg_ok):
    result = run_cli("--format", "tree", "--max-depth", "0", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert "util.py" not in result.stdout and "core.py" in result.stdout


def test_success_exit_code_is_zero_and_target_errors_are_two(run_cli, samplepkg_ok):
    assert run_cli("--format", "tree", "--dir", str(samplepkg_ok)).exit_code == 0
    assert run_cli("--format", "tree", "--dir", str(samplepkg_ok / "nope")).exit_code == 2


# ---------- B04: directory without modules ----------


def test_directory_without_python_modules_is_a_friendly_error(run_cli, tmp_path):
    empty = tmp_path / "vazio"
    empty.mkdir()
    (empty / "notes.txt").write_text("x")
    result = run_cli("--format", "tree", "--dir", str(empty))
    assert result.exit_code == 2
    assert "No Python modules found in" in _flat(result.stderr)
    assert "vazio" in _flat(result.stderr)
    assert result.stdout == ""
    assert not isinstance(result.exception, KeyError)


def test_directory_without_modules_does_not_write_output_file(run_cli, tmp_path):
    empty = tmp_path / "vazio"
    empty.mkdir()
    target = tmp_path / "out.json"
    result = run_cli("--format", "json", "-o", str(target), "--dir", str(empty))
    assert result.exit_code == 2
    assert not target.exists()


def test_missing_env_file_is_accepted(samplepkg_ok, tmp_path):
    result = CliRunner().invoke(
        typer_app, ["--env", str(tmp_path / "does-not-exist.rc"), "--static", "--dir", str(samplepkg_ok)]
    )
    assert result.exit_code == 0


def test_cwd_is_not_modified_by_cli(run_cli, samplepkg_ok):
    before = os.getcwd()
    run_cli("--static", "--dir", str(samplepkg_ok))
    assert os.getcwd() == before


# ---------- review fixes ----------


def test_save_json_matches_snapshot(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    out = tmp_path / "cwd"
    out.mkdir()
    monkeypatch.chdir(out)
    result = run_cli("--save", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert_snapshot("save_samplepkg.json", (out / "samplepkg.json").read_text(encoding="utf-8"))


def test_save_deprecation_warning_mentions_tui_and_the_old_behavior(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_cli("--save", "--dir", str(samplepkg_ok))
    warning = _flat(result.stderr)
    assert "no longer opens the TUI" in warning
    assert "--format tui --save" in warning


def test_save_of_dotted_name_uses_the_resolved_name(run_cli, tmp_path, monkeypatch, fixtures_dir):
    monkeypatch.chdir(tmp_path)
    result = run_cli("--save", "--dir", str(fixtures_dir / "samplepkg" / "sub"))
    assert result.exit_code == 0
    assert (tmp_path / "sub.json").exists()


class _BrokenStdout:
    def write(self, _text):
        raise BrokenPipeError

    def flush(self):
        raise BrokenPipeError

    def isatty(self):
        return False

    def fileno(self):  # Rich redirects this fd to devnull on a broken pipe: give it a harmless, private one
        return self._fd

    def __init__(self):
        self._fd = os.open(os.devnull, os.O_WRONLY)

    def close(self):
        os.close(self._fd)


@pytest.mark.parametrize("fmt", ["json", "tree"])
def test_broken_pipe_on_real_renderers_is_a_silent_success(samplepkg_ok, monkeypatch, fmt):
    from inspackage import cli
    from inspackage._inspection import inspect_target

    broken = _BrokenStdout()
    monkeypatch.setattr(sys, "stdout", broken)
    try:
        cli._render_to_stdout(FORMATS[fmt], inspect_target(None, str(samplepkg_ok)))  # must not raise
    finally:
        broken.close()


@pytest.mark.parametrize("exc", [BrokenPipeError(), SystemExit(1)])  # SystemExit(1): what Rich raises
def test_broken_pipe_exits_zero_without_message(run_cli, samplepkg_ok, monkeypatch, exc):
    def render(info, out):
        raise exc

    monkeypatch.setitem(FORMATS, "json", OutputFormat("json", render, "x"))
    result = run_cli("--format", "json", "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert result.stderr == ""


@pytest.mark.parametrize("fmt", ["json", "tree"])
def test_piping_to_a_closed_reader_exits_zero_quietly(fmt):
    cmd = [sys.executable, "-c", "from inspackage.cli import typer_app; typer_app()", "--format", fmt]
    cmd += ["--dir", os.path.join(os.path.dirname(__file__), "..", "inspackage")]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # pylint: disable=consider-using-with
    proc.stdout.close()
    stderr = proc.stderr.read()
    assert proc.wait() == 0
    assert stderr == b""


def test_invalid_format_without_target_is_a_usage_error(run_cli):
    result = run_cli("--format", "yaml")
    assert result.exit_code == 1
    assert "Invalid format 'yaml'" in _flat(result.stderr)


@pytest.mark.parametrize("args", [["--format", "json"], ["--static"], ["-o", "x.json"], ["--save"]])
def test_format_options_without_target_report_missing_target(run_cli, args):
    result = run_cli(*args)
    assert result.exit_code == 1
    assert "Missing target" in result.stderr
    assert "Usage" not in result.stdout


@pytest.mark.parametrize(
    ("name", "check"),
    [("out.json", lambda text: json.loads(text)["schema_version"] == 1), ("out.txt", lambda t: "core.py" in t)],
)
def test_output_extension_infers_the_format(run_cli, samplepkg_ok, tmp_path, name, check):
    target = tmp_path / name
    result = run_cli("-o", str(target), "--dir", str(samplepkg_ok))
    assert result.exit_code == 0
    assert check(target.read_text(encoding="utf-8"))


def test_output_with_unknown_extension_asks_for_a_format(run_cli, samplepkg_ok, tmp_path):
    target = tmp_path / "out.dat"
    result = run_cli("-o", str(target), "--dir", str(samplepkg_ok))
    assert result.exit_code == 1
    assert "default format is tui" in _flat(result.stderr) and "--format" in result.stderr
    assert not target.exists()


def test_failed_render_leaves_no_partial_file_and_keeps_the_old_one(run_cli, samplepkg_ok, tmp_path, monkeypatch):
    def render(info, out):
        out.write("partial")
        raise RuntimeError("kaboom")

    monkeypatch.setitem(FORMATS, "json", OutputFormat("json", render, "x"))
    target = tmp_path / "out.json"
    target.write_text("old", encoding="utf-8")
    fresh = tmp_path / "fresh.json"
    for path in (target, fresh):
        result = run_cli("--format", "json", "-o", str(path), "--dir", str(samplepkg_ok))
        assert result.exit_code == 2 and "kaboom" in result.stderr
    assert target.read_text(encoding="utf-8") == "old"
    assert not fresh.exists()
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith(".")) == []


def test_successful_output_leaves_no_temporary_files(run_cli, samplepkg_ok, tmp_path):
    outdir = tmp_path / "o"
    outdir.mkdir()
    run_cli("--format", "json", "-o", str(outdir / "x.json"), "--dir", str(samplepkg_ok))
    assert [p.name for p in outdir.iterdir()] == ["x.json"]


def test_error_messages_are_not_wrapped_in_the_middle_of_a_path(run_cli, tmp_path):
    missing = tmp_path / ("very_long_directory_name_" * 6) / "missing"
    result = run_cli("--format", "tree", "--dir", str(missing))
    assert result.exit_code == 2
    assert str(missing) in result.stderr


def test_env_file_values_are_applied_to_the_tui(samplepkg_ok, tmp_path, monkeypatch):
    monkeypatch.setenv("DARK_THEME", "before")  # restored (removed) by monkeypatch after load_dotenv overrides it
    monkeypatch.delenv("LIGHT_THEME", raising=False)
    rc = tmp_path / "custom.rc"
    rc.write_text("DARK_THEME=x\n", encoding="utf-8")
    seen = {}

    def fake_run(self, *args, **kwargs):
        seen["dark"] = self.dark_theme

    monkeypatch.setattr("inspackage.render.InspackageApp.run", fake_run)
    result = CliRunner().invoke(typer_app, ["-e", str(rc), "--dir", str(samplepkg_ok)])
    assert result.exit_code == 0
    assert os.environ["DARK_THEME"] == "x"
    assert seen["dark"] == "x"
