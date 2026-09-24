# SPDX-License-Identifier: MIT

from pathlib import Path

from wizard_audit.config import load_config


def test_default_config_is_audit_only() -> None:
    config = load_config(Path("config/default.yaml"), environ={}, cli_overrides={})
    assert config.generate_poc is False


def test_cli_overrides_environment(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("output: file-output\n", encoding="utf-8")
    config = load_config(
        config_file,
        environ={"WIZARD_OUTPUT": "env-output"},
        cli_overrides={"output": "cli-output"},
    )
    assert config.output == "cli-output"
