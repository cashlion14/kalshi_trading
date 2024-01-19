import os
import pandas as pd
from datetime import time
import yfinance as yf
from datetime import datetime as dt
import re


#BASIC STRATEGY

#get each day
#in each day iterate until the end of the day
#if, after a certain time of the day (usually ~3:50) the price is at a certain level, buy it
#if price plumets afterwards, sell it
#if eod, check close price and count profit

# only buy if its unlikely to leave range (current in middle of range) and S&P hasn't moved much
#buy days where it will end within the zone, don't buy days where it ends up outside the zone


months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']

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

def get_datapaths():
    datapaths = []
    for month in months_array:
        datapaths += [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/' + month) for f in filenames]
    return datapaths

def calculate_return(sold_price,sold,bought_price,trade_capital,price,close,interval):
    if sold:
        percent_return = 1 + ((sold_price-bought_price) / 100)
        trade_return = trade_capital * percent_return
    else:
        
        if abs(price-close) < interval:
            #goes to 1
            percent_return = 1 + ((100-bought_price) / 100)
            trade_return = trade_capital * percent_return
            sold_price = 100
        else:
            trade_return = 0
            sold_price = 0
            
    return percent_return,trade_return,sold_price


def print_day_summary(capital, trade_capital, trade_return, bought_price, sold_price, day):
    print('Day:', day)
    print('Bought', trade_capital, 'contracts at', bought_price)
    print('Sold at', sold_price, "creating a return of", round(trade_return - trade_capital,2))
    print('Ending capital:', capital)
    print('------------------------------------')


def eod_backtester(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, sell_price, bought_floor):
    capital = 100
    p_days = 0
    l_days = 0
    losses = []
    
    spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
    spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

    # datapaths = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD') for f in filenames]
    
    datapaths = get_datapaths()
    
    for datapath in datapaths:
        #initialize variables for each day
        bought = False
        sold = False
        sold_price = -1
        bought_price = 0
        trade_capital = int(capital * capital_ratio/10)
        
        
        last_slash = datapath.rfind('/')
        mkt_string = datapath[last_slash+1:]
        
        #create the csv name from the mkt_string
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9.]+', mkt_string)
        year = date[:2]
        month = date[2:5]
        day = date[-2:]
        price = int(price[1:5])
        
        #create the start and end times for the current day
        date_year = int('20'+year)
        date_month = months_array.index(month) + 1 
        
        if day[0] == '0':
            date_day = int(day[1])
        else:
            date_day = int(day)
        
        day = dt(date_year, date_month, date_day)
        if day > dt(2023, 5, 19):
            interval = 13
        else:
            interval = 25
        
        #get day data --> this takes a long time
        df = pd.read_csv(datapath)
        df.reset_index()
        df['datetime']= pd.to_datetime(df['datetime'])
        op, close, fifbefore = get_stock_info(spx_prices, date_year, date_month, date_day, buy_minute)
        
        if op == 0 and close == 0 and fifbefore == 0:
            continue
        
        #go through each entry in database
        for index, row in df.iterrows():
            current_time = row['datetime'].time()
            ask = row['ask']
            bid = row['bid']
    
    
            #THIS IS THE STRATEGY
            
            #if correct time
            if current_time > time(15, buy_minute, 0):
                #if price is in ask range and S&P price is within the middle interval_ratio of the market range
                if ask > ask_low and ask < ask_high and abs(fifbefore-price) < interval*(interval_ratio/10):
                    #if the S&P hasn't moved more than percent_change in the day and haven't bought yet
                    if 100*(abs(op-close)/op) < percent_change and not bought:
                        #buy the stock at this price
                        bought = True
                        bought_price = ask
            
            #if within the time bounds
            if current_time > time(15, sell_minute, 0):
                #if can sell above our threshold price or have lost bought_floor amount of money, sell
                if(bid >= sell_price or ask < bought_price-bought_floor) and bought:
                    if not sold:
                        sold = True
                        sold_price = bid
        
        
        #calculate returns
        if bought:
            percent_return,trade_return,sold_price = calculate_return(sold_price,sold,bought_price,trade_capital,price,close,interval)
            
            #update day counters and new capital value
            if trade_return < trade_capital:
                l_days += 1
                losses.append(day)
            elif trade_return > trade_capital:
                p_days += 1
            
            capital = round(capital + trade_return - trade_capital, 2) - 0.01
            print_day_summary(capital, trade_capital, trade_return, bought_price, sold_price, day)
    
    print(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, bid_price, bought_floor)
    return capital, p_days, l_days, losses


if __name__ == "__main__":
    buy_minute = 55
    sell_minute = 56
    capital_ratio = 2 #divide by ten, is the ratio u multiply by to get the amount u put down every trade
    interval_ratio = 8 #divide by 10, its the percent of the range youd buy in (in the middle)
    ask_low = 70
    ask_high = 97
    percent_change = 2
    bid_price = 98 #what will u sell it at
    bought_floor = 10 #if its dropping how far below buy do u wait to sell
    print(eod_backtester(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, bid_price, bought_floor))