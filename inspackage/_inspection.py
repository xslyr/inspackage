import ast
import importlib.util
import os
from ast import AnnAssign, Assign, ClassDef, FunctionDef, stmt
from collections import defaultdict

from dotenv import load_dotenv
from rich.tree import Tree

from inspackage.style import Color, Icon, console


def get_tree(package_name="", package_path="", env="~/.inspackagerc"):
    """Method to get tree_dict containing all details from package or path."""
    load_dotenv(env)

    if not package_path:
        package_path = find_package_path(package_name)

    tree_dict = {}
    if package_path:
        tree_dict = __get_dict_path_structure(package_path)

    if tree_dict != {}:
        tree = __create_tree_path(tree_dict)  # type: ignore
        # debug_console = Console(record=True, width=200)
        # debug_console.print(tree)
        # debug_console.save_html("tree_debug.html")
        return tree

    return tree_dict


def find_package_path(package_name: str):
    """Method to get env_path from package name"""

    spec = importlib.util.find_spec(package_name)

    if not spec or not spec.origin:
        console.print(f"\n[{Color.error}]Error:[/] Package '{package_name}' not found on current venv!\n")
        raise

    return os.path.dirname(spec.origin)


def __get_dict_path_structure(path: str):
    """Recursive method to capture a dict containing all details from path."""

    name = os.path.basename(path)

    if not os.path.isdir(path) and ".py" in name and not name.startswith("_") and not name.startswith("."):
        file_parse = ast.parse(open(path, "r", encoding="utf-8").read())
        file_structure = defaultdict(list)
        for item in file_parse.body:
            file_structure = __get_dict_file_structure(item, file_structure)
        return {"name": name, "type": "file", "structure": file_structure}

    elif os.path.isdir(path) and not name.startswith("_") and not name.startswith("."):
        data = {"name": name, "type": "directory", "nodes": []}
        try:
            with os.scandir(path) as it:
                for entry in it:
                    result = __get_dict_path_structure(entry.path)
                    if result:
                        data["nodes"].append(result)
        except PermissionError:
            pass
        return data

    return None


def __get_dict_file_structure(node: stmt, file_dict: defaultdict):
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
                                    citems["property"].append(i.name)
                                    continue

                                returns = ast.unparse(i.returns) if i.returns else ""
                                params = ast.unparse(i.args)
                                for rem in ["self,", "self", "cls,", "cls"]:
                                    params = params.replace(rem, "")

                                params = str.lstrip(params)
                                data = (i.name, params, returns)
                                insert_on = "constructor" if "__init__" in pre_analysis else "methods"

                                citems[insert_on].append(data)

                file_dict["class"].append(citems)

    return file_dict


def __create_tree_path(tree_dict: dict):
    """Method to create a path details on rich tree from a tree_dict"""

    def _format_method_data(data_tuple):
        """Helper para formatar tupla (nome, params, return) em string segura"""
        name, params, ret = data_tuple
        ret_str = f" -> {ret}" if ret else ""
        return f"{name}({params}){ret_str}"

    def _create_node(data: dict, parent_node: Tree):
        """Recursive method to create tree path from root dict."""

        if data["type"] == "directory":
            current_node = parent_node.add(f"Path: {data['name']}")
            for item in data["nodes"]:
                _create_node(item, current_node)
            return current_node

        current_node = parent_node.add("File: " + data["name"])
        for key, value in data["structure"].items():
            if len(value) > 0:
                match key:
                    case "variables":
                        node_n1 = current_node.add("Variables: ")
                        for v in value:
                            node_n1.add(str(v))

                    case "methods":
                        node_n1 = current_node.add("Methods: ")
                        for v in value:
                            node_n1.add(_format_method_data(v))

                    case _:  # class
                        for c in value:
                            node_n1 = current_node.add("Class: " + c["name"])

                            for cls_key, cls_val in c.items():
                                match cls_key:
                                    case "constructor":
                                        construct_str = _format_method_data(cls_val[0])
                                        node_n1.add("Constructor: " + construct_str)

                                    case "variables":
                                        node_n2 = node_n1.add("Variables: ")
                                        for v in cls_val:
                                            node_n2.add(str(v))

                                    case "property":
                                        node_n2 = node_n1.add("Properties: ")
                                        for v in cls_val:
                                            if isinstance(v, tuple):
                                                node_n2.add(f"{v[0]} -> {v[1]}" if v[1] else v[0])
                                            else:
                                                node_n2.add(str(v))

                                    case "methods":
                                        node_n2 = node_n1.add("Methods: ")
                                        for v in cls_val:
                                            node_n2.add(_format_method_data(v))

        return current_node

    root_tree = Tree(tree_dict["name"])

    for node in tree_dict["nodes"]:
        _create_node(node, root_tree)

    return root_tree


def __create_tree_file(tree: Tree, file_dict: dict):
    """Method to create a file details on rich tree from a file_dict_structure"""

    def __create_tree_class(tree: Tree, file_dict: dict):
        """SubMethod to create a class details on rich tree from a file_dict_structure"""

        cnode = tree.add(" Class:")
        for item in file_dict["class"]:
            c = cnode.add("[{}]{}[/]".format(Color.class_name, item["name"]))

            if len(item["constructor"]) > 0:
                constructors = c.add(" Constructors:")
                for i in item["constructor"]:
                    constructors.add(
                        "[{}]{}[/] [{}]({})[/]".format(Color.class_method_name, i[0], Color.class_method_params, i[1])
                    )

            if len(item["variables"]) > 0:
                variables = c.add(" Variables:")
                for i in item["variables"]:
                    variables.add("[{}]{}[/]".format(Color.class_variables, i[0]))

            if len(item["property"]) > 0:
                properties = c.add(" Properties:")
                for i in item["property"]:
                    if i[1]:
                        properties.add(
                            "[{}]{}[/][{}] -> {}[/]".format(
                                Color.class_property, i[0], Color.class_property_returns, i[1]
                            )
                        )
                    else:
                        properties.add("[{}]{}[/]".format(Color.method_name, i[0]))

            if len(item["methods"]) > 0:
                methods = c.add(" Methods:")
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

    if len(file_dict["variables"]) > 0:
        vnode = tree.add(f"[{Color.variables}] {Icon.var} Variables:[/]")
        for item in file_dict["variables"]:
            vnode.add("[{}]{}[/]".format(Color.variables, item))

    if len(file_dict["methods"]) > 0:
        mnode = tree.add(f"[{Color.method_name}] {Icon.method} Methods:[/]")
        for item in file_dict["methods"]:
            if item[2]:
                mnode.add(
                    "[{}]{}[/] [{}]({})[/][{}] -> {}[/]".format(
                        Color.method_name, item[0], Color.method_params, item[1], Color.method_returns, item[2]
                    )
                )
            else:
                mnode.add("[{}]{}[/][{}]({})[/]".format(Color.method_name, item[0], Color.method_params, item[1]))

    if len(file_dict["class"]) > 0:
        __create_tree_class(tree, file_dict)

    return tree


__all__ = ["get_tree", "find_package_path"]
