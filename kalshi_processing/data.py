from datetime import datetime as dt
from datetime import timedelta
from enum import Enum
import csv
import yfinance as yf
from client import ExchangeClient, start_kalshi_api
import pandas as pd

class IndexMarket(Enum):
    SpDailyRange = 1
    SpUpDown = 2
    SpYearlyRange = 3
    NasdaqDailyRange = 4
    NasdaqUpDown = 5
    NasdaqYearlyRange = 6

'''
Gives daily price data for a given ticker
'''      
def get_daily_index_prices(ticker: str, start_date: dt, end_date: dt) -> pd.DataFrame:
    index = yf.Ticker(ticker)
    df = index.history(interval = "1d", start = start_date, end = end_date)
    df.drop('Volume', axis=1, inplace=True)
    df.drop('Dividends', axis=1, inplace=True)
    df.drop('Stock Splits', axis=1, inplace=True)
    return df

'''
Finds all days on which the market is open between the start date and end date
'''
def get_market_days(start_date: dt, end_date: dt) -> pd.DataFrame:
    df = pd.read_csv("data_storage/market_data/market_days.csv", )
    df['market_open']= pd.to_datetime(df['market_open']).dt.tz_convert(None)
    df = df[df['market_open'].between(start_date, end_date)]
    days = df['market_open'].to_list()
    for index, day in enumerate(days):
        days[index] = day.date()
           
'''
Returns a list of lists of the form [market string, start date, end date]
These kalshi markets make up the market over the whole time period and are above the volume threshhold 
'''
def get_sub_markets(account: ExchangeClient, market: IndexMarket, start_date: dt, end_date: dt, interval: dt, volume_threshold: int) -> list[list]:
    if market == IndexMarket.SpUpDown:
        'INXZ-24JAN02-T4769.83'
        #price is the previous day's close
        raise NotImplementedError
    elif market == IndexMarket.NasdaqUpDown:
        raise NotImplementedError
    elif market == IndexMarket.SpDailyRange:
        prices_df = get_daily_index_prices('^SPX', start_date, end_date)
        market_days = get_market_days(start_date, end_date)
        #SP INXD-24JAN05-T4625
    elif market == IndexMarket.NasdaqDailyRange:
        prices_df = get_daily_index_prices('^NDX', start_date, end_date)
        #NDQ NASDAQ100D-24JAN05-T16300
    elif market == IndexMarket.SpYearlyRange or market == IndexMarket.NasdaqYearlyRange:
        pass

'''
Creates a csv for a given market string from start_date to end_date.
Saves files to the data storage folder. 
Assumes market is not currently open.
'''
def create_csv(account: ExchangeClient, market: str, start_date: dt, end_date: dt) -> None:

    # limit issue with pages
    # how will I organize the data storage folder?

    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())
    
    data = account.get_market_history(ticker=market, limit=1000, min_ts=start_timestamp, max_ts=end_timestamp)
    data_dict = data['history']
    
    field_names = ['datetime', 'bid', 'ask', 'open_interest', 'volume']
    csv_name = f'data_storage/kalshi_data/{market}_{start_date}_{end_date}.csv'
    
    with open(csv_name, 'w') as file:
        writer = csv.DictWriter(file, fieldnames = field_names)
        writer.writeheader()
        
        for entry in data_dict:
            modified_entry = {}
            modified_entry['datetime'] = dt.fromtimestamp(entry['ts']).replace(microsecond=0)
            modified_entry['bid'] = entry['yes_bid']
            modified_entry['ask'] = entry['yes_ask']
            modified_entry['open_interest'] = entry['open_interest']
            modified_entry['volume'] = entry['volume']
            writer.writerow(modified_entry)

'''
Creates csvs with kalshi data and writes them to the data_storage folder.
    account: the ExchangeClient representing a kalshi account
    market: the type of index market that will be stored
    start_date: the first time at which to retrieve data (include hour + minute)
    end_date: the last time at which to retrieve data (include hour + minute)
    interval: the interval at which to retrieve data
    volume_threshhold: the % volume of the total event a market must have to be saved
Assumes market is not currently open.
'''
def create_index_market_csvs(market: IndexMarket, start_date: dt, end_date: dt, interval: dt, volume_threshold: int) -> None:
    
    account = start_kalshi_api()
    markets = get_sub_markets(account, market, start_date, end_date, interval, volume_threshold)
    
    for mkt_string, start, end in markets:
        create_csv(account, mkt_string, start, end)

if __name__ == "__main__":
    exchange_client = start_kalshi_api()
    # create_csv(exchange_client, 'INXDU-23AUG15-T4499.99', dt.fromtimestamp(1692104400), dt.fromtimestamp(1692109400))
    # create_csv(exchange_client, 'INXDU-23DEC29-T4749.99', dt(2023, 12, 29, 9, 0, 1), dt(2023, 12, 29, 13, 0, 0))
    # print(exchange_client.get_market_history('INXZ-23DEC26-T4754.63'))


    
    
