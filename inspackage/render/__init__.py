"""Output formats: a registry mapping the ``--format`` name to a render function.

To add a format (html, llm, graph, ...) write ``def render_x(info, out)`` and register it in :data:`FORMATS`; the CLI
needs no other change. Text formats write to ``out`` (stdout or an opened file); interactive formats ignore it.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

from rich.console import Console

from inspackage._inspection import to_tree_map
from inspackage.model import InspectionResult
from inspackage.tree import InspackageApp, TreeBuilder

Renderer = Callable[[InspectionResult, TextIO], None]

# Accepted by the roadmap but not implemented yet: the CLI reports them as "not available in this version".
PLANNED_FORMATS = ("html", "md", "llm", "graph")


@dataclass(frozen=True)
class OutputFormat:
    name: str
    render: Renderer
    description: str
    interactive: bool = False


def render_tree(info: InspectionResult, out: TextIO) -> None:
    """Rich tree. Colors only when ``out`` is a terminal; plain (unwrapped) text otherwise."""

    tty = out.isatty()
    console = Console(file=out, **({} if tty else {"color_system": None, "force_terminal": False}))  # type: ignore
    tree = TreeBuilder(interactive=False).build(to_tree_map(info))
    console.print(tree, soft_wrap=not tty)


def render_json(info: InspectionResult, out: TextIO) -> None:
    """Public JSON contract (``info.to_dict()``, with ``schema_version``), never colored."""

    out.write(json.dumps(info.to_dict(), indent=2, ensure_ascii=False) + "\n")


def render_tui(info: InspectionResult, out: TextIO) -> None:  # pylint: disable=unused-argument
    """Interactive Textual app (does not use ``out``)."""

    widget = TreeBuilder(interactive=True).build(to_tree_map(info))
    InspackageApp(widget).run()  # type: ignore[arg-type]


FORMATS: dict[str, OutputFormat] = {
    fmt.name: fmt
    for fmt in (
        OutputFormat("tui", render_tui, "interactive tree (default)", interactive=True),
        OutputFormat("tree", render_tree, "static text tree"),
        OutputFormat("json", render_json, "JSON with schema_version"),
    )
}
