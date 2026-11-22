import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_typer_and_textual_are_declared_dependencies():
    assert '"textual' in PYPROJECT
    assert '"typer' in PYPROJECT


def test_rich_is_declared_as_direct_dependency():
    deps = PYPROJECT.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert re.search(r'"rich\b', deps)


def test_classifiers_cover_python_3_10():
    assert "Programming Language :: Python :: 3.10" in PYPROJECT


def test_version_is_not_hardcoded_in_package_init():
    # The fallback "0.0.0+unknown" is a placeholder, not a copy of the release version: only the real one is forbidden.
    source = (ROOT / "inspackage" / "__init__.py").read_text(encoding="utf-8")
    project_version = re.search(r'^version = "([^"]+)"', PYPROJECT, re.MULTILINE).group(1)
    assert f'"{project_version}"' not in source
    assert "importlib.metadata" in source
