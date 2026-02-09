import os
from enum import Enum
from typing import Tuple

from rich.tree import Tree as RichTree
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Tree
from textual.widgets.tree import TreeNode as TextualTree
from typer import Context

from inspackage.style import Icon

NodeType = RichTree | TextualTree
CategoryStyle = Enum(
    "CategoryStyle",
    [
        "title",
        "paths",
        "files",
        "title_vars",
        "item_vars",
        "title_methods",
        "item_methods",
        "title_class",
        "class_constructor",
        "class_title_vars",
        "class_item_vars",
        "class_title_properties",
        "class_item_properties",
        "class_title_methods",
        "class_item_methods",
    ],
)


class TreeBuilder:
    FINAL_NODES = [
        CategoryStyle.item_vars,
        CategoryStyle.item_methods,
        CategoryStyle.class_constructor,
        CategoryStyle.class_item_vars,
        CategoryStyle.class_item_methods,
        CategoryStyle.class_item_properties,
    ]

    def __init__(self, ctx: Context):
        self.interactive = not ctx.obj["static"]
        self.widget = None

    def build(self, tree_map: dict):
        """Method to create a path details on rich tree from a tree_dict"""

        if self.interactive:
            self.widget = Tree(tree_map["name"])
            self.widget.root.expand()
            root_node = self.widget.root
        else:
            root_node = RichTree(tree_map["name"])

        for data in tree_map["nodes"]:
            self.__create_nodes_from_map(data, root_node)

        return self.widget if self.interactive else root_node

    def __main_formatter(self, data: str | Tuple, category: CategoryStyle) -> str:
        """Formatter to unify label, colors & main texts."""

        # conferir se as properties recebem tuplas ou strings
        result = ""
        match category:
            case CategoryStyle.title:
                result = data

            case CategoryStyle.paths:
                result = f"{Icon.paths} {data}"

            case CategoryStyle.files:
                result = f"{Icon.files} {data}"

            # ---------- Files ----------

            case CategoryStyle.title_vars:
                result = f"{Icon.variables} Vars:"

            case CategoryStyle.item_vars:
                result = data

            case CategoryStyle.title_methods:
                result = f"{Icon.methods} Methods:"

            case CategoryStyle.item_methods:
                pattern = "{} ({})" if not data[-1] else "{} ({}) -> {}"
                result = pattern.format(*data)

            # ---------- Class ----------

            case CategoryStyle.title_class:
                result = f"{Icon.classes} Class: {data}"

            case CategoryStyle.class_constructor:
                result = "{} ({})".format(*data) if isinstance(data, Tuple) else data

            case CategoryStyle.class_title_vars:
                result = f"{Icon.variables} Variables: "

            case CategoryStyle.class_item_vars:
                result = data

            case CategoryStyle.class_title_properties:
                result = f"{Icon.methods} Properties: "

            case CategoryStyle.class_item_properties:
                result = data

            case CategoryStyle.class_title_methods:
                result = f"{Icon.methods} Methods: "

            case CategoryStyle.class_item_methods:
                pattern = "{} ({})" if not data[-1] else "{} ({}) -> {}"
                result = pattern.format(*data)

        return str(result)

    def __add_new_node(self, parent_node: NodeType, txt: str | Tuple, category: CategoryStyle, expand: bool = False):
        formatted_txt = self.__main_formatter(txt, category)
        if isinstance(parent_node, TextualTree):
            if category in TreeBuilder.FINAL_NODES:
                return parent_node.add(formatted_txt, allow_expand=False)
            else:
                return parent_node.add(formatted_txt, expand=expand)

        return parent_node.add(formatted_txt)

    def __create_nodes_from_map(self, data: dict, parent_node: NodeType):
        """Recursive method to create tree path from root dict."""

        if data["category"] == "directory":
            current_node = self.__add_new_node(parent_node, data["name"], CategoryStyle.paths, True)
            for item in data["nodes"]:
                self.__create_nodes_from_map(item, current_node)
            return current_node

        return self.__create_file_node(data, parent_node)

    def __create_file_node(self, data: dict, parent_node: NodeType):
        current_node = self.__add_new_node(parent_node, data["name"], CategoryStyle.files, False)

        for key, value in data["structure"].items():
            if len(value) > 0:
                match key:
                    case "variables":
                        node_n1 = self.__add_new_node(current_node, "", CategoryStyle.title_vars, False)
                        for v in value:
                            self.__add_new_node(node_n1, str(v), CategoryStyle.item_vars, False)

                    case "methods":
                        node_n1 = self.__add_new_node(current_node, "", CategoryStyle.title_methods)
                        for v in value:
                            self.__add_new_node(node_n1, v, CategoryStyle.item_methods, False)

                    case _:  # class
                        for c in value:
                            node_n1 = self.__add_new_node(current_node, c["name"], CategoryStyle.title_class, False)
                            for cls_key, cls_val in c.items():
                                match cls_key:
                                    case "constructor":
                                        self.__add_new_node(node_n1, cls_val[0], CategoryStyle.class_constructor, False)

                                    case "variables":
                                        node_n2 = self.__add_new_node(
                                            node_n1, "", CategoryStyle.class_title_vars, False
                                        )
                                        for v in cls_val:
                                            self.__add_new_node(node_n2, str(v), CategoryStyle.class_item_vars, False)

                                    case "property":
                                        node_n2 = self.__add_new_node(
                                            node_n1, "", CategoryStyle.class_title_properties, False
                                        )
                                        for v in cls_val:
                                            if isinstance(v, tuple):
                                                self.__add_new_node(
                                                    node_n2, v, CategoryStyle.class_item_properties, False
                                                )
                                            else:
                                                self.__add_new_node(
                                                    node_n2, str(v), CategoryStyle.class_item_properties, False
                                                )

                                    case "methods":
                                        node_n2 = self.__add_new_node(
                                            node_n1, "", CategoryStyle.class_title_methods, False
                                        )
                                        for v in cls_val:
                                            self.__add_new_node(node_n2, v, CategoryStyle.class_item_methods, False)
        return current_node


class InspackageApp(App):
    TITLE = "Inspackage"
    SUB_TITLE = "Python Package Analyzer"
    BINDINGS = [("q", "quit", "quit"), ("d", "toggle_dark", "toggle_dark")]

    def __init__(self, tree: Tree):
        super().__init__()
        self.on_dark_mode: bool = True
        self.light_theme = os.getenv("LIGHT_THEME", "textual-light")
        self.dark_theme = os.getenv("LIGHT_THEME", "flexoki")
        self._tree = tree

    def on_mount(self) -> None:
        self.theme = self.dark_theme if self.on_dark_mode else self.light_theme

    def action_toggle_dark(self) -> None:
        self.on_dark_mode = not self.on_dark_mode
        self.theme = self.dark_theme if self.on_dark_mode else self.light_theme

    def compose(self) -> ComposeResult:
        yield Header()
        yield self._tree
        yield Footer()
