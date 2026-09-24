#!/usr/bin/env python3
"""Compatibility entry point for the production audit workflow.

Despite the historical filename, this entry point is intentionally audit-only.
It delegates to :mod:`wizard_audit.cli`; it never creates, executes, or
validates exploit payloads. PoC generation remains a separate future workflow
requiring an explicit, reviewed implementation.
"""

from __future__ import annotations

from wizard_audit.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
