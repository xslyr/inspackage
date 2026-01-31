import importlib.util
import os

from dotenv import load_dotenv

from inspack.cli import c
from inspack.rules import check_file, check_path
from inspack.style import Icon


def run(package_name: str, env_file: str = "~/.inspackrc"):
    load_dotenv(env_file)
    spec = importlib.util.find_spec(package_name)

    if not spec or not spec.origin:
        c.print(f"\n[red]Error:[/] Package '{package_name}' not found on current venv!\n")
        return

    package_path = os.path.dirname(spec.origin)
    mapping = list(os.walk(package_path))
    base_path = os.path.dirname(mapping[0][0])
    print("")

    for item in mapping:
        basename = os.path.basename(item[0])
        if check_path(basename):
            paths = [path for path in item[1] if check_path(path)]
            files = [file[:-3] for file in item[2] if check_file(file)]
            current_dir = item[0].replace(base_path, "")

            c.print(f"{Icon.folder}  {current_dir}")

            for path in paths:
                c.print(f"[green]  {Icon.folder} {path}[/]")

            for file in files:
                c.print(f"[blue]  {Icon.file} {file}[/]")

            print("\n")
