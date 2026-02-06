import sys

from inspackage import cli

if __name__ == "__main__":
    # Para debugar, descomente a linha do comando que deseja testar:
    # sys.argv = ["run.py", "--help"]
    # sys.argv = ["run.py", "--version"]
    # sys.argv = ["run.py", "rich"]

    sys.argv = ["run.py", "dotenv"]
    cli.app()

    # pasta = "/home/xsly/Documentos/wspace/inspackage/.venv/lib/python3.13/site-packages/textual"
    # r = __get_dict_path_structure(pasta)

    # print(r)
