# SPDX-License-Identifier: MIT

from pathlib import Path

from wizard_audit.config import load_config


def test_config_precedence_cli_over_env_over_file(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("output: from-file\ndeep: false\n", encoding="utf-8")
    loaded = load_config(config, environ={"WIZARD_OUTPUT": "from-env", "WIZARD_DEEP": "true"}, cli_overrides={"output": "from-cli"})
    assert loaded.output == "from-cli"
    assert loaded.deep is True
