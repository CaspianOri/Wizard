# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Sequence

from .diagnostics import Diagnostics
from .models import AuditConfig
from .orchestrator import Orchestrator
from .validation import validate_address, validate_file_path, validate_solc_version, validate_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit-first Solidity security analysis tool")
    parser.add_argument("-f", "--file", help="Single Solidity file to audit")
    parser.add_argument("-d", "--dir", help="Directory containing Solidity sources")
    parser.add_argument("-o", "--output", default="./audit-output", help="Output directory")
    parser.add_argument("--deep", action="store_true", help="Enable deeper audit heuristics")
    parser.add_argument("--generate-poc", action="store_true", help="Explicitly enable PoC generation; default is audit-only")
    parser.add_argument("--solc-version", help="Preferred solc version, e.g. 0.8.20")
    parser.add_argument("--rpc", help="RPC URL used for on-chain evidence gathering")
    parser.add_argument("--rpc-fork", help="Fork RPC URL")
    parser.add_argument("--address", help="Contract address to audit")
    parser.add_argument("--strict", action="store_true", help="Fail if findings are present")
    parser.add_argument("--config", help="Path to YAML or TOML config")
    return parser


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    correlation_id = os.environ.get("WIZARD_CORRELATION_ID") or None
    diagnostics = Diagnostics(correlation_id)

    try:
        file_path = validate_file_path(args.file) if args.file else None
        directory_path = validate_file_path(args.dir) if args.dir else None
        validate_solc_version(args.solc_version)
        validate_url(args.rpc)
        validate_url(args.rpc_fork)
        validate_address(args.address)

        config = AuditConfig(
            file=str(file_path) if file_path else None,
            directory=str(directory_path) if directory_path else None,
            output=args.output,
            deep=args.deep,
            generate_poc=args.generate_poc,
            strict=args.strict,
            solc_version=args.solc_version,
            rpc=args.rpc,
            rpc_fork=args.rpc_fork,
            capital_source="funded",
            fork_block=None,
            config_path=args.config,
            correlation_id=correlation_id,
            workspace_root=".",
        )

        if args.generate_poc:
            diagnostics.add("info", "cli", "PoC generation explicitly requested; audit-only default remains in effect unless this flag is set")

        orchestrator = Orchestrator(config, diagnostics)
        results = orchestrator.run()
        print(json.dumps({"status": "ok", "results": results}, indent=2, sort_keys=True))
        return 0
    except (FileNotFoundError, PermissionError, ValueError, RuntimeError) as exc:
        diagnostics.add("error", "cli", str(exc), input_file=args.file, directory=args.dir)
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
