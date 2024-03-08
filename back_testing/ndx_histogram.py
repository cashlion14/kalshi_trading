
#build a histogram of daily beginning ndx prices

import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import timedelta
import pandas as pd
from datetime import datetime as dt

'''
Finds all days on which the market is open between the start date and end date
Returns a list of date objects
'''
def get_market_days(start_date, end_date) -> list:
    df = pd.read_csv("data_storage/market_data/market_days.csv", )
    
    #conversion to allow between comparison
    df['market_open']= pd.to_datetime(df['market_open']).dt.tz_convert(None)
    
    #find all market days within range
    df = df[df['market_open'].between(start_date, end_date+timedelta(1))]
    days = df['market_open'].to_list()
    
    #change format and return
    for index, day in enumerate(days):
        days[index] = day.date()
    return days

"""
Returns open, close, and current price of the s&p. Returns 0, 0, 0 if data unavailable.
"""
def get_stock_info(df, year, month, day, buy_minute):
    df = df[df['Time'].between(dt(year, month, day, 9, 30, 0), dt(year, month, day, 16, 00, 0))]
    
    close = df['Last'].to_list()[0]
    opens = df['Open'].to_list()
    open = opens[-1]
    
    try:
        df = df[df['Time'].between(dt(year, month, day, 15, buy_minute, 0), dt(year, month, day, 15, buy_minute, 0))]
        fifbefore = df['Open'].to_list()[0]
    except:
        # print(year, month, day)
        return 0, 0, 0 
    
    return open, close, fifbefore


market_days = get_market_days(dt(2023, 5, 19, 8, 0, 0), dt(2023, 12, 31, 17, 0, 0))
months = ['JAN', 'FEB', "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

spx_prices = pd.read_csv('data_storage/market_data/combined_ndx.csv')
spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

days_data = []
data = []
for entry in market_days:
        month = months[entry.month-1]
        day = entry.day
        if day < 10:
            day = '0' + str(day)

        datapaths = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(f'data_storage/kalshi_data/NASDAQ100D/23/{month}/{day}') for f in filenames]
        if len(datapaths) == 0:
            continue
        
        #get initial s&p prices
        open, close, decision_price = get_stock_info(spx_prices, entry.year, entry.month, entry.day, 50)
        if open == 0 and close == 0 and decision_price == 0:
            continue
        
        
        closest = 0
        for datapath in datapaths:
            print(open, datapath[-9:-4])
            if abs(open - int(datapath[-9:-4])) < 50:
                closest = datapath
        
        if closest==0:
            continue
                
        # Read the file into a pandas DataFrame
        df = pd.read_csv(closest)

        # Get the first value in the 'Open' column
        average_first_ten = df['ask'].iloc[:50].mean()
        data.append(average_first_ten)
        days_data.append((entry, average_first_ten))
        
    

days_data.sort(key= lambda entry : entry[1])
print(days_data)
print(sum(data)/len(data))


 
# Plotting a basic histogram
plt.hist(data, bins=50, color='skyblue', edgecolor='black')
 
# Adding labels and title
plt.xlabel('Values')
plt.ylabel('Frequency')
plt.title('Basic Histogram')
 
# Display the plot
plt.show()