from client import start_kalshi_api
from datetime import datetime, time
import yfinance as yf

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

#get S&P data

def getSAPData():
    print('getting S&P data')
    SAP_history = yf.download(tickers="^SPX", period="1d", interval="1m")
    print('got SAP data')
    SAP_open = SAP_history['Open'][0]
    SAP_current = SAP_history['Open'][-1]
    return SAP_open, SAP_current

def getKalshiData(current_datetime, SAP_current):
    #Get Kalshi Data
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")

    exchange_client = start_kalshi_api()
    kalshi_ticker = 'INXD-' + year + month + day
    event_response = exchange_client.get_markets(event_ticker=kalshi_ticker)

    market_bids = dict()
    market_asks = dict()
    for event in event_response['markets']:
        event_ticker = event['ticker']
        if event_ticker[-5] == 'B':
            midpoint = float(event_ticker[-4:])
            market_bid = event['yes_bid'] #Ask and bid only for the yes catgegory
            market_ask = event['yes_ask']
            
            market_bids[midpoint] = market_bid
            market_asks[midpoint] = market_ask
        
    min_distance = 10000000    
    closestMarket = 0
    for index, midpoint in enumerate(market_bids.keys()):
        if (abs(SAP_current - midpoint) < min_distance):
            min_distance = abs(SAP_current - midpoint)
            closestMarket = midpoint

    kalshi_midpoint = closestMarket        
    kalshi_bid = market_bids[closestMarket]
    kalshi_ask = market_asks[closestMarket]
    # print(kalshi_midpoint,kalshi_bid,kalshi_ask)
    
    return exchange_client.get_balance(), kalshi_midpoint, kalshi_bid, kalshi_ask



def decideBuy(current_time, current_capital, kalshi_midpoint, kalshi_bid, kalshi_ask, SAP_open, SAP_current, have_bought):
    if current_time > time(15,BUY_MINUTE,0):
        #if price is in ask range
        if kalshi_ask > ASK_LOW and kalshi_ask < ASK_HIGH:
            #if S&P price is within the middle interval_ratio of the market range
            if abs(SAP_current - kalshi_midpoint) < KALSHI_INTERVAL_SIZE*INTERVAL_RATIO:
                #if the S&P hasn't moved more than percent_change in the day and haven't bought yet
                if 100*(abs(SAP_open-SAP_current)/SAP_open) < PERCENT_CHANGE and not have_bought:
                    buy_kalshi()
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
            
             
def buy_kalshi():
    pass
        
def sell_kalshi():
    pass

# print(event_response)

if __name__ == "__main__":
    
    # if current_time < time(16, 0 , 0) and current_time > time(9,30,0):
    
    have_bought = False
    have_sold = False
    bought_price = -1
    
    #get current time    
    current_datetime = datetime.now()
    
    SAP_open, SAP_current = getSAPData()
    current_capital, kalshi_midpoint, kalshi_bid, kalshi_ask = getKalshiData(current_datetime,SAP_current)

    if not have_bought:
        have_bought, bought_price = decideBuy(current_datetime.time(),current_capital, kalshi_midpoint, kalshi_bid, kalshi_ask, SAP_open, SAP_current, have_bought)
        
    if not have_sold:    
        have_sold = decideSell()
    

    
    