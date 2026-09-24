# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostics
from .models import AuditConfig, Finding


class Exporter:
    """Stable JSON export for audit artifacts."""

    def __init__(self, config: AuditConfig, diagnostics: Diagnostics) -> None:
        self.config = config
        self.diagnostics = diagnostics
        self.outdir = Path(config.output).resolve()
        self.outdir.mkdir(parents=True, exist_ok=True)

    def write_report(self, findings: list[Finding], *, evidence: dict[str, Any] | None = None) -> Path:
        payload = {
            "tool": "wizard-audit",
            "version": "0.1.0",
            "schema_version": 1,
            "correlation_id": self.diagnostics.correlation_id,
            "findings": [
                {
                    "id": item.id,
                    "category": item.category,
                    "title": item.title,
                    "contract": item.contract,
                    "function": item.function,
                    "line": item.line,
                    "confidence": item.confidence,
                    "score": item.score,
                    "description": item.description,
                    "evidence": [
                        {
                            "kind": ev.kind,
                            "source": ev.source,
                            "location": ev.location,
                            "detail": ev.detail,
                        }
                        for ev in item.evidence
                    ],
                    "state_vars": item.state_vars,
                    "sources": item.sources,
                }
                for item in findings
            ],
            "evidence": evidence or {},
        }
        report_path = self.outdir / "findings.json"
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return report_path

    def write_summary(self, findings: list[Finding]) -> Path:
        summary = {
            "total_findings": len(findings),
            "by_category": {},
        }
        for finding in findings:
            summary["by_category"][finding.category] = summary["by_category"].get(finding.category, 0) + 1
        path = self.outdir / "summary.json"
        path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_diagnostics(self) -> Path:
        path = self.outdir / "diagnostics.json"
        path.write_text(self.diagnostics.to_json(), encoding="utf-8")
        return path
