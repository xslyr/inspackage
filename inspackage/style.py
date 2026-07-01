from inspackage import __version__


class Icon:
    packages = "📦"
    paths = "🗁"
    files = "🗎"
    classes = "🏗️"
    variables = "🏷️"
    methods = "🔧"


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


__all__ = ["Icon", "help_message_template"]
