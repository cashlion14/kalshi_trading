import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
import datetime
from datetime import time
import os
import re

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
Print out what trades happened on a given day
"""
def print_day_summary(capital, trade_capital, trade_return, bought_price, sold_price, day, market, bought_middle, bought_edge, bought_twice, sold): 
    if bought_middle:
        bought_type = 'Bought in Middle'
    if bought_edge:
        bought_type = 'Bought in Edge'
    if bought_twice:
        bought_type = 'Bought in Middle and then Next'
    if sold:
        bought_type = 'Bought in Middle and then Sold'
    
    print('Day:', day)
    print('Trade Type:', bought_type)
    print('Market:', market[40:58])
    print('Bought', trade_capital, 'contracts at', bought_price)
    print('Sold at', sold_price, "creating a return of", round(100*(round(trade_return - trade_capital,2)/trade_capital), 2), '%')
    print('Ending capital:', capital)
    print('------------------------------------')

"""
Given a datetime and a kalshi dataframe, find the nearest bid and ask entries
"""
def get_nearest_bid_ask(time, df):
    idx = df.index.searchsorted(time, side='left')
    row = df.iloc[idx - 1]
    return row['bid'], row['ask']

def eod_strategy_revised(buy_minute, interval_ratio, ask_low, ask_high, percent_change, capital, bought_floor, capital_ratio):
    loss_dayes = []
    p_losses = 0
    total_days = 0
    losing_days = 0
    middle_days = 0
    middle_twice_days = 0
    middle_sold_days = 0
    edge_days = 0
    count_return = True
    
    market_days = get_market_days(dt(2023, 5, 19, 8, 0, 0), dt(2023, 12, 31, 17, 0, 0))
    months = ['JAN', 'FEB', "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

    spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
    spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

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
        open, close, decision_price = get_stock_info(spx_prices, entry.year, entry.month, entry.day, buy_minute)
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
        middle_df = middle_df.set_index('datetime')
        
        
        #get the middle price of the kalshi_market
        last_slash = 0
        for index, char in enumerate(middle):
            if char == '/':
                last_slash = index
        mkt_string = middle[last_slash+1:]
        
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9.]+', mkt_string)
        kalshi_middle_price = int(price[1:5]) 
        

        beg_price = middle_df.iloc[:1]['ask'].tolist()[0]
        # print(beg_price)
        
        win = abs(close - kalshi_middle_price) < 12.5
        # print(win)
        
        capital_ratio = 0.42
        trade_capital = capital*0.42
        final_price= 100 if win else 0
        percent_return = 0 if not win else 1 + (100-beg_price)/100
        trade_return = trade_capital*percent_return
        
        if trade_return ==0:
            losing_days += 1
        
        if trade_return > 0:
            if count_return:
                capital = capital + trade_return - trade_capital
            count_return = not count_return
        
        
        print(capital, entry)
            
        
    return capital, losing_days/total_days
        
        
    


if __name__ == "__main__":
    b = 76/24
    kellyCriterion = 0.56 - 0.44/b
    # print(kellyCriterion)
    print(eod_strategy_revised(50, 5, 70, 97, 2, 100, 10, 10))

    #where could we take losses
    #if we buy middle:
        #if we buy edge after:
            #it could go through both (unlikely) or it could go back in the other direction
        #if we sell
        #if it doesn't land in the middle
    #if we buy edge: 
    
    #problem with backtester: it assumes profit rather than it jumping through both ranges
    #need to fix that and do more testing to make strategy better
    
    #so we can get a list of one or two bought markets and determine if close was in range
    #can also see how much it is likely to jump and once it gets outside that, we can be sure about buying
    #change arb price to 97?