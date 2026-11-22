import asyncio
from types import SimpleNamespace

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


def test_dark_theme_is_independent_from_light_theme_variable(samplepkg_ok, monkeypatch):
    monkeypatch.setenv("LIGHT_THEME", "textual-ansi")
    monkeypatch.delenv("DARK_THEME", raising=False)
    app = InspackageApp(_build_widget(samplepkg_ok))
    assert app.dark_theme != "textual-ansi"
    monkeypatch.setenv("DARK_THEME", "nord")
    assert InspackageApp(_build_widget(samplepkg_ok)).dark_theme == "nord"


def _labels(node):
    yield str(node.label)
    for child in node.children:
        yield from _labels(child)


def test_tui_labels_show_markup_like_text_literally(tmp_path):
    (tmp_path / "m.py").write_text(
        'def f(x: list[int], y="[/]") -> dict[str, int]: ...\ndef g(y="[/x]"): ...\n'
        "class C:\n    def __init__(self, a: list[int]): ...\n"
    )
    labels = list(_labels(_build_widget(tmp_path / "m.py").root))
    assert any("list[int]" in label and "dict[str, int]" in label for label in labels), labels
    assert any("[/x]" in label for label in labels), labels
