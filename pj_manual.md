# General tracing and origin report 

```
# bittytax_conv martino/logs/*/*.csv martino/logs/*/*/*.csv martino/logs/Binance\ Hanne/dep\ \&\ withdrawals/*.xlsx martino/logs/excel\ info\ in\ bitty\ formaat.xlsx --duplicates &> used_files.txt
BITTYFILE="BittyTax_Records-20mei.xlsx"
bittytax $BITTYFILE --skipint -d &> output_verbose.txt
bittytax $BITTYFILE  --nopdf &> output.txt
cat output_verbose.txt | grep "<- transfer" &> transfers.txt
python analyze_transfers.py &> missing_links_new.txt
```
----



# Annual Staking report
Export via https://stake.tax/ in bittytax format

```
bittytax <file> --skipint --taxyear 2022

```
if issues:
```
cat <file> | grep -v "_UNKNOWN" > cleaned.csv
```