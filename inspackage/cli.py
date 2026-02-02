from rich.console import Console
from typer import Context, Exit, Option, Typer

from inspackage import __version__
from inspackage.style import help_message_template

c = Console()
app = Typer()


@app.command()
def help_message(flag):
    if flag:
        print(help_message_template)


@app.command()
def version(flag):
    if flag:
        print(__version__)
        raise Exit(code=0)


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    help: bool = Option("-h", "--help", callback=help_message, is_eager=True),
    version: bool = Option("-v", "--version", callback=version, is_eager=True),
):
    if ctx.invoked_subcommand:
        return

    print(help_message_template)
