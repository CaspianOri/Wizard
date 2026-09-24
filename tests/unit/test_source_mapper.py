# SPDX-License-Identifier: MIT

from pathlib import Path

from wizard_audit.source_mapper import SourceMapper


def test_offset_to_line_uses_line_starts() -> None:
    starts = {0: 0, 4: 4, 9: 9}
    assert SourceMapper._offset_to_line(0, starts) == 1
    assert SourceMapper._offset_to_line(3, starts) == 1
    assert SourceMapper._offset_to_line(4, starts) == 2
    assert SourceMapper._offset_to_line(100, starts) == 3


def test_parse_src_requires_all_components() -> None:
    assert SourceMapper._parse_src("10:4:2") == (10, 4, 2)
    assert SourceMapper._parse_src("10:4") is None
    assert SourceMapper._parse_src("-1:4:0") is None


def test_build_maps_source_index_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "Contract.sol"
    source.write_text("contract C {}\n\nfunction f() {}\n", encoding="utf-8")
    ast = {"sourceList": ["Contract.sol"], "nodeType": "SourceUnit", "nodes": [{"nodeType": "FunctionDefinition", "src": "17:15:0"}]}
    SourceMapper({"Contract.sol": source}).build(ast)
    node = ast["nodes"][0]
    assert node["_source_file"] == "Contract.sol"
    assert node["_source_line"] == 3
    assert node["_source_offset"] == 17
    assert node["_source_length"] == 15
