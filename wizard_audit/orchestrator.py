# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostics
from .models import AuditConfig


class Orchestrator:
    """Coordinates the audit workflow for Solidity code."""

    def __init__(self, config: AuditConfig, diagnostics: Diagnostics | None = None) -> None:
        self.config = config
        self.diagnostics = diagnostics or Diagnostics(config.correlation_id)

    def run(self) -> list[dict[str, Any]]:
        if self.config.file is None and self.config.directory is None:
            raise ValueError("Either --file or --dir must be supplied")

        source_files = self._prepare_sources()
        if not source_files:
            raise FileNotFoundError("No Solidity files were found")

        from .compiler import Compiler
        from .exporter import Exporter
        from .hunter import AuditHunter
        from .scorer import Scorer
        from .source_mapper import SourceMapper

        compiler = Compiler(self.diagnostics, Path(self.config.workspace_root).resolve())
        version = compiler.detect_pragma(source_files)
        compiler.ensure_compiler(version)
        ast = compiler.compile(source_files)

        mapper = SourceMapper({path.name: path for path in source_files})
        source_texts = {path.name: path.read_text(encoding="utf-8", errors="replace") for path in source_files}
        mapper.build(ast)

        hunter = AuditHunter(self.diagnostics)
        findings = hunter.scan(ast, source_texts)
        for finding in findings:
            breakdown = Scorer.score(finding)
            finding.confidence = breakdown.confidence
            finding.score = breakdown.score

        exporter = Exporter(self.config, self.diagnostics)
        report_path = exporter.write_report(findings, evidence={"compiler_version": version, "files": [str(path) for path in source_files]})
        exporter.write_summary(findings)
        exporter.write_diagnostics()

        self.diagnostics.add(
            "info",
            "orchestrator",
            "Audit completed successfully",
            report=str(report_path),
            total_findings=len(findings),
        )

        return [
            {
                "id": item.id,
                "category": item.category,
                "confidence": item.confidence,
                "score": item.score,
                "line": item.line,
            }
            for item in findings
        ]

    def _prepare_sources(self) -> list[Path]:
        selected: list[Path] = []
        if self.config.file:
            file_path = Path(self.config.file).expanduser().resolve()
            if file_path.is_file() and file_path.suffix.lower() == ".sol":
                selected.append(file_path)
        if self.config.directory:
            directory = Path(self.config.directory).expanduser().resolve()
            if directory.is_dir():
                for file_path in sorted(directory.rglob("*.sol")):
                    selected.append(file_path)
        return selected
