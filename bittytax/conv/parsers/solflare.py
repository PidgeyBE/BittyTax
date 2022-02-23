# -*- coding: utf-8 -*-
from decimal import Decimal

from bittytax.conv.dataparser import DataParser
from bittytax.conv.exceptions import UnexpectedTypeError
from bittytax.conv.out_record import TransactionOutRecord


WALLET = "Solflare"


def parse_solflare(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["timestamp"])

    if row_dict["tx_type"] == "STAKING":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_STAKING,
                                                data_row.timestamp,
                                                buy_asset=row_dict["received_currency"],
                                                buy_quantity=row_dict["received_amount"],
                                                wallet=WALLET,
                                                note=row_dict["txid"])

    elif row_dict["tx_type"] == "TRANSFER":
        if len(str(row_dict["received_amount"])):
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                    data_row.timestamp,
                                                    buy_asset=row_dict["received_currency"],
                                                    buy_quantity=row_dict["received_amount"],
                                                    wallet=WALLET,
                                                    note=row_dict["txid"])
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                    data_row.timestamp,
                                                    sell_asset=row_dict["sent_currency"],
                                                    sell_quantity=row_dict["sent_amount"],
                                                    fee_asset=row_dict["fee_currency"],
                                                    fee_quantity=row_dict["fee"],
                                                    wallet=WALLET,
                                                    note=row_dict["txid"])
    elif row_dict["tx_type"] in ["_INIT_ACCOUNT", "_STAKING_DELEGATE"]:
        # dunno what to do yet
        pass
    else:
        raise UnexpectedTypeError(0, 'Type', row_dict["tx_type"])


DataParser(DataParser.TYPE_EXCHANGE,
           'Solflare',
           ['timestamp', 'tx_type', 'taxable', 'received_amount', 'received_currency', 'sent_amount', 'sent_currency', 'fee', 'fee_currency', 'comment', 'txid', 'url', 'exchange', 'wallet_address'],
           worksheet_name='Solflare',
           row_handler=parse_solflare)

