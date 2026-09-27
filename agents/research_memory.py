from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def read_json(path: str | Path) -> Any:
    target = Path(path)
    if not target.exists():
        return []
    return json.loads(target.read_text(encoding="utf-8"))


def save_memory_bundle(base_dir: str | Path, memory_name: str, payload: dict[str, Any]) -> None:
    root = ensure_directory(base_dir)
    write_json(root / f"{memory_name}.json", payload)
    write_markdown(root / f"{memory_name}.md", "# Memory bundle\n\n" + json.dumps(payload, indent=2, sort_keys=True))


def load_memory_entries(base_dir: str | Path, name: str) -> list[dict[str, Any]]:
    file_path = Path(base_dir) / f"{name}.json"
    data = read_json(file_path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []
