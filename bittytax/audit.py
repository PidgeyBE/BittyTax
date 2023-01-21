# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal
from collections import defaultdict

from colorama import Fore, Back, Style
from tqdm import tqdm
import time
import dateutil.parser


from .config import config
from .price.valueasset import ValueAsset

class AuditRecords(object):
    def __init__(self, transaction_records):
        self.wallets = {}
        self.wallet_values = defaultdict(dict)
        self.totals = {}
        self.failures = []

        if config.debug:
            print("%saudit transaction records" % Fore.CYAN)

        for tr in tqdm(transaction_records,
                       unit='tr',
                       desc="%saudit transaction records%s" % (Fore.CYAN, Fore.GREEN),
                       disable=bool(config.debug or not sys.stdout.isatty())):
            if config.debug:
                print("%saudit: TR %s" % (Fore.MAGENTA, tr))
            if tr.buy:
                self._add_tokens(tr.wallet, tr.buy.asset, tr.buy.quantity)

            if tr.sell:
                self._subtract_tokens(tr.wallet, tr.sell.asset, tr.sell.quantity)

            if tr.fee:
                self._subtract_tokens(tr.wallet, tr.fee.asset, tr.fee.quantity)

        # Convert to BTC and USD values
        print("*"*150)
        print("CONVERTING ASSET VALUES -- THIS MIGHT TAKE A WHILE")
        print("*"*150)
        print()
        date = dateutil.parser.parse("2021-12-31", dayfirst=False)
        date = date.replace(tzinfo=config.TZ_LOCAL)
        num_wallets = len(self.wallets)
        value_asset = ValueAsset(price_tool=True)
        for i, wallet in enumerate(self.wallets.keys()):
            print("*"*150)
            print(f"Converting {wallet} {(i+1)/num_wallets}...")
            print()
            for asset, value in self.wallets[wallet].items():
                if asset == config.ccy:
                    self.wallet_values[wallet][asset] = {
                                "BTC": None,
                                config.ccy: value,
                    }
                elif asset in config.FIAT_LIST or asset == "BTC":
                    eur_value, name, _ = value_asset.get_historical_price(
                        asset, date,
                        target_asset=config.ccy
                    )
                    self.wallet_values[wallet][asset] = {
                                "BTC": None if asset != "BTC" else value,
                                config.ccy: eur_value*value,
                    }
                else:
                    # time.sleep(1)
                    eur_value, name, _ = value_asset.get_historical_price(
                        asset, date,
                        target_asset=config.ccy
                    )
                    btc_value, name, _ = value_asset.get_historical_price(
                        asset, date,
                        target_asset="BTC"
                    )
                    self.wallet_values[wallet][asset] = {
                                "BTC": btc_value*value if btc_value else None,
                                config.ccy: eur_value*value if eur_value else None,
                    }
            # if i==0:
            #     break

        print(f"WALLET CONVERSUIONS {self.wallet_values}")

        if config.debug:
            print("%saudit: final balances by wallet" % Fore.CYAN)
            for wallet in sorted(self.wallets, key=str.lower):
                for asset in sorted(self.wallets[wallet]):
                    print("%saudit: %s:%s=%s%s%s" % (
                        Fore.YELLOW,
                        wallet,
                        asset,
                        Style.BRIGHT,
                        '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                        Style.NORMAL))

            print("%saudit: final balances by asset" % Fore.CYAN)
            for asset in sorted(self.totals):
                print("%saudit: %s=%s%s%s" % (
                    Fore.YELLOW,
                    asset,
                    Style.BRIGHT,
                    '{:0,f}'.format(self.totals[asset].normalize()),
                    Style.NORMAL))

        if config.audit_hide_empty:
            self._prune_empty(self.wallets)

    def _add_tokens(self, wallet, asset, quantity):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] += quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] += quantity

        if config.debug:
            print("%saudit:   %s:%s=%s (+%s)" % (
                Fore.GREEN,
                wallet,
                asset,
                '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                '{:0,f}'.format(quantity.normalize())))

    def _subtract_tokens(self, wallet, asset, quantity):
        if wallet not in self.wallets:
            self.wallets[wallet] = {}

        if asset not in self.wallets[wallet]:
            self.wallets[wallet][asset] = Decimal(0)

        self.wallets[wallet][asset] -= quantity

        if asset not in self.totals:
            self.totals[asset] = Decimal(0)

        self.totals[asset] -= quantity

        if config.debug:
            print("%saudit:   %s:%s=%s (-%s)" % (
                Fore.GREEN,
                wallet,
                asset,
                '{:0,f}'.format(self.wallets[wallet][asset].normalize()),
                '{:0,f}'.format(quantity.normalize())))

        if self.wallets[wallet][asset] < 0 and asset not in config.fiat_list:
            tqdm.write("%sWARNING%s Balance at %s:%s is negative %s" % (
                Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW,
                wallet, asset, '{:0,f}'.format(self.wallets[wallet][asset].normalize())))

    def _prune_empty(self, wallets):
        for wallet in list(wallets):
            for asset in list(wallets[wallet]):
                if wallets[wallet][asset] == Decimal(0):
                    wallets[wallet].pop(asset)
            if len(wallets[wallet]) == 0:
                wallets.pop(wallet)

    def compare_pools(self, holdings):
        passed = True
        for asset in sorted(self.totals):
            if asset in config.fiat_list:
                continue

            if asset in holdings:
                if self.totals[asset] == holdings[asset].quantity:
                    if config.debug:
                        print("%scheck pool: %s (ok)" % (Fore.GREEN, asset))
                else:
                    if config.debug:
                        print("%scheck pool: %s %s (mismatch)" % (
                            Fore.RED, asset,
                            '{:+0,f}'.format((holdings[asset].quantity-
                                              self.totals[asset]).normalize())))

                    self._log_failure(asset, self.totals[asset], holdings[asset].quantity)
                    passed = False
            else:
                if config.debug:
                    print("%scheck pool: %s (missing)" % (Fore.RED, asset))

                self._log_failure(asset, self.totals[asset], None)
                passed = False

        return passed

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
