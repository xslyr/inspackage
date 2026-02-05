# from rich.console import Console
# from inspackage.inspection import list_details
# c = Console()
# # pname = "markdown_it"
# # pname = "astroid"
# pname = "dotenv"
# result = list_details(c, package_name=pname)


import sys

from inspackage import cli

if __name__ == "__main__":
    # Para debugar, descomente a linha do comando que deseja testar:
    # sys.argv = ["run.py", "--help"]
    # sys.argv = ["run.py", "--version"]
    # sys.argv = ["run.py", "rich"]
    sys.argv = ["run.py", "dotenv"]
    cli.app()
