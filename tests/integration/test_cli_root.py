import pytest
from click.testing import CliRunner

import solax


@pytest.mark.integration
def test_root_cli_lists_command_groups():
    runner = CliRunner()
    result = runner.invoke(solax.cli, ["--help"])

    assert result.exit_code == 0
    assert "configure" in result.output
    assert "extract" in result.output
    assert "analyse" in result.output
    assert "view" in result.output

