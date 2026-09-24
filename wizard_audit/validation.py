# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

SOLC_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_file_path(raw_path: str | None, *, must_exist: bool = True) -> Path | None:
    if raw_path is None:
        return None
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"Path does not exist: {candidate}")
    return candidate


def ensure_within_root(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    root_resolved = root.resolve(strict=False)
    common = os.path.commonpath([str(root_resolved), str(resolved)])
    if common != str(root_resolved):
        raise ValueError(f"Path escapes root: {path}")
    return resolved


def validate_solc_version(version: str | None) -> str | None:
    if version is None:
        return None
    normalized = version.strip()
    if not SOLC_VERSION_RE.fullmatch(normalized):
        raise ValueError(f"Invalid solc version format: {version!r}")
    return normalized


def validate_address(value: str | None) -> str | None:
    if value is None:
        return None
    if not ADDRESS_RE.fullmatch(value):
        raise ValueError(f"Invalid Ethereum address: {value!r}")
    return value.lower()


def validate_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid HTTP(S) URL: {value!r}")
    return value
