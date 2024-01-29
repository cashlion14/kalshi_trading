import os
import pandas as pd
from datetime import time
import yfinance as yf
from datetime import datetime as dt
from datetime import timedelta
import re


#get each day
#in each day iterate until the end of the day
#if price is at a certain level, buy it
#if price plumets, sell it
#if eod, check close price and count profit

### use kelly strategy for pricing
### only buy if its unlikely to leave range
#buy days where it will end within the zone, don't buy days where it ends up outside the zone


#buy when the s&p hasn't changed much during the day
#and sell it quickly if it is moving towards to edge

#returns the open, close, and fifteen minutes before price
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

def eod_backtester(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, buy_price, bought_floor):
    capital = 500
    total_return = 0
    total_loss = 0
    p_days = 0
    l_days = 0
    losses = []
    
    spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
    spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

    # datapaths = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD') for f in filenames]
    
    jan = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/JAN') for f in filenames]
    feb = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/FEB') for f in filenames]
    mar = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/MAR') for f in filenames]
    apr = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/APR') for f in filenames]
    may = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/MAY') for f in filenames]
    jun = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/JUN') for f in filenames]
    jul = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/JUL') for f in filenames]
    aug = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/AUG') for f in filenames]
    sep = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/SEP') for f in filenames]
    oct = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/OCT') for f in filenames]
    nov = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/NOV') for f in filenames]
    dec = [os.path.join(dirpath,f) for (dirpath, dirnames, filenames) in os.walk('data_storage/kalshi_data/INXD/23/DEC') for f in filenames]
    
    datapaths = jan + feb + mar + apr + may + jun + jul + aug + sep + oct + nov + dec
    
    
    # Do not include headers when exporting the data

    for datapath in datapaths:
        bought = False
        sold = False
        sold_price = -1
        bought_price = 0
        trade_capital = int(capital * capital_ratio/10)
        
        
        last_slash = 0
        for index, char in enumerate(datapath):
            if char == '/':
                last_slash = index
        mkt_string = datapath[last_slash+1:]
        
        #create the csv name from the mkt_string
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9.]+', mkt_string)
        year = date[:2]
        month = date[2:5]
        day = date[-2:]
        price = int(price[1:5])
        
        #create the start and end times for the current day
        date_year = int('20'+year)
        
        if month == "JAN":
            date_month = 1
        if month == 'FEB':
            date_month = 2
        if month == 'MAR':
            date_month = 3
        if month == 'APR':
            date_month = 4
        if month == 'MAY':
            date_month = 5
        if month == "JUN":
            date_month = 6
        if month == 'JUL':
            date_month = 7
        if month == 'AUG':
            date_month = 8
        if month == 'SEP':
            date_month = 9
        if month == 'OCT':
            date_month = 10
        if month == 'NOV':
            date_month = 11
        if month == "DEC":
            date_month = 12
        
        if day[0] == '0':
            date_day = int(day[1])
        else:
            date_day = int(day)
        
        day = dt(date_year, date_month, date_day)
        if day > dt(2023, 5, 19):
            interval = 13
        else:
            interval = 25
        
        #get day data
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
    
            #if correct time and correct price, buy
            if current_time > time(15, buy_minute, 0):
                #need to be able to get this price
                if ask > ask_low and ask < ask_high and abs(fifbefore-price) < interval*(interval_ratio/10):
                    if 100*(abs(op-close)/op) < percent_change and not bought:
                        bought = True
                        bought_price = ask
            
            #if correct time and correct price, sell
            if current_time > time(15, sell_minute, 0) and (bid >= bid_price or ask < bought_price-bought_floor) and bought:
                if not sold:
                    sold = True
                    sold_price = bid
        
        if bought:
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
                    # print(capital, trade_capital, trade_return, bought_price, sold_price, day)
            
            if trade_return < trade_capital:
                l_days += 1
                losses.append(day)
            elif trade_return > trade_capital:
                p_days += 1
            
            capital = round(capital + trade_return - trade_capital, 2) - 0.01
            print(capital, trade_capital, trade_return, bought_price, sold_price, day)
    
    print(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, bid_price, bought_floor)
    return capital, p_days, l_days, losses
           
if __name__ == "__main__":
    buy_minute = 55
    sell_minute = 56
    #divide by ten, is the ratio u multiply by to get the amount u put down every trade
    capital_ratio = 2
    #divide by 10, its the percent of the range youd buy in (in the middle)
    interval_ratio = 8
    ask_low = 70
    ask_high = 97
    percent_change = 2
    #what will u sell it at
    bid_price = 98
    #if its dropping how far below buy do u wait to sell
    bought_floor = 10
    
    print(eod_backtester(buy_minute, sell_minute, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, bid_price, bought_floor))
    # max_capital = [0]
    # index = 0
    # for capital_ratio in range(1, 6):
    #     for interval_ratio in range(2, 6):
    #         for ask_low in range(65, 86):
    #             for ask_high in range(86, 97):
    #                 for percent_change in range(1, 3):
    #                     for buy_price in range(97, 100):
    #                         for bought_floor in range(2, 15):
    #                             print(f'running trial {index}')
    #                             capital = eod_backtester(capital_ratio, interval_ratio, ask_low, ask_high, percent_change, buy_price, bought_floor)
    #                             print(capital, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, buy_price, bought_floor)
    #                             if capital > max_capital[0]:
    #                                 max_capital = [capital, capital_ratio, interval_ratio, ask_low, ask_high, percent_change, buy_price, 10]
    #                             index += 1
    # print(max_capital)

    #2, 5, 93, 97, 2, 98, 5
    #if it moves out of our interval sell & buy the next one over
    #dynamically change the amount we are betting each day
    #53, 54, 2, 6/8, 80, 97, 98, 5
    
    #fix stupid code
    #clean up print statements
    #clean up the github
    #run the backtest into 2024
    
    #buy the one it's moving into
    #big wins small losses strategy
    #dynamically change paramaters (amount we're betting) -> bet less on uncertain days
    
    #same thing with above and below
    #paper trade?
    #real trade
    #same thing on the NASDAQ
    