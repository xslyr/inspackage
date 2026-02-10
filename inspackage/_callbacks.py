from rich.console import Console
from typer import Exit

from inspackage import __version__
from inspackage.exception import DefaultExceptions

console = Console()

HELP_MESSAGE_TEMPLATE = r"""[green]Inspackage[/]({}) is an Analiser of Structure Python Package of your env packages.
[bright_blue]Usage:[/]
  inspackage \[options] <package_name_or_path>

[bright_blue]Options:[/]
  -h, --help            Show this help message
  -i, --interactive     Enable interactive mode
  -v, --verbose         Verbose mode
  -s, --save            Save inspection on file
  --version:            Show current version

""".format(__version__)


def callback_help(value: bool):
    """Função de callback para a opção --help."""
    if value:
        console.print(HELP_MESSAGE_TEMPLATE)
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
        console.print(HELP_MESSAGE_TEMPLATE)
        raise Exit()


class Icon:
    packages = "📦"
    paths = "🗁"
    files = "🗎"
    classes = "🏗️"
    variables = "🏷️"
    methods = "🔧"
