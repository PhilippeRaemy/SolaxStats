import re
from datetime import datetime, timedelta
import json
import os
from distutils.command.upload import upload
from turtledemo.sorting_animate import partition
from typing import List, Tuple

import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

import click
import requests
from numpy.ma.core import power
from pandas import DataFrame
from pyarrow.pandas_compat import dataframe_to_types

import solax_configure as cfg
import schemas
from clock_watch import clock_watch


@click.group()
@click.version_option()
def cli():
    """Handles solax inverter stats"""


@cli.group()
def extract():
    """Stats retrieval and basic aggregations"""


def login(url, proxies, user_name, encrypted_password) -> requests.Session:
    headers = {
        'Accept'            : 'application/json, text/plain, */*',
        'Accept-Encoding'   : 'gzip, deflate, br',
        'Accept-Language'   : 'en-US,en;q=0.9,fr;q=0.8',
        'Connection'        : 'keep-alive',
        'Content-Length'    : '81',
        'Content-Type'      : 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host'              : 'www.solaxcloud.com',
        'Origin'            : 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest'    : None,
        'Sec-Fetch-Mode'    : 'cors',
        'Sec-Fetch-Site'    : 'same-origin',
        'User-Agent'        : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang'              : 'en_US',
        'sec-ch-ua'         : '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile'  : '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    payload = {'username': user_name, 'userpwd': encrypted_password}

    session = requests.Session()
    response = session.post(url, headers=headers, data=payload)  # , proxies=proxies, verify=False)
    return session, (json_decode(response))


def json_decode(response):
    json_response = json.loads(response.content.decode('utf8'))
    return json_response


# Press the green button in the gutter to run the script.
def get_daily_data(session, token, url, date: datetime, proxies):
    payload = {
        'siteId': cfg.site_id,
        'time'  : date.strftime('%Y-%m-%d')
    }
    headers = {
        'Accept'            : 'application/json, text/plain, */*',
        'Accept-Encoding'   : 'gzip, deflate, br',
        'Accept-Language'   : 'en-US,en;q=0.9,fr;q=0.8',
        'Connection'        : 'keep-alive',
        'Content-Length'    : str(len(payload)),
        'Content-Type'      : 'application/x-www-form-urlencoded;charset=UTF-8',
        'Host'              : 'www.solaxcloud.com',
        'Origin'            : 'https://www.solaxcloud.com',
        'Sec-Fetch-Dest'    : 'empty',
        'Sec-Fetch-Mode'    : 'cors',
        'Sec-Fetch-Site'    : 'same-origin',
        'User-Agent'        : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'lang'              : 'en_US',
        'sec-ch-ua'         : '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile'  : '?0',
        'sec-ch-ua-platform': '"Windows"',
        'token'             : token,
        'version'           : 'blue',
    }
    # print(payload)
    # print(json.dumps(headers, indent=2))
    # print(len(payload))
    return session.post(url, headers=headers, data=payload)  # , proxies=proxies, verify=False)


@extract.command('history')
def extract_history():
    with clock_watch(print, f'Download history') as cw:
        # fiddler proxy
        http_proxy = "http://127.0.0.1:8888"
        https_proxy = "http://127.0.0.1:8888"

        proxies = {
            "http" : http_proxy,
            "https": https_proxy,
        }

        try:
            with open(cfg.local_file, 'r') as stats_file:
                stats = json.loads(stats_file.read())
        except Exception as ex:
            print(ex)
            stats = []

        solax_rawdata_folder = cfg.solax_rawdata_folder
        os.makedirs(cfg.solax_stats_folder, exist_ok=True)
        os.makedirs(solax_rawdata_folder, exist_ok=True)
        target_file = cfg.solax_stats_file
        target_file_pattern = cfg.re_json

        try:
            last_json_datetime = max(cfg.date_from_filename(fi)
                                     for fi in os.listdir(solax_rawdata_folder)
                                     if cfg.re_json.match(fi))
        except:
            last_json_datetime = datetime.strptime('2023-09-01', '%Y-%m-%d')

        session, session_response = login('https://www.solaxcloud.com/phoebus/login/loginNew', proxies,
                                          cfg.user_name, cfg.encrypted_password)
        while last_json_datetime < datetime.now():
            data = get_daily_data(session, session_response.get('token'),
                                  'https://www.solaxcloud.com/blue/phoebus/site/getSiteTotalPower',
                                  last_json_datetime, proxies
                                  )
            json_response = json_decode(data)

            json_file = os.path.join(solax_rawdata_folder, cfg.gen_json_d(last_json_datetime))
            with open(json_file, 'w') as fi:
                fi.write(json.dumps(json_response, indent=2))

            json_to_feather(json_file, json_response.get('object'))
            df: pd.DataFrame = pd.DataFrame(json_response.get('object'))

            last_json_datetime += timedelta(days=1)
            cw.print(f'Done {json_file}')
    _aggregate_all()


def json_to_feather(json_file, data=None):
    if not data:
        # print(f'read {json_file}')
        with open(json_file, 'r') as fi:
            data = json.loads(fi.read()).get('object')

    df: pd.DataFrame = pd.DataFrame(data)
    date_columns = ['year', 'month', 'day']
    timestamp_columns = date_columns + ['hour', 'minute']
    if [c for c in date_columns if c not in df.columns]:  # any timestamp column missing, happens in early files
        ma = cfg.target_file_pattern.match(json_file)
        for c in date_columns:
            df[c] = ma.groupdict[c]

    df['timestamp'] = pd.to_datetime(df[timestamp_columns])
    df['elapsed_time'] = df['timestamp'].diff().dt.total_seconds().fillna(300)
    for powerColumn in schemas.POWER_SCHEMA.power_columns:
        if powerColumn in df.columns:
            df[powerColumn + 'KWh'] = df[powerColumn] * df['elapsed_time'] / 3.6
        else:
            print("Missing column " + powerColumn)

    feather_file = json_file.replace('.json', '.feather')
    df.to_feather(feather_file)
    # print(f'wrote {feather_file}')


@extract.command('compress')
@click.option('--force', is_flag=True, default=False)
def compress(force):
    count = 0
    for fi in os.listdir(cfg.solax_rawdata_folder):
        if not cfg.re_json.match(fi):
            continue
        json_file = os.path.join(cfg.solax_rawdata_folder, fi)
        feather_file = json_file.replace('.json', '.feather')

        if not force and os.path.exists(feather_file):
            continue
        json_to_feather(json_file)

        count += 1

    print(f'compressed {count} json files into feather')


def concat_impl(dfs: List[pd.DataFrame], grouping: List[str]) -> pd.DataFrame:
    df = (pd.concat((d  # .dropna(axis=1)
                     for d in dfs
                     if not d.empty), ignore_index=True, verify_integrity=False)
          .groupby(grouping)
          .agg({'elapsed_time': 'sum', **{col: 'sum' for col in schemas.ENERGY_SCHEMA.energy_columns}}))
    for col in schemas.ENERGY_SCHEMA.power_columns:
        if col in df.columns:
            df[col] = df['col' + 'KWh'] / df['elapse_time'] * 3.6
    return df


# TODO: match granularities to the analysis granularities...

granularities = ['All', 'Hourly', 'Daily', 'Monthly']
partioning = ['None']  # , 'Monthly', 'Yearly']


@extract.command('aggregate-all')
def aggregate_all():
    _aggregate_all()


def _aggregate_all():
    with clock_watch(print, 'aggregate all') as cw:
        for partition in partioning:
            for granularity in granularities:
                if not (granularity == 'Yearly' and partition == 'Monthly'):
                    cw.print(f'{granularity} by {partition}')
                    _aggregate(granularity, partition)


@extract.command('aggregate')
@click.option('--granularity', '-f', help='Granularity of the aggregation', required=False, default='All',
              type=click.Choice(granularities, case_sensitive=False))
@click.option('--partition', '-f', help='Partitioning of the files', required=False, default='None',
              type=click.Choice(partioning, case_sensitive=False))
@click.option('--force', is_flag=True, default=False)
def aggregate(granularity, partition):
    return _aggregate(granularity, partition)


def _aggregate(granularity, partition):
    with clock_watch(print, f'Aggregating solax raw files by {granularity} ' +
                            ('into one  file' if partition == 'None' else f'in {partition} files.')) as cw:
        if partition == 'None':
            file_namer = cfg.gen_feather_a(granularity)
        elif partition == 'Yearly':
            file_namer = cfg.gen_feather_y(granularity)
        elif partition == 'Monthly':
            file_namer = cfg.gen_feather_m(granularity)
        else:
            raise ValueError(f'Invalid partition {partition}.')

        feather_file_pattern = re.compile(file_namer(None), re.IGNORECASE)

        folder = cfg.solax_stats_folder
        rawdata = cfg.solax_rawdata_folder
        files = os.listdir(rawdata)
        try:
            max_partition = max((fi for fi in files if feather_file_pattern.match(fi)))
        except ValueError:
            max_partition = ''

        if granularity == 'All':
            grouping = ['year', 'month', 'day', 'hour', 'minute']
        elif granularity == 'Hourly':
            grouping = ['year', 'month', 'day', 'hour']
        elif granularity == 'Daily':
            grouping = ['year', 'month', 'day']
        elif granularity == 'Monthly':
            grouping = ['year', 'month']
        elif granularity == 'Yearly':
            if partition == 'Monthly':
                raise ValueError(f'Cannot partition in {partition} for {granularity} granularity.')
            grouping = ['year']
        else:
            raise ValueError(f'Invalid  granularity {granularity}.')

        previous_partition = ''
        current_partition = ''
        dfs: List[pd.DataFrame] = []
        for fi in files:
            ma = cfg.re_feather_d.match(fi)
            if not ma:
                continue
            current_partition = file_namer(fi)
            if current_partition < max_partition:
                continue
            # print(f'read {fi}, current_partition:{current_partition}')
            if previous_partition and (current_partition != previous_partition):
                filename = os.path.join(folder, previous_partition)
                concat_impl(dfs, grouping).to_feather(filename)
                cw.print(f' > saved {filename}')
                dfs = []
            previous_partition = current_partition
            df = pd.read_feather(os.path.join(rawdata, fi))
            dfs.append(df)

        if current_partition:
            filename = os.path.join(folder, current_partition)
            concat_impl(dfs, grouping).to_feather(filename)
            cw.print(f' > saved {filename}')


if __name__ == '__main__':
    click.cli()
