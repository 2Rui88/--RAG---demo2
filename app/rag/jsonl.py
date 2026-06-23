from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Protocol


class JsonSerializable(Protocol):
    def to_dict(self) -> dict[str, object]:
        ...


def write_jsonl(path: Path, rows: Iterable[JsonSerializable]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count
