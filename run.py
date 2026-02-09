import sys

from inspackage import cli

if __name__ == "__main__":
    sys.argv = ["run.py", "--static", "--save", "astroid"]
    cli.app()
