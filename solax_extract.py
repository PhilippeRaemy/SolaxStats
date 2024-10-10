import re
from datetime import datetime, timedelta
import json
import os
from distutils.command.upload import upload
from turtledemo.sorting_animate import partition
from typing import List, Tuple

import pandas as pd

import click
import requests
from numpy.ma.core import power
from pandas import DataFrame
from pyarrow.pandas_compat import dataframe_to_types

import configure
import schemas


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
    print(json.dumps(json_response, indent=2))
    return json_response


# Press the green button in the gutter to run the script.
def get_daily_data(session, token, url, date: datetime, proxies):
    payload = {
        'siteId': configure.site_id,
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
    print(payload)
    print(json.dumps(headers, indent=2))
    print(len(payload))
    return session.post(url, headers=headers, data=payload)  # , proxies=proxies, verify=False)


@extract.command('history')
def history():
    # fiddler proxy
    http_proxy = "http://127.0.0.1:8888"
    https_proxy = "http://127.0.0.1:8888"

    proxies = {
        "http" : http_proxy,
        "https": https_proxy,
    }

    try:
        with open(configure.local_file, 'r') as stats_file:
            stats = json.loads(stats_file.read())
    except Exception as ex:
        print(ex)
        stats = []

    solax_stats_folder = configure.solax_stats_folder
    os.makedirs(solax_stats_folder, exist_ok=True)
    target_file = configure.solax_stats_file
    target_file_pattern = configure.re_json

    try:
        last_json_datetime = max(configure.date_from_filename(fi)
                                 for fi in os.listdir(solax_stats_folder)
                                 if configure.re_json.match(fi))
    except:
        last_json_datetime = datetime.strptime('2023-09-01', '%Y-%m-%d')

    session, session_response = login('https://www.solaxcloud.com/phoebus/login/loginNew', proxies,
                                      configure.user_name, configure.encrypted_password)
    while last_json_datetime < datetime.now():
        data = get_daily_data(session, session_response.get('token'),
                              'https://www.solaxcloud.com/blue/phoebus/site/getSiteTotalPower',
                              last_json_datetime, proxies
                              )
        json_response = json_decode(data)

        json_file = os.path.join(solax_stats_folder, configure.gen_json_d(last_json_datetime))
        with open(json_file, 'w') as fi:
            fi.write(json.dumps(json_response, indent=2))

        json_to_feather(json_file, json_response.get('object'))
        df: pd.DataFrame = pd.DataFrame(json_response.get('object'))

        last_json_datetime += timedelta(days=1)


def json_to_feather(json_file, data=None):
    if not data:
        print(f'read {json_file}')
        with open(json_file, 'r') as fi:
            data = json.loads(fi.read()).get('object')

    df: pd.DataFrame = pd.DataFrame(data)
    date_columns = ['year', 'month', 'day']
    timestamp_columns = date_columns + ['hour', 'minute']
    if [c for c in date_columns if c not in df.columns]:  # any timestamp column missing, happens in early files
        ma = configure.target_file_pattern.match(json_file)
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
    print(f'wrote {feather_file}')


@extract.command('compress')
@click.option('--force', is_flag=True, default=False)
def compress(force):
    count = 0
    for fi in os.listdir(configure.solax_stats_folder):
        if not configure.re_json.match(fi):
            continue
        json_file = os.path.join(configure.solax_stats_folder, fi)
        feather_file = json_file.replace('.json', '.feather')

        if not force and os.path.exists(feather_file):
            continue
        json_to_feather(json_file)

        count += 1

    print(f'compressed {count} json files into feather')


def aggregate_impl(dfs: List[pd.DataFrame], grouping: List[str]) -> pd.DataFrame:
    df = pd.concat(dfs).groupby(grouping).agg({'elapsed_time': 'sum',
                                               **{col: 'sum' for col in schemas.ENERGY_SCHEMA.energy_columns}})
    for col in schemas.ENERGY_SCHEMA.power_columns:
        df[col] = df['col' + 'KWh'] / df['elapse_time'] * 3.6
    return df


@extract.command('aggregate')
@click.option('--granularity', '-f', help='Granularity of the aggregation', required=False, default='All',
              type=click.Choice(['All', 'Hourly', 'Daily', 'Monthly'], case_sensitive=False))
@click.option('--partition', '-f', help='Partitioning of the files', required=False, default='None',
              type=click.Choice(['None', 'Monthly', 'Yearly'], case_sensitive=False))
@click.option('--force', is_flag=True, default=False)
def aggregate(granularity, partition, force):
    if partition == 'None':
        feather_file_pattern = configure.re_feather_a
        file_namer = configure.gen_feather_a(granularity)
    elif partition == 'Yearly':
        feather_file_pattern = configure.re_feather_y
        file_namer = configure.gen_feather_y(granularity)
    elif partition == 'Monthly':
        feather_file_pattern = configure.re_feather_m
        file_namer = configure.gen_feather_m(granularity)
    else:
        raise ValueError(f'Invalid partition {partition}.')

    folder = configure.solax_stats_folder
    files = os.listdir(folder)
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
    dfs: List[pd.DataFrame] = []
    for fi in files:
        ma = configure.re_feather_d.match(fi)
        if not ma or fi < max_partition:
            continue
        current_partition = file_namer(fi)
        if previous_partition and current_partition != previous_partition:
            aggregate_impl(dfs, grouping).to_feather(os.join(folder, previous_partition))
            dfs = []
            previous_partition = current_partition
        df = pd.read_feather(os.join(folder, fi))
        dfs.append(df)

    if previous_partition:
        aggregate_impl(dfs, grouping).to_feather(os.join(folder, previous_partition))


if __name__ == '__main__':
    click.cli()
