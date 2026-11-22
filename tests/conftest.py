import importlib
import sys
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from inspackage.cli import typer_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Fixtures are inspected as data (some contain a deliberate SyntaxError); never collect them.
collect_ignore_glob = ["fixtures/*"]


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def samplepkg_path(fixtures_dir) -> Path:
    return fixtures_dir / "samplepkg"


@pytest.fixture
def run_cli(monkeypatch, tmp_path):
    """Invoke the CLI and return the click Result. Uses an empty env file so ~/.inspackagerc never interferes."""
    monkeypatch.delenv("LIGHT_THEME", raising=False)

    def _run(*args: str):
        env_file = tmp_path / "empty.rc"
        env_file.touch()
        return CliRunner().invoke(typer_app, ["--env", str(env_file), *args])

    return _run


@pytest.fixture
def on_syspath(monkeypatch, fixtures_dir):
    """Make tests/fixtures importable by name (without touching the venv) and reset import caches."""
    monkeypatch.syspath_prepend(str(fixtures_dir))
    importlib.invalidate_caches()
    yield fixtures_dir
    for mod in [m for m in sys.modules if m.split(".")[0] in {"samplepkg", "nspkg", "single_module"}]:
        del sys.modules[mod]
    importlib.invalidate_caches()


@pytest.fixture
def samplepkg_ok(samplepkg_path, tmp_path) -> Path:
    """Copy of samplepkg without the file that has a SyntaxError (isolates bugs from B05)."""
    dest = tmp_path / "samplepkg"
    shutil.copytree(samplepkg_path, dest, ignore=shutil.ignore_patterns("broken.py", "__pycache__"))
    return dest
