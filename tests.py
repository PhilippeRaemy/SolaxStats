from click.testing import CliRunner
from solax_extract import extract

def test_extract():
  runner = CliRunner()
  result = runner.invoke(extract)
  assert result.exit_code == 0
  print(result.output)
