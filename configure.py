import click

@click.group()
@click.version_option()
def cli():
    """Handles solax inverter stats"""

@cli.group()
def configure():
    pass

@configure()
def show():
    print('not implemented yet')


@configure()
def edit():
    print('not implemented yet')

