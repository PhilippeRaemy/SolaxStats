import click

import solax_extract
# import configure

@click.group()
def cli():
    pass

cli.add_command(solax_extract.extract)
# cli.add_command(configure.configure)
