import asyncio
from types import SimpleNamespace

import pytest
from textual.widgets import Tree

from inspackage._inspection import get_tree_map
from inspackage.tree import InspackageApp, TreeBuilder


def _build_widget(path) -> Tree:
    ctx = SimpleNamespace(obj={"static": False})
    return TreeBuilder(ctx).build(get_tree_map(package_path=str(path)))  # type: ignore[arg-type]


def test_tui_renders_tree_and_toggles_theme(samplepkg_ok, monkeypatch):
    monkeypatch.delenv("LIGHT_THEME", raising=False)

    async def scenario():
        app = InspackageApp(_build_widget(samplepkg_ok))
        async with app.run_test() as pilot:
            tree = app.query_one(Tree)
            assert str(tree.root.label) == "samplepkg"
            assert len(tree.root.children) > 0
            assert app.on_dark_mode is True
            await pilot.press("d")
            assert app.on_dark_mode is False
            assert app.theme == app.light_theme
            await pilot.press("d")
            assert app.theme == app.dark_theme
            await pilot.press("q")

    asyncio.run(scenario())


@pytest.mark.xfail(strict=True, reason="B13 #9")
def test_dark_theme_is_independent_from_light_theme_variable(samplepkg_ok, monkeypatch):
    monkeypatch.setenv("LIGHT_THEME", "textual-ansi")
    monkeypatch.delenv("DARK_THEME", raising=False)
    app = InspackageApp(_build_widget(samplepkg_ok))
    assert app.dark_theme != "textual-ansi"
