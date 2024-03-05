from client import start_kalshi_api
from client import start_demo_api
from datetime import datetime
from datetime import time as Time
import yfinance as yf

from PIL import Image, ImageGrab
import pytesseract as ocr
import re

import sched, time
import uuid
import logging
import requests


DEMO_MODE = False
PAPER_TRADE = False
TESTING = False
FAKE_DATA = False

BUY_MINUTE = 50         # first minute (3:xx PM) we allow to buy 
SELL_MINUTE = 56        # first minute (3:xx PM) we allow to sell
CAPTIAL_PERCENTAGE = .2 # percentage of our capital to bet on each trade
INTERVAL_RATIO = 5      # #divide by 10, its the percent of the range youd buy in (in the middle)
ASK_LOW = 70            #minumum price to buy stock at
ASK_HIGH = 97           #maximum price to buy stock at
PERCENT_CHANGE = 2      #maximum percent change of the NDX below which we will buy on that day (volatility control)
SELL_PRICE = 98         #price at which to always sell in order to lock in profit
LOSS_FLOOR = 10         #amount that, if the price drops this much below our buy price, we sell to mitigate losses 
KALSHI_INTERVAL_SIZE = 13
ARB_VAL = 99

months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']


class Kalshi_Market:
    def __init__(self,ticker,midpoint,bid,ask,vol):
        self.ticker = ticker
        self.midpoint = midpoint
        self.bid = bid
        self.ask = ask
        self.vol = vol

    def __str__(self) -> str:
        return str(self.ticker) + ' (bid,ask,vol): ' + str(self.bid) + ', ' + str(self.ask) + ', ' + str(self.vol)

def getNDXData():
    print('getting NDX data')
    NDX_history = yf.download(tickers="^NDX", period="1d", interval="1m")
    print('got NDX data')
    NDX_open = NDX_history['Open'].iloc[0]
    
    if FAKE_DATA:
        NDX_current = 0
    else:
        NDX_current = takeNDXScreenshot()
    return NDX_open, NDX_current

def takeNDXScreenshot():
    ss_region = (150,210, 250, 270)
    ss_img = ImageGrab.grab(ss_region)
    # ss_img.show()

    num = str(ocr.image_to_string(ss_img))

    temp = re.findall(r'\d+', num)
    res = list(map(int, temp))
    NDXVal = int(''.join([str(x) for x in res]))
    return NDXVal


def getKalshiData(exchange_client,current_datetime, NDX_current):
    #Get Kalshi Data
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    
    range_ticker = 'NASDAQ100-' + year + month + day
    above_ticker = 'NASDAQ100U-' + year + month + day
    print('Range Ticker:', range_ticker)
    print('Above Ticker:', above_ticker)
    range_response = exchange_client.get_markets(event_ticker=range_ticker)
    above_response = exchange_client.get_markets(event_ticker=above_ticker)
    print(range_response)
    print(above_response)
    # print(event_response)
    
    range_markets = []
    above_markets = []
    

    for event in range_response['markets']:
        event_ticker = event['ticker']
        if event_ticker[-6] == 'B':
            
        
            market_orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']['yes']
            
            
            if market_orderbook != None:
                market_data = market_orderbook[-1]
                market_bid = market_data[0]
                market_vol = market_data[1]
                
            
                midpoint = float(event_ticker[-5:])
                market_ask = event['yes_ask']
                
                market_object = Kalshi_Market(event_ticker,midpoint,market_bid,market_ask,market_vol)
                range_markets.append(market_object)
                
    for event in above_response['markets']:
        event_ticker = event['ticker']
        if event_ticker[-9] == 'B':
            
        
            market_orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']['yes']
            
            
            if market_orderbook != None:
                market_data = market_orderbook[-1]
                market_bid = market_data[0]
                market_vol = market_data[1]
                
            
                midpoint = float(event_ticker[-8:])
                market_ask = event['yes_ask']
                
                market_object = Kalshi_Market(event_ticker,midpoint,market_bid,market_ask,market_vol)
                above_markets.append(market_object)
        
        
    min_distance = 10000000    
    closest_range_market_index = -1
    for i in range(len(range_markets)):
        market_object = range_markets[i]
        if (abs(NDX_current - market_object.midpoint) < min_distance):
            min_distance = abs(NDX_current - market_object.midpoint)
            closest_range_market_index = i
            
    min_distance = 10000000    
    closest_above_market_index = -1
    for i in range(len(above_markets)):
        market_object = above_markets[i]
        if (abs(NDX_current - market_object.midpoint) < min_distance) and NDX_current > market_object.midpoint:
            min_distance = abs(NDX_current - market_object.midpoint)
            closest_above_market_index = i
    
    # print([i.ticker for i in kalshi_markets])
    
    closest_market = range_markets[closest_range_market_index]
    print(range_markets)
        
    if closest_range_market_index - 1 < 0:
        market_above = None
    else:
        market_above = range_markets[closest_range_market_index-1]
        
        
    above_market = above_markets[closest_above_market_index]
    
    return closest_market, market_above, above_market   
    print(closestMarket.ticker)
            
    # kalshi_bid = market_bids[closestMarket]
    # kalshi_ask = market_asks[closestMarket]
    # print(kalshi_midpoint,kalshi_bid,kalshi_ask)
    
    
    # return kalshi_ticker, kalshi_midpoint, kalshi_bid, kalshi_ask, exchange_client


def updateKalshiData(exchange_client,current_datetime,range_market,above_range_market,above_market):    
    
    range_event_response = exchange_client.get_orderbook(range_market.ticker)
    range_yes_book = range_event_response['orderbook']['yes']
    range_no_book = range_event_response['orderbook']['no']
    
    range_market.bid = range_yes_book[-1][0]
    range_market.ask = 100 - range_no_book[-1][0]
    range_market.vol = min(range_yes_book[-1][1], range_no_book[-1][1])
    
    #do for above range book
    if above_range_market is not None:
        above_range_event_response = exchange_client.get_orderbook(above_range_market.ticker)
        above_range_yes_book = above_range_event_response['orderbook']['yes']
        above_range_no_book = above_range_event_response['orderbook']['no']
        
        above_range_market.bid = above_range_yes_book[-1][0]
        above_range_market.ask = 100 - above_range_no_book[-1][0]
        above_range_market.vol = min(above_range_yes_book[-1][1], above_range_no_book[-1][1])
    
    
    #do for higher book
    if above_market is not None:
        above_event_response = exchange_client.get_orderbook(above_market.ticker)
        above_yes_book = above_event_response['orderbook']['yes']
        above_no_book = above_event_response['orderbook']['no']
        
        above_market.bid = above_yes_book[-1][0]
        above_market.ask = 100 - above_no_book[-1][0]
        above_market.vol = min(above_yes_book[-1][1], above_no_book[-1][1])

    return range_market, above_range_market, above_market
            
        
        
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
    bought_edge = False
    bought_twice = False
    sold = False
    sold_price = None
    
    
    while True:
    
        #get current time    
        current_datetime = datetime.now()
        current_time = current_datetime.time()
        
        
        if DEMO_MODE:
            exchange_client = start_demo_api()
        else:
            exchange_client = start_kalshi_api()
        
        
        if TESTING or (current_time < Time(16,0) and current_time > Time(9,30)):    
            NDX_open, NDX_current = getNDXData()
            print('NDX Data (open, current):',NDX_open, NDX_current)
            
            
            if not markets_set:
                range_market, higher_range_market,above_market = getKalshiData(exchange_client,current_datetime,NDX_current)
                markets_set = True
            else:
                range_market, higher_range_market,above_market = updateKalshiData(exchange_client,current_datetime,range_market, higher_range_market,above_market)
            
            print(range_market)
            print(higher_range_market)
            print(above_market)
            
            
            total_capital = exchange_client.get_balance()['balance']
            

            if TESTING or current_time < Time(16,0,0):
                print('is in time range')
                range_bid, range_ask = range_market.bid, range_market.ask
                if higher_range_market is not None:
                    higher_range__bid, higher_range_ask = higher_range_market.bid, higher_range_market.ask
                if above_market is not None:
                    above_bid, above_ask = above_market.bid, above_market.ask
                
                # kalshi_midpoint = cur_market.midpoint
                
                # strategy:
                #get the range and the immediate higher range
                #get the above bracket that the index is in 
                
                range_difference = range_ask - higher_range_ask
                
                if range_difference 
                
                
                
                
                is_in_middle_range = abs(NDX_current-kalshi_midpoint) < KALSHI_INTERVAL_SIZE*(INTERVAL_RATIO/10)
                print('is in middle range:',is_in_middle_range)
                
                if not bought_middle and not bought_edge:
                    if is_in_middle_range:
                        if middle_ask < ASK_HIGH:
                            if 100*(abs(NDX_open-NDX_current)/NDX_open) < PERCENT_CHANGE:
                                buy_kalshi(exchange_client,cur_market, total_capital * CAPTIAL_PERCENTAGE, 'yes')
                                bought_price = middle_ask
                                bought_middle = True
                    else:
                        is_higher = NDX_current - kalshi_midpoint > 0
                        side_ask = higher_ask if is_higher else lower_ask
                        print('considering straddle buy with markets at', middle_ask, side_ask)
                        if middle_ask + side_ask < ARB_VAL:
                            bought_price = middle_ask + side_ask
                            bought_edge = True
                            buy_kalshi(exchange_client,cur_market, total_capital * CAPTIAL_PERCENTAGE/2, 'yes')
                            buy_kalshi(exchange_client,higher_market if is_higher else lower_market, total_capital * CAPTIAL_PERCENTAGE/2, 'yes')
                            
                
                elif bought_middle and not is_in_middle_range:
                    higher = NDX_current - kalshi_midpoint > 0
                    side_ask = higher_ask if higher else lower_ask
                    
                    
                    if abs(NDX_current - kalshi_midpoint) > 10 and not sold and not bought_twice:
                        print('considering loss arb with', bought_price, side_ask)
                        if bought_price + side_ask < 98:
                            bought_price += side_ask
                            bought_twice = True
                            buy_kalshi(exchange_client,higher_market if higher else lower_market,total_capital * CAPTIAL_PERCENTAGE, 'yes')
                        
                    elif middle_ask < bought_price - LOSS_FLOOR and not sold and not bought_twice:
                        print('considering mitigating losses')
                        sell_loss = middle_bid - bought_price
                        double_loss = 100 - bought_price - side_ask
                        
                        print('sell loss: ', sell_loss, "double_loss: ", double_loss)
                        if sell_loss > double_loss:
                            sold = True
                            sold_price = middle_bid
                            buy_kalshi(exchange_client,cur_market,total_capital * CAPTIAL_PERCENTAGE,'no')
                        else:
                            bought_twice = True
                            bought_price += side_ask
                            buy_kalshi(exchange_client,higher_market if higher else lower_market,total_capital * CAPTIAL_PERCENTAGE, 'yes')
            else:
                print('not in time range')

        print('---------------------------')
        time.sleep(1)
    

if __name__ == "__main__":
    # market_object = Kalshi_Market('INX-24FEB14-B4962',4962,1,1,1)
    # buy_kalsh2(start_kalshi_api(),market_object,100,'yes')
    operate_kalshi()