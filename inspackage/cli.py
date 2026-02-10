import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from typer import Argument, Context, Exit, Option, Typer

from inspackage._callbacks import (
    callback_help,
    callback_version,
    check_if_both_params_sent,
    check_only_one_params_sent,
    console,
    help_message_template,
)
from inspackage._inspection import get_tree_map
from inspackage.tree import InspackageApp, TreeBuilder

app = Typer(add_help_option=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    help: bool = Option(None, "-h", "--help", callback=callback_help, is_eager=True),
    version: bool = Option(None, "--version", callback=callback_version, is_eager=True),
    static: bool = Option(False, "--static"),
    verbose: bool = Option(False, "-v", "--verbose"),
    save: bool = Option(False, "-s", "--save"),
    env: Path = Option(
        Path("~/.inspackagerc").expanduser(),
        "--env",
        "-e",
        help="Optional env file to change rules & prefered styles. Default: ~/.inspackagerc",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    package_path: Optional[Path] = Option(None, "--dir", "-d", help="Package path to inspect."),
    package_name: Optional[str] = Argument("", help="Package name to inspect."),
):
    try:
        _package_path = package_path.expanduser().as_posix()  # type: ignore
    except AttributeError:
        _package_path = ""

    check_if_both_params_sent([package_name, _package_path])

    load_dotenv(env.as_posix(), override=True)

    ctx.obj = {
        "static": static,
        "save": save,
        "verbose": verbose,
        "package_name": package_name,
        "package_path": _package_path,
    }

    if ctx.invoked_subcommand is None:
        check_only_one_params_sent([package_name, _package_path])

        tree_map = get_tree_map(package_name, _package_path)
        tree = TreeBuilder(ctx).build(tree_map)
        if static:
            console.print(tree)
        else:
            app = InspackageApp(tree)  # type: ignore
            app.run()

        if save:
            filename = package_name or os.path.basename(_package_path)
            with open(f"{filename}.json", "w", encoding="utf-8") as f:
                json.dump(tree_map, f, indent=4, ensure_ascii=False)

        raise Exit()

    console.print(help_message_template)
