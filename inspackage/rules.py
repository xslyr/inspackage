import os
from ast import AnnAssign, Assign, ClassDef, FunctionDef, stmt

rule_list = {
    # rules to apply on path names
    "paths": [
        ("RULE_PATH_STARTSWITH_UNDERLINE", False),
        ("RULE_PATH_STARTSWITH_DOT", False),
        (
            "RULE_PATH_EXCLUDE_DIRS",
            [
                ".venv",
                "venv",
                "__pycache__",
                ".virtual_documents",
                ".git",
                ".vscode",
                ".idea",
                ".mypy_cache",
                ".ipynb_checkpoints",
            ],
        ),
    ],
    # rules to apply on file names
    "files": [
        ("RULE_FILE_INCLUDE_INIT_", True),
        ("RULE_FILE_STARTSWITH_UNDERLINE", False),
        ("RULE_FILE_STARTSWITH_DOT", False),
    ],
    # rules to apply on file content
    "file_content": {
        # vars
        "RULE_VARIABLE_INCLUDE": True,
        "variable_rules": [
            ("RULE_VARIABLE_STARTSWITH_UNDERLINE", False),
        ],
        # methods
        "RULE_METHODS_INCLUDE": True,
        "method_rules": [
            ("RULE_METHOD_STARTSWITH_UNDERLINE", False),
        ],
        # class
        "RULE_CLASS_INCLUDE": True,
        "class_rules": [
            ("RULE_CLASS_STARTSWITH_UNDERLINE", False),
            ("RULE_CLASS_CONSTRUCTOR", True),
            ("RULE_CLASS_MAGIC_METHODS", False),
            ("RULE_CLASS_ANOTHER_METHODS_UNDERLINE", False),
        ],
    },
}

rule_config = {"paths": [], "files": [], "file_content": []}

for item in rule_config.keys():
    if item == "file_content":
        for key, value in rule_list["file_content"].items():
            if "rules" in key:
                for rule in value:
                    rule_config[item].append((rule[0], os.getenv(rule[0], rule[1])))
            else:
                rule_config[item].append((key, os.getenv(key, value)))

    else:
        for rule in rule_list[item]:
            rule_config[item].append((rule[0], os.getenv(rule[0], rule[1])))


def checkrules_pathname(pathname: str):
    result = []
    for key, value in rule_config["paths"]:
        match key:
            case "RULE_PATH_STARTSWITH_UNDERLINE":
                if value:
                    result.append(pathname.startswith("_"))
                continue
            case "RULE_PATH_STARTSWITH_DOT":
                if value:
                    result.append(pathname.startswith("."))
                continue
            case "RULE_PATH_EXCLUDE_DIRS":
                result.append(pathname not in value)
                continue

    return all(result)


def checkrules_filename(filename: str):
    result = []
    for key, value in rule_config["files"]:
        match key:
            case "RULE_FILE_INCLUDE_INIT_":
                if filename == "__init__.py":
                    result.append(value)
                continue

            case "RULE_FILE_STARTSWITH_UNDERLINE":
                if filename != "__init__.py":
                    result.append(filename.startswith("_") == value)
                continue

            case "RULE_FILE_STARTSWITH_DOT":
                result.append(filename.startswith(".") == value)
                continue

    return all(result)


def checkrules_file_content(node: stmt):
    result = []

    if isinstance(node, Assign) or isinstance(node, AnnAssign):
        if not rule_config["RULE_VARIABLE_INCLUDE"]:
            return False
        else:
            for key, value in rule_config["variable_rules"]:
                match key:  # match case here to stay prepared for another rules
                    case "RULE_VARIABLE_STARTSWITH_UNDERLINE":
                        if isinstance(node, Assign):
                            result.append(str(node.targets[0]).startswith("_") == value)
                        else:
                            result.append(str(node.target).startswith("_") == value)
                continue

    if isinstance(node, FunctionDef):
        if not rule_config["RULE_METHODS_INCLUDE"]:
            return False
        else:
            for key, value in rule_config["method_rules"]:
                match key:
                    case "RULE_METHOD_STARTSWITH_UNDERLINE":
                        ...
                    case "RULE_PROPERTY_STARTSWITH_UNDERLINE":
                        ...
                continue

    if isinstance(node, ClassDef):
        if not rule_config["RULE_CLASS_INCLUDE"]:
            return False
        else:
            for key, value in rule_config["class_rules"]:
                match key:
                    case "RULE_CLASS_STARTSWITH_UNDERLINE":
                        ...
                    case "RULE_CLASS_CONSTRUCTOR":
                        ...
                    case "RULE_CLASS_MAGIC_METHODS":
                        ...
                    case "RULE_CLASS_ANOTHER_METHODS_UNDERLINE":
                        ...

    return all(result)
