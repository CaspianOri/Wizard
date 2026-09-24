# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostics
from .validation import validate_file_path, validate_solc_version


class ToolRunner:
    """Safe tool runner with timeout and bounded environment."""

    def __init__(self, diagnostics: Diagnostics, *, sandbox: bool = True) -> None:
        self.diagnostics = diagnostics
        self.sandbox = sandbox

    def run(
        self,
        cmd: list[str],
        *,
        timeout: int = 300,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        expect_json: bool = False,
        allow_empty: bool = False,
    ) -> tuple[int, str, str]:
        safe_env = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "HOME", "TMPDIR", "USER", "SHELL"}
        }
        if env:
            safe_env.update(env)

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            message = f"Command not found: {cmd[0]}"
            self.diagnostics.add("error", "tool_runner", message, command=cmd, timeout=timeout)
            raise RuntimeError(message) from exc
        except subprocess.TimeoutExpired as exc:
            message = f"Command timed out after {timeout}s: {' '.join(cmd)}"
            self.diagnostics.add("error", "tool_runner", message, command=cmd, timeout=timeout)
            raise RuntimeError(message) from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        if completed.returncode != 0 and not stdout and not allow_empty:
            message = f"Command exited with rc={completed.returncode}: {' '.join(cmd)}"
            self.diagnostics.add("error", "tool_runner", message, command=cmd, stderr=stderr[:2000])
            raise RuntimeError(message)

        if expect_json and stdout.strip():
            try:
                json.loads(stdout)
            except json.JSONDecodeError as exc:
                message = f"Tool output was not valid JSON: {cmd[0]}"
                self.diagnostics.add(
                    "error",
                    "tool_runner",
                    message,
                    command=cmd,
                    stdout=stdout[:2000],
                    stderr=stderr[:2000],
                )
                raise RuntimeError(message) from exc

        return completed.returncode, stdout, stderr


class Compiler:
    """Wrapper around the Solidity compiler with strict validation."""

    PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);")

    def __init__(self, diagnostics: Diagnostics, workspace_root: Path) -> None:
        self.diagnostics = diagnostics
        self.workspace_root = workspace_root
        self.compiler_path: str | None = None
        self.version: str | None = None

    def detect_pragma(self, files: list[Path]) -> str:
        discovered: list[str] = []
        for source in files:
            try:
                content = source.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self.diagnostics.add("warning", "compiler", f"Unable to read source {source}", path=str(source), error=str(exc))
                continue
            for match in self.PRAGMA_RE.finditer(content):
                discovered.append(match.group(1).strip())

        if not discovered:
            self.diagnostics.add("warning", "compiler", "No pragma discovered; defaulting to 0.8.20")
            return "0.8.20"

        candidates: list[str] = []
        for value in discovered:
            match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
            if match:
                candidates.append(".".join(match.groups()))

        if not candidates:
            self.diagnostics.add("warning", "compiler", f"Unparsed pragma values: {discovered}")
            return "0.8.20"

        return max(candidates, key=lambda item: tuple(int(part) for part in item.split(".")))

    def ensure_compiler(self, version: str | None) -> str:
        normalized = validate_solc_version(version) if version is not None else "0.8.20"
        solc_path = shutil.which("solc")
        if solc_path is None:
            raise RuntimeError("solc not installed or not reachable from PATH")
        self.version = normalized
        self.compiler_path = solc_path
        self.diagnostics.add("info", "compiler", f"Using compiler at {solc_path} with version {normalized}")
        return solc_path

    def compile(self, file_paths: list[Path]) -> dict[str, Any]:
        if self.compiler_path is None:
            raise RuntimeError("Compiler was not initialized")

        command = [self.compiler_path, "--ast-json", "--base-path", str(self.workspace_root)]
        for path in file_paths:
            command.append(str(path))

        runner = ToolRunner(self.diagnostics, sandbox=True)
        rc, stdout, stderr = runner.run(command, timeout=300, cwd=self.workspace_root, expect_json=True)
        if rc != 0:
            raise RuntimeError(stderr or stdout or "solc compile failed")

        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            self.diagnostics.add("error", "compiler", "Compiler returned invalid JSON", stderr=stderr[:2000])
            raise RuntimeError("Compiler returned invalid JSON") from exc
        return payload
