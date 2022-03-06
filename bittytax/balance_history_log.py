# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from collections import defaultdict
from copy import deepcopy
  
from colorama import Fore, Back, Style
from tqdm import tqdm

from .config import config
from .transactions import TransactionRecord

PRINT_ASSETS = ["EUR", "USD", "XMR", "BTC", "ETH", "SOL", "FTT"]


TYPE_DEPOSIT = TransactionRecord.TYPE_DEPOSIT
TYPE_MINING = TransactionRecord.TYPE_MINING
TYPE_STAKING = TransactionRecord.TYPE_STAKING
TYPE_INTEREST = TransactionRecord.TYPE_INTEREST
TYPE_DIVIDEND = TransactionRecord.TYPE_DIVIDEND
TYPE_INCOME = TransactionRecord.TYPE_INCOME
TYPE_GIFT_RECEIVED = TransactionRecord.TYPE_GIFT_RECEIVED
TYPE_AIRDROP = TransactionRecord.TYPE_AIRDROP
TYPE_TRADE = TransactionRecord.TYPE_TRADE
TYPE_WITHDRAWAL = TransactionRecord.TYPE_WITHDRAWAL
TYPE_SPEND = TransactionRecord.TYPE_SPEND
TYPE_GIFT_SENT = TransactionRecord.TYPE_GIFT_SENT
TYPE_GIFT_SPOUSE = TransactionRecord.TYPE_GIFT_SPOUSE
TYPE_CHARITY_SENT = TransactionRecord.TYPE_CHARITY_SENT
TYPE_LOST = TransactionRecord.TYPE_LOST
TYPE_TRADE = TransactionRecord.TYPE_TRADE

EXTERNAL_TYPES = {TYPE_SPEND, TYPE_GIFT_SENT, TYPE_GIFT_SPOUSE, TYPE_CHARITY_SENT,
                    TYPE_DEPOSIT, TYPE_WITHDRAWAL
                }

def ddict():
    return defaultdict(ddict)

class BalanceHistoryLog(object):
    def __init__(self, transaction_records):
        self.rows = defaultdict(ddict)
        self.days = defaultdict(ddict)
        self.months = defaultdict(ddict)
        self.years = defaultdict(ddict)
        self.assets = PRINT_ASSETS
        self.other_assets = []

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


        # In montly/transaction overviews, we don't make a difference between Internal/External
        self.months_diff = deepcopy(self.months)
        years = [y for y in self.years]
        for year in years:
            months = [y for y in self.months[year]]
            for month in months:
                assets = set([k for k in self.months_diff[year][month]["Internal"].keys()] + [k for k in self.months_diff[year][month]["External"].keys()])
                for asset in assets:
                    self.months_diff[year][month][asset] = self.months_diff[year][month]["Internal"].get(asset, 0) + self.months_diff[year][month]["External"].get(asset, 0)
                del self.months_diff[year][month]["Internal"]
                del self.months_diff[year][month]["External"]

        self.years_diff = deepcopy(self.years)
        years = [y for y in self.years]
        for year in years:
            assets = set([k for k in self.years_diff[year]["Internal"].keys()] + [k for k in self.years_diff[year]["External"].keys()])
            for asset in assets:
                self.years_diff[year][asset] = self.years_diff[year]["Internal"].get(asset, 0) + self.years_diff[year]["External"].get(asset, 0)
            del self.years_diff[year]["Internal"]
            del self.years_diff[year]["External"]

        # cummulative numbers
        self.years_cum = deepcopy(self.years_diff)
       
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

        if buy.asset not in self.assets and buy.asset not in self.other_assets:
            self.other_assets.append(buy.asset)

        # rows
        if buy.asset not in self.rows[timestamp]:
            self.rows[timestamp][buy.asset] = buy.quantity
        else:
            self.rows[timestamp][buy.asset] += buy.quantity
        self.rows[timestamp]["t_type"] = buy.t_type
        self.rows[timestamp]["wallet"] = buy.wallet

        # define type
        category = "Internal"
        if buy.t_type in EXTERNAL_TYPES and buy.asset in config.FIAT_LIST:
            category = "External"

        # days
        if buy.asset not in self.days[timestamp.year].get(timestamp.month, {}).get(timestamp.day, {}):
            self.days[timestamp.year][timestamp.month][timestamp.day][buy.asset] = buy.quantity
        else:
            self.days[timestamp.year][timestamp.month][timestamp.day][buy.asset] += buy.quantity 

        # months
        if buy.asset not in self.months[timestamp.year][timestamp.month][category]:
            self.months[timestamp.year][timestamp.month][category][buy.asset] = buy.quantity
        else:
            self.months[timestamp.year][timestamp.month][category][buy.asset] += buy.quantity 

        # years
        if buy.asset not in self.years[timestamp.year][category]:
            self.years[timestamp.year][category][buy.asset] = buy.quantity
        else:
            self.years[timestamp.year][category][buy.asset] += buy.quantity 


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

            if fee.asset not in self.months[timestamp.year][timestamp.month][category]:
                self.months[timestamp.year][timestamp.month][category][fee.asset] = -(fee.quantity)
            else:
                self.months[timestamp.year][timestamp.month][category][fee.asset] -= fee.quantity 

            if fee.asset not in self.years[timestamp.year][category]:
                self.years[timestamp.year][category][fee.asset] = -(fee.quantity)
            else:
                self.years[timestamp.year][category][fee.asset] -= fee.quantity 


    def _subtract_tokens(self, sell, fee):
        timestamp = sell.timestamp

        if sell.asset not in self.assets and sell.asset not in self.other_assets:
            self.other_assets.append(sell.asset)

        # define type
        category = "Internal"
        if sell.t_type in EXTERNAL_TYPES and sell.asset in config.FIAT_LIST:
            category = "External"

        # rows
        if sell.asset not in self.rows[timestamp]:
            self.rows[timestamp][sell.asset] = -(sell.quantity)
        else:
            self.rows[timestamp][sell.asset] -= sell.quantity
        self.rows[timestamp]["t_type"] = sell.t_type
        self.rows[timestamp]["wallet"] = sell.wallet

        # days
        if sell.asset not in self.days[timestamp.year][timestamp.month][timestamp.day]:
            self.days[timestamp.year][timestamp.month][timestamp.day][sell.asset] = -(sell.quantity)
        else:
            self.days[timestamp.year][timestamp.month][timestamp.day][sell.asset] -= sell.quantity 


        # months
        if sell.asset not in self.months[timestamp.year][timestamp.month][category]:
            self.months[timestamp.year][timestamp.month][category][sell.asset] = -(sell.quantity)
        else:
            self.months[timestamp.year][timestamp.month][category][sell.asset] -= sell.quantity 

        # years
        if sell.asset not in self.years[timestamp.year][category]:
            self.years[timestamp.year][category][sell.asset] = -(sell.quantity)
        else:
            self.years[timestamp.year][category][sell.asset] -= sell.quantity

    
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

            if fee.asset not in self.months[timestamp.year][timestamp.month][category]:
                self.months[timestamp.year][timestamp.month][category][fee.asset] = -(fee.quantity)
            else:
                self.months[timestamp.year][timestamp.month][category][fee.asset] -= fee.quantity 

            if fee.asset not in self.years[timestamp.year][category]:
                self.years[timestamp.year][category][fee.asset] = -(fee.quantity)
            else:
                self.years[timestamp.year][category][fee.asset] -= fee.quantity 


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
