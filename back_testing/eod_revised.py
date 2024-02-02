import pandas as pd
from datetime import timedelta
from datetime import datetime as dt
import datetime
from datetime import time
import os
import re

#every day
#get the open, price near end, and close price
#initial could be 

#right now we are selling when the price drops. 
#what if we instead sold it when it got closer to edge?
#idea is what if we bought the market next door

#go through each day
#get open, close, min before price
#find market it is in and the market it is near
#run through the market that the price is in
#write function to get nearest price in the other market

#at a certain minute analyze whether to buy
#then once that decision is made determine when or if to sell


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
        bought_type = 'Bought in Middle Section'
    if bought_edge:
        bought_type = 'Bought in Edge Section'
    if bought_twice:
        bought_type = 'Bought in Middle Section and then Bought Next Section'
    if sold:
        bought_type = 'Bought in Middle Section and then Sold'
    
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
    trading_days = 0
    
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
        
        #set the interval for the market
        if entry > datetime.date(2023, 5, 19):
            interval = 13
        else:
            interval = 25

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
        
        lower_df = pd.read_csv(lower)
        lower_df.reset_index()
        lower_df['datetime']= pd.to_datetime(lower_df['datetime'])
        lower_df = lower_df.set_index('datetime')
        
        higher_df = pd.read_csv(higher)
        higher_df.reset_index()
        higher_df['datetime']= pd.to_datetime(higher_df['datetime'])
        higher_df = higher_df.set_index('datetime')
        
        #get the middle price of the kalshi_market
        last_slash = 0
        for index, char in enumerate(middle):
            if char == '/':
                last_slash = index
        mkt_string = middle[last_slash+1:]
        
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9.]+', mkt_string)
        kalshi_middle_price = int(price[1:5]) 
        
        bought_middle = False
        bought_edge = False
        bought_twice = False
        current_spx = decision_price
        sold = False
        sold_price = None
        
        #go through each entry in database
        for index, row in middle_df.iterrows():
            current_dt = index
            current_time = index.time()
            middle_ask = row['ask']
            middle_bid = row['bid']
            
            #start deciding whether to trade
            if current_time > time(15, buy_minute, 0):
                lower_bid, lower_ask = get_nearest_bid_ask(current_dt, lower_df)
                higher_bid, higher_ask = get_nearest_bid_ask(current_dt, higher_df)
                open, close, current_spx = get_stock_info(spx_prices, 2023, entry.month, entry.day, current_time.minute)
                is_in_middle_range = abs(current_spx-kalshi_middle_price) < interval*(interval_ratio/10)
                
                if is_in_middle_range:
                    if middle_ask > ask_low and middle_ask < ask_high and not bought_middle and not bought_edge and 100*(abs(open-close)/open) < percent_change:
                        bought_price = middle_ask
                        bought_middle = True
                else:
                    higher = current_spx - kalshi_middle_price > 0
                    side_ask = higher_ask if higher else lower_ask
                    if middle_ask + side_ask < 99 and not bought_middle and not bought_edge:
                        bought_price = middle_ask + side_ask
                        bought_edge = True
                
                if bought_middle and not is_in_middle_range:
                    higher = current_spx - kalshi_middle_price > 0
                    side_ask = higher_ask if higher else lower_ask
                    if abs(current_spx - kalshi_middle_price) > 10 and bought_price + side_ask < 98 and not sold and not bought_twice:
                        bought_price += side_ask
                        bought_twice = True
                    elif not sold and not bought_twice and middle_ask < bought_price-bought_floor:
                        sell_loss = middle_bid - bought_price
                        double_loss = 100 - bought_price - side_ask
            
                        if sell_loss > double_loss:
                            sold = True
                            sold_price = middle_bid
                        else:
                            bought_twice = True
                            bought_price += side_ask
        
        #determine final profitability
        if bought_middle or bought_edge:
            trading_days += 1
            trade_capital = capital * (capital_ratio/10)
            if bought_middle:
                if bought_twice:
                    percent_return = 1 + (100-bought_price)/100
                    trade_return = trade_capital * percent_return
                elif sold:
                    percent_return = 1 + (sold_price-bought_price)/100
                    trade_return = trade_capital * percent_return
                else:
                    if abs(close-kalshi_middle_price) < 12.5:
                        percent_return = 1 + (100-bought_price)/100
                        trade_return = trade_capital * percent_return
                    else:
                        raise Exception('ruh roh')
            if bought_edge:
                percent_return = 1 + (100-bought_price)/100
                trade_return = trade_capital * percent_return
                
                
            capital = capital + trade_return - trade_capital
            if trade_return < trade_capital:
                p_losses += 1
                loss_dayes.append(entry)
                
            if sold_price is None:
                sold_price = 100
            print_day_summary(capital, trade_capital, trade_return, bought_price, sold_price, entry, middle, bought_middle, bought_edge, bought_twice, sold)
    
    return capital, 100*(p_losses/trading_days), 100*(trading_days/total_days), loss_dayes
             
                 
if __name__ == "__main__":
    print(eod_strategy_revised(50, 5, 70, 97, 2, 100, 10, 2))
    
    