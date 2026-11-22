import os
from pathlib import Path


def collect_strings(obj) -> list[str]:
    """Flatten every string (keys and values) found in a nested dict/list/tuple."""
    found: list[str] = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(collect_strings(key))
            found.extend(collect_strings(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(collect_strings(item))
    return found


def tree_has(tree_map, text: str) -> bool:
    """True if any string in tree_map equals text exactly."""
    return text in collect_strings(tree_map)


def tree_contains(tree_map, text: str) -> bool:
    """True if any string in tree_map contains text."""
    return any(text in s for s in collect_strings(tree_map))


def snapshot_path(name: str) -> Path:
    return Path(__file__).parent / "snapshots" / name


def assert_snapshot(name: str, actual: str) -> None:
    """Compare text to tests/snapshots/<name>; (re)write it only when UPDATE_SNAPSHOTS=1."""
    path = snapshot_path(name)
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
    elif not path.exists():
        raise AssertionError(f"Snapshot {path.name} does not exist; run with UPDATE_SNAPSHOTS=1 to create it")
    assert path.read_text(encoding="utf-8") == actual
