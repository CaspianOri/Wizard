# Architecture and security boundaries

## Runtime modes

The repository now treats audit/reporting as the production workflow. The
historical `weaponized_poc_generator.py` name is retained only as a compatible
entry point and delegates to `wizard_audit.cli`. It does not generate or run
exploit templates.

- **Audit mode (default):** compile, map source locations, run conservative
  static rules, score findings deterministically, and write JSON evidence.
- **PoC mode:** intentionally not coupled to audit execution. A finding is not
  promoted to an exploit artifact merely because it is high confidence. Any
  future implementation must be a separate, explicit command with validation,
  approval, and independent tests.

## Module boundaries

- `Compiler`: bounded external compiler invocation and JSON loading.
- `SourceMapper`: deterministic `start:length:sourceIndex` mapping.
- `AuditHunter`: conservative evidence-based rules.
- `Scorer`: deterministic confidence and score calculation.
- `Exporter`: versioned, stable JSON artifacts.
- `Diagnostics`: structured events with correlation IDs.
- `config`: YAML baseline, `WIZARD_*` overrides, then CLI overrides.

External analyzers are optional evidence sources, never ground truth. Missing
Slither/Mythril/solc must produce diagnostics and a controlled failure or
explicit degraded result; they must not silently change the report.

## Security boundaries

- User paths must be resolved and constrained before use.
- External tools run with a bounded timeout and a reduced environment.
- Tool output is treated as untrusted data and parsed as JSON only when
  requested.
- Secrets are not accepted as source content or persisted by the audit
  exporter. RPC URLs should be supplied through environment/configuration and
  must not be included in diagnostic messages when they contain credentials.
- Generated output is never executed automatically.

This tool is for authorized code review and security research only. It is not
an exploit viability oracle, symbolic executor, or substitute for a manual
audit.

## Test strategy

1. **Unit:** source offsets, source-index resolution, path containment,
   compiler-version validation, URL/address validation, deterministic scoring,
   config precedence, and JSON serialization.
2. **Integration:** vulnerable and safe corpus contracts, stable findings and
   diagnostics, missing optional tools, compiler failure, and audit-only
   output invariants.
3. **Regression:** snapshot normalized JSON (excluding timestamps and
   correlation IDs), track false positives on the safe corpus, and require
   explicit review for rule changes.

Recommended commands:

```bash
pytest
python weaponized_poc_generator.py --help
```
