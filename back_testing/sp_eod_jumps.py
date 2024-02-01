import pandas as pd
from datetime import date
from datetime import time


spx_string = "data_storage/market_data/combined_spx.csv"

#get prices
#every day get high and low price in last five minutes of the day
#calculate difference
#add to counter variables

spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

new_day = True
did_today = False
total_days = 0
jump_days = 0

current_min = 100000
current_max = 0
current_day = 0
for index, row in spx_prices.iterrows():
    if new_day:
        total_days += 1
        current_min = 100000
        current_max = 0
        current_day = row['Time'].date()
        new_day = False
        print(row['Time'])
    else:
        if row['Time'].time() >= time(15, 55, 0) and row['Time'].time() <= time(16, 0, 0):
            if row['Time'].date() != current_day:
                new_day = True
                did_today = False
                continue
            
            if row['Low'] < current_min:
                current_min = row['Low']
            if row['High'] > current_max:
                current_max = row['High']
            
            if current_max-current_min > 7 and not did_today:
                print(current_max, current_min)
                jump_days += 1
                did_today = True
        
print(100*(jump_days/total_days))

#7 point jump ~10% of the time on last 5
#20 point jump 0% on last 5, 3% on last 15