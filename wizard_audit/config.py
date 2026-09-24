# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import AuditConfig
from .validation import validate_address, validate_solc_version, validate_url

_FIELDS = {
    "file", "directory", "output", "deep", "generate_poc", "format", "strict",
    "solc_version", "rpc", "rpc_fork", "capital_source", "fork_block",
    "config_path", "correlation_id", "workspace_root",
}
_ENV_PREFIX = "WIZARD_"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")
    return {str(key): value for key, value in data.items() if str(key) in _FIELDS}


def load_config(
    config_path: str | Path | None = None,
    *,
    cli_overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> AuditConfig:
    """Load config with explicit precedence: CLI, environment, then YAML defaults."""
    selected = Path(config_path).expanduser() if config_path else Path("config/default.yaml")
    values: dict[str, Any] = _load_file(selected) if selected.is_file() else {}
    env = environ if environ is not None else os.environ
    for key in _FIELDS:
        env_key = _ENV_PREFIX + key.upper()
        if env_key in env:
            values[key] = env[env_key]
    for key, value in (cli_overrides or {}).items():
        if key in _FIELDS and value is not None:
            values[key] = value

    for key in {"deep", "generate_poc", "strict"}:
        if key in values:
            values[key] = _as_bool(values[key])
    if values.get("fork_block") is not None:
        values["fork_block"] = int(values["fork_block"])
    if values.get("solc_version"):
        values["solc_version"] = validate_solc_version(str(values["solc_version"]))
    if values.get("rpc"):
        values["rpc"] = validate_url(str(values["rpc"]))
    if values.get("rpc_fork"):
        values["rpc_fork"] = validate_url(str(values["rpc_fork"]))
    if values.get("address"):
        values["address"] = validate_address(str(values["address"]))
    values["config_path"] = str(selected) if selected.is_file() else values.get("config_path")
    return AuditConfig(**{key: value for key, value in values.items() if key in _FIELDS})
