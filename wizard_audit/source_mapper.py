# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from .diagnostics import Diagnostics


class SourceMapper:
    """Reliable AST source mapping backed by real source offsets and line starts."""

    def __init__(self, source_files: dict[str, Path]) -> None:
        self.source_files = source_files

    def build(self, ast: dict) -> dict[str, dict[str, object]]:
        mapping: dict[str, dict[str, object]] = {}
        for source_path, file_path in self.source_files.items():
            content = file_path.read_text(encoding="utf-8", errors="replace")
            line_starts = {0: 0}
            for index, ch in enumerate(content):
                if ch == "\n":
                    line_starts[index + 1] = index + 1
            mapping[source_path] = {
                "path": str(file_path),
                "line_starts": line_starts,
                "line_count": len(content.splitlines()),
            }

        for node in self._iter_nodes(ast):
            node_type = node.get("nodeType")
            if node_type is None:
                continue
            src = node.get("src")
            if not isinstance(src, str) or not src:
                continue
            start, length = self._parse_src(src)
            if start is None:
                continue
            resolved = self._resolve_source_file(start, mapping)
            if resolved is None:
                continue
            file_key, meta = resolved
            line_number = self._offset_to_line(start, meta["line_starts"])
            node["_source_file"] = file_key
            node["_source_line"] = line_number
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
    def _parse_src(src: str) -> tuple[int | None, int | None]:
        parts = src.split(":")
        if len(parts) < 2:
            return None, None
        try:
            start = int(parts[0])
            length = int(parts[1])
            return start, length
        except ValueError:
            return None, None

    @staticmethod
    def _offset_to_line(offset: int, line_starts: dict[int, int]) -> int:
        if not line_starts:
            return 1
        candidates = sorted(line_starts)
        last_line = 1
        for line_start in candidates:
            if line_start <= offset:
                last_line = line_start
            else:
                break
        return sum(1 for line_start in candidates if line_start <= offset)

    def _resolve_source_file(
        self,
        offset: int,
        mapping: dict[str, dict[str, object]],
    ) -> tuple[str, dict[str, object]] | None:
        for source_key, meta in mapping.items():
            line_starts = meta.get("line_starts", {})
            if not isinstance(line_starts, dict):
                continue
            if any(start <= offset for start in line_starts):
                return source_key, meta
        return None

    def line_number_for(self, src: str, source_path: str) -> int:
        start, _ = self._parse_src(src)
        if start is None:
            return 1
        meta = self.source_files.get(source_path)
        if meta is None:
            return 1
        content = meta.read_text(encoding="utf-8", errors="replace")
        line_starts = {0: 0}
        for index, ch in enumerate(content):
            if ch == "\n":
                line_starts[index + 1] = index + 1
        return self._offset_to_line(start, line_starts)
