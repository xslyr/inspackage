import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_typer_and_textual_are_declared_dependencies():
    assert '"textual' in PYPROJECT
    assert '"typer' in PYPROJECT


@pytest.mark.xfail(strict=True, reason="B17 #23")
def test_rich_is_declared_as_direct_dependency():
    deps = PYPROJECT.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert re.search(r'"rich\b', deps)


@pytest.mark.xfail(strict=True, reason="B17 #23")
def test_classifiers_cover_python_3_10():
    assert "Programming Language :: Python :: 3.10" in PYPROJECT


@pytest.mark.xfail(strict=True, reason="B17 #23")
def test_version_is_not_hardcoded_in_package_init():
    source = (ROOT / "inspackage" / "__init__.py").read_text(encoding="utf-8")
    assert not re.search(r'__version__\s*=\s*"\d', source)
