import click

import solax_extract

@click.group()
def cli():
    pass

cli.add_command(solax_extract.extract)
