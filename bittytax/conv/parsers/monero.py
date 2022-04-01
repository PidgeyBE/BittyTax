# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError, UnexpectedTypeError

WALLET = "Monero"


def parse_monero(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['date'])

    symbol = "XMR"

    if row_dict['direction'] == "in":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['amount'],
                                                 buy_asset=symbol,
                                                #  fee_quantity=Decimal(row_dict['TX total']) - \
                                                #               Decimal(row_dict['Value']),
                                                #  fee_asset=symbol,
                                                 wallet=WALLET)
    elif row_dict['direction'] == "out":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=row_dict['amount'],
                                                 sell_asset=symbol,
                                                 fee_quantity=row_dict['fee'],
                                                 fee_asset=symbol,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(parser.in_header.index('direction'), 'direction', row_dict['direction'])


DataParser(DataParser.TYPE_WALLET,
           "Monero",
           ['blockHeight', 'epoch', 'date', 'direction', 'amount', 'atomicAmount', 'fee',
           'txid', 'label', 'subaddrAccount', 'paymentId'],
           worksheet_name="Monero",
           row_handler=parse_monero)
