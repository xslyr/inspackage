import ast
import importlib.util
import os
from ast import AnnAssign, Assign, ClassDef, FunctionDef, stmt
from collections import defaultdict

from typer import Exit

from inspackage._callbacks import console
from inspackage.exception import DefaultExceptions
from inspackage.rules import checkrules_filename, checkrules_pathname


def get_tree_map(package_name: str | None = "", package_path: str = "") -> dict:
    """Method to get tree_dict containing all details from package or path."""

    if package_path:
        package_path = os.path.abspath(package_path)
    else:
        package_path = find_package_path(package_name)  # type: ignore

    return __get_path_map(package_path) if package_path else {}


def find_package_path(package_name: str):
    """Method to get env_path from package name"""

    spec = importlib.util.find_spec(package_name)

    if not spec or not spec.origin:
        console.print(DefaultExceptions.package_not_found.format(package_name))
        raise Exit(code=1)

    return os.path.dirname(spec.origin)


def __get_path_map(path: str):
    """Recursive method to capture a dict containing all details from path."""

    name = os.path.basename(path)

    if not os.path.isdir(path) and ".py" in name and checkrules_filename(name):
        with open(path, "r") as file:
            try:
                file_parse = ast.parse(file.read())
                file_structure = defaultdict(list)
                for item in file_parse.body:
                    file_structure = __get_file_map(item, file_structure)
                return {"name": name, "category": "file", "structure": dict(file_structure)}
            except SyntaxError:
                return {}

    if os.path.isdir(path) and checkrules_pathname(name):
        data = {"name": name, "category": "directory", "nodes": []}
        with os.scandir(path) as it:
            for entry in it:
                result = __get_path_map(entry.path)
                if result:
                    data["nodes"].append(result)
        return data

    return {}


def __get_file_map(node: stmt, file_dict: defaultdict):
    """Method to create a dict file details from ast node"""

    match node:
        case Assign():
            if not str(node.targets[0]).startswith("_"):
                file_dict["variables"].append(ast.unparse(node.targets[0]))

        case AnnAssign():
            if not str(node.target).startswith("_"):
                file_dict["variables"].append(f"{ast.unparse(node.target)} : {ast.unparse(node.annotation)}")

        case FunctionDef():
            if not str(node.name).startswith("_"):
                returns = ast.unparse(node.returns) if node.returns else None
                params = ast.unparse(node.args)
                file_dict["methods"].append((node.name, params, returns))

        case ClassDef():
            if not str(node.name).startswith("_"):
                citems = defaultdict(list)
                citems["name"] = node.name  # type: ignore
                for i in node.body:
                    match i:
                        case Assign():
                            if not str(i.targets[0]).startswith("_"):
                                citems["variables"].append(ast.unparse(i.targets[0]))
                        case AnnAssign():
                            if not str(i.target).startswith("_"):
                                citems["variables"].append(f"{ast.unparse(i.target)} : {ast.unparse(i.annotation)}")
                        case FunctionDef():
                            pre_analysis = ast.unparse(i)
                            if "__init__" in pre_analysis or "def _" not in pre_analysis:
                                if "@property" in pre_analysis:
                                    citems["properties"].append(i.name)
                                    continue

                                returns = ast.unparse(i.returns) if i.returns else ""
                                params = ast.unparse(i.args)
                                for rem in ["self,", "self", "cls,", "cls"]:
                                    params = params.replace(rem, "")

                                params = str.lstrip(params)
                                data = (i.name, params, returns)
                                insert_on = "constructor" if "__init__" in pre_analysis else "methods"

                                citems[insert_on].append(data)

                file_dict["classes"].append(citems)

    return file_dict


__all__ = ["get_tree_map", "find_package_path"]
