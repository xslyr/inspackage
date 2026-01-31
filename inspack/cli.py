from rich.console import Console
from typer import Context, Exit, Option, Typer

from inspack import __command__, __version__
from inspack.style import Icon

c = Console()
app = Typer()


def version(flag):
    if flag:
        print(__version__)
        raise Exit(code=0)


def help_message(flag):
    c.print(f"""
[green]Inspack[/] - Analiser of Structure Python Package.

[blue]Usage:[/] {__command__} <package_import_name>

[blue]Examples:[/]
    {__command__} json
    {__command__} requests

[blue]Label Description:[/]
    {Icon.folder}  Path (Module)
    {Icon.file}  Python File
    {Icon.obj}  Class
    {Icon.method}  Methods
    {Icon.var}  Variables

""")


@app.callback(invoke_without_command=True)
def main(
    ctx: Context,
    help: bool = Option("-h", "--help", callback=help_message, is_eager=True),
    version: bool = Option("-v", "--version", callback=version, is_eager=True),
):
    if ctx.invoked_subcommand:
        return

    help_message(True)
