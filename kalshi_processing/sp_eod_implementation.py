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
PERCENT_CHANGE = 2      #maximum percent change of the S&P below which we will buy on that day (volatility control)
SELL_PRICE = 98         #price at which to always sell in order to lock in profit
LOSS_FLOOR = 10         #amount that, if the price drops this much below our buy price, we sell to mitigate losses 
KALSHI_INTERVAL_SIZE = 13
ARB_VAL = 99

months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
SAP_Data = [4970,4970,4970,4990]


class Kalshi_Market:
    def __init__(self,ticker,midpoint,bid,ask,vol):
        self.ticker = ticker
        self.midpoint = midpoint
        self.bid = bid
        self.ask = ask
        self.vol = vol

    def __str__(self) -> str:
        return str(self.ticker) + ' (bid,ask,vol): ' + str(self.bid) + ', ' + str(self.ask) + ', ' + str(self.vol)

def getSAPData():
    print('getting S&P data')
    SAP_history = yf.download(tickers="^SPX", period="1d", interval="1m")
    print('got SAP data')
    SAP_open = SAP_history['Open'].iloc[0]
    
    if FAKE_DATA:
        SAP_current = 0
    else:
        SAP_current = takeSAPScreenshot()
    return SAP_open, SAP_current

def takeSAPScreenshot():
    ss_region = (150,210, 250, 270)
    ss_img = ImageGrab.grab(ss_region)
    # ss_img.show()

    num = str(ocr.image_to_string(ss_img))

    temp = re.findall(r'\d+', num)
    res = list(map(int, temp))
    SAPVal = int(''.join([str(x) for x in res]))
    return SAPVal


def getKalshiData(exchange_client,current_datetime, SAP_current):
    #Get Kalshi Data
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    
    kalshi_ticker = 'INX-' + year + month + day
    print('Kalshi Ticker:', kalshi_ticker)
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)
    print(event_response)
    # print(event_response)
    
    kalshi_markets = []
    

    for event in event_response['markets']:
        event_ticker = event['ticker']
        if event_ticker[-5] == 'B':
            
        
            market_orderbook = exchange_client.get_orderbook(event_ticker)['orderbook']['yes']
            
            
            if market_orderbook != None:
                market_data = market_orderbook[-1]
                market_bid = market_data[0]
                market_vol = market_data[1]
                
            
                midpoint = float(event_ticker[-4:])
                market_ask = event['yes_ask']
                
                market_object = Kalshi_Market(event_ticker,midpoint,market_bid,market_ask,market_vol)
                kalshi_markets.append(market_object)
        
        
    min_distance = 10000000    
    closest_market_index = -1
    for i in range(len(kalshi_markets)):
        market_object = kalshi_markets[i]
        if (abs(SAP_current - market_object.midpoint) < min_distance):
            min_distance = abs(SAP_current - market_object.midpoint)
            closest_market_index = i
    
    # print([i.ticker for i in kalshi_markets])
    
    closest_market = kalshi_markets[closest_market_index]
    print(kalshi_markets)
    
    if closest_market_index+1 >= len(kalshi_markets):
        market_below = None
    else:
        market_below = kalshi_markets[closest_market_index+1]
        
    if closest_market_index - 1 < 0:
        market_above = None
    else:
        market_above = kalshi_markets[closest_market_index-1]
    
    
    return closest_market, market_below, market_above   
    print(closestMarket.ticker)
            
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
            SAP_open, SAP_current = getSAPData()
            print('SAP Data (open, current):',SAP_open, SAP_current)
            
            
            if not markets_set:
                cur_market, lower_market,higher_market = getKalshiData(exchange_client,current_datetime,SAP_current)
                markets_set = True
            else:
                cur_market, lower_market, higher_market = updateKalshiData(exchange_client,current_datetime,cur_market,lower_market,higher_market)
            
            print(lower_market)
            print(cur_market)
            print(higher_market)
            
            
            total_capital = exchange_client.get_balance()['balance']
            

            if TESTING or (current_time > Time(15,BUY_MINUTE,0) and current_time < Time(16,0,0)):
                print('is in time range')
                middle_bid, middle_ask = cur_market.bid, cur_market.ask
                if lower_market is not None:
                    lower_bid, lower_ask = lower_market.bid, lower_market.ask
                if higher_market is not None:
                    higher_bid, higher_ask = higher_market.bid, higher_market.ask
                
                kalshi_midpoint = cur_market.midpoint
                is_in_middle_range = abs(SAP_current-kalshi_midpoint) < KALSHI_INTERVAL_SIZE*(INTERVAL_RATIO/10)
                print('is in middle range:',is_in_middle_range)
                
                if not bought_middle and not bought_edge:
                    if is_in_middle_range:
                        if middle_ask < ASK_HIGH:
                            if 100*(abs(SAP_open-SAP_current)/SAP_open) < PERCENT_CHANGE:
                                buy_kalshi(exchange_client,cur_market, total_capital * CAPTIAL_PERCENTAGE, 'yes')
                                bought_price = middle_ask
                                bought_middle = True
                    else:
                        is_higher = SAP_current - kalshi_midpoint > 0
                        side_ask = higher_ask if is_higher else lower_ask
                        print('considering straddle buy with markets at', middle_ask, side_ask)
                        if middle_ask + side_ask < ARB_VAL:
                            bought_price = middle_ask + side_ask
                            bought_edge = True
                            buy_kalshi(exchange_client,cur_market, total_capital * CAPTIAL_PERCENTAGE/2, 'yes')
                            buy_kalshi(exchange_client,higher_market if is_higher else lower_market, total_capital * CAPTIAL_PERCENTAGE/2, 'yes')
                            
                
                elif bought_middle and not is_in_middle_range:
                    higher = SAP_current - kalshi_midpoint > 0
                    side_ask = higher_ask if higher else lower_ask
                    
                    
                    if abs(SAP_current - kalshi_midpoint) > 10 and not sold and not bought_twice:
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