import json
import os
import re

import pandas as pd

import matplotlib.pyplot as plt
import numpy as np

import solax_extract
import click
from datetime import datetime


@click.group()
@click.version_option()
def cli():
    """analyse the data"""


@cli.group()
def analyse():
    """configure connectivity"""


@analyse.command("show")
@click.option('--day', prompt='iso date yyyy-MM-dd')
@click.option('--uom', prompt='Unit of measure. Available values are W, kW and KWh',
              type=click.Choice(['W', 'kW', 'kWh'], case_sensitive=False))
def show(day: str, uom: str):
    """read the data for one day and display"""
    jfile_re = re.compile(f'.*{day}.json')
    to_be_deleted = ['inverterSn', 'powerdc', 'uploadTimeValue', 'fiveMinuteVal', 'powerdc3', 'powerdc4']
    power_columns = ['powerdc1', 'powerdc2',
                     'pac1', 'pac2', 'pac3',
                     'pvPower', 'gridpower', 'feedinpower', 'EPSPower', 'epspower', 'EpsActivePower',
                     'consumeEnergyMeter2', 'feedinPowerMeter2', 'Meter2ComState', 'relayPower', 'batPower1']
    for jfile, feather_file in (
            (
                    os.path.join(solax_extract.solax_stats_folder, fi),
                    os.path.join(solax_extract.solax_stats_folder, fi.replace('.json', '.feather'))
            )
            for fi in os.listdir(solax_extract.solax_stats_folder) if jfile_re.match(fi)):

        if not os.path.exists(feather_file):
            print(f'read {jfile}')
            with open(jfile, 'r') as fi:
                raw_data = json.loads(fi.read())
                data = raw_data.get('object')
                df: pd.DataFrame = pd.DataFrame(data)
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
                # df.to_feather(feather_file)
                # print(f'wrote {feather_file}')
        fig, ax = plt.subplots()             # Create a figure containing a single Axes.
        for power_column in power_columns:
            ax.plot(df['timestamp'], df[power_column], label=power_column)  # Plot some data on the Axes.
        ax.set_xlabel(day)
        ax.set_ylabel(uom)
        ax.set_title('Solaire Sillons')
        ax.legend()

        plt.show()

@analyse.command("edit")
def edit():
    print('not implemented yet')
