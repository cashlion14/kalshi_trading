from datetime import datetime as dt
from datetime import timedelta
from enum import Enum
import csv
import yfinance as yf
from client import ExchangeClient, start_kalshi_api
import pandas as pd
import re

class IndexMarket(Enum):
    SpDailyRange = 1
    SpUpDown = 2
    SpYearlyRange = 3
    SpAboveBelow = 4
    NasdaqDailyRange = 5
    NasdaqUpDown = 6
    NasdaqYearlyRange = 7
    NasdaqAboveBelow = 8
    
class IndexInterval(Enum):
    OneMin = 1
    ThreeMin = 2
    FiveMin = 3
    FifteenMin = 4
    OneHour = 5

### HELPER FUNCTIONS ###

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
Returns a list of date objects
'''
def get_market_days(start_date: dt, end_date: dt) -> list:
    df = pd.read_csv("data_storage/market_data/market_days.csv", )
    df['market_open']= pd.to_datetime(df['market_open']).dt.tz_convert(None)
    df = df[df['market_open'].between(start_date, end_date+timedelta(1))]
    days = df['market_open'].to_list()
    for index, day in enumerate(days):
        days[index] = day.date()
    return days

'''
Takes in a list market days as date objects and returns a list of kalshi date strings
'''
def market_to_kalshi_dates(market_days: list) -> list:
    kalshi_days = []
    for market_day in market_days:
        year = str(market_day.year)[-2:]
        month = market_day.month
        
        if month == 1:
            month = 'JAN'
        if month == 2:
            month = 'FEB'
        if month == 3:
            month = 'MAR'
        if month == 4:
            month = 'APR'
        if month == 5:
            month = 'MAY'
        if month == 6:
            month = 'JUN'
        if month == 7:
            month = 'JUL'
        if month == 8:
            month = 'AUG'
        if month == 9:
            month = 'SEP'
        if month == 10:
            month = 'OCT'
        if month == 11:
            month = 'NOV'
        if month == 12:
            month = 'DEC'

        day = market_day.day
        if day < 10:
            day = '0' + str(day)
        else:
            day = str(day)
    
        kalshi_days.append(year+month+day)
    return kalshi_days

'''
Returns a list of market strings for s&p or nasdaq up/down markets
Known issue: up/down markets are not open some days due to low vol, which means ~1/3 days throw errors
'''
def get_up_down_sub_markets(yf_ticker: str, kalshi_ticker: str, start_date: dt, end_date: dt, market_days: list) -> list[str]:
    #get prices for all of the market days btwn start and end date, plus the preceeding day or two
    prices = get_daily_index_prices(yf_ticker, start_date, end_date)['Close'].tolist()
    preprices = get_daily_index_prices(yf_ticker, start_date-timedelta(3), start_date-timedelta(1))['Close'].tolist()
    
    market_tickers = market_to_kalshi_dates(market_days)
    
    #create the first ticker using the prev day's price
    markets = []    
    ticker = market_tickers[0]
    price = round(preprices[-1], 2)
    if str(price)[-2] == '.':
        price = str(price) + '0'
    markets.append(f'{kalshi_ticker}-{ticker}-T{price}')
    
    #create all tickers
    for index in range(len(market_tickers)):
        if index == 0:
            continue
        ticker = market_tickers[index]
        price = round(prices[index-1], 2)
        
        #if rounded to a 0 in hundredths place, add the 0
        if str(price)[-2] == '.':
            price = str(price) + '0'

        markets.append(f'{kalshi_ticker}-{ticker}-T{price}')
    return markets

'''
Returns a list of market strings for s&p or nasdaq yearly range markets
Known issue: Nasdaq 2022 yearly range market does not have enough vol
'''
def get_yearly_range_sub_markets(year_to_ticker: dict, start_date: dt, end_date: dt) -> list[str]:
    start_year = start_date.year
    end_year = end_date.year
    years_requested = list(range(start_year, end_year+1))
    
    markets = []
    for year in years_requested:
        markets.append(year_to_ticker[year])
    return markets

'''
Finds all prices that a Kalshi s&p market could exist at between that day's high and low prices
'''
def find_sp_daily_range_prices(markets: list, start_date: dt, high_prices: list, low_prices: list, market_tickers: list):
    #before May 19th 2023 markets are 50 points wide, after they are 25 wide
    before_051923 = start_date < dt(2023, 5, 19, 9, 30, 0)
    
    for high, low, ticker in zip(high_prices, low_prices, market_tickers):
        if ticker == '23MAY19':
            before_051923 = False
            
        if before_051923:
            if low % 100 > 25 and low % 100 < 75:
                first_price = int(str(low)[:2]+'25')
            else:
                first_price = int(str(low)[:2]+'75')
            
            price = first_price
            while price <= high:
                markets.append(f'INXD-{ticker}-B{price}')
                price += 50
                
        else: 
            if low % 100 > 12 and low % 100 < 37:
                first_price = int(str(low)[:2]+'12')
            elif low % 100 >=37 and low % 100 < 62:
                first_price = int(str(low)[:2]+'37')
            elif low % 100 >= 62 and low % 100 < 87:
                first_price = int(str(low)[:2]+'62')
            else:
                first_price = int(str(low)[:2]+'87')
            
            price = first_price
            while price <= high:
                markets.append(f'INXD-{ticker}-B{price}')
                price += 25
                
    return markets

'''
Finds all prices that a Kalshi nasdaq market could exist at between that day's high and low prices
'''
def find_nd_daily_range_prices(markets: list, high_prices: list, low_prices: list, market_tickers: list):
    
    for high, low, ticker in zip(high_prices, low_prices, market_tickers):
        
        first_price = int(str(low)[:2]+str(int(str(low)[2])-1)+'50')
        
        price = first_price
        while price <= high:
            markets.append(f'NASDAQ100D-{ticker}-B{price}')
            price += 100
                
    return markets

'''
Returns a list of market strings for s&p or nasdaq daily range markets
Known issue: some random SPX days use ticker INDW instead of INDX, causing some errors
'''
def get_daily_range_sub_markets(market_days: list, market: IndexMarket, yf_ticker: str, start_date: dt, end_date: dt):
    prices_df = get_daily_index_prices(yf_ticker, start_date, end_date)
        
    high_prices = prices_df['High'].tolist()
    low_prices = prices_df['Low'].tolist()
    
    market_tickers = market_to_kalshi_dates(market_days)
    markets = []
    
    if market == IndexMarket.SpDailyRange:
        return find_sp_daily_range_prices(markets, start_date, high_prices, low_prices, market_tickers)
    else:
        return find_nd_daily_range_prices(markets, high_prices, low_prices, market_tickers)

'''
Returns a list of markets strings
These kalshi markets make up the market over the whole time period
'''
def get_sub_markets(account: ExchangeClient, market: IndexMarket, start_date: dt, end_date: dt) -> list[str]:
    market_days = get_market_days(start_date, end_date)
    
    if market == IndexMarket.SpUpDown:
        return get_up_down_sub_markets('^SPX', 'INXZ', start_date, end_date, market_days)
    
    elif market == IndexMarket.NasdaqUpDown:
        return get_up_down_sub_markets('^NDX', 'NASDAQ100Z', start_date, end_date, market_days)
    
    elif market == IndexMarket.SpDailyRange:
        return get_daily_range_sub_markets(market_days, market, '^SPX', start_date, end_date)
        
    elif market == IndexMarket.NasdaqDailyRange:
        return get_daily_range_sub_markets(market_days, market, '^NDX', start_date, end_date)
        
    elif market == IndexMarket.SpAboveBelow:
        pass
    
    elif market == IndexMarket.NasdaqAboveBelow:
        pass
        
    elif market == IndexMarket.SpYearlyRange:
        year_to_ticker = {
            2024: ['INXD-24DEC31-T3200', 'INXD-24DEC31-T5799.99', 'INXD-24DEC31-B3300', 'INXD-24DEC31-B3500', 
                    'INXD-24DEC31-B3700', 'INXD-24DEC31-B3900', 'INXD-24DEC31-B4100', 'INXD-24DEC31-B4300', 
                    'INXD-24DEC31-B4500', 'INXD-24DEC31-B4700', 'INXD-24DEC31-B4900', 'INXD-24DEC31-B5100', 
                    'INXD-24DEC31-B5300', 'INXD-24DEC31-B5500', 'INXD-24DEC31-B5700'], 
            2023: ['INXY-23DEC29-T2700', 'INXY-23DEC29-T5299.99', 'INXY-23DEC29-B2800', 'INXY-23DEC29-B3000', 
                    'INXY-23DEC29-B3200', 'INXY-23DEC29-B3400', 'INXY-23DEC29-B3600', 'INXY-23DEC29-B3800', 
                    'INXY-23DEC29-B4000', 'INXY-23DEC29-B4200', 'INXY-23DEC29-B4400', 'INXY-23DEC29-B4600', 
                    'INXY-23DEC29-B4800', 'INXY-23DEC29-B5000', 'INXY-23DEC29-B5200'], 
            2022: ['INXY-22DEC30-T2600', 'INXY-22DEC30-T5200', 'INXY-22DEC30-B2700', 'INXY-22DEC30-B2900', 
                    'INXY-22DEC30-B3100', 'INXY-22DEC30-B3300', 'INXY-22DEC30-B3500', 'INXY-22DEC30-B3700', 
                    'INXY-22DEC30-B3900', 'INXY-22DEC30-B4100', 'INXY-22DEC30-B4300', 'INXY-22DEC30-B4500', 
                    'INXY-22DEC30-B4700', 'INXY-22DEC30-B4900', 'INXY-22DEC30-B5100']}
        return get_yearly_range_sub_markets(year_to_ticker, start_date, end_date)
        
    elif market == IndexMarket.NasdaqYearlyRange:
        year_to_ticker = {
            2024: ['NASDAQ100Y-24DEC31-T12000', 'NASDAQ100Y-24DEC31-T18499.99', 'NASDAQ100Y-24DEC31-B12250', 
                    'NASDAQ100Y-24DEC31-B12750', 'NASDAQ100Y-24DEC31-B13250', 'NASDAQ100Y-24DEC31-B13750', 
                    'NASDAQ100Y-24DEC31-B14250', 'NASDAQ100Y-24DEC31-B14750', 'NASDAQ100Y-24DEC31-B15250', 
                    'NASDAQ100Y-24DEC31-B15750', 'NASDAQ100Y-24DEC31-B16250', 'NASDAQ100Y-24DEC31-B16750', 
                    'NASDAQ100Y-24DEC31-B17250', 'NASDAQ100Y-24DEC31-B17750', 'NASDAQ100Y-24DEC31-B18250'],
            2023: ['NASDAQ100Y-23DEC29-T8500', 'NASDAQ100Y-23DEC29-T14999.99', 'NASDAQ100Y-23DEC29-B8750', 
                    'NASDAQ100Y-23DEC29-B9250', 'NASDAQ100Y-23DEC29-B9750', 'NASDAQ100Y-23DEC29-B10250', 
                    'NASDAQ100Y-23DEC29-B10750', 'NASDAQ100Y-23DEC29-B11250', 'NASDAQ100Y-23DEC29-B11750', 
                    'NASDAQ100Y-23DEC29-B12250', 'NASDAQ100Y-23DEC29-B12750', 'NASDAQ100Y-23DEC29-B13250', 
                    'NASDAQ100Y-23DEC29-B13750', 'NASDAQ100Y-23DEC29-B14250', 'NASDAQ100Y-23DEC29-B14750']
                          }
        return get_yearly_range_sub_markets(year_to_ticker, start_date, end_date)

'''
Creates a csv for a given market string from start_date to end_date.
Saves files to the data storage folder. Saves as market-start-end if no name given. 
Assumes market is not open. 
'''
def create_csv(account: ExchangeClient, market: str, start_date: dt, end_date: dt, csv_name: str | bool = None) -> None:

    start_timestamp = int(start_date.timestamp())
    end_timestamp = int((end_date).timestamp())
    
    initial = True
    data_dict = []
    while initial or data_cursor is not None:
        if initial:
            data = account.get_market_history(ticker=market, limit=1000, min_ts=start_timestamp, max_ts=end_timestamp)
        else:
            data = account.get_market_history(ticker=market, limit=1000, cursor=data_cursor, min_ts=start_timestamp, max_ts=end_timestamp)
        initial = False
        data_dict = data_dict + data['history']
        data_cursor = data['cursor']
    
    if len(data_dict) == 0:
        raise Exception('Your API call has returned no data')
    
    field_names = ['datetime', 'bid', 'ask', 'open_interest', 'volume']
    
    if csv_name is None:
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

### MAIN FUNCTION ###

'''
Creates csvs with kalshi data and writes them to the data_storage folder.
    account: the ExchangeClient representing a kalshi account
    market: the type of index market that will be stored
    start_date: the first time at which to retrieve data (include hour + minute)
    end_date: the last time at which to retrieve data (include hour + minute)
    interval: the interval at which to retrieve data
Assumes market is not currently open.
'''
def create_index_market_csvs(market: IndexMarket, start_date: dt, end_date: dt, interval: IndexInterval) -> None:
    
    account = start_kalshi_api()
    markets = get_sub_markets(account, market, start_date, end_date, interval)
    
    total_trials = 0
    successes = 0
    errors = 0
    
    for mkt_string, start, end in markets:
        mkt_prefix, date, price = re.findall(r'[a-zA-z0-9]+', mkt_string)
        year = date[:2]
        month = date[2:5]
        day = date[-2:]
        csv_name = f'data_storage/kalshi_data/{mkt_prefix}/{year}/{month}/{day}/{mkt_string}.csv'
        
        try:
            create_csv(account, mkt_string, start, end, csv_name)
            successes += 1
        except:
            errors += 1
        total_trials += 1
    
    print(f'The error rate for {market} between {start_date} and {end_date} was {round(errors/total_trials, 0)}')

if __name__ == "__main__":
    exchange_client = start_kalshi_api()
    # create_csv(exchange_client, 'INXDU-23AUG15-T4499.99', dt.fromtimestamp(1692104400), dt.fromtimestamp(1692109400))
    # create_csv(exchange_client, 'INXDU-23DEC29-T4749.99', dt(2023, 12, 29, 9, 0, 1), dt(2023, 12, 29, 13, 0, 0))
    # print(exchange_client.get_market_history('INXZ-23DEC26-T4754.63'))
    # get_daily_index_prices('^SPX', dt(2023, 12, 4, 9, 30)-timedelta(3), dt(2023, 12, 4, 14, 30)-timedelta(1))
    # market_days = get_market_days(dt(2023, 11, 28, 9, 30), dt(2023, 12, 5, 12, 30))
    # print(market_to_kalshi_dates(market_days))
    # print(exchange_client.get_market_history('NASDAQ100D-23DEC11-B16250'))
    # create_csv(exchange_client, 'NASDAQ100D-23DEC11-B16250', dt(2023, 12, 11, 9, 45, 0), dt(2023, 12, 11, 16, 0, 0))
    # prices_df = get_daily_index_prices('^SPX', dt(2023, 12, 4, 9, 30)-timedelta(3), dt(2023, 12, 4, 14, 30)-timedelta(1))
    # print(type(prices_df['Low'].to_list()[0]))