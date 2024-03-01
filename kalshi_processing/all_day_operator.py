from datetime import datetime as dt
from datetime import time as time
import time as sleeper
from client import start_kalshi_api
import logging
import yfinance as yf
import pandas as pd
from PIL import ImageGrab
import pytesseract as ocr
import re
import uuid
from enum import Enum

### KALSHI CLASS REPRESENTATIONS ###

"""
A Kalshi Market containing information about a given range market
    bids and asks: structured as a list of price-volume tuples, [(price, vol), (price, vol), ...]
"""
class KalshiMarket:
    def __init__(self,ticker,midpoint,yeses, nos):
        self.ticker = ticker
        self.midpoint = midpoint
        self.yeses = yeses
        self.nos = nos
        
    def get_best_yes_ask(self):
        return self.yeses[0][0]

    def get_best_yes_bid(self):
        return 100-self.nos[0][0]

    def get_ticker(self):
        return self.ticker

    def get_midpoint(self):
        return self.midpoint

"""
Represents the positions that we currently have
    each position is indexed by market, price, and volume
    positions is a dictionary within a dictionary
    the outer dictionary maps ticker to a dictionary containing yes and no
    within the inner dictionary, map yes & no string to a list
    list contains price-volume tuples [(price, vol), (price, vol), ...]
"""
class Orderbook:
    def __init__(self):
        self.positions = {}
    
    def get_market_positions(self, ticker: str, yes_market: bool):
        return self.positions[ticker]['yes' if yes_market else 'no']
    
    def total_open_portfolio():
        pass
    
    def check_eod_mid_order():
        pass

"""
Represents a position we have taken in the market
"""
class Position:
    def __init__(self, position_type):
        self.position_type = position_type

"""
Represents the different types of orders a may position may fall under, i.e. which strategy the position is used for
"""
class PositionType(Enum):
    BodOrder = 1
    ModArbOrder = 2
    EodArbOrder = 3
    EodMiddleOrder = 4

### UTILITY FUNCTIONS ###

"""
Get NDX Open and Current Price
"""
def getIndexOpen(ticker="^NDX"):
    print(f'getting {ticker} open')
    logging.info(f'getting {ticker} open')
    
    index_history = yf.download(tickers=ticker, period="1d", interval="1m")
    
    print(f'got {ticker} open')
    logging.info(f'got {ticker} open')
    
    index_open = index_history['Open'].iloc[0]
    return index_open

"""
Takes a screenshot of Kalshi to get the current NDX price
Keep safari open to the left of the screen, one tab, not logged in, scrolled to top
"""
def getNDXCurrentPrice():
    logging.info(f'Getting current NDX price')
    ss_region = (150,210, 260, 270)
    ss_img = ImageGrab.grab(ss_region)
    # ss_img.show()

    num = str(ocr.image_to_string(ss_img))
    temp = re.findall(r'\d+', num)
    NDXVal = int(''.join([str(x) for x in temp]))
    logging.info(f'Got current NDX price')
    return NDXVal

"""
Places a basic kalshi market buy order
    account: get by running start_kalshi_api()
    market: a KalshiMarket object
    amount: the number of contracts to buy
    side: a string, 'yes' or 'no'
"""
def placeKalshiMarketOrder(account, market: KalshiMarket, amount, side):
    ticker = market.get_ticker()
    order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':side,
                    'count':int(amount//100)}
    account.create_order(**order_params)
    logging.info(f'Bought {amount} of {side} contracts on market {ticker}')

### STRATEGIES ### 

def run_bod(capital):
    pass

def run_all_day_arbitrage(capital):
    pass

def run_eod(account, capital, orderbook: Orderbook, NDXopen, market_size=100, middle_range_percent=50, arb_value=98, capital_percentage=0.5, ask_high=97, percent_change=2):
    #get current NDX price and working capital
    current_index_price = getNDXCurrentPrice()
    working_capital = capital*0.80
    
    #get markets above, middle, below
    low_market, current_market, high_market = KalshiMarket, KalshiMarket, KalshiMarket
    
    #get midpoint
    current_market_midpoint = current_market.get_midpoint()
    
    #check if NDX is in middle range
    in_middle_range = abs(current_index_price-current_market_midpoint) < (market_size/2)*(middle_range_percent/100)
    
    #run buying steps: can buy middle or buy the edge
    if not in_middle_range:
        is_above_midpoint = current_index_price - current_market_midpoint > 0
        current_ask = current_market.get_best_yes_ask()
        closest_range_ask = high_market.get_best_yes_ask() if is_above_midpoint else low_market.get_best_yes_ask()
        logging.info(f'Considering an edge buy with current market at {current_ask}, closest market at {closest_range_ask}')
        
        if current_ask + closest_range_ask < arb_value:
            placeKalshiMarketOrder(account, current_market, (working_capital * capital_percentage)/2, 'yes')
            placeKalshiMarketOrder(account,high_market if is_above_midpoint else low_market, (working_capital * capital_percentage)/2, 'yes')
            
            #TODO add to positions book, use better capital allocation for amount to buy
            #TODO log the orders
    else:
        if current_market.get_best_yes_ask() < ask_high:
            if 100*(abs(NDXopen-current_index_price)/NDXopen) < percent_change:
                placeKalshiMarketOrder(account,current_market, working_capital * capital_percentage, 'yes')
            
                #TODO add to positions book, use better capital allocation for amount to buy
        
    #if bought, run risk management steps
    if in_middle_range and orderbook.check_eod_mid_order():
        is_above_midpoint = current_index_price - current_market_midpoint > 0
        current_ask = current_market.get_best_yes_ask()
        closest_range_ask = high_market.get_best_yes_ask() if is_above_midpoint else low_market.get_best_yes_ask()
        
        if abs(current_index_price - current_market_midpoint) > 10:
            pass 

def run_strategies(account, orderbook, capital, current_time, NDXopen):
    bod_capital = capital*(1/10)
    arb_capital = capital*(8/10)
    eod_capital = capital*(1/10)
    
    if current_time > time(9,30, 0) and current_time < time(9,45, 0):
        logging.info(f'Trying to run beginning of day strategy with ${bod_capital} in capital')
        run_bod(bod_capital, orderbook)
                    
    elif current_time > time(9, 45, 0) and current_time < time(15, 50, 0):
        logging.info(f'Trying to run middle of day arb strategy with ${arb_capital} in capital')
        run_all_day_arbitrage(arb_capital, orderbook)
    
    elif current_time > time(15, 50, 0) and current_time < time(16, 0, 0):
        logging.info(f'Trying to run end of day strategy with ${eod_capital} in capital')
        run_eod(account, eod_capital, orderbook, NDXopen)

### OPERATOR ###

def operate_kalshi():
    #start up the logging functionality
    current_datetime = dt.now()
    logging.basicConfig(filename=f'logs/{current_datetime}.log', filemode='a', format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S', level=logging.INFO)
    logging.info(f'Beginning kalshi operator.')
    
    #connect to trading account and get initial balance
    try:
        account = start_kalshi_api()
        capital = account.get_balance()['balance']/100
        logging.info(f'Connected to api. Current balance is ${capital}.')
    except Exception as error:
        logging.critical(f'Cannot connect to kalshi server/cannot get balance: {error}.')
    
    #create the day's orderbook
    orderbook = Orderbook()
    
    while True:
        current_datetime = dt.now()
        current_time = current_datetime.time()
        
        if current_time < time(16,0,0):
            if current_time > time(9,30,0):
                NDXopen = getIndexOpen()
                
                try:
                    run_strategies(account, orderbook, capital, current_time, NDXopen)
                except Exception as error:
                    print('An error occurred running strategies: \n', error)
                    logging.warning(f'An error occurred running strategies: {error}')
            
            else:
                print(f'Current Time is: {current_time}. It is not yet time to trade.')
                logging.info(f'It is not yet time to trade.')
                sleeper.sleep(10)
        else:
            print(f'Current Time is {current_time}. The trading day is over.')
            logging.info(f'The trading day is over.')
            break
        
if __name__ == "__main__":
    operate_kalshi()   
        