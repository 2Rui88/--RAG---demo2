from __future__ import annotations

from typing import Protocol


class QueryRewriter(Protocol):
    def rewrite(self, query: str, history: list[dict[str, str]] | None = None) -> str:
        ...


class NoopQueryRewriter:
    def rewrite(self, query: str, history: list[dict[str, str]] | None = None) -> str:
        return query
