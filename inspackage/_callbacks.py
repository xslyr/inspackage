from typer import Context, Exit

from inspackage import __version__
from inspackage.exception import DefaultExceptions
from inspackage.style import console, help_message_template


def callback_help(value: bool):
    """Função de callback para a opção --help."""
    if value:
        console.print(help_message_template)
        raise Exit()


def callback_version(value: bool):
    """Função de callback para a opção --version."""
    if value:
        console.print(f"[green]Inspackage[/] version: {__version__}")
        raise Exit()


def check_package_and_path_send(ctx: Context):
    """Função de verificar se ambos parametros package e directory foram enviados."""
    if all(ctx.obj.values()):
        console.print(DefaultExceptions.package_and_path_send)
        raise Exit()
