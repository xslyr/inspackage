import contextlib
import os
import sys
import tempfile
from pathlib import Path
from typing import List, NoReturn, Optional

import typer
from click import UsageError
from dotenv import load_dotenv
from rich.markup import escape
from typer import Argument, Context, Exit, Option, Typer
from typer.core import TyperCommand

from inspackage._callbacks import callback_version, err_console
from inspackage._inspection import inspect_target
from inspackage.exception import DefaultExceptions, InspectionTargetError
from inspackage.model import InspectionResult, iter_errors, iter_modules
from inspackage.render import FORMATS, PLANNED_FORMATS, OutputFormat

EXIT_USAGE = 1
EXIT_TARGET = 2

typer_app = Typer(add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})


class _Command(TyperCommand):
    """Command whose parsing errors (unknown option, bad value, ...) exit with 1 instead of click's 2."""

    def parse_args(self, ctx, args):
        try:
            return super().parse_args(ctx, args)
        except UsageError as err:
            err.exit_code = EXIT_USAGE
            raise


def _fail(message: str, code: int) -> NoReturn:
    """Short red error on stderr (no traceback) and exit."""
    err_console.print(f"[bright_red]Error:[/] {escape(message)}")
    raise Exit(code=code)


def _warn(message: str) -> None:
    err_console.print(f"[yellow]Warning:[/] {escape(message)}")


def _choose_format(name: Optional[str], static: bool) -> OutputFormat | None:
    """Validate ``--format``/``--static``; returns ``None`` when neither was given."""

    if static:
        _warn("--static is deprecated; use --format tree.")
        if name not in (None, "tree"):
            _fail(f"--static conflicts with --format {name}.", EXIT_USAGE)
        name = "tree"
    if name is None:
        return None
    if name in FORMATS:
        return FORMATS[name]
    if name in PLANNED_FORMATS:
        _fail(f"Format '{name}' is not available in this version. Available: {', '.join(FORMATS)}.", EXIT_USAGE)
    _fail(f"Invalid format '{name}'. Choose one of: {', '.join(FORMATS)}.", EXIT_USAGE)


def _format_from_extension(output: Path) -> OutputFormat:
    """``-o`` without ``--format``: ``.json`` -> json, ``.txt`` -> tree; anything else needs an explicit format."""

    name = {".json": "json", ".txt": "tree"}.get(output.suffix.lower())
    if name is None:
        _fail(
            f"Cannot infer the format from '{output}': the default format is tui, which cannot be written to a file. "
            "Use --format tree or --format json (or an -o name ending in .json or .txt).",
            EXIT_USAGE,
        )
    return FORMATS[name]


def _silence_stdout() -> None:
    """After a broken pipe (``| head``) point fd 1 at devnull so the interpreter's final flush stays quiet."""

    with contextlib.suppress(OSError, ValueError, AttributeError):
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())


def _render_to_stdout(fmt: OutputFormat, info: InspectionResult) -> None:
    """Render to stdout; a closed reader (``| head -1``) is a normal end, not an error."""

    try:
        fmt.render(info, sys.stdout)
        sys.stdout.flush()
    except BrokenPipeError:
        _silence_stdout()
    except SystemExit as err:  # Rich turns BrokenPipeError into SystemExit(1) after redirecting stdout itself
        if err.code not in (1, None):
            raise
        _silence_stdout()


def _render_to_file(fmt: OutputFormat, info: InspectionResult, output: Path) -> None:
    """Render into a temporary file next to ``output`` and ``os.replace`` it: never leaves a partial file."""

    mode = None
    try:
        mode = output.stat().st_mode & 0o777
    except OSError:
        pass
    if mode is None:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    handle_fd, tmp_name = tempfile.mkstemp(dir=output.resolve().parent, prefix=f".{output.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8") as handle:
            fmt.render(info, handle)
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, output)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _write(fmt: OutputFormat, info: InspectionResult, output: Optional[Path]) -> None:
    """Render ``info`` to ``output`` (a file, atomically) or to stdout."""

    if output is None:
        _render_to_stdout(fmt, info)
        return
    try:
        _render_to_file(fmt, info, output)
    except OSError as err:
        _fail(f"Could not write '{output}': {err.strerror or err}", EXIT_USAGE)


def _report(info: InspectionResult) -> None:
    """``--verbose`` diagnostics on stderr: what was resolved and what could not be read."""

    errors = list(iter_errors(info))
    err_console.print(f"[dim]Resolved: {escape(info.abspath or info.path)}[/]")
    err_console.print(f"[dim]Modules: {sum(1 for _ in iter_modules(info))}, errors: {len(errors)}[/]")
    for path, message in errors:
        err_console.print(f"[dim]  {escape(path)}: {escape(message)}[/]")


def _resolve(target: Optional[str], path: Optional[Path], options: dict, verbose: bool) -> InspectionResult:
    try:
        info = inspect_target(target or None, path.expanduser().as_posix() if path else None, **options)
    except InspectionTargetError as err:
        err_console.print(err.message)
        raise Exit(code=EXIT_TARGET) from err
    except Exception as err:  # pylint: disable=broad-except
        if verbose:
            err_console.print_exception()
        else:
            err_console.print(
                f"[bright_red]Error:[/] Inspection failed: {escape(str(err))} (use --verbose for details)"
            )
        raise Exit(code=EXIT_TARGET) from err
    return info


@typer_app.command(cls=_Command)
def main(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    ctx: Context,
    target: Optional[str] = Argument(None, metavar="[TARGET]", help="Package name, or path (e.g. '.' or './pkg')."),
    package_path: Optional[Path] = Option(None, "--dir", "-d", help="Package directory or .py file to inspect."),
    format_name: Optional[str] = Option(
        None, "--format", metavar="FORMAT", help="Output format: tui (interactive, default), tree or json."
    ),
    output: Optional[Path] = Option(None, "--output", "-o", help="Write the output to this file (text formats only)."),
    include_private: bool = Option(False, "--include-private", help="Include names starting with '_'."),
    exclude: Optional[List[str]] = Option(
        None, "--exclude", metavar="GLOB", help="Skip files/directories matching this glob. Repeatable."
    ),
    max_depth: Optional[int] = Option(None, "--max-depth", min=0, help="Maximum sub-package depth to descend."),
    static: bool = Option(False, "--static", help="Deprecated alias of --format tree."),
    save: bool = Option(
        False, "--save", "-s", help="Deprecated: write <package>.json to the current directory (see --format/-o)."
    ),
    verbose: bool = Option(False, "--verbose", "-v", help="Show resolved path, counts and errors on stderr."),
    env: Path = Option(
        Path("~/.inspackagerc").expanduser(),
        "--env",
        "-e",
        help="Optional env file to change rules & preferred styles.",
        show_default="~/.inspackagerc",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    version: Optional[bool] = Option(
        None, "--version", callback=callback_version, is_eager=True, help="Show the version and exit."
    ),
):
    """Inspackage inspects the structure of a Python package, directory or module (never imports it).

    Examples: inspackage .  |  inspackage requests --format tree  |  inspackage --dir src -o pkg.json --format json

    Exit codes: 0 ok, 1 invalid usage, 2 target not found or not inspectable.
    """

    del version
    if target and package_path is not None:
        err_console.print(DefaultExceptions.package_and_path_send)
        raise Exit(code=EXIT_USAGE)

    fmt = _choose_format(format_name, static)
    if fmt is None and save:
        fmt = FORMATS["json"]  # --save alone means "--format json -o <name>.json"
    if fmt is None and output is not None:
        fmt = _format_from_extension(output)
    if not target and package_path is None:
        if fmt is None and output is None and not save:
            typer.echo(ctx.get_help())
            raise Exit()
        _fail("Missing target: give a package name, a path or --dir (see --help).", EXIT_USAGE)

    load_dotenv(env.as_posix(), override=True)

    if save:
        _warn(
            "--save is deprecated and no longer opens the TUI; use --format json -o <name>.json "
            "(--format tui --save keeps the old behavior: writes the JSON, then opens the TUI)."
        )
    fmt = fmt or FORMATS["tui"]
    if output is not None and fmt.interactive:
        _fail("--output cannot be used with --format tui; choose --format tree or json.", EXIT_USAGE)

    options = {"include_private": include_private, "exclude": tuple(exclude or ()), "max_depth": max_depth}
    try:
        info = _resolve(target, package_path, options, verbose)
        if verbose:
            _report(info)
        if not any(True for _ in iter_modules(info)):
            _fail(f"No Python modules found in {info.abspath or info.path}", EXIT_TARGET)

        json_fmt = FORMATS["json"]
        save_file = Path(f"{info.name.removesuffix('.py')}.json")
        if save and fmt is json_fmt:
            output = output or save_file  # --save is just "--format json -o <name>.json"
        elif save:
            _write(json_fmt, info, save_file)  # written first: the TUI blocks until the user quits
        _write(fmt, info, output)
    except Exit:
        raise
    except Exception as err:  # pylint: disable=broad-except
        if verbose:
            err_console.print_exception()
        else:
            err_console.print(
                f"[bright_red]Error:[/] Unexpected failure: {escape(str(err))} (use --verbose for details)"
            )
        raise Exit(code=EXIT_TARGET) from err
