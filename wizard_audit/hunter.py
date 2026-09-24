# SPDX-License-Identifier: MIT

from __future__ import annotations

import re
from typing import Any

from .diagnostics import Diagnostics
from .models import Evidence, Finding


class AuditHunter:
    """Deterministic rules for likely Solidity issues."""

    def __init__(self, diagnostics: Diagnostics) -> None:
        self.diagnostics = diagnostics

    def scan(self, ast: dict[str, Any], source_texts: dict[str, str]) -> list[Finding]:
        findings: list[Finding] = []
        for node in self._iter_nodes(ast):
            if node.get("nodeType") != "ContractDefinition":
                continue
            contract_name = str(node.get("name", "<anonymous>"))
            for child in node.get("nodes", []):
                if child.get("nodeType") != "FunctionDefinition":
                    continue
                function_name = str(child.get("name", "fallback"))
                function_src = child.get("src")
                if not isinstance(function_src, str):
                    continue
                line_number = self._estimate_line(function_src, source_texts)
                details = self._extract_function_details(child)
                if details["writes_state"] and self._has_guard(details["modifiers"]):
                    continue
                if self._looks_like_reentrancy(details):
                    findings.append(
                        Finding(
                            id=f"reentrancy_{contract_name}_{function_name}",
                            category="reentrancy",
                            title="State-changing external call before settlement",
                            contract=contract_name,
                            function=function_name,
                            line=line_number,
                            confidence="medium",
                            score=5,
                            description="Public or external function performs an external call before state settlement.",
                            evidence=[
                                Evidence(
                                    kind="ast",
                                    source="compiler",
                                    location=f"{contract_name}.{function_name}",
                                    detail={"src": function_src, "nodeType": "FunctionDefinition"},
                                )
                            ],
                            state_vars=details["writes_state"],
                            sources=["ast"],
                        )
                    )
        return findings

    def _looks_like_reentrancy(self, details: dict[str, Any]) -> bool:
        writes = set(details["writes_state"])
        calls = details["external_calls"]
        if not writes:
            return False
        if not calls:
            return False
        return True

    def _has_guard(self, modifiers: list[str]) -> bool:
        guard_names = {"onlyOwner", "onlyRole", "onlyAdmin", "nonReentrant", "whenNotPaused"}
        return any(name in guard_names for name in modifiers)

    @staticmethod
    def _extract_function_details(node: dict[str, Any]) -> dict[str, Any]:
        writes_state: list[str] = []
        external_calls: list[str] = []
        modifiers: list[str] = []

        for modifier in node.get("modifiers", []):
            name = modifier.get("modifierName", {}).get("name")
            if name:
                modifiers.append(name)

        for child in AuditHunter._iter_nodes(node):
            if child.get("nodeType") == "Identifier":
                name = child.get("name")
                if name and re.search(r"(?:owner|admin|balance|totalSupply)", name, re.IGNORECASE):
                    if child.get("referencedDeclaration") is not None:
                        writes_state.append(name)
            if child.get("nodeType") == "FunctionCall":
                expression = child.get("expression") or {}
                call_name = expression.get("name") or expression.get("memberName")
                if call_name:
                    external_calls.append(call_name)

        return {
            "writes_state": sorted(set(writes_state)),
            "external_calls": external_calls,
            "modifiers": modifiers,
        }

    @staticmethod
    def _estimate_line(src: str, source_texts: dict[str, str]) -> int:
        try:
            start_offset = int(src.split(":")[0])
        except (IndexError, ValueError):
            return 1
        for text in source_texts.values():
            cursor = 0
            for line_number, line in enumerate(text.splitlines(), start=1):
                cursor += len(line) + 1
                if cursor >= start_offset:
                    return line_number
        return 1

    @staticmethod
    def _iter_nodes(node: object):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from AuditHunter._iter_nodes(value)
        elif isinstance(node, list):
            for item in node:
                yield from AuditHunter._iter_nodes(item)
