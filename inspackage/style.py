from enum import Enum

from rich.console import Console

console = Console()

_ItemsPath = Enum("_ItemsRoot", ["root", "packages", "paths", "files"])
_ItemsFile = Enum("_ItemsFile", ["classes", "methods", "variables", "properties", "constructors"])


class Icon:
    eye = "\uf06e"
    folder = "\uf115"  # "\uf07b"
    file = "\uf0c5"
    obj = "\uf0e8"
    var = "\uf02b"
    method = "\uf0ad"


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


help_message_template = r"""[green]Inspackage[/] is an Analiser of Structure Python Package of your env packages.
[blue]Usage:[/] 
    inspackage \[options] <package_import_name>

[blue]Options:[/]
    -h --help:      Show this help message.
    -v --version:   Show current version.

[blue]Label Description:[/]
    {}  Path (Module)
    {}  Python File
    {}  Class
    {}  Methods
    {}  Variables

""".format(Icon.folder, Icon.file, Icon.obj, Icon.method, Icon.var)


__all__ = ["console", "Icon", "help_message_template", "Color"]
