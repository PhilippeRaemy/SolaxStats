from click.testing import CliRunner
from solax_extract import extract


def test_extract():
    runner = CliRunner()
    result = runner.invoke(extract, ['--help'])
    assert result.exit_code == 0
    assert 'history' in result.output
    assert 'aggregate' in result.output
