import copy
import json
import os
import re
import sys

import click


def read_config():
    solax_stats_folder = os.environ.get('SOLAX_STATS_FOLDER', os.path.dirname(__file__))
    solax_stats_file = os.environ.get('SOLAX_STATS_FILE', 'solax.json')

    local_file = os.path.join(solax_stats_folder, solax_stats_file)
    config = {
        'user_name': os.environ.get('USER_NAME'),
        'site_password': os.environ.get('SITE_PASSWORD'),
        'config_password': os.environ.get('CONFIG_PASSWORD'),
        'encrypted_password': os.environ.get('ENCRYPTED_PASSWORD'),
        'site_id': os.environ.get('SITE_ID'),
        'solax_stats_folder': solax_stats_folder,
        'solax_stats_file': solax_stats_file,
        'target_file_pattern': re.compile('.*(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d).json$'),
        'local_file': local_file
    }


    indirections=5
    while --indirections:
        if os.path.exists(local_file):
            with open(local_file, 'r') as cgf:
                config = {**config, **json.loads(cgf.read())}
        configured = os.path.join(config['solax_stats_folder'], config['solax_stats_file'])
        if local_file == configured:
            break
        local_file = configured

    this_module = sys.modules[__name__]
    for k, v in config.items():
        setattr(this_module, k, v)

    return config


_config = read_config()


@click.group()
@click.version_option()
def cli():
    """Handles solax inverter stats"""


@cli.group()
def configure():
    """configure connectivity"""


def get_config():
    return _config


@configure.command("show")
def show():
    cfg = copy.deepcopy(_config)
    for k in cfg.keys():
        if 'password' in k:
            cfg[k] = '******'
    print(json.dumps(cfg, indent=2, default=str))


@configure.command("edit")
def edit():
    print('not implemented yet')
