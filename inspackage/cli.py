from typing import Optional

from typer import Argument, Context, Exit, Option, Typer

from inspackage._callbacks import callback_help, callback_version, check_package_and_path_send
from inspackage._inspection import get_tree
from inspackage.style import console, help_message_template

app = Typer(add_help_option=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    help: bool = Option(None, "-h", "--help", callback=callback_help, is_eager=True),
    version: bool = Option(None, "-v", "--version", callback=callback_version, is_eager=True),
    env: str = Option(
        "~/.inspackagerc",
        "--env",
        "-e",
        help="Optional env file to change rules of inspection. Default: ~/.inspackagerc",
    ),
    package_path: Optional[str] = Option(None, "--dir", "-d", help="Package path to inspect."),
    package_name: Optional[str] = Argument(None, help="Package name to inspect."),
):
    ctx.obj = {"package_name": package_name, "package_path": package_path}
    check_package_and_path_send(ctx)

    if ctx.invoked_subcommand is None:
        if not any(ctx.obj.values()):
            console.print(help_message_template)
            raise Exit()

        tree = get_tree(**ctx.obj, env=env)
        console.print(tree)
        raise Exit()

    console.print(help_message_template)


@app.command()
def ai(ctx: Context, package_name: Optional[str] = Argument(None, help="Package name to inspect.")): ...
