# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from collections import defaultdict
from copy import deepcopy
  
from colorama import Fore, Back, Style
from tqdm import tqdm

from .config import config

PRINT_ASSETS = ["EUR", "USD", "XMR", "BTC", "ETH", "SOL"]

def ddict():
    return defaultdict(ddict)

class BalanceHistoryLog(object):
    def __init__(self, transaction_records):
        self.rows = defaultdict(ddict)
        self.days = defaultdict(ddict)
        self.months = defaultdict(ddict)
        self.years = defaultdict(ddict)
        self.assets = PRINT_ASSETS

        if config.debug:
            print("%sBalance History log transaction records" % Fore.CYAN)

        for tr in tqdm(transaction_records,
                       unit='tr',
                       desc="%sBalance history transaction records%s" % (Fore.CYAN, Fore.GREEN),
                       disable=bool(config.debug or not sys.stdout.isatty())):
            if config.debug:
                print("%sBalanceHist: TR %s" % (Fore.MAGENTA, tr))
            if tr.buy:
                self._add_tokens(tr.buy, tr.fee)

            if tr.sell:
                self._subtract_tokens(tr.sell, tr.fee)

        # cummulative numbers
        self.years_cum = deepcopy(self.years)
        years = [y for y in self.years]
        # add previous year to every year to calculate the cumulative
        # skip first year
        for year in years[1:]:
            for asset in self.years_cum[year-1]:
                if asset in self.years_cum[year]:
                    self.years_cum[year][asset] += self.years_cum[year-1][asset]
                else:
                    self.years_cum[year][asset] = self.years_cum[year-1][asset]


    def _add_tokens(self, buy, fee):
        timestamp = buy.timestamp

        # rows
        if buy.asset not in self.rows[timestamp]:
            self.rows[timestamp][buy.asset] = buy.quantity
        else:
            self.rows[timestamp][buy.asset] += buy.quantity
        self.rows[timestamp]["t_type"] = buy.t_type

        # days
        if buy.asset not in self.days[timestamp.year].get(timestamp.month, {}).get(timestamp.day, {}):
            self.days[timestamp.year][timestamp.month][timestamp.day][buy.asset] = buy.quantity
        else:
            self.days[timestamp.year][timestamp.month][timestamp.day][buy.asset] += buy.quantity 

        # months
        if buy.asset not in self.months[timestamp.year][timestamp.month]:
            self.months[timestamp.year][timestamp.month][buy.asset] = buy.quantity
        else:
            self.months[timestamp.year][timestamp.month][buy.asset] += buy.quantity 

        # years
        if buy.asset not in self.years[timestamp.year]:
            self.years[timestamp.year][buy.asset] = buy.quantity
        else:
            self.years[timestamp.year][buy.asset] += buy.quantity 


        # fees
        if fee:
            if fee.asset not in self.rows[timestamp]:
                self.rows[timestamp][fee.asset] = -(fee.quantity)
            else:
                self.rows[timestamp][fee.asset] -= fee.quantity
            if fee.asset not in self.days[timestamp.year][timestamp.month][timestamp.day]:
                self.days[timestamp.year][timestamp.month][timestamp.day][fee.asset] = -(fee.quantity)
            else:
                self.days[timestamp.year][timestamp.month][timestamp.day][fee.asset] -= fee.quantity 

            if fee.asset not in self.months[timestamp.year][timestamp.month]:
                self.months[timestamp.year][timestamp.month][fee.asset] = -(fee.quantity)
            else:
                self.months[timestamp.year][timestamp.month][fee.asset] -= fee.quantity 

            if fee.asset not in self.years[timestamp.year]:
                self.years[timestamp.year][fee.asset] = -(fee.quantity)
            else:
                self.years[timestamp.year][fee.asset] -= fee.quantity 

    def _subtract_tokens(self, sell, fee):
        timestamp = sell.timestamp

        # rows
        if sell.asset not in self.rows[timestamp]:
            self.rows[timestamp][sell.asset] = -(sell.quantity)
        else:
            self.rows[timestamp][sell.asset] -= sell.quantity
        self.rows[timestamp]["t_type"] = sell.t_type

        # days
        if sell.asset not in self.days[timestamp.year][timestamp.month][timestamp.day]:
            self.days[timestamp.year][timestamp.month][timestamp.day][sell.asset] = -(sell.quantity)
        else:
            self.days[timestamp.year][timestamp.month][timestamp.day][sell.asset] -= sell.quantity 


        # months
        if sell.asset not in self.months[timestamp.year][timestamp.month]:
            self.months[timestamp.year][timestamp.month][sell.asset] = -(sell.quantity)
        else:
            self.months[timestamp.year][timestamp.month][sell.asset] -= sell.quantity 


        # years
        if sell.asset not in self.years[timestamp.year]:
            self.years[timestamp.year][sell.asset] = -(sell.quantity)
        else:
            self.years[timestamp.year][sell.asset] -= sell.quantity
    
        # fees
        if fee:
            if fee.asset not in self.rows[timestamp]:
                self.rows[timestamp][fee.asset] = -(fee.quantity)
            else:
                self.rows[timestamp][fee.asset] -= fee.quantity
            if fee.asset not in self.days[timestamp.year][timestamp.month][timestamp.day]:
                self.days[timestamp.year][timestamp.month][timestamp.day][fee.asset] = -(fee.quantity)
            else:
                self.days[timestamp.year][timestamp.month][timestamp.day][fee.asset] -= fee.quantity 

            if fee.asset not in self.months[timestamp.year][timestamp.month]:
                self.months[timestamp.year][timestamp.month][fee.asset] = -(fee.quantity)
            else:
                self.months[timestamp.year][timestamp.month][fee.asset] -= fee.quantity 
            if fee.asset not in self.years[timestamp.year]:
                self.years[timestamp.year][fee.asset] = -(fee.quantity)
            else:
                self.years[timestamp.year][fee.asset] -= fee.quantity 

    def print(self):

        # header
        print(f"timestamp\t", end="")
        for asset in PRINT_ASSETS:
            print(f"{asset}\t", end="")
        print()
        # print all transactions
        for year, ydata in self.years.items():

            for time, data in self.rows.items():
                line = False
                if time.year == year:
                    p = f"{time}\t"
                    for asset in PRINT_ASSETS:
                        if asset in data:
                            p += f"{data[asset]} {asset} {data['t_type']}"
                        else:
                            p += "\t"
                    print(p)
            print(f"TOTAL {year}\t", end="")
            for asset in PRINT_ASSETS:
                print(ydata.get(asset, "\t"), end="")
            print()

    def _log_failure(self, asset, audit, s104):
        failure = {}
        failure['asset'] = asset
        failure['audit'] = audit
        failure['s104'] = s104

        self.failures.append(failure)

    def report_failures(self):
        header = "%-8s %25s %25s %25s" % ('Asset',
                                          'Audit Balance',
                                          'Section 104 Pool',
                                          'Difference')

        print('\n%s%s' % (Fore.YELLOW, header))
        for failure in self.failures:
            if failure['s104'] is not None:
                print("%s%-8s %25s %25s %s%25s" % (
                    Fore.WHITE,
                    failure['asset'],
                    '{:0,f}'.format(failure['audit'].normalize()),
                    '{:0,f}'.format(failure['s104'].normalize()),
                    Fore.RED,
                    '{:+0,f}'.format((failure['s104']-failure['audit']).normalize())))
            else:
                print("%s%-8s %25s %s%25s" % (
                    Fore.WHITE,
                    failure['asset'],
                    '{:0,f}'.format(failure['audit'].normalize()),
                    Fore.RED,
                    '<missing>'))
