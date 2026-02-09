from enum import Enum

from rich.console import Console

from inspackage import __version__

console = Console(record=True, width=200)

_ItemsPath = Enum("_ItemsRoot", ["root", "packages", "paths", "files"])
_ItemsFile = Enum("_ItemsFile", ["classes", "methods", "variables", "properties", "constructors"])


class Icon:
    packages = "📦"
    paths = "🗁"
    files = "🗎"
    classes = "🏗️"
    variables = "🏷️"
    methods = "🔧"


class Color:
    error = "bright_red"
    package = "bright_red"
    path = "bright_yellow"
    file = "bright_yellow"

    variables = "bright_green"

    method_name = "bright_blue"
    method_params = "bright_blue"
    method_returns = "bright_blue"

    class_name = "bright_cyan"
    class_constructor = "bright_cyan"
    class_variables = "bright_cyan"
    class_property = "bright_cyan"
    class_property_returns = "bright_cyan"
    class_method_name = "bright_cyan"
    class_method_params = "bright_cyan"
    class_method_returns = "bright_cyan"


help_message_template = r"""[green]Inspackage[/]({}) is an Analiser of Structure Python Package of your env packages.
[bright_blue]Usage:[/] 
  inspackage \[options] <package_name_or_path>

[bright_blue]Options:[/]
  -h, --help            Show this help message
  -i, --interactive     Enable interactive mode
  -v, --verbose         Verbose mode
  -s, --save            Save inspection on file
  --version:            Show current version

""".format(__version__)

textual_tree_themes = """
textual-dark
textual-light
nord
gruvbox
catppuccin-mocha
dracula
tokyo-night
monokai
flexoki
catppuccin-late
solarized-light
solarized-dark
rose-pine
rose-pine-moon
rose-pine-dwan
atom-one-dark
atom-one-light
"""


__all__ = ["console", "Icon", "help_message_template", "Color"]
