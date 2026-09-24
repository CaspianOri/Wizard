# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostics
from .models import AuditConfig, Evidence, Finding


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    score: int
    confidence: str
    rationale: str


class Scorer:
    """Deterministic confidence scoring for findings."""

    @staticmethod
    def score(finding: Finding) -> ScoreBreakdown:
        score = 0
        rationale: list[str] = []

        if "ast" in finding.sources:
            score += 2
            rationale.append("AST evidence")
        if "slither" in finding.sources:
            score += 3
            rationale.append("external analyzer")
        if finding.state_vars:
            score += 2
            rationale.append("state variable correlation")
        if finding.function and finding.line > 0:
            score += 1
            rationale.append("source mapping present")
        if finding.category in {"reentrancy", "access_control"}:
            score += 1
            rationale.append("high-risk category")

        if score >= 7:
            confidence = "high"
        elif score >= 4:
            confidence = "medium"
        else:
            confidence = "low"

        return ScoreBreakdown(score=score, confidence=confidence, rationale=", ".join(rationale))
