import copy
import json
import os
import re
import sys
from datetime import datetime

import click

file_segments = []
dated_file_pattern: re.compile('.*\.(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)\..*$')


def date_from_filename(filename):
    ma = dated_file_pattern.match(filename)
    if ma:
        di = ma.groupdict()
        return datetime(int(di['year']), int(di['month']), int(di['day']))
    return datetime(1900, 1, 1)


def gen_json_d(filename):
    return '.'.join(file_segments, [date_from_filename(filename).strftime('%Y-%m-%d'), 'json']),


def gen_feather_d(filename):
    return '.'.join(file_segments, [date_from_filename(filename).strftime('%Y-%m-%d'), 'feather']),


def gen_feather_m(filename):
    return '.'.join(file_segments, [date_from_filename(filename).strftime('%Y-%m'), 'feather']),


def gen_feather_y(filename):
    return '.'.join(file_segments, [date_from_filename(filename).strftime('%Y'), 'feather']),


def gen_feather_a(filename):
    return '.'.join(file_segments, ['feather'])


def read_config():
    solax_stats_folder = os.environ.get('SOLAX_STATS_FOLDER', os.path.dirname(__file__))
    solax_stats_file = os.environ.get('SOLAX_STATS_FILE', 'solax.json')

    def insert_re(segments, *args) -> re:
        return re.compile('.'.join(segments + args))

    local_file = os.path.join(solax_stats_folder, solax_stats_file)
    file_segments = solax_stats_file.split('.')[:-1]

    config = {
        'user_name'          : os.environ.get('USER_NAME'),
        'site_password'      : os.environ.get('SITE_PASSWORD'),
        'config_password'    : os.environ.get('CONFIG_PASSWORD'),
        'encrypted_password' : os.environ.get('ENCRYPTED_PASSWORD'),
        'site_id'            : os.environ.get('SITE_ID'),
        'solax_stats_folder' : solax_stats_folder,
        'solax_stats_file'   : solax_stats_file,
        'target_file_pattern': re.compile('.*(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d).json$'),
        'local_file'         : local_file,
        're_json'            : insert_re(file_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d)', 'json'),
        're_feather_d'       : insert_re(file_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d)', 'feather'),
        're_feather_m'       : insert_re(file_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)', 'feather'),
        're_feather_y'       : insert_re(file_segments, r'(?P<yyyy>\d{4})', 'feather'),
        're_feather_a'       : insert_re(file_segments, 'feather'),
        'file_segments'      : file_segments
    }

    indirections = 5
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
