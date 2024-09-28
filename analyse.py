import json
import os
import re

import pandas as pd

import matplotlib.pyplot as plt
import numpy as np
from dateutil.relativedelta import relativedelta

import solax_extract
import click
from datetime import datetime


@click.group()
@click.version_option()
def cli():
    """analyse the data"""


@cli.group()
def analyse():
    """Various analysis functions"""


"""
We're interested in:
    * Energy produced PV
    * Energy produced Battery
    * Energy consumed total
    * Grid Purchases in MWh
    * Grid sales in MWh
    * Count of Battery cycles : sum (abs battery variation) / 2
... by hour over a period of time (eventually peak/offpeak is enough
"""


@analyse.command("show")
@click.option('--day', help='iso date yyyy-MM-dd', required=False, default=None, type=str)
@click.option('--month', help='iso month yyyy-MM', required=False, default=None, type=str)
@click.option('--year', help='iso year yyyy', required=False, default=None, type=str)
@click.option('--from', 'from_', help='iso date yyyy-MM-dd', required=False, default=None, type=str)
@click.option('--to', help='iso date yyyy-MM-dd', required=False, default=None, type=str)
@click.option('--uom', help='Unit of measure. Available values are W, kW and KWh',
              type=click.Choice(['W', 'kW', 'kWh'], case_sensitive=False), default='kW')
def show(day: str, month: str, year: str, from_: str, to: str, uom: str):
    """read the data for a range of days and display"""
    date_from = datetime(2000, 1, 1)
    date_to = datetime(2100, 1, 1)

    if sum([
        1 if day else 0,
        1 if month else 0,
        1 if year else 0,
        1 if from_ or to else 0
    ]) > 1:
        print("Cannot specify more than one type of date range option.")
        return
    if day:
        date_from = date_to = datetime.strptime(day, '%Y-%m-%d')
        xlabel = day
    if month:
        date_from = datetime.strptime(month + '-01', '%Y-%m-%d')
        date_to = date_from + relativedelta(months=1, days=-1)
        xlabel = month
    if year:
        date_from = datetime.strptime(year + '-01-01', '%Y-%m-%d')
        date_to = date_from + relativedelta(years=1, days=-1)
        xlabel = year
    if from_:
        date_from = datetime.strptime(from_, '%Y-%m-%d')
    if to:
        date_to = datetime.strptime(to, '%Y-%m-%d')

    if from_ or to:
        xlabel = date_from.strftime('%Y-%m-%d') + '..' + date_to.strftime('%Y-%m-%d')
    to_be_deleted = ['inverterSn', 'powerdc', 'uploadTimeValue', 'fiveMinuteVal', 'powerdc3', 'powerdc4']
    power_columns = ['powerdc1', 'powerdc2',
                     'pac1', 'pac2', 'pac3',
                     'pvPower', 'gridpower', 'feedinpower', 'EPSPower', 'epspower', 'EpsActivePower',
                     'consumeEnergyMeter2', 'feedinPowerMeter2', 'Meter2ComState', 'relayPower', 'batPower1']

    jfile_re = re.compile(r'.*(?P<yyyy>\d{4})-(?P<mm>\d\d)-(?P<dd>\d\d).json')
    dfs = []
    for jfile, feather_file, value_date in (
            (jfile,
             feather_file,
             datetime(
                 int(jfile_ma.groupdict()['yyyy']),
                 int(jfile_ma.groupdict()['mm']),
                 int(jfile_ma.groupdict()['dd'])))
            for jfile, feather_file, jfile_ma in (
            (os.path.join(solax_extract.solax_stats_folder, fi),
             os.path.join(solax_extract.solax_stats_folder, fi.replace('.json', '.feather')),
             jfile_re.match(fi))
            for fi in os.listdir(solax_extract.solax_stats_folder)) if jfile_ma
    ):
        if not (value_date >= date_from and value_date <= date_to):
            continue

        if os.path.exists(feather_file):
            print(f'read {feather_file}')
            df = pd.read_feather(feather_file)
        else:
            print('Some feather file missing. Run solax.exe extract compress first.')
            print(f'read {jfile}')
            with open(jfile, 'r') as fi:
                raw_data = json.loads(fi.read())
                df: pd.DataFrame = pd.DataFrame(raw_data.get('object'))
            df.to_feather(feather_file)
            print(f'wrote {feather_file}')

        timestamp_columns = ['year', 'month', 'day', 'hour', 'minute']
        df['timestamp'] = pd.to_datetime(df[timestamp_columns])
        to_be_deleted = to_be_deleted + timestamp_columns
        df['elapsed_time'] = df['timestamp'].diff().dt.total_seconds().fillna(300)

        if uom == 'W':
            pass
        elif uom == 'kW':
            for power_column in power_columns:
                df[power_column] = df[power_column] / 1000.0
        elif uom == 'kWh':
            for power_column in power_columns:
                df[power_column] = df[power_column] * df['elapsed_time'] / 3600.0 / 1000.0
        else:
            raise ValueError(f'Invalid unit of measure :{uom}')

        df.drop(columns=to_be_deleted, inplace=True)

        print(df.to_string(sparsify=False))

        dfs.append(df)

    df = pd.concat(dfs)
    fig, ax = plt.subplots()  # Create a figure containing a single Axes.
    for power_column in power_columns:
        ax.plot(df['timestamp'], df[power_column], label=power_column)  # Plot some data on the Axes.

    ax.set_xlabel(xlabel)
    ax.set_ylabel(uom)
    ax.set_title('Solaire Sillons')
    ax.legend()
    plt.show()
