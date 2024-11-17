import json
import os
import re

import pandas as pd

import matplotlib.pyplot as plt
import numpy as np
from dateutil.relativedelta import relativedelta

import solax_configure
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


class prices():
    def __init__(self):
        with open(os.path.join(configure.solax_stats_folder, 'prices.json'), 'r') as fi:
            prices = json.loads(fi.read)
            prices['profiles'] = [{**p,
                                   "peak-days":
                                       p.get("peak-days",
                                             [p['peak-week'] for d in range(0, 5)] +
                                             [p['peak-weekend'] for d in range(5, 7)]
                                             )
                                   } for p in prices['profiles']]
            self._prices = [prices]

    class price:
        def __init__(self, buy, sell):
            self.buy = buy
            self.sell = sell

    def get_price(self, dt: datetime):
        buy = next((p for p in self._prices['buy'] if p['date_from'] <= dt < p['date_to']), None)
        sell = next((p for p in self._prices['sell'] if p['date_from'] <= dt < p['date_to']), None)
        profile = next((p for p in self._prices['profile'] if p['date_from'] <= dt < p['date_to']), None)
        if not buy or not sell or not profile:
            raise ValueError(f"No prices found for {dt}")
        hour = dt.hour
        weekday = dt.weekday()
        peak_day = profile['peak-days'][weekday]
        return prices.price(buy['peak'] if peak_day[0] <= hour < peak_day[1] else buy['offpeak'],
                            sell['peak'] if peak_day[0] <= hour < peak_day[1] else sell['offpeak'])


granularities = {
    '5min'   : 1 / 24 / 12,
    'Hour'   : 1 / 24,
    'Peak'   : 1 / 2,
    'Day'    : 1,
    'Month'  : 30,
    'Quarter': 90,
    'Year'   : 360,
}


@analyse.command("show")
@click.option('--period', '-p', required=True, type=str,
              help='Report period. A day can be specified as yyyy-MM-dd, a month as yyyy-MM, a year as yyyy or a custom range as yyyy-MM-dd..yyyy-MM-dd')
@click.option('--report', '-r', help='Report type', required=False, default='Raw',
              type=click.Choice(['Raw', 'Financial', 'Battery', 'Panels'], case_sensitive=False))
@click.option('--by', '-by', help='Report type', required=False, default='5min',
              type=click.Choice(granularities.keys(), case_sensitive=False))
@click.option('--uom', '-u', help='Unit of measure. Available values are W, kW and KWh',
              type=click.Choice(['W', 'kW', 'kWh'], case_sensitive=False), default='kW')
def show(report: str, by: str, period: str, uom: str):
    """read the data for a range of days and display
       for now not using partitions
    """
    # v TODO: use appropriate data file given granularity
    print(period)
    period_ma = re.match('(?P<from>(\d{4}((-(?P<mm>\d\d))?(-(?P<dd>\d\d))?)?))(..(?P<to>\d{4}-\d\d-\d\d))?$', period)
    print(period_ma)
    if not period_ma:
        print("Invalid period specified.")
        return
    match_dict = period_ma.groupdict()

    from_ = match_dict.get('from')
    to = match_dict.get('to')
    mm = match_dict.get('mm')
    dd = match_dict.get('dd')

    if to:
        date_from = datetime.strptime(from_, '%Y-%m-%d')
        date_to = datetime.strptime(to, '%Y-%m-%d')
    elif dd:
        date_from = date_to = datetime.strptime(from_, '%Y-%m-%d')
    elif mm:
        date_from = datetime.strptime(from_ + '-01', '%Y-%m-%d')
        date_to = date_from + relativedelta(months=1, days=-1)
    else:  # year:
        date_from = datetime.strptime(from_ + '-01-01', '%Y-%m-%d')
        date_to = date_from + relativedelta(years=1, days=-1)
    to_be_deleted = ['inverterSn', 'powerdc', 'uploadTimeValue', 'fiveMinuteVal', 'powerdc3', 'powerdc4']
    power_columns = ['powerdc1', 'powerdc2',
                     'pac1', 'pac2', 'pac3',
                     'pvPower', 'gridpower', 'feedinpower', 'EPSPower', 'epspower', 'EpsActivePower',
                     'consumeEnergyMeter2', 'feedinPowerMeter2', 'Meter2ComState', 'relayPower', 'batPower1']

    if (date_to - date_from).total_seconds() < granularities[by]:
        raise ValueError(f'The selected period is too  short to be represented in {by}')

    jfile_re = configure.target_file_pattern
    dfs = []
    solax_stats_folder = configure.solax_stats_folder
    for jfile, feather_file, value_date in (
            (jfile,
             feather_file,
             datetime(
                 int(jfile_ma.groupdict()['year']),
                 int(jfile_ma.groupdict()['month']),
                 int(jfile_ma.groupdict()['day'])))
            for jfile, feather_file, jfile_ma in (
            (os.path.join(solax_stats_folder, fi),
             os.path.join(solax_stats_folder, fi.replace('.json', '.feather')),
             jfile_re.match(fi))
            for fi in os.listdir(solax_stats_folder)) if jfile_ma
    ):
        if not (value_date >= date_from and value_date <= date_to):
            continue

        if os.path.exists(feather_file):
            print(f'read {feather_file}')
            df = pd.read_feather(feather_file)
        else:
            print('Some feather file missing. Run solax.exe extract compress first.')
            return

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

        # TODO : use https://pandas.pydata.org/docs/user_guide/style.html to visualize the data
        print(df.to_string(sparsify=False))

        dfs.append(df)

    df = pd.concat(dfs)
    fig, ax = plt.subplots()  # Create a figure containing a single Axes.
    for power_column in power_columns:
        ax.plot(df['timestamp'], df[power_column], label=power_column)  # Plot some data on the Axes.

    ax.set_xlabel(period)
    ax.set_ylabel(uom)
    ax.set_title('Solaire Sillons')
    ax.legend()
    plt.show()
