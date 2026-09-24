# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import logging
from typing import Sequence

from .config import load_config
from .diagnostics import Diagnostics
from .orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit-first Solidity security analysis tool")
    parser.add_argument("-f", "--file")
    parser.add_argument("-d", "--dir", dest="directory")
    parser.add_argument("-o", "--output")
    parser.add_argument("--deep", action="store_true", default=None)
    parser.add_argument("--generate-poc", action="store_true", default=None)
    parser.add_argument("--solc-version")
    parser.add_argument("--rpc")
    parser.add_argument("--rpc-fork")
    parser.add_argument("--strict", action="store_true", default=None)
    parser.add_argument("--workspace-root")
    parser.add_argument("--correlation-id")
    parser.add_argument("--config")
    return parser


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    diagnostics = Diagnostics(args.correlation_id)
    try:
        overrides = vars(args).copy()
        config_file = overrides.pop("config", None)
        config = load_config(config_file, cli_overrides=overrides)
        if config.generate_poc:
            diagnostics.add("info", "cli", "PoC generation explicitly requested")
        results = Orchestrator(config, diagnostics).run()
        print(json.dumps({"status": "ok", "results": results}, indent=2, sort_keys=True))
        return 0
    except (FileNotFoundError, PermissionError, ValueError, RuntimeError) as exc:
        diagnostics.add("error", "cli", str(exc))
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
