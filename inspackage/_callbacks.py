from rich.console import Console
from typer import Exit

from inspackage import __version__

console = Console()
err_console = Console(stderr=True)


def callback_version(value: bool):
    """Função de callback para a opção --version."""
    if value:
        console.print(f"[green]Inspackage[/] version: {__version__}")
        raise Exit()


class Icon:
    packages = "📦"
    paths = "🗁"
    files = "🗎"
    classes = "🏗️"
    variables = "🏷️"
    methods = "🔧"
    errors = "⚠"
