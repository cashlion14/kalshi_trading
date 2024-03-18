from client import start_kalshi_api
from client import start_demo_api
from datetime import datetime
from datetime import time as Time
import yfinance as yf
from PIL import ImageGrab
import pytesseract as ocr
import re
import uuid
import logging

### SETUP VARIABLES ###

DEMO_MODE = False
PAPER_TRADE = False
TESTING = False
FAKE_DATA = False

BUY_MINUTE = 50         # first minute (3:xx PM) we allow to buy 
SELL_MINUTE = 56        # first minute (3:xx PM) we allow to sell
CAPITAL_PERCENTAGE = .2 # percentage of our capital to bet on each trade (from 0 to 1)
INTERVAL_RATIO = 5      # multiple by 10 to get percent of range you would buy in (spanning middle)
ASK_LOW = 70            #minumum price to buy stock at
ASK_HIGH = 97           #maximum price to buy stock at
PERCENT_CHANGE = 2      #maximum percent change of the S&P, above which we will not buy on that day (volatility control)
SELL_PRICE = 98         #price at which to always sell in order to lock in profit
LOSS_FLOOR = 10         #amount that, if the price drops this much below our buy price, we sell to mitigate losses 
KALSHI_INTERVAL_SIZE = 50 #size of the kalshi range market
ARB_VAL = 99            #if less than this, will buy both edge markets for abitrage

months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']

"""
Class representing a Kalshi Market
    vol is the volume available at the lowest ask price
"""
class Kalshi_Market:
    def __init__(self,ticker,midpoint,bid,ask_low,vol_low, ask_high = None, vol_high = None):
        self.ticker = ticker
        self.midpoint = midpoint
        self.bid = bid
        self.ask = ask_low
        self.vol = vol_low
        self.ask_high = ask_high
        self.vol_high = vol_high

    def __str__(self) -> str:
        return str(self.ticker) + ' (bid,ask,vol, 2ask, 2vol): ' + str(self.bid) + ', ' + str(self.ask) + ', ' + str(self.vol) + str(self.ask_high) + str(self.vol_high)

"""
Get NDX Open and Current Price
"""
def getNDXOpen():
    print('getting NDX open')
    NDX_history = yf.download(tickers="^NDX", period="1d", interval="1m")
    print('got NDX open')
    NDX_open = NDX_history['Open'].iloc[0]
    return NDX_open

"""
Takes a screenshot of Kalshi to get the current NDX price
Keep safari open to the left of the screen, not logged in, scrolled to top
"""
def getNDXCurrentPrice():
    ss_region = (150,210, 250, 270)
    ss_img = ImageGrab.grab(ss_region)
    # ss_img.show()

    num = str(ocr.image_to_string(ss_img))

    temp = re.findall(r'\d+', num)
    NDXVal = int(''.join([str(x) for x in temp]))
    print('got current NDX price')
    
    if FAKE_DATA:
        return 0
    else:
        return NDXVal

"""
Gets data for three Kalshi markets: below, current, and above
"""
def getKalshiData(exchange_client,current_datetime,NDX_current):
    
    #get current datetime
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    #create prefix for NDX range markets and get all markets with that prefix
    kalshi_ticker = 'NASDAQ100-' + year + month + day
    # print('Kalshi Ticker:', kalshi_ticker)
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)
    # print(event_response)
    
    #turn markets into KalshiMarket objects
    kalshi_markets = []
    for event in event_response['markets']:
        event_ticker = event['ticker']
        if event_ticker[-6] == 'B':
            
            #get prices for given market
            market_orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']['yes']

            if market_orderbook is not None:
                market_data = market_orderbook[-1]
                market_bid = market_data[0]
                market_vol = market_data[1]
                
                midpoint = float(event_ticker[-5:])
                market_ask = event['yes_ask']
                
                market_object = Kalshi_Market(event_ticker,midpoint,market_bid,market_ask,market_vol)
                kalshi_markets.append(market_object)
            
    #find the closest market to the current price
    min_distance = 10000000    
    closest_market_index = -1
    for i in range(len(kalshi_markets)):
        market_object = kalshi_markets[i]
        if (abs(NDX_current - market_object.midpoint) < min_distance):
            min_distance = abs(NDX_current - market_object.midpoint)
            closest_market_index = i
    
    # print([i.ticker for i in kalshi_markets])
    
    closest_market = kalshi_markets[closest_market_index]
    # print(kalshi_markets)
    
    if closest_market_index+1 >= len(kalshi_markets):
        market_below = None
    else:
        market_below = kalshi_markets[closest_market_index+1]
        
    if closest_market_index - 1 < 0:
        market_above = None
    else:
        market_above = kalshi_markets[closest_market_index-1]
    
    
    return closest_market, market_below, market_above   
    # print(closestMarket.ticker)
            
    # kalshi_bid = market_bids[closestMarket]
    # kalshi_ask = market_asks[closestMarket]
    # print(kalshi_midpoint,kalshi_bid,kalshi_ask)
    
    
    # return kalshi_ticker, kalshi_midpoint, kalshi_bid, kalshi_ask, exchange_client


def updateKalshiData(exchange_client,current_datetime,cur_market,lower_market,higher_market):    
    
    cur_event_response = exchange_client.get_orderbook(cur_market.ticker)
    cur_yes_book = cur_event_response['orderbook']['yes']
    cur_no_book = cur_event_response['orderbook']['no']
    
    cur_market.bid = cur_yes_book[-1][0]
    cur_market.ask = 100 - cur_no_book[-1][0]
    cur_market.vol = min(cur_yes_book[-1][1], cur_no_book[-1][1])
    
    #do for lower book
    if lower_market is not None:
        lower_event_response = exchange_client.get_orderbook(lower_market.ticker)
        lower_yes_book = lower_event_response['orderbook']['yes']
        lower_no_book = lower_event_response['orderbook']['no']
        
        lower_market.bid = lower_yes_book[-1][0]
        lower_market.ask = 100 - lower_no_book[-1][0]
        lower_market.vol = min(lower_yes_book[-1][1], lower_no_book[-1][1])
    
    
    #do for higher book
    if higher_market is not None:
        higher_event_response = exchange_client.get_orderbook(higher_market.ticker)
        higher_yes_book = higher_event_response['orderbook']['yes']
        higher_no_book = higher_event_response['orderbook']['no']
        
        higher_market.bid = higher_yes_book[-1][0]
        higher_market.ask = 100 - higher_no_book[-1][0]
        higher_market.vol = min(higher_yes_book[-1][1], higher_no_book[-1][1])

    return cur_market, lower_market, higher_market
            
        
        
def buy_kalshi(exchange_client,market,amt,side):

    account = start_kalshi_api()
    print('connected to kalshi')
    print(account.get_exchange_status())
    balance = account.get_balance()
    print(balance)
    positions = account.get_positions()
    # print(positions) 

    ticker = market.ticker
    order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':side,
                    'count':int(amt//100)}
    
    if not TESTING:
        account.create_order(**order_params)
        print('bought',amt,'of',side,'of',ticker)
    else:
        print('testing but would buy ',amt,'of',side,'of',ticker)
    
    


def operate_kalshi():
    logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    logging.info('So should this')

    markets_set = False
    
    bought_middle = False
    bought_times = 0
    bought_edge = False
    bought_twice = False
    sold = False
    sold_price = None
    used_all_capital = False
    
    NDX_open = getNDXOpen()
    
    while True:
    
        #get current time    
        current_datetime = datetime.now()
        current_time = current_datetime.time()
        
        
        if DEMO_MODE:
            exchange_client = start_demo_api()
        else:
            exchange_client = start_kalshi_api()
        
        
        if TESTING or (current_time < Time(16,0) and current_time > Time(9,30)):    
            NDX_current = getNDXCurrentPrice()
            print('NDX Data (open, current):',NDX_open, NDX_current)
            
            
            if not markets_set:
                cur_market, lower_market,higher_market = getKalshiData(exchange_client,current_datetime,NDX_current)
                markets_set = True
            else:
                try:
                    cur_market, lower_market, higher_market = updateKalshiData(exchange_client,current_datetime,cur_market,lower_market,higher_market)
                except:
                    cur_market, lower_market,higher_market = getKalshiData(exchange_client,current_datetime,NDX_current)
            
            print(lower_market)
            print(cur_market)
            print(higher_market)
            
            
            total_capital = exchange_client.get_balance()['balance']
            

            if TESTING or (current_time > Time(15,BUY_MINUTE,0) and current_time < Time(16,0,0)):
                
                if bought_times == 3:
                    used_all_capital = True
                    
                print('is in time range')
                middle_bid, middle_ask = cur_market.bid, cur_market.ask
                if lower_market is not None:
                    lower_bid, lower_ask = lower_market.bid, lower_market.ask
                if higher_market is not None:
                    higher_bid, higher_ask = higher_market.bid, higher_market.ask
                
                kalshi_midpoint = cur_market.midpoint
                is_in_middle_range = abs(NDX_current-kalshi_midpoint) < KALSHI_INTERVAL_SIZE*(INTERVAL_RATIO/10)
                print('is in middle range:',is_in_middle_range)
                
                
                if not used_all_capital:
                    if is_in_middle_range:
                        if middle_ask < ASK_HIGH:
                            if 100*(abs(NDX_open-NDX_current)/NDX_open) < PERCENT_CHANGE:
                                buy_kalshi(exchange_client,cur_market, total_capital * CAPITAL_PERCENTAGE, 'yes')
                                bought_times += 1
                                middle_bought_price = middle_ask
                                bought_middle = True
                    else:
                        is_higher = NDX_current - kalshi_midpoint > 0
                        side_ask = higher_ask if is_higher else lower_ask
                        print('considering straddle buy with markets at', middle_ask, side_ask)
                        if middle_ask + side_ask < ARB_VAL:
                            edge_bought_price = middle_ask + side_ask
                            bought_edge = True
                            buy_kalshi(exchange_client,cur_market, total_capital * CAPITAL_PERCENTAGE/2, 'yes')
                            buy_kalshi(exchange_client,higher_market if is_higher else lower_market, total_capital * CAPITAL_PERCENTAGE/2, 'yes')
                            bought_times += 1
                
                if bought_middle and not is_in_middle_range:
                    higher = NDX_current - kalshi_midpoint > 0
                    side_ask = higher_ask if higher else lower_ask
                    
                    
                    if abs(NDX_current - kalshi_midpoint) > 10 and not sold and not bought_twice:
                        print('considering loss arb with', middle_bought_price, side_ask)
                        if middle_bought_price + side_ask <= 98:
                            middle_bought_price += side_ask
                            bought_twice = True
                            buy_kalshi(exchange_client,higher_market if higher else lower_market,total_capital * CAPITAL_PERCENTAGE, 'yes')
                            bought_times += 1
                            
                    elif middle_ask < middle_bought_price - LOSS_FLOOR and not sold and not bought_twice:
                        print('considering mitigating losses')
                        sell_loss = middle_bid - middle_bought_price
                        double_loss = 100 - middle_bought_price - side_ask
                        
                        print('sell loss: ', sell_loss, "double_loss: ", double_loss)
                        if sell_loss > double_loss:
                            sold = True
                            sold_price = middle_bid
                            buy_kalshi(exchange_client,cur_market,total_capital * CAPITAL_PERCENTAGE,'no')
                            bought_times += 1
                        else:
                            bought_twice = True
                            middle_bought_price += side_ask
                            buy_kalshi(exchange_client,higher_market if higher else lower_market,total_capital * CAPITAL_PERCENTAGE, 'yes')
                            bought_times += 1
            
            else:
                print('not in time range')

        print('---------------------------')
        # time.sleep(0.5)
    

if __name__ == "__main__":
    # market_object = Kalshi_Market('INX-24FEB14-B4962',4962,1,1,1)
    # buy_kalsh2(start_kalshi_api(),market_object,100,'yes')
    operate_kalshi()
    
    #TODO: change KalshiMarket filling s.t. we get the second lowest market as well
    
    #current problems:
    #what happens if market shifts rapidly in an unexpected direction?
    #how do we buy up enough volume if the volume is not enough?
    #how do we handle markets changing rapidly?
    #how do we handle rate limiting and risk management?
    #biggest thing is to get a better conceptual model of the market so that we can adjust the buying strategy
    #want a market that takes into account the order book rather than the edges of the book
    #just go next step of complexity
    #so what I want to be able to do is look at the markets above and below the spread
    
    #what im doing is constantly getting the order book again and again
    
    #operate: get the open price
    #for the last 15 minutes of the day
    #get the three markets and then update those markets constantly
    #implement strategy on the three markets
    #when I decide to buy, decide how much I want to buy using
    
    #so I want to update those markets often
    #when I'm running strategy I would need to check whether 
    #add more money to the strategy -> be able to buy at max volume
    #fixed trading error
    #now make it so that the strategy can handle more volume
    #then make it run automatically
    #make strategy run without crashing
    #it would be nice to just automate this on the computer and log everything that is printed to a file
    
    
    #to implement higher trading volumes for tomorrow, I need to set it to buy multiple times
    
    
    """
    A Kalshi Market containing information about a given range market
        bids and asks: structured as a list of price-volume tuples, [(price, vol), (price, vol), ...]
    """
    class KalshiMarket:
        def __init__(self,ticker,midpoint,bids, asks):
            self.ticker = ticker
            self.midpoint = midpoint
            self.bids = bids
            self.asks = asks

    """
    Keeps track of the current positions that we hold
        each position is indexed by market, price, and volume
        positions is a dictionary within a dictionary
        the outer dictionary maps ticker to a dictionary containing yes and no
        within the inner dictionary, map yes & no string to a list
        list contains price-volume tuples [(price, vol), (price, vol), ...]
    """
    class Positions:
        def __init__(self):
            self.positions = {}
        
        def get_market_positions(self, ticker: str, yes_market: bool):
            return self.positions[ticker]['yes' if yes_market else 'no']