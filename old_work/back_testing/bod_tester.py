import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
import os
import re

#go through every day, take the average price of the market that it starts in
#tabulate the number of days that the market ends correctly versus total

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
Given markets and the current s&p price, returns path names for current market as well as market above and below.
"""
def find_current_and_nearest_market(datapaths, current_price): 
    best_datapath = ''
    min_dist = 1000
    
    last_dash = datapaths[0].rfind('-')
    datapaths.sort(key=lambda datapath: int(datapath[last_dash+2:last_dash+6]))
    
    for datapath in datapaths:
        market_price = int(datapath[last_dash+2:last_dash+6])
        distance = abs(market_price - current_price)
        
        if distance < min_dist:
            min_dist = distance
            best_datapath = datapath
            higher = current_price > market_price

    for index, entry in enumerate(datapaths):
        if entry == best_datapath:
            try:
                higher = datapaths[index+1]
            except:
                lower = datapaths[index-1]
                return lower, best_datapath, ""
            try:
                lower = datapaths[index-1]
            except:
                higher = datapaths[index+1]
                return "", best_datapath, higher
    
    return lower, best_datapath, higher

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


def bod_tester():
    
    market_days = get_market_days(dt(2023, 5, 19, 8, 0, 0), dt(2023, 12, 31, 17, 0, 0))
    months = ['JAN', 'FEB', "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
    spx_prices['Time']= pd.to_datetime(spx_prices['Time'])
    total_days = 0
    end_same_days = 0
    total_cost = 0
    
    for entry in market_days:
        
        total_days += 1
        month = months[entry.month-1]
        day = entry.day
        if day < 10:
            day = '0' + str(day)
            
            
        #find the given day's datapaths
        datapaths = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk(f'data_storage/kalshi_data/INXD/23/{month}/{day}') for f in filenames]
        if len(datapaths) == 0:
            continue
        
        #get initial s&p prices
        open, close, decision_price = get_stock_info(spx_prices, entry.year, entry.month, entry.day, 55)
        if open == 0 and close == 0 and decision_price == 0:
            continue
        
        # nearest can be empty string if market was at top of range
        lower, middle, higher = find_current_and_nearest_market(datapaths, decision_price)
        if lower == "" or higher == "":
            continue
        
        # get day data --> this takes a long time
        middle_df = pd.read_csv(middle)
        middle_df.reset_index()
        middle_df['datetime']= pd.to_datetime(middle_df['datetime'])
        # middle_df = middle_df.set_index('datetime')
        
        
        #get the middle price of the kalshi_market
        last_slash = 0
        for index, char in enumerate(middle):
            if char == '/':
                last_slash = index
        mkt_string = middle[last_slash+1:]
        
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9.]+', mkt_string)
        kalshi_middle_price = int(price[1:5]) 
        print(kalshi_middle_price)
        print(close)
        
        if abs(close - kalshi_middle_price) < 12.5:
            end_same_days += 1
        
        beg_price = middle_df.iloc[:1]['ask'].tolist()[0] 
        total_cost += beg_price/100
    
    print(total_days, end_same_days, total_cost)
    print(end_same_days/total_days, total_cost/total_days)
    
bod_tester()