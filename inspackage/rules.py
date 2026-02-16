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

for category, rule_group in rule_config.items():
    if category == "file_content":
        for rule_name, rule_value in rule_list["file_content"].items():
            if "rules" in rule_name:
                for item in rule_value:
                    rule_group.append((item[0], bool(os.getenv(item[0], item[1]))))
            else:
                rule_group.append((rule_name, bool(os.getenv(rule_name, rule_value))))

    else:
        for rule_name, rule_value in rule_list[category]:
            default_value = None
            if rule_name == "RULE_PATH_EXCLUDE_DIRS":
                default_value = list(os.getenv(rule_name, rule_value))
            else:
                default_value = bool(os.getenv(rule_name, rule_value))
            rule_group.append((rule_name, default_value))


def checkrules_pathname(pathname: str):
    result = []
    for k, v in rule_config["paths"]:
        match k:
            case "RULE_PATH_STARTSWITH_UNDERLINE":
                if v:
                    result.append(pathname.startswith("_"))
                continue
            case "RULE_PATH_STARTSWITH_DOT":
                if v:
                    result.append(pathname.startswith("."))
                continue
            case "RULE_PATH_EXCLUDE_DIRS":
                result.append(pathname not in v)
                continue

    return all(result)


def checkrules_filename(filename: str):
    result = []
    for k, v in rule_config["files"]:
        match k:
            case "RULE_FILE_INCLUDE_INIT_":
                if filename == "__init__.py":
                    result.append(v)
                continue

            case "RULE_FILE_STARTSWITH_UNDERLINE":
                if filename != "__init__.py":
                    result.append(filename.startswith("_") == v)
                continue

            case "RULE_FILE_STARTSWITH_DOT":
                result.append(filename.startswith(".") == v)
                continue

    return all(result)


def checkrules_file_content(node: stmt):
    result = []

    if isinstance(node, (Assign, AnnAssign)):
        if not rule_config["RULE_VARIABLE_INCLUDE"]:
            return False

        for k, v in rule_config["variable_rules"]:
            match k:  # match case here to stay prepared for another rules
                case "RULE_VARIABLE_STARTSWITH_UNDERLINE":
                    if isinstance(node, Assign):
                        result.append(str(node.targets[0]).startswith("_") == v)
                    else:
                        result.append(str(node.target).startswith("_") == v)
            continue

    if isinstance(node, FunctionDef):
        if not rule_config["RULE_METHODS_INCLUDE"]:
            return False

        for k, v in rule_config["method_rules"]:
            match k:
                case "RULE_METHOD_STARTSWITH_UNDERLINE":
                    ...
                case "RULE_PROPERTY_STARTSWITH_UNDERLINE":
                    ...
            continue

    if isinstance(node, ClassDef):
        if not rule_config["RULE_CLASS_INCLUDE"]:
            return False

        for k, v in rule_config["class_rules"]:
            match k:
                case "RULE_CLASS_STARTSWITH_UNDERLINE":
                    ...
                case "RULE_CLASS_CONSTRUCTOR":
                    ...
                case "RULE_CLASS_MAGIC_METHODS":
                    ...
                case "RULE_CLASS_ANOTHER_METHODS_UNDERLINE":
                    ...

    return all(result)
