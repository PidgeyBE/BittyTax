# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import os
from decimal import Decimal
from datetime import datetime
import json

from colorama import Fore, Back, Style
from tqdm import tqdm

from ..version import __version__
from ..config import config
from .pricedata import PriceData


class ValueAsset(object):
    def __init__(self, price_tool=False):
        self.price_tool = price_tool
        self.price_report = {}
        data_sources_required = set(config.data_source_fiat +
                                    config.data_source_crypto) | \
                                {x.split(':')[0]
                                 for v in config.data_source_select.values() for x in v}
        self.price_data = PriceData(data_sources_required, price_tool)

        # Addition to store cache long term
        self.cache_path = os.path.join(config.BITTYTAX_PATH, "historic_price_cache.json")
        self.cache = {} # self.cache[asset][target_asset][date]["price"]
        self._load_cache()

    def save_cache(self):
        """Getting historical values is very expensive, so save as much as possible."""
        with open(self.cache_path, "w") as json_file:
            json.dump(self.cache, json_file)

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as json_file:
                self.cache = json.load(json_file)

    def _get_from_cache(self, asset, target_asset, date):
        if date in self.cache.get(asset, {}).get("valuta", {}).get(target_asset, {}):
            asset_price_ccy = self.cache[asset]["valuta"][target_asset][date]
            name = self.cache[asset]["name"]
            data_source = self.cache[asset]["data_source"]
            if asset_price_ccy is not None:
                asset_price_ccy = Decimal(asset_price_ccy)
            return asset_price_ccy, name, data_source

    def _add_to_cache(self, asset, target_asset, date, asset_price_ccy, name, data_source):
        if asset not in self.cache:
            self.cache[asset] = {"name": name, "data_source": data_source, "valuta": {}}
        if target_asset not in self.cache[asset]["valuta"]:
            self.cache[asset]["valuta"][target_asset] = {}
        if isinstance(asset_price_ccy, Decimal):
            asset_price_ccy = str(asset_price_ccy)
        self.cache[asset]["valuta"][target_asset][date] = asset_price_ccy
        # Autosave as I expect getting values from API's is expensive and all progress should
        # be saved.
        self.save_cache()

    def get_value(self, asset, timestamp, quantity):
        if asset == config.ccy:
            return quantity, True

        if quantity == 0:
            return Decimal(0), False

        asset_price_ccy, _, _ = self.get_historical_price(asset, timestamp)
        if asset_price_ccy is not None:
            value = asset_price_ccy * quantity
            if config.debug:
                print("%sprice: %s, 1 %s=%s %s, %s %s=%s%s %s%s" % (
                    Fore.YELLOW,
                    timestamp.strftime('%Y-%m-%d'),
                    asset,
                    config.sym() + '{:0,.2f}'.format(asset_price_ccy),
                    config.ccy,
                    '{:0,f}'.format(quantity.normalize()),
                    asset,
                    Style.BRIGHT,
                    config.sym() + '{:0,.2f}'.format(value),
                    config.ccy,
                    Style.NORMAL))
            return value, False

        tqdm.write("%sWARNING%s Price for %s on %s is not available, using price of %s" % (
                   Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                   asset, timestamp.strftime('%Y-%m-%d'), config.sym() + '{:0,.2f}'.format(0)))
        return Decimal(0), False

    def get_current_value(self, asset, quantity):
        asset_price_ccy, name, data_source = self.get_latest_price(asset)
        if asset_price_ccy is not None:
            return asset_price_ccy * quantity, name, data_source

        return None, None, None

    def get_historical_price(self, asset, timestamp, no_cache=False, target_asset=None):
        asset_price_ccy = None

        if not self.price_tool and timestamp.date() >= datetime.now().date():
            tqdm.write("%sWARNING%s Price for %s on %s, no historic price available, "
                       "using latest price" % (Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                                               asset, timestamp.strftime('%Y-%m-%d')))
            return self.get_latest_price(asset)

        # first get value out of diskcache
        date = timestamp.strftime('%Y-%m-%d')
        if not no_cache:
            c = self._get_from_cache(asset, target_asset, date)
            if c is not None:
                return c

        if asset == 'BTC' or asset in config.fiat_list:
            asset_price_ccy, name, data_source, url = self.price_data.get_historical(asset,
                                                                                     config.ccy,
                                                                                     timestamp,
                                                                                     no_cache)
            self.price_report_cache(asset, timestamp, name, data_source, url, asset_price_ccy)
        else:
            asset_price_btc, name, data_source, url = self.price_data.get_historical(asset,
                                                                                     'BTC',
                                                                                     timestamp,
                                                                                     no_cache)
            if target_asset == config.ccy: 
                if asset_price_btc is not None:
                    btc_price_ccy, name2, data_source2, url2 = self.price_data.get_historical(
                        'BTC', config.ccy, timestamp, no_cache)
                    if btc_price_ccy is not None:
                        asset_price_ccy = btc_price_ccy * asset_price_btc

                    self.price_report_cache('BTC', timestamp, name2, data_source2, url2, btc_price_ccy)
            elif target_asset == "BTC":
                asset_price_ccy = asset_price_btc
            else:
                print(f"SHITTT target_asset {target_asset} is not supported")

            self.price_report_cache(asset, timestamp, name, data_source, url, asset_price_ccy,
                                    asset_price_btc)
        if asset_price_ccy is None:
            print(f"OOPS Lookup for asset {asset}->{target_asset} on {timestamp} was no success! URL {url}")
        
        # fill cache
        self._add_to_cache(asset, target_asset, date, asset_price_ccy, name, data_source)
        
        return asset_price_ccy, name, data_source

    def get_latest_price(self, asset):
        asset_price_ccy = None

        if asset == 'BTC' or asset in config.fiat_list:
            asset_price_ccy, name, data_source = self.price_data.get_latest(asset, config.ccy)
        else:
            asset_price_btc, name, data_source = self.price_data.get_latest(asset, 'BTC')

            if asset_price_btc is not None:
                btc_price_ccy, _, _ = self.price_data.get_latest('BTC', config.ccy)
                if btc_price_ccy is not None:
                    asset_price_ccy = btc_price_ccy * asset_price_btc

        return asset_price_ccy, name, data_source

    def price_report_cache(self, asset, timestamp, name, data_source, url,
                           price_ccy, price_btc=None):
        if timestamp > config.get_tax_year_end(timestamp.year):
            tax_year = timestamp.year + 1
        else:
            tax_year = timestamp.year

        if tax_year not in self.price_report:
            self.price_report[tax_year] = {}

        if asset not in self.price_report[tax_year]:
            self.price_report[tax_year][asset] = {}

        date = timestamp.strftime('%Y-%m-%d')
        if date not in self.price_report[tax_year][asset]:
            self.price_report[tax_year][asset][date] = {'name': name,
                                                        'data_source': data_source,
                                                        'url': url,
                                                        'price_ccy': price_ccy,
                                                        'price_btc': price_btc}
