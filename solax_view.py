import tempfile
import webbrowser

import click
import pandas as pd


@click.group()
@click.version_option()
def cli():
    """analyse the data"""


@cli.group()
def view():
    """Various analysis functions"""


@view.command("file")
@click.argument('filename', required=True, type=str)
def feather_view(filename):
    if not len(filename) >= 8 or not filename[-8:] == '.feather':
        raise ValueError(f'The filename is expected to have a `.feather` extension. Found {filename[-8:]}.')
    df = pd.read_feather(filename)
    # Convert DataFrame to HTML
    html_string = df.to_html()

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
        temp_file.write(html_string.encode())

    # Open the temporary file in the default browser
    webbrowser.open(temp_file.name)
