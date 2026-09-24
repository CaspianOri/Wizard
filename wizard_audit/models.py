# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Evidence:
    kind: str
    source: str
    location: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Finding:
    id: str
    category: str
    title: str
    contract: str
    function: str
    line: int
    confidence: str
    score: int
    description: str
    evidence: list[Evidence] = field(default_factory=list)
    state_vars: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuditConfig:
    file: str | None = None
    directory: str | None = None
    output: str = "./audit-output"
    deep: bool = False
    generate_poc: bool = False
    format: str = "json"
    strict: bool = True
    solc_version: str | None = None
    rpc: str | None = None
    rpc_fork: str | None = None
    capital_source: str = "funded"
    fork_block: int | None = None
    config_path: str | None = None
    correlation_id: str | None = None
    workspace_root: str = "."

    def output_dir(self) -> Path:
        return Path(self.output).resolve()
