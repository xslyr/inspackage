import sys
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


def _write(fmt: OutputFormat, info: InspectionResult, output: Optional[Path]) -> None:
    """Render ``info`` to ``output`` (a file) or to stdout."""

    if output is None:
        fmt.render(info, sys.stdout)
        return
    try:
        with open(output, "w", encoding="utf-8") as handle:
            fmt.render(info, handle)
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
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    version: Optional[bool] = Option(
        None, "--version", callback=callback_version, is_eager=True, help="Show the version and exit."
    ),
    ctx: Context = typer.Context,  # type: ignore[assignment]
):
    """Inspackage inspects the structure of a Python package, directory or module (never imports it).

    Examples: inspackage .  |  inspackage requests --format tree  |  inspackage --dir src -o pkg.json --format json

    Exit codes: 0 ok, 1 invalid usage, 2 target not found or not inspectable.
    """

    del version
    if not target and package_path is None:
        typer.echo(ctx.get_help())
        raise Exit()
    if target and package_path is not None:
        err_console.print(DefaultExceptions.package_and_path_send)
        raise Exit(code=EXIT_USAGE)

    load_dotenv(env.as_posix(), override=True)

    fmt = _choose_format(format_name, static)
    if save:
        _warn("--save is deprecated; use --format json -o <name>.json.")
    if fmt is None:
        fmt = FORMATS["json"] if save else FORMATS["tui"]  # --save alone means "--format json -o <name>.json"
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
