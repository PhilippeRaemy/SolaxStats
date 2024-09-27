import click

@click.group()
@click.version_option()
def cli():
    """Handles solax inverter stats"""

@cli.group()
def configure():
    """configure connectivity"""

@configure.command("show")
def show():
    print('not implemented yet')


@configure.command("edit")
def edit():
    print('not implemented yet')

