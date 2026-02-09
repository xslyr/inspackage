from typer import Exit

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


def check_if_both_params_sent(params: list):
    """Função de verificar se ambos parametros package e directory foram enviados."""
    if all(params):
        console.print(DefaultExceptions.package_and_path_send)
        raise Exit(code=1)


def check_only_one_params_sent(params: list):
    if not any(params):
        console.print(help_message_template)
        raise Exit()
