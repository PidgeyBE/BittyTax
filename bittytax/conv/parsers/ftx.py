# -*- coding: utf-8 -*-
from decimal import Decimal

from bittytax.conv.dataparser import DataParser
from bittytax.conv.exceptions import UnexpectedTypeError
from bittytax.conv.out_record import TransactionOutRecord


WALLET = "FTX"


def parse_ftx_deposits_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict.get('time', row_dict["Time"]), dayfirst=True)

    if row_dict.get('status', row_dict["Status"]) not in ('complete', 'confirmed'):
        return
    
    t_type =  TransactionOutRecord.TYPE_DEPOSIT
    if row_dict.get("coin", row_dict["Coin"]) == "SRM_LOCKED":
        t_type = TransactionOutRecord.TYPE_AIRDROP

    data_row.t_record = TransactionOutRecord(t_type,
                                             data_row.timestamp,
                                             buy_asset=row_dict.get("coin", row_dict["Coin"]),
                                             buy_quantity=row_dict.get("size", row_dict["Amount"]),
                                             wallet=WALLET,
                                             note=row_dict.get('txid', row_dict["Transaction ID"]))


def parse_ftx_withdrawals_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict.get('time', row_dict["Time"]))

    if row_dict.get('status', row_dict["Status"]) != 'complete':
        return

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_asset=row_dict.get("coin", row_dict["Coin"]),
                                             sell_quantity=row_dict.get("size", row_dict["Amount"]),
                                             fee_asset=row_dict.get("coin", row_dict["Coin"]),
                                             fee_quantity=row_dict['fee'] or '0',
                                             wallet=WALLET,
                                             note=row_dict.get('txid', row_dict["Transaction ID"]))


def parse_ftx_trades_crypto(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time'])

    if '/' in row_dict['Market']:
        # Spot (BTC/USD)
        base_asset, quote_asset = row_dict['Market'].split('/')
    else:
        # Futures (BTC-PERP / BTC-2131)
        base_asset = row_dict['Market']
        quote_asset = row_dict['Fee Currency']

    if row_dict['Side'] == 'buy':
        sell_quantity = row_dict['Total']
        if sell_quantity == 0 and float(row_dict['Fee']) == 0:
            record_type = TransactionOutRecord.TYPE_AIRDROP
            sell_asset = fee_asset = ''
            sell_quantity = fee_quantity = None
        else:
            record_type = TransactionOutRecord.TYPE_TRADE
            sell_asset = quote_asset
            fee_asset = row_dict['Fee Currency']
            fee_quantity = row_dict['Fee']

        data_row.t_record = TransactionOutRecord(record_type,
                                                 data_row.timestamp,
                                                 buy_asset=base_asset,
                                                 buy_quantity=row_dict['Size'],
                                                 sell_asset=sell_asset,
                                                 sell_quantity=sell_quantity,
                                                 fee_asset=fee_asset,
                                                 fee_quantity=fee_quantity,
                                                 wallet=WALLET,
                                                 note=row_dict['Order Type'])
    elif row_dict['Side'] == 'sell':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_asset=quote_asset,
                                                 buy_quantity=row_dict['Total'],
                                                 sell_asset=base_asset,
                                                 sell_quantity=row_dict['Size'],
                                                 fee_asset=row_dict['Fee Currency'],
                                                 fee_quantity=row_dict['Fee'],
                                                 wallet=WALLET,
                                                 note=row_dict['Order Type'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('Order Type'), 'Order Type', row_dict['Order Type'])

def parse_ftx_trades_crypto_v2(data_row, parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['createdAt'])

    if '/' in row_dict['market']:
        # Spot (BTC/USD)
        base_asset, quote_asset = row_dict['market'].split('/')
    else:
        # Futures (BTC-PERP / BTC-2131)
        base_asset = row_dict['market']
        quote_asset = row_dict['feeCurrency']

    if row_dict['side'] == 'buy':
        sell_quantity = row_dict['total']
        if sell_quantity == 0 and float(row_dict['fee']) == 0:
            record_type = TransactionOutRecord.TYPE_AIRDROP
            sell_asset = fee_asset = ''
            sell_quantity = fee_quantity = None
        else:
            record_type = TransactionOutRecord.TYPE_TRADE
            sell_asset = quote_asset
            fee_asset = row_dict['feeCurrency']
            fee_quantity = row_dict['fee']

        data_row.t_record = TransactionOutRecord(record_type,
                                                 data_row.timestamp,
                                                 buy_asset=base_asset,
                                                 buy_quantity=row_dict['size'],
                                                 sell_asset=sell_asset,
                                                 sell_quantity=sell_quantity,
                                                 fee_asset=fee_asset,
                                                 fee_quantity=fee_quantity,
                                                 wallet=WALLET,
                                                 note=row_dict['type'])
    elif row_dict['side'] == 'sell':
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_asset=quote_asset,
                                                 buy_quantity=row_dict['total'],
                                                 sell_asset=base_asset,
                                                 sell_quantity=row_dict['size'],
                                                 fee_asset=row_dict['feeCurrency'],
                                                 fee_quantity=row_dict['fee'],
                                                 wallet=WALLET,
                                                 note=row_dict['type'])
    else:
        raise UnexpectedTypeError(parser.in_header.index('type'), 'type', row_dict['type'])

def parse_ftx_dust_conversion_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])
    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                             data_row.timestamp,
                                             buy_asset=row_dict['to'],
                                             buy_quantity=row_dict['proceeds'],
                                             sell_asset=row_dict['from'],
                                             sell_quantity=row_dict['size'],
                                             fee_asset=row_dict['to'],  # A guess
                                             fee_quantity=row_dict['fee'],
                                             wallet=WALLET)


def parse_ftx_funding_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])

    payment = Decimal(row_dict['payment'])
    if payment > 0:
        # Getting paid by other side
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_asset='USD',   # No non-USD future markers at the moment
                                                 buy_quantity=payment,
                                                 sell_asset=row_dict['future'],
                                                 sell_quantity=0,
                                                 wallet=WALLET,
                                                 note='Funding fee')
    else:
        # Paying to the other side
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_asset=row_dict['future'],
                                                 buy_quantity=0,
                                                 sell_asset='USD',
                                                 sell_quantity=abs(payment),
                                                 wallet=WALLET,
                                                 note='Funding fee')


def parse_ftx_lending_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['time'])
    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                             data_row.timestamp,
                                             buy_asset=row_dict['coin'],
                                             buy_quantity=row_dict['proceeds'],
                                             fee_asset='USD',
                                             fee_quantity=row_dict['feeUsd'],
                                             wallet=WALLET)


def parse_ftx_staking_crypto(data_row, _parser, **kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict['Time'])
    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_STAKING,
                                                 data_row.timestamp,
                                                 buy_quantity=row_dict['Reward'],
                                                 buy_asset=row_dict['Coin'],
                                                 wallet=WALLET,
                                                 note=row_dict['Notes'])

DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Deposits',
           ['id', 'time', 'coin', 'size', 'status', 'additionalInfo', 'txid', '_delete'],
           worksheet_name='FTX D',
           row_handler=parse_ftx_deposits_crypto)


DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Deposits',
           ['', 'Time', 'Coin', 'Amount', 'Status', 'Additional info', 'Transaction ID', ''],
           worksheet_name='FTX D',
           row_handler=parse_ftx_deposits_crypto)


DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Withdrawals',
           ['time', 'coin', 'size', 'address', 'status', 'txid', 'fee', 'id'],
           worksheet_name='FTX W',
           row_handler=parse_ftx_withdrawals_crypto)


DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Withdrawals',
           ['Time', 'Coin', 'Amount', 'Destination', 'Status', 'Transaction ID', 'fee', ''],
           worksheet_name='FTX W',
           row_handler=parse_ftx_withdrawals_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Trades',
           ['id', 'time', 'market', 'side', 'type', 'size', 'price', 'total', 'fee', 'feeCurrency'],
           worksheet_name='FTX T',
           row_handler=parse_ftx_trades_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Trades',
           ['ID', 'Time', 'Market', 'Side', 'Order Type', 'Size', 'Price', 'Total', 'Fee', 'Fee Currency'],
           worksheet_name='FTX T',
           row_handler=parse_ftx_trades_crypto)

# FTX order history.csv 
# DataParser(DataParser.TYPE_EXCHANGE,
#            'FTX Trades',
#            ['id', 'clientId', 'createdAt', 'market', 'side', 'size', 'type',
#            'filledSize', 'size', 'avgFillPrice', 'price', 'status', 'ioc', 'postOnly', 'reduceOnly'],
#            worksheet_name='FTX T',
#            row_handler=parse_ftx_trades_crypto_v2)

# Not actually necessary as dust conversion is exported with trades with a note "OTC".
# DataParser(DataParser.TYPE_EXCHANGE,
#            'FTX Dust Conversion',
#            ['time', 'from', 'to', 'size', 'fee', 'price', 'proceeds', 'status'],
#            worksheet_name='FTX DC',
#            row_handler=parse_ftx_dust_conversion_crypto)


DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Funding',
           ['time', 'future', 'payment', 'rate'],
           worksheet_name='FTX F',
           row_handler=parse_ftx_funding_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Lending Interest',
           ['time', 'coin', 'size', 'rate', 'proceeds', 'feeUsd'],
           worksheet_name='FTX L',
           row_handler=parse_ftx_lending_crypto)

DataParser(DataParser.TYPE_EXCHANGE,
           'FTX Staking',
           ['Time', 'Notes', 'Coin', 'Reward'],
           worksheet_name='FTX St',
           row_handler=parse_ftx_staking_crypto)