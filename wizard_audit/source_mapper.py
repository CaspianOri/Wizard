# SPDX-License-Identifier: MIT

from __future__ import annotations

from bisect import bisect_right
from pathlib import Path
from typing import Any


class SourceMapper:
    """Map Solidity AST byte offsets to source lines deterministically."""

    def __init__(self, source_files: dict[str, Path]) -> None:
        self.source_files = source_files
        self._line_starts: dict[str, dict[int, int]] = {}

    def build(self, ast: dict[str, Any]) -> dict[str, dict[str, object]]:
        mapping: dict[str, dict[str, object]] = {}
        for source_index, (source_path, file_path) in enumerate(self.source_files.items()):
            content = file_path.read_text(encoding="utf-8", errors="replace")
            starts = {0: 0}
            starts.update({index + 1: index + 1 for index, char in enumerate(content) if char == "\n"})
            self._line_starts[source_path] = starts
            mapping[source_path] = {
                "path": str(file_path),
                "source_index": source_index,
                "line_starts": starts,
                "line_count": max(1, content.count("\n") + 1),
            }

        source_list = ast.get("sourceList") if isinstance(ast, dict) else None
        for node in self._iter_nodes(ast):
            src = node.get("src")
            parsed = self._parse_src(src) if isinstance(src, str) else None
            if parsed is None:
                continue
            start, length, source_index = parsed
            resolved = self._resolve_source_file(source_index, start, mapping, source_list)
            if resolved is None:
                continue
            file_key, meta = resolved
            starts = meta["line_starts"]
            assert isinstance(starts, dict)
            node["_source_file"] = file_key
            node["_source_line"] = self._offset_to_line(start, starts)
            node["_source_offset"] = start
            node["_source_length"] = length
        return mapping

    @staticmethod
    def _iter_nodes(node: object):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from SourceMapper._iter_nodes(value)
        elif isinstance(node, list):
            for item in node:
                yield from SourceMapper._iter_nodes(item)

    @staticmethod
    def _parse_src(src: str) -> tuple[int, int, int] | None:
        parts = src.split(":")
        if len(parts) != 3:
            return None
        try:
            start, length, source_index = (int(part) for part in parts)
        except ValueError:
            return None
        if start < 0 or length < 0 or source_index < 0:
            return None
        return start, length, source_index

    @staticmethod
    def _offset_to_line(offset: int, line_starts: dict[int, int]) -> int:
        """Return the 1-based line containing offset using sorted line starts."""
        if offset < 0 or not line_starts:
            return 1
        starts = sorted(line_starts)
        return max(1, bisect_right(starts, offset))

    def _resolve_source_file(
        self,
        source_index: int,
        offset: int,
        mapping: dict[str, dict[str, object]],
        source_list: object,
    ) -> tuple[str, dict[str, object]] | None:
        for source_key, meta in mapping.items():
            if meta.get("source_index") == source_index:
                return source_key, meta
        if isinstance(source_list, list) and source_index < len(source_list):
            source_name = str(source_list[source_index])
            if source_name in mapping:
                return source_name, mapping[source_name]
        if len(mapping) == 1:
            return next(iter(mapping.items()))
        return None

    def line_number_for(self, src: str, source_path: str) -> int:
        parsed = self._parse_src(src)
        if parsed is None:
            return 1
        starts = self._line_starts.get(source_path)
        if starts is None:
            path = self.source_files.get(source_path)
            if path is None:
                return 1
            content = path.read_text(encoding="utf-8", errors="replace")
            starts = {0: 0}
            starts.update({i + 1: i + 1 for i, char in enumerate(content) if char == "\n"})
        return self._offset_to_line(parsed[0], starts)
