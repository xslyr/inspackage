import ast
import importlib.util
import os
from ast import AnnAssign, Assign, ClassDef, FunctionDef, stmt

from dotenv import load_dotenv
from rich.tree import Tree

from inspackage.rules import check_file, check_path
from inspackage.style import Color, Icon, console


def get_tree(package_name="", package_path="", env="~/.inspackagerc"):
    load_dotenv(env)

    if not package_path:
        package_path = find_package_path(package_name)

    mapping = list(os.walk(package_path))

    root_text = package_name if package_name != "" else package_path
    root = Tree(f"[{Color.package}]{Icon.eye}  {root_text}[/]")
    tree = {}

    for map_item in mapping:
        current_path = os.path.relpath(map_item[0], package_path)
        if current_path == ".":
            current_path = "/"

        if check_path(current_path):
            tree[current_path] = root.add(f"[{Color.path}] {Icon.folder}  {current_path}[/]")

            if current_path != "/":
                paths = [path for path in map_item[1] if check_path(path)]
                for path in paths:
                    tree[current_path].add(f"[{Color.path}] {Icon.folder}  {path}[/]")

            files = [file for file in map_item[2] if check_file(file)]
            for file in files:
                ftree = tree[current_path].add(f"[{Color.file}] {Icon.file}  {file}[/]")
                ftree = __get_file_details(ftree, file, current_path, package_path)

    return root


def find_package_path(package_name: str):
    spec = importlib.util.find_spec(package_name)

    if not spec or not spec.origin:
        console.print(f"\n[{Color.error}]Error:[/] Package '{package_name}' not found on current venv!\n")
        raise

    return os.path.dirname(spec.origin)


def __get_file_details(tree: Tree, file: str, current_path: str, package_path: str):
    pathfile = os.path.normpath(f"{package_path}/{current_path}/{file}")

    file_parse = ast.parse(open(pathfile, "r", encoding="utf-8").read())

    fitems = {"variables": [], "methods": [], "class": []}
    for i in file_parse.body:
        fitems = _check_file_structure(i, fitems)

    return _create_file_tree_specification(tree, fitems)


def _create_file_tree_specification(tree: Tree, fitems: dict):
    # ----- file variables ----
    if len(fitems["variables"]) > 1:
        vnode = tree.add(f"[{Color.variables}] {Icon.var} Variables:[/]")
        for item in fitems["variables"]:
            vnode.add("[{}]{}[/]".format(Color.variables, item))

    # ----- file methods -----
    if len(fitems["methods"]) > 1:
        mnode = tree.add(f"[{Color.method_name}] {Icon.method} Methods:[/]")
        for item in fitems["methods"]:
            if item[2]:
                mnode.add(
                    "[{}]{}[/] [{}]({})[/][{}] -> {}[/]".format(
                        Color.method_name, item[0], Color.method_params, item[1], Color.method_returns, item[2]
                    )
                )
            else:
                mnode.add("[{}]{}[/][{}]({})[/]".format(Color.method_name, item[0], Color.method_params, item[1]))

    # ----- class -----
    if len(fitems["class"]) > 1:
        cnode = tree.add(f"[{Color.class_name}] {Icon.obj} Class:[/]")
        for item in fitems["class"]:
            c = cnode.add("[{}]{}[/]".format(Color.class_name, item["name"]))

            # ----- class constructor -----
            if len(item["constructor"]) > 0:
                constructors = c.add(f"[{Color.class_method_name}] Constructors:[/]")
                for i in item["constructor"]:
                    constructors.add(
                        "[{}]{}[/] [{}]({})[/]".format(Color.class_method_name, i[0], Color.class_method_params, i[1])
                    )

            # ----- class variables -----
            if len(item["variables"]) > 0:
                variables = c.add(f"[{Color.class_variables} ]Variables:[/]")
                for i in item["variables"]:
                    variables.add("[{}]{}[/]".format(Color.class_variables, i[0]))

            # ----- class property -----
            if len(item["property"]) > 0:
                properties = c.add(f"[{Color.class_property}] Properties:[/]")
                for i in item["property"]:
                    if i[1]:
                        properties.add(
                            "[{}]{}[/][{}] -> {}[/]".format(
                                Color.class_property, i[0], Color.class_property_returns, i[1]
                            )
                        )
                    else:
                        properties.add("[{}]{}[/]".format(Color.method_name, i[0]))

            # ----- class methods -----
            if len(item["methods"]) > 0:
                methods = c.add(f"[{Color.class_method_name}] Methods:[/]")
                for i in item["methods"]:
                    if i[2]:
                        methods.add(
                            "[{}]{}[/][{}] ({})[/][{}] -> {}[/]".format(
                                Color.class_method_name,
                                i[0],
                                Color.class_method_params,
                                i[1],
                                Color.class_method_returns,
                                i[2],
                            )
                        )
                    else:
                        methods.add(
                            "[{}]{}[/][{}] ({})[/]".format(
                                Color.class_method_name, i[0], Color.class_method_params, i[1]
                            )
                        )

    return tree


def _check_file_structure(node: stmt, fitems: dict):
    match node:
        case Assign():
            if not str(node.targets[0]).startswith("_"):
                fitems["variables"].append(ast.unparse(node.targets[0]))

        case AnnAssign():
            if not str(node.target).startswith("_"):
                fitems["variables"].append(f"{ast.unparse(node.target)} : {ast.unparse(node.annotation)}")

        case FunctionDef():
            if not str(node.name).startswith("_"):
                returns = ast.unparse(node.returns) if node.returns else None
                params = ast.unparse(node.args)
                for i in ["self,", "self", "cls,", "cls"]:
                    params = params.replace(i, "")
                params = str.lstrip(params)
                fitems["methods"].append((node.name, params, returns))

        case ClassDef():
            if not str(node.name).startswith("_"):
                citems = {"name": node.name, "constructor": [], "variables": [], "property": [], "methods": []}
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
                                    citems["property"].append(i.name)
                                    continue

                                returns = ast.unparse(i.returns) if i.returns else None
                                params = ast.unparse(i.args)
                                for rem in ["self,", "self", "cls,", "cls"]:
                                    params = params.replace(rem, "")

                                params = str.lstrip(params)
                                data = (i.name, params, returns)
                                insert_on = "constructor" if "__init__" in pre_analysis else "methods"

                                citems[insert_on].append(data)

                fitems["class"].append(citems)

    return fitems
