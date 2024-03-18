from client import start_kalshi_api
from datetime import datetime
from datetime import time as Time


NASDAQ_INTERVAL_SIZE = 50



class Kalshi_Range_Market:
    
    def __init__(self,ticker,midpoint,no_price,yes_price,vol):
        self.ticker = ticker
        self.midpoint = midpoint
        self.no_price = no_price
        self.yes_price = yes_price
        self.vol = vol
        self.range_floor = self.midpoint - NASDAQ_INTERVAL_SIZE
        self.range_ceiling = self.midpoint + NASDAQ_INTERVAL_SIZE
    
    def __str__(self) -> str:
        return str(self.ticker) + ' (yes,no,vol): ' + str(self.yes_price) + ', ' + str(self.no_price) + ', ' + str(self.vol)

class Kalshi_Above_Market:
    def __init__(self,ticker,strike_val,no_price,yes_price,vol):
        self.ticker = ticker
        self.strike_val = strike_val
        self.no_price = no_price
        self.yes_price = yes_price
        self.vol = vol
    
    def __str__(self) -> str:
        return str(self.ticker) + ' (yes,no,vol): ' + str(self.yes_price) + ', ' + str(self.no_price) + ', ' + str(self.vol)

months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']


def get_kalshi_date():
    current_datetime = datetime.now()
    current_time = current_datetime.time()
    
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
    return year + month + '28'


def get_range_markets(exchange_client,date):
    
    kalshi_ticker = 'NASDAQ100-' + date
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)
    
    kalshi_range_markets = []
    
    for event in event_response['markets']:
        event_ticker = event['ticker']
        
        if event_ticker[-6] == 'B':
            orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']
            yes_orderbook = orderbook['yes']
            no_orderbook = orderbook['no']
            
            if yes_orderbook != None and no_orderbook != None:
                yes_data = yes_orderbook[-1]
                market_bid = 100 - yes_data[0]
                market_vol = yes_data[1]
                

                midpoint = float(event_ticker[-5:])
                
                no_data = no_orderbook[-1]
                market_ask = 100 - no_data[0]
                market_vol = min(market_vol,no_data[1])
                
                
                market_object = Kalshi_Range_Market(event_ticker,midpoint,market_bid,market_ask,market_vol)
                kalshi_range_markets.append(market_object)
    
    kalshi_range_markets.reverse()
    return kalshi_range_markets
            
def get_above_markets(exchange_client,date):
    
    kalshi_ticker = 'NASDAQ100U-' + date
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)
    
    kalshi_above_markets = []
    
    for event in event_response['markets']:
        event_ticker = event['ticker']
        market_orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']
        yes_orderbook = market_orderbook['yes']
        no_orderbook = market_orderbook['no']
        
        if yes_orderbook != None and no_orderbook != None:
                yes_data = yes_orderbook[-1]
                market_bid = 100 - yes_data[0]
                
                
                strike_val = round(float(event_ticker[-8:]),0)
                
                no_data = no_orderbook[-1]
                market_ask = 100 - no_data[0]
                market_vol = min(no_data[1],yes_data[1])
                
                
                market_object = Kalshi_Above_Market(event_ticker,strike_val,market_bid,market_ask,market_vol)
                kalshi_above_markets.append(market_object)
    
    kalshi_above_markets.reverse()
    return kalshi_above_markets
         
def get_above_market(above_markets,target):
    for above_market in above_markets:
        if above_market.strike_val == target:
            return above_market
    return -1


def detect_arbitrage(range_markets,above_markets):
    for range_market in range_markets:
        range_floor = range_market.range_floor
        range_ceiling = range_market.range_ceiling
        
        
        floor_market = get_above_market(above_markets,range_floor)
        ceiling_market = get_above_market(above_markets,range_ceiling)
        
        if floor_market != -1 and ceiling_market != -1:
            print(floor_market.yes_price, range_market.no_price, ceiling_market.no_price, '=', sum([floor_market.yes_price, range_market.no_price, ceiling_market.no_price]),  '<2')
            print(floor_market.no_price, range_market.yes_price,ceiling_market.yes_price, '=', sum([floor_market.no_price, range_market.yes_price,ceiling_market.yes_price]),'<1')
            
            
            other = floor_market.yes_price + floor_market.no_price + range_market.yes_price + range_market.no_price + ceiling_market.yes_price + ceiling_market.no_price
            print(other, '<3')
        
        
        
        
        
         
            
if __name__ == "__main__":
    exchange_client = start_kalshi_api()
    date = get_kalshi_date()
    
    
    range_markets = get_range_markets(exchange_client,date)
    above_markets = get_above_markets(exchange_client,date)
    
    
    for market in range_markets:
        print(market)
        
    for market in above_markets:
        print(market)
    
    
    detect_arbitrage(range_markets,above_markets)
    
    
    