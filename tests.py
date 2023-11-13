from click.testing import CliRunner
from main import extract

def test_extract():
  runner = CliRunner()
  result = runner.invoke(extract)
  assert result.exit_code == 0
