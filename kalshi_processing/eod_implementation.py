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


DEMO_MODE = False

BUY_MINUTE = 55         # first minute (3:xx PM) we allow to buy 
SELL_MINUTE = 56        # first minute (3:xx PM) we allow to sell
CAPTIAL_PERCENTAGE = 20 # percentage of our capital to bet on each trade
INTERVAL_RATIO = 8      # #divide by 10, its the percent of the range youd buy in (in the middle)
ASK_LOW = 70            #minumum price to buy stock at
ASK_HIGH = 97           #maximum price to buy stock at
PERCENT_CHANGE = 2      #maximum percent change of the S&P below which we will buy on that day (volatility control)
SELL_PRICE = 98         #price at which to always sell in order to lock in profit
LOSS_FLOOR = 10         #amount that, if the price drops this much below our buy price, we sell to mitigate losses 
KALSHI_INTERVAL_SIZE = 25


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

def getSAPData():
    # print('getting S&P data')
    SAP_history = yf.download(tickers="^SPX", period="1d", interval="1m")
    # print('got SAP data')
    SAP_open = SAP_history['Open'].iloc[0]
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


def getKalshiData(current_datetime, SAP_current):
    #Get Kalshi Data
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")

    if DEMO_MODE:
        exchange_client = start_demo_api()
    else:
        exchange_client = start_kalshi_api()
        
    
    kalshi_ticker = 'INX-' + year + month + day
    print('Kalshi Ticker:', kalshi_ticker)
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)

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
    market_below = kalshi_markets[closest_market_index+1]
    market_above = kalshi_markets[closest_market_index-1]
    
    return closest_market, market_below, market_above
    
    print(closestMarket.ticker)
            
    # kalshi_bid = market_bids[closestMarket]
    # kalshi_ask = market_asks[closestMarket]
    # print(kalshi_midpoint,kalshi_bid,kalshi_ask)
    
    
    # return kalshi_ticker, kalshi_midpoint, kalshi_bid, kalshi_ask, exchange_client



def decideBuy(current_time, current_capital, kalshi_midpoint, kalshi_bid, kalshi_ask, SAP_open, SAP_current, have_bought, exchange_client):
    if current_time > Time(15,BUY_MINUTE,0):
        #if price is in ask range
        if kalshi_ask > ASK_LOW and kalshi_ask < ASK_HIGH:
            #if S&P price is within the middle interval_ratio of the market range
            if abs(SAP_current - kalshi_midpoint) < KALSHI_INTERVAL_SIZE*INTERVAL_RATIO:
                #if the S&P hasn't moved more than percent_change in the day and haven't bought yet
                if 100*(abs(SAP_open-SAP_current)/SAP_open) < PERCENT_CHANGE and not have_bought:
                    amt = current_capital*CAPTIAL_PERCENTAGE
                    side = 'yes'
                    buy_kalshi(amt,side,exchange_client)
                    return True, kalshi_ask
    return False, -1
                    

def decideSell(current_time, kalshi_bid, kalshi_ask, have_bought):
    #if within sell time bounds
    if current_time > time(15,SELL_MINUTE,0):
        #if can sell above our threshold price or have lost loss_floor amount of money, sell
        if (kalshi_bid > SELL_PRICE or kalshi_ask < bought_price - LOSS_FLOOR) and have_bought:
            sell_kalshi()
            return True
    
    return False
            
             
def buy_kalshi(amt, side,exchange_client):
    print('buying kalshi')
    # ticker = 
    # order_params = {'ticker':ticker,
    #                 'client_order_id':str(uuid.uuid4()),
    #                 'type':'market',
    #                 'action':'buy',
    #                 'side':side,
    #                 'count':amt}
    # exchange_client.create_order(**order_params)
        
def sell_kalshi():
    pass

# print(event_response)


def operate_kalshi():
    
    have_bought = False
    have_sold = False
    bought_price = -1
    
    while True:
    
        #get current time    
        current_datetime = datetime.now()
        current_time = current_datetime.time()
        
        
        if current_time < Time(16,0) and current_time > Time(9,30):    
            SAP_open, SAP_current = getSAPData()
            print('SAP Data (open, current):',SAP_open, SAP_current)
            
            closest_market, market_below,market_above = getKalshiData(current_datetime,SAP_current)
            print(market_below)
            print(closest_market)
            print(market_above)
            
            
            # if not have_bought:
            #     have_bought, bought_price = decideBuy(current_datetime.time(),exchange_client.get_balance(), kalshi_midpoint, kalshi_bid, kalshi_ask, SAP_open, SAP_current, have_bought,exchange_client)
                
                
            # if have_bought and not have_sold:    
            #     have_sold = decideSell(current_time, kalshi_bid, kalshi_ask, have_bought)
        
        
        
        else:
            print('out of time range and reseting variables')
            have_bought = False
            have_sold = False
            bought_price = -1

        print('---------------------------')
        time.sleep(15)
    

if __name__ == "__main__":
    operate_kalshi()