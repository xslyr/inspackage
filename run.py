from rich.console import Console

from inspackage.inspection import list_details

c = Console()

# pname = "markdown_it"
# pname = "astroid"
pname = "dotenv"
result = list_details(c, package_name=pname)
