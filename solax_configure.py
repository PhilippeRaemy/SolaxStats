import copy
import json
import os
import re
import sys
from datetime import datetime

import click

file_segments = []
dated_file_pattern = re.compile('.*\.(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)\..*$')

SECRET_KEYS = {
    'user_name',
    'site_password',
    'config_password',
    'encrypted_password',
    'api_token',
}


def date_from_filename(filename):
    if isinstance(filename, datetime):
        return filename
    ma = dated_file_pattern.match(filename)
    if ma:
        di = ma.groupdict()
        return datetime(int(di['year']), int(di['month']), int(di['day']))
    return datetime(1900, 1, 1)


def gen_json_d(filename):
    return '.'.join(file_segments + [date_from_filename(filename).strftime('%Y-%m-%d'), 'json'])


def gen_feather_d(filename):
    return '.'.join(file_segments + [date_from_filename(filename).strftime('%Y-%m-%d'), 'feather'])


def gen_feather_m(granularity):
    def namer(filename):
        if filename:
            return '.'.join(file_segments + [granularity, date_from_filename(filename).strftime('%Y-%m'), 'feather'])
        return '\\.'.join(file_segments + [granularity, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)', 'feather'])

    return namer


def gen_feather_y(granularity):
    def namer(filename):
        if filename:
            return '.'.join(file_segments + [granularity, date_from_filename(filename).strftime('%Y'), 'feather'])
        return '\\.'.join(file_segments + [granularity, r'(?P<yyyy>\d{4})', 'feather'])

    return namer


def gen_feather_a(granularity):
    def namer(filename):
        if filename:
            return '.'.join(file_segments + [granularity, 'feather'])
        return '\\.'.join(file_segments + [granularity, 'feather'])

    return namer


def read_json_file(file_path):
    if not file_path or not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf8') as fi:
        content = fi.read().strip()
        return json.loads(content) if content else {}


def write_json_file(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf8') as fi:
        json.dump(data, fi, indent=2)


def save_public_config(updates):
    local_file = getattr(sys.modules[__name__], 'local_file', None)
    if not local_file:
        raise ValueError('Cannot save public config before read_config initialization.')

    filtered = {k: v for k, v in updates.items() if v is not None and k not in SECRET_KEYS}
    if not filtered:
        return

    current = read_json_file(local_file)
    current.update(filtered)
    write_json_file(local_file, current)

    _config.update(filtered)
    this_module = sys.modules[__name__]
    for k, v in filtered.items():
        setattr(this_module, k, v)


def save_secret_config(updates):
    local_secrets_file = getattr(sys.modules[__name__], 'local_secrets_file', None)
    if not local_secrets_file:
        raise ValueError('Cannot save secret config before read_config initialization.')

    filtered = {k: v for k, v in updates.items() if v is not None and k in SECRET_KEYS}
    if not filtered:
        return

    current = read_json_file(local_secrets_file)
    current.update(filtered)
    write_json_file(local_secrets_file, current)

    _config.update(filtered)
    this_module = sys.modules[__name__]
    for k, v in filtered.items():
        setattr(this_module, k, v)


def migrate_secrets_from_public(local_file, local_secrets_file):
    public_cfg = read_json_file(local_file)
    if not public_cfg:
        return {}

    secret_updates = {k: public_cfg.get(k) for k in SECRET_KEYS if public_cfg.get(k) is not None}
    if not secret_updates:
        return {}

    existing_secrets = read_json_file(local_secrets_file)
    merged_secrets = {**existing_secrets, **secret_updates}
    write_json_file(local_secrets_file, merged_secrets)

    for key in SECRET_KEYS:
        if key in public_cfg:
            del public_cfg[key]
    write_json_file(local_file, public_cfg)
    return secret_updates


def read_config():
    solax_stats_folder = os.environ.get('SOLAX_STATS_FOLDER', os.path.dirname(__file__))
    solax_stats_file = os.environ.get('SOLAX_STATS_FILE', 'solax.json')
    solax_secrets_file = os.environ.get('SOLAX_SECRETS_FILE', 'solax_secrets.json')

    def insert_re(segments, *args) -> re:
        return re.compile('.'.join(segments + list(args)))

    local_file = os.path.join(solax_stats_folder, solax_stats_file)

    config = {
        'user_name'           : os.environ.get('SOLAX_USER_NAME', os.environ.get('USER_NAME')),
        'site_password'       : os.environ.get('SOLAX_SITE_PASSWORD', os.environ.get('SITE_PASSWORD')),
        'config_password'     : os.environ.get('CONFIG_PASSWORD'),
        'encrypted_password'  : os.environ.get('SOLAX_ENCRYPTED_PASSWORD', os.environ.get('ENCRYPTED_PASSWORD')),
        'auth_mode'           : os.environ.get('SOLAX_AUTH_MODE', 'auto'),
        'api_token'           : os.environ.get('SOLAX_API_TOKEN'),
        'solax_login_url'     : os.environ.get('SOLAX_LOGIN_URL', 'https://global.solaxcloud.com/#/login'),
        'site_id'             : os.environ.get('SITE_ID'),
        'solax_stats_folder'  : solax_stats_folder,
        'solax_stats_file'    : solax_stats_file,
        'solax_secrets_file'  : solax_secrets_file,
        'target_file_pattern' : re.compile('.*(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d).json$'),
        'local_file'          : local_file,
        'local_secrets_file'  : os.path.join(solax_stats_folder, solax_secrets_file),
        're_json'             : None,
        're_feather_d'        : None,
        # 're_feather_m'       : insert_re(file_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)', 'feather'),
        # 're_feather_y'       : insert_re(file_segments, r'(?P<yyyy>\d{4})', 'feather'),
        # 're_feather_a'       : insert_re(file_segments, 'feather'),
        'file_segments'       : []
    }

    indirections = 5
    while --indirections:
        if os.path.exists(local_file):
            config = {**config, **read_json_file(local_file)}
        configured = os.path.join(config['solax_stats_folder'], config['solax_stats_file'])
        configured_secrets = os.path.join(config['solax_stats_folder'], config.get('solax_secrets_file', solax_secrets_file))
        if local_file == configured:
            break
        local_file = configured
        config['local_secrets_file'] = configured_secrets

    config['local_file'] = local_file
    config['local_secrets_file'] = os.path.join(config['solax_stats_folder'], config['solax_secrets_file'])

    # Migrate old secrets accidentally stored in the public config file.
    migrated_secrets = migrate_secrets_from_public(config['local_file'], config['local_secrets_file'])

    # Merge secrets file on top of public config.
    config = {**config, **read_json_file(config['local_secrets_file'])}
    config = {**config, **migrated_secrets}

    final_segments = config['solax_stats_file'].split('.')[:-1]
    config['file_segments'] = final_segments
    config['re_json'] = insert_re(final_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d)', 'json')
    config['re_feather_d'] = insert_re(final_segments, r'(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d)', 'feather')

    # post-read settings
    config['solax_rawdata_folder']= os.path.join(config['solax_stats_folder'], 'rawdata')

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
        if 'password' in k or 'token' in k:
            cfg[k] = '******'
    print(json.dumps(cfg, indent=2, default=str))


@configure.command("edit")
def edit():
    print('not implemented yet')
