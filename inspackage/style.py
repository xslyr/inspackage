from inspackage import __command__


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


help_message_template = f"""
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

"""


__all__ = ["Icon", "help_message"]
