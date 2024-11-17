import click

import solax_extract
import solax_configure
import solax_analyse
import solax_view


@click.group()
def cli():
    pass


cli.add_command(solax_configure.configure)
cli.add_command(solax_extract.extract)
cli.add_command(solax_analyse.analyse)
cli.add_command(solax_view.view)

if __name__ == '__main__':
    cli()
