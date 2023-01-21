# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
import os
from decimal import Decimal
from collections import defaultdict
from copy import deepcopy
import dateutil.parser
import datetime
  
from colorama import Fore, Back, Style
from tqdm import tqdm

from .config import config
from .transactions import TransactionRecord
from .price.valueasset import ValueAsset


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

def last_day_of_month(any_day):
    # this will never fail
    # get close to the end of the month for any day, and add 4 days 'over'
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    # subtract the number of remaining 'overage' days to get last day of current month, or said programattically said, the previous day of the first of next month
    date = next_month - datetime.timedelta(days=next_month.day)
    return datetime.datetime(year=date.year, month=date.month, day=date.day)

class BalanceHistoryLog(object):
    def __init__(self, transaction_records):
        self.rows = defaultdict(ddict)
        self.days = defaultdict(ddict)
        self.months = defaultdict(ddict)
        self.years = defaultdict(ddict)
        self.assets = PRINT_ASSETS
        self.other_assets = []
        self.staking = {}
        self.staking_yearly_sum = {}

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
            
            if tr.t_type == TYPE_STAKING:
                self._stake(tr.buy)

        # calculate staking overview
        self.stake_to_eur()
        self.yearly_stake()

        # calculate monthly and yearly diffs and sums
        self.calculate_diffs_and_sums()
        # Get price values for every asset
        self.get_monthly_values_in_eur()


    def calculate_diffs_and_sums(self):
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


        self.months_cum = deepcopy(self.months_diff)
        for year in years:
            months = [y for y in self.months_diff[year]]
            for month in months:
                year_offset = 1 if month == 1 else 0
                month_diff = -11 if month == 1 else 1
                for asset in self.months_cum[year-year_offset][month-month_diff]:
                    if asset in self.months_cum[year][month]:
                        self.months_cum[year][month][asset] += self.months_cum[year-year_offset][month-month_diff][asset]
                    else:
                        self.months_cum[year][month][asset] = self.months_cum[year-year_offset][month-month_diff][asset]


    def get_monthly_values_in_eur(self):
        self.months_cum_converted = {}
        value_asset = ValueAsset(price_tool=True)
        assets = set()
        for year in self.months_cum:
            self.months_cum_converted[year] = {}
            for month in self.months_cum[year]:
                self.months_cum_converted[year][month] = {}
                cumul = 0
                for asset, value in self.months_cum[year][month].items():
                    
                    date = last_day_of_month(datetime.date(year, month, 1))
                    date = date.replace(tzinfo=config.TZ_LOCAL)

                    if asset == config.ccy:
                        self.months_cum_converted[year][month][asset] = {
                            "value": value,
                            config.ccy: value,
                            }
                    elif asset in config.FIAT_LIST or asset == "BTC":
                        eur_value, name, _ = value_asset.get_historical_price(
                            asset, date,
                            target_asset=config.ccy
                        )
                        self.months_cum_converted[year][month][asset] = {
                            "value": value,
                            config.ccy: value*eur_value
                        }
                    else:
                        eur_value, name, _ = value_asset.get_historical_price(
                            asset, date,
                            target_asset=config.ccy
                        )
                        self.months_cum_converted[year][month][asset] = {
                            "value": value,
                            config.ccy: value*eur_value if eur_value else None,
                        }

                    if self.months_cum_converted[year][month][asset][config.ccy] is not None:
                        cumul += self.months_cum_converted[year][month][asset][config.ccy]
                        assets.add(asset)
                # save cumul
                # self.months_cum_converted[year][month]["CUMMULATIVE"] = {config.ccy: cumul}
        value_asset.save_cache()

        # Save cumulative total
        p = os.path.join(config.BITTYTAX_PATH, "monthly_cumul.csv")
        with open(p, "w") as f:
            f.write(f'Date')
            for asset in assets:
                f.write(f', {asset}')
            f.write('\n')
            for year in self.months_cum:
                for month in self.months_cum_converted[year]:
                    f.write(f'{month}/{year}')
                    for asset in assets:
                        eur_value = self.months_cum_converted[year][month].get(asset, {}).get(config.ccy, "")
                        f.write(f', {eur_value}')
                    f.write('\n')

    def _stake(self, record):

        timestamp = record.timestamp
        year = timestamp.year
        month = timestamp.month
        day = timestamp.day
        asset = record.asset
        quantity = record.quantity

        if year not in self.staking:
            self.staking[year] = {}
        if month not in self.staking[year]:
            self.staking[year][month] = {}
        if day not in self.staking[year][month]:
            self.staking[year][month][day] = {}
        
        if asset in self.staking[year][month][day]:
            self.staking[year][month][day][asset]["value"] += quantity
        else:
            self.staking[year][month][day][asset] = {"value": quantity}


    def stake_to_eur(self):
        value_asset = ValueAsset(price_tool=True)
        for year in self.staking:
            for month in self.staking[year]:
                for day in self.staking[year][month]:
                    for asset in self.staking[year][month][day]:
                        value = self.staking[year][month][day][asset]["value"]
                        date = datetime.datetime(year, month, day)
                        date = date.replace(tzinfo=config.TZ_LOCAL)
                        if asset == config.ccy:
                            self.staking[year][month][day][asset][config.ccy] = value,
                        elif asset in config.FIAT_LIST or asset == "BTC":
                            eur_value, name, _ = value_asset.get_historical_price(
                                asset, date,
                                target_asset=config.ccy
                            )
                            self.staking[year][month][day][asset][config.ccy] = value*eur_value
                        else:
                            eur_value, name, _ = value_asset.get_historical_price(
                                asset, date,
                                target_asset=config.ccy
                            )
                            self.staking[year][month][day][asset][config.ccy] = value*eur_value if eur_value else None

    def yearly_stake(self):
        for year in self.staking:
            self.staking_yearly_sum[year] = 0
            for month in self.staking[year]:
                for day in self.staking[year][month]:
                    for asset in self.staking[year][month][day]:
                        if self.staking[year][month][day][asset][config.ccy] is None:
                            continue
                        self.staking_yearly_sum[year] += self.staking[year][month][day][asset][config.ccy]

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
