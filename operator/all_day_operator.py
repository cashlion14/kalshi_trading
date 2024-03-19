from datetime import datetime as dt
from datetime import time as time
import time as sleeper
from client import start_kalshi_api, ExchangeClient
import logging
import yfinance as yf
import pandas as pd
from PIL import ImageGrab
import pytesseract as ocr
import re
import uuid
from enum import Enum
import math
import webbrowser
import os
from email_sender import send_trade_update
from email_sender import send_log

### ENUMS ###

"""
Represents the type of the market that we are currently dealing with
"""
class MarketType(Enum):
    Range = 1
    Above = 2

"""
Represents the different types of orders a may position may fall under, i.e. which purpose the position is used for
"""
class PositionType(Enum):
    BodOrder = 1
    ModArbOrder = 2
    EodArbOrder = 3
    EodMiddleOrder = 4
    EodLateArbOrder = 5
    EodReverseMiddleOrder = 6

"""
Represents the strategy currently being run
""" 
class Strategy(Enum):
    Bod = 1
    ModArb = 2
    Eod = 3

### KALSHI CLASS REPRESENTATIONS ###

"""
A Kalshi Market containing information about a given range market
    yeses and nos: structured as a list of bid price to volume tuples, [(price, vol), (price, vol), ...] 
"""
class KalshiMarket:
    def __init__(self,ticker,midpoint,yeses, nos, market_type, size=100):
        self.ticker = ticker
        self.midpoint = midpoint
        self.yeses = yeses[::-1]
        self.nos = nos[::-1]
        self.size = size
        self.type = market_type
        
    #returns the best asking price and volume
    def get_best_yes_ask(self, volume=False):
        if volume:
            return 100-self.nos[0][0], self.nos[0][1]
        else:
            return 100-self.nos[0][0]

    def get_best_yes_bid(self, volume=False):
        if volume:
            return self.yeses[0][0], self.yeses[0][1]
        else:
            return self.yeses[0][0]
    
    def get_best_no_ask(self, volume=False):
        if volume:
            return 100-self.yeses[0][0], self.yeses[0][1]
        else:
            return 100-self.yeses[0][0]

    def get_ticker(self) -> str:
        return self.ticker

    def get_midpoint(self) -> int:
        return self.midpoint
    
    def get_range_floor(self) -> int:
        return self.midpoint - self.size/2
    
    def get_range_ceiling(self) -> int:
        return self.midpoint + self.size/2
      
"""
Represents a position we have taken in the market
"""
class Position:
    def __init__(self, amount:int, price:int, ticker:str, position_type:PositionType):
        self.amount = amount
        self.price = price
        self.ticker = ticker
        self.position_type = position_type
        self.risk_status = False
        
    def get_risk_status(self):
        return self.risk_status
    
    def set_risk_status(self):
        self.risk_status = True
    
    def get_ticker(self):
        return self.ticker
    
    def get_price(self):
        return self.price
    
    def get_position_type(self):
        return self.position_type
    
    def set_position_type(self, position_type):
        self.position_type = position_type
    
    def get_amount(self):
        return self.amount
    
    def set_amount(self, amount):
        self.amount = amount
    
    def equal(self, other):
        return self.get_amount() == other.get_amount() and self.get_price() == other.get_price() and self.get_risk_status() == other.get_risk_status() and self.get_ticker() == other.get_ticker() and self.get_position_type() == other.get_position_type()      
            
"""
Represents our collective current positions
    capital is split into categories for each strategy
    contracts bought for each strategy are stored as lists
"""
class Orderbook:
    def __init__(self, bod_cap:int, mod_cap:int, eod_cap:int):
        self.starting_capital = (bod_cap, mod_cap, eod_cap)
        #when adjusting bod_cap, price might be slightly higher than realized bc of limit buy up to 47
        self.bod_capital  = bod_cap
        self.mod_capital = mod_cap
        self.eod_capital = eod_cap/2
        self.eod_reserve_capital = eod_cap/2
        
        self.bod_contracts = []
        #list of lists, where each sublist is a triplet of orders
        self.mod_contracts = []
        
        self.eod_middle_contracts = []
        #list of lists, where each sublist is a pair of orders
        self.eod_arb_contracts = []
        
    def get_starting_capital(self) -> int:
        return self.starting_capital
    
    def get_bod_capital(self) -> int:
        return self.bod_capital
    
    def set_bod_capital(self, amount) -> int:
        self.bod_capital += amount
    
    def get_mod_capital(self) -> int:
        return self.mod_capital
    
    def set_mod_capital(self, amount) -> int:
        self.mod_capital += amount
    
    def get_eod_capital(self) -> int:
        return self.eod_capital
    
    def set_eod_capital(self, amount) -> int:
        self.eod_capital += amount
        
    def get_eod_reserve_capital(self) -> int:
        return self.eod_reserve_capital
        
    def set_eod_reserve_capital(self, amount) -> int:
        self.eod_reserve_capital += amount
        
    def get_eod_middle_contracts(self) -> list[Position]:
        return self.eod_middle_contracts

    def add_eod_middle_contract(self, position) -> None:
        self.eod_middle_contracts.append(position)
        
    def get_eod_arb_contracts(self) -> list[Position]:
        return self.eod_arb_contracts
        
    def add_eod_arb_contracts(self, positions) -> None:
        self.eod_arb_contracts.append(positions)
    
    def get_eod_middle_contracts(self) -> list[Position]:
        return self.mod_contracts
        
    def add_mod_arb_contracts(self, positions) -> None:
        self.mod_contracts.append(positions)
    
    def get_bod_contracts(self) -> list[Position]:
        return self.bod_contracts
        
    def add_bod_contract(self, position) -> None:
        self.bod_contracts.append(position)
        
    #return True if we have open eod middle positions
    def check_eod_middle(self) -> bool:
        if len(self.get_eod_middle_contracts()) > 0:
            for position in self.get_eod_middle_contracts():
                if not position.get_risk_status():
                    return True
        return False
    
    #remove a contract from the orderbook
    def remove_eod_middle_contract(self, position) -> None:
        to_delete = -1
        for index, past_position in enumerate(self.get_eod_middle_contracts()):
            if position.equal(past_position):
                to_delete = index
        
        if to_delete < 0:
            raise Exception('Trying to update orderbook to reflect turning middle buy into edge arb, could not find order to move')
        else:
            del self.get_eod_middle_contracts()[index]
    
    #gets the order with the highest bought price of type position_type
    def get_max_price_open_position(self, position_type) -> Position:
        if position_type == PositionType.EodMiddleOrder:
            return max(self.get_eod_middle_contracts(), key = lambda position : position.get_price() if position.get_risk_status() else -1)
    
    #gets the order with the lowest bought price of type position_type
    def get_min_price_open_position(self, position_type) -> Position:
        if position_type == PositionType.EodMiddleOrder:
            return min(self.get_eod_middle_contracts(), key = lambda position : position.get_price() if position.get_risk_status() else 100000)
        
    """
    Take in a position and add it to the correct tracker in the orderbook
        position_type: the PositionType
        amount: amount of contracts bought
        side: yes or no
        order responses: the responses received from Kalshi
        past_order_to_update: the Position we need to update, if relevant
    """
    def trackPositions(self, position_type: PositionType, amount: int, side: str, order_response: dict, second_order_response: dict=dict(), third_order_response: dict=dict(), past_order_to_update: Position=Position(0,0,'',PositionType.BodOrder), bod_price: int = 0) -> None:
        if position_type == PositionType.EodMiddleOrder:
            order_status = order_response['order']['status']
            if order_status == 'executed':
                
                price = order_response['order'][f'{side}_price']
                position = Position(amount, price, order_response['order']['ticker'], PositionType.EodMiddleOrder)
                
                self.add_eod_middle_contract(position)
                self.set_eod_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price)))
                
            elif order_status == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')
        
        elif position_type == PositionType.EodArbOrder:
            first_order_status = order_response['order']['status']
            second_order_status = second_order_response['order']['status']
            if first_order_status == 'executed' and second_order_status == 'executed':
                
                first_order_price = order_response['order'][f'{side}_price']
                first_position = Position(amount, first_order_price, order_response['order']['ticker'], PositionType.EodArbOrder)
                
                second_order_price = second_order_response['order'][f'{side}_price']
                second_position = Position(amount, second_order_price, second_order_response['order']['ticker'], PositionType.EodArbOrder)
                
                self.add_eod_arb_contracts((first_position, second_position))
                
                self.set_eod_capital(-1 * (amount*(first_order_price/100) + calculateKalshiFee(amount, first_order_price)))
                self.set_eod_capital(-1 * (amount*(second_order_price/100) + calculateKalshiFee(amount, second_order_price)))
            
            elif first_order_status == 'canceled' and second_order_status == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Only one side of arb order could be completed')
            
        elif position_type == PositionType.EodLateArbOrder:
            order_status = order_response['order']['status']
            if order_status == 'executed':
                
                price = order_response['order'][f'{side}_price']
                position = Position(amount, price, order_response['order']['ticker'], PositionType.EodLateArbOrder)
                position.set_risk_status()
                
                self.add_eod_middle_contract(position)
                self.set_eod_reserve_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price)))

                if past_order_to_update.get_amount() > amount:
                    unmanaged_position = Position(past_order_to_update.get_amount() - amount, past_order_to_update.get_price(), past_order_to_update.get_ticker(), PositionType.EodMiddleOrder)
                    self.add_eod_middle_contract(unmanaged_position)
                    past_order_to_update.set_amount(amount)
                
                past_order_to_update.set_risk_status()
                    
            elif order_status == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')
            
        elif position_type == PositionType.EodReverseMiddleOrder:
            order_status = order_response['order']['status']
            if order_status == 'executed':
                
                price = order_response['order'][f'{side}_price']
                
                self.set_eod_capital(amount*((100-price)/100) - calculateKalshiFee(amount, price))
                
                if past_order_to_update.get_amount() > amount:
                    unmanaged_position = Position(past_order_to_update.get_amount() - amount, past_order_to_update.get_price(), past_order_to_update.get_ticker(), PositionType.EodMiddleOrder)
                    self.add_eod_middle_contract(unmanaged_position)
                    past_order_to_update.set_amount(amount)
                
                past_order_to_update.set_risk_status()
                 
            elif order_status == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')
        
        elif position_type == PositionType.ModArbOrder:
            if order_response['order']['status'] == 'executed' and second_order_response['order']['status'] == 'executed' and third_order_response['order']['status'] == 'executed':
                
                if side == '1':
                    side = ('no', 'yes', 'yes')
                elif side == '2':
                    side = ('yes', 'no', 'yes')
                    
                first_order_price = order_response['order'][f'{side[0]}_price']
                first_position = Position(amount, first_order_price, order_response['order'][f'ticker'], PositionType.ModArbOrder)
                
                second_order_price = second_order_response['order'][f'{side[1]}_price']
                second_position = Position(amount, second_order_price, second_order_response['order'][f'ticker'], PositionType.ModArbOrder)
                
                third_order_price = third_order_response['order'][f'{side[2]}_price']
                third_position = Position(amount, third_order_price, third_order_response['order'][f'ticker'], PositionType.ModArbOrder)
    
                self.add_mod_arb_contracts((first_position, second_position, third_position))
                
                self.set_mod_capital(-1 * (amount*(first_order_price/100) + calculateKalshiFee(amount, first_order_price)))
                self.set_mod_capital(-1 * (amount*(second_order_price/100) + calculateKalshiFee(amount, second_order_price)))
                self.set_mod_capital(-1 * (amount*(third_order_price/100) + calculateKalshiFee(amount, third_order_price)))
            
            elif order_response['order']['status'] == 'canceled' and second_order_response['order']['status'] == 'canceled' and third_order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Only one side of arb order could be completed')
        
        elif position_type == PositionType.BodOrder:
            if order_response['order']['status'] == 'executed':
                
                price = bod_price
                position = Position(amount, price, order_response['order']['ticker'], PositionType.BodOrder)
                
                self.add_bod_contract(position)
                
                self.set_bod_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price)))
                
            elif order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')

### UTILITY FUNCTIONS ###

"""
Get Index Open Price
    only works after 946am for the given day
"""
def getIndexOpen(ticker:str="^NDX") -> int:
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
If safari is False, can use chrome instead
"""
def getNDXCurrentPrice(safari:bool=True) -> int:
    if safari:
        logging.info(f'Getting current NDX price')
        ss_region = (150,210, 260, 270)
        ss_img = ImageGrab.grab(ss_region)
        # ss_img.show()

        num = str(ocr.image_to_string(ss_img))
        temp = re.findall(r'\d+', num)
        NDXVal = int(''.join([str(x) for x in temp]))
        logging.info(f'Got current NDX price')
        return NDXVal
    else:
        logging.info(f'Getting current NDX price')
        ss_region = (150,290, 260, 330)
        ss_img = ImageGrab.grab(ss_region)
        # ss_img.show()

        num = str(ocr.image_to_string(ss_img))
        temp = re.findall(r'\d+', num)
        NDXVal = int(''.join([str(x) for x in temp]))
        logging.info(f'Got current NDX price {NDXVal}')
        return NDXVal

"""
Places a basic kalshi market buy order
    account: get by running start_kalshi_api()
    market: a KalshiMarket object
    amount: the number of contracts to buy
    side: a string, 'yes' or 'no'
    max_price: the maximum price at which order will buy
"""
def placeKalshiMarketOrder(account: ExchangeClient, market: KalshiMarket, amount: int, side: str, max_price: int) -> None:
    ticker = market.get_ticker()
    order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'limit',
                    'action':'buy',
                    f'{side}_price': max_price,
                    'side':side,
                    'count': amount}
    return account.create_order(**order_params)

"""
Gets the beginning of the day market, current, and returns it. If it doesn't exist, will return empty market object
"""
def getBodMarkets(account, current_datetime, months_array, current_index_price):
    #create current, high, low tickers
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    current_ticker = 'NASDAQ100-' + year + month + day + '-B' + str(current_index_price)[:3]+'50'
    
    #create KalshiMarkets
    current_orderbook = account.get_orderbook(current_ticker)['orderbook']
    
    if current_orderbook is not None:
        yes_book = current_orderbook['yes']
        no_book = current_orderbook['no']
        
        yeses = yes_book if yes_book is not None else []
        nos = no_book if no_book is not None else []
        
        midpoint = float(current_ticker[-5:])
        
        current_market = KalshiMarket(current_ticker,midpoint,yeses,nos, MarketType.Range)
    else:
        current_market = KalshiMarket(current_ticker,midpoint,[],[], MarketType.Range)
    
    return current_market

"""
Gets middle of the day markets (all range, all above/below). If there is no volume, it won't get added to the list. 
"""
def getModMarkets(account, current_datetime, months_array) -> tuple[list[KalshiMarket], list[KalshiMarket]]:
    
    #create current, high, low tickers
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    range_event = 'NASDAQ100-' + year + month + day
    range_event_response = account.get_markets(event_ticker=range_event)

    range_markets = []
    for range_event in range_event_response['markets']:
        range_event_ticker = range_event['ticker']
        
        if range_event_ticker[-6] == 'B':
            orderbook = account.get_orderbook(range_event_ticker)['orderbook']
            yes_orderbook = orderbook['yes']
            no_orderbook = orderbook['no']
            
            if yes_orderbook != None and no_orderbook != None:
                midpoint = float(range_event_ticker[-5:])
                
                market = KalshiMarket(range_event_ticker, midpoint, yes_orderbook, no_orderbook, MarketType.Range)
                range_markets.append(market)
    
    above_event = 'NASDAQ100U-' + year + month + day
    above_event_response = account.get_markets(event_ticker=above_event)
    
    above_markets = []
    for above_event in above_event_response['markets']:
        above_event_ticker = above_event['ticker']
        market_orderbook = account.get_orderbook(above_event_ticker)['orderbook']
        yes_orderbook = market_orderbook['yes']
        no_orderbook = market_orderbook['no']
        
        if yes_orderbook != None and no_orderbook != None:
            strike_val = round(float(above_event_ticker[-8:]),0)
            
            above_market = KalshiMarket(above_event_ticker,strike_val, yes_orderbook, no_orderbook, MarketType.Above)
            above_markets.append(above_market)
    
    return range_markets, above_markets

"""
Gets end of day markets (low, middle, high). If there is no volume on the market will return empty market object. If market is on edge of the range will not include it
"""
def getEodMarkets(account: ExchangeClient, current_datetime: dt, months_array: list[str], current_index_price: int) -> tuple[KalshiMarket, KalshiMarket, KalshiMarket]:
    
    #create current, high, low tickers
    day = current_datetime.strftime("%d")
    month_num = int(current_datetime.strftime("%m"))
    month = months_array[month_num - 1]
    year = current_datetime.strftime("%y")
        
    current_ticker = 'NASDAQ100-' + year + month + day + '-B' + str(current_index_price)[:3]+'50'
    
    high_ticker = current_ticker[:21] + str(int(current_ticker[21])+1) + current_ticker[22:]
    low_ticker = current_ticker[:21] + str(int(current_ticker[21])-1) + current_ticker[22:]
    
    #create KalshiMarkets
    current_orderbook = account.get_orderbook(current_ticker)['orderbook']
    if current_orderbook is not None:
        yes_book = current_orderbook['yes']
        no_book = current_orderbook['no']
        
        yeses = yes_book if yes_book is not None else []
        nos = no_book if no_book is not None else []
        
        if len(yeses) == 0 and len(nos) == 0:
            raise Exception('current market has no volume')
        
        midpoint = float(current_ticker[-5:])
        
        current_market = KalshiMarket(current_ticker,midpoint,yeses,nos, MarketType.Range)
    else:
        current_market = KalshiMarket(current_ticker,midpoint,[],[], MarketType.Range)
    
    high_orderbook = account.get_orderbook(high_ticker)['orderbook']
    if high_orderbook is not None:
        yes_book = high_orderbook['yes']
        no_book = high_orderbook['no']
        
        yeses = yes_book if yes_book is not None else []
        nos = no_book if no_book is not None else []
        
        midpoint = float(high_ticker[-5:])
        
        high_market = KalshiMarket(high_ticker,midpoint,yeses,nos, MarketType.Range)
    else:
        high_market = KalshiMarket(high_ticker,midpoint,[],[],MarketType.Range)
    
    low_orderbook = account.get_orderbook(low_ticker)['orderbook']
    if low_orderbook is not None:
        yes_book = low_orderbook['yes']
        no_book = low_orderbook['no']
        
        yeses = yes_book if yes_book is not None else []
        nos = no_book if no_book is not None else []
        
        midpoint = float(high_ticker[-5:])
        
        low_market = KalshiMarket(low_ticker,midpoint,yeses,nos, MarketType.Range)
    else:
        low_market = KalshiMarket(low_ticker,midpoint,[],[], MarketType.Range)

    return low_market, current_market, high_market

"""
Calculates the total fee related to the Kalshi order. Fee only applies if order is immediate.
    APPLIES ONLY TO NASDAQ AND SPX MARKETS
    amount: number of contracts
    price: price of the contract from 0 -> 100
"""
def calculateKalshiFee(amount, price):
    price = price/100
    return math.ceil(100*(0.035 * amount * price * (1-price)))/100

"""
Calculates the number of contracts to buy for a given order
    current_price: from 0 to 100
"""
def calculateVolumeToTrade(position_type: PositionType, capital: float | int, current_price: int, closest_price: int=0, third_price: int=0) -> int:
    current_price = current_price/100
    
    if position_type == PositionType.EodMiddleOrder:
        numerator = capital - 0.01
        denominator = current_price + 0.035 * current_price * (1-current_price)
        return math.floor(numerator/denominator)
    
    elif position_type == PositionType.EodArbOrder:
        closest_price = closest_price/100
        
        numerator = capital - 0.02
        den_one = (current_price + closest_price)
        den_two = 0.035*current_price*(1-current_price)
        den_three = 0.035*closest_price*(1-closest_price)
        return math.floor(numerator/(den_one+den_two+den_three))
    
    elif position_type == PositionType.ModArbOrder:
        closest_price = closest_price/100
        third_price = third_price/100
        
        numerator = capital - 0.03
        den_one = (current_price + closest_price + third_price)
        den_two = 0.035*current_price*(1-current_price)
        den_three = 0.035*closest_price*(1-closest_price)
        den_four = 0.035*third_price*(1-third_price)
        return math.floor(numerator/(den_one+den_two+den_three+den_four))
    
    elif position_type == PositionType.BodOrder:
        numerator = capital - 0.01
        denominator = current_price + 0.035 * current_price * (1-current_price)
        return math.floor(numerator/denominator)
        
### STRATEGIES ### 

"""
Runs the BOD strategy. Strategy: every day in the morning, buy the market that the index is currently in. It's historically underpriced and will make money.
"""
def run_bod(account: ExchangeClient, orderbook: Orderbook, current_datetime:dt, months_array:list[str], current_index_price: int) -> None:
    #get the current market and buy it up to 27 percent
    current_market = getBodMarkets(account, current_datetime, months_array, current_index_price)
    current_market_ask = current_market.get_best_yes_ask()
    
    bod_capital = orderbook.get_bod_capital() * 0.27
    if len(orderbook.get_bod_contracts()) == 0:
        trade_volume = calculateVolumeToTrade(PositionType.BodOrder, bod_capital, current_market_ask)
        bod_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', 47)
        send_trade_update('yes', current_market_ask, trade_volume)

        orderbook.trackPositions(PositionType.BodOrder, trade_volume, 'yes', bod_order, bod_price=current_market_ask) 
        logging.info(f'Made an order for Bod contract of amount {trade_volume} at price {current_market_ask} on market {current_market.get_ticker()}')
    else:
        sleeper.sleep(60)
    
"""
Runs MOD all day arbitrage strategy. Strategy: try to arb between range and above/below markets.
"""
def run_all_day_arbitrage(account: ExchangeClient, orderbook: Orderbook, current_datetime: dt, months_array: list[str]):
    range_markets, above_markets = getModMarkets(account, current_datetime, months_array)
    
    for range_market in range_markets:
        range_floor = range_market.get_range_floor()
        range_ceiling = range_market.get_range_ceiling()
        
        floor_market = -1
        for above_market in above_markets:
            if above_market.get_midpoint() == range_floor:
                floor_market = above_market
                
        ceiling_market = -1
        for above_market in above_markets:
            if above_market.get_midpoint() == range_ceiling:
                ceiling_market = above_market
        
        if floor_market != -1 and ceiling_market != -1:
            range_market_yes_ask, range_market_yes_vol = range_market.get_best_yes_ask(volume=True)
            range_market_no_ask, range_market_no_vol = range_market.get_best_no_ask(volume=True)
            floor_market_yes_ask, floor_market_yes_vol = floor_market.get_best_yes_ask(volume=True)
            floor_market_no_ask, floor_market_no_vol = floor_market.get_best_no_ask(volume=True)
            ceiling_market_yes_ask, ceiling_market_yes_vol = ceiling_market.get_best_yes_ask(volume=True)
            ceiling_market_no_ask, ceiling_market_no_vol = ceiling_market.get_best_no_ask(volume=True)
            
            logging.info(f'Testing arbitrage opportunity 1, <$2, with a floor market yes of {floor_market_yes_ask}, a range market no of {range_market_no_ask} and a ceiling market no of {ceiling_market_no_ask}.')
            max_contracts_buyable = min(floor_market_yes_vol, range_market_no_vol, ceiling_market_no_vol)
            if sum([floor_market_yes_ask/100, range_market_no_ask/100, ceiling_market_no_ask/100]) + calculateKalshiFee(max_contracts_buyable, floor_market_yes_ask)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, range_market_no_ask)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, ceiling_market_no_ask)/max_contracts_buyable < 2:
            
                mod_capital = orderbook.get_mod_capital()
                max_order_capital = (floor_market_yes_ask/100 + range_market_no_ask/100 + ceiling_market_no_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, floor_market_yes_ask) + calculateKalshiFee(max_contracts_buyable, range_market_no_ask) + calculateKalshiFee(max_contracts_buyable, ceiling_market_no_ask)
            
                trade_volume = max_contracts_buyable if mod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, mod_capital, floor_market_yes_ask, range_market_no_ask, ceiling_market_no_ask) 
            
                first_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'yes', floor_market_yes_ask)
                second_edge_order = placeKalshiMarketOrder(account, range_market, trade_volume, 'no', range_market_no_ask)
                third_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'no', ceiling_market_no_ask)
                send_trade_update('yes/no/no', 'Range/Above', trade_volume)
                
                
                orderbook.trackPositions(PositionType.ModArbOrder, trade_volume, '2', first_edge_order, second_order_response=second_edge_order, third_order_response=third_edge_order) 

                logging.info(f'Made an order for range/above arb of volume {trade_volume} at prices {floor_market_yes_ask/100} and {range_market_no_ask/100} and {ceiling_market_no_ask}')
            
            logging.info(f'Testing arbitrage opportunity 2, <$1, with a floor market no of {floor_market_no_ask}, a range market yes of {range_market_yes_ask} and a ceiling market yes of {ceiling_market_yes_ask}.')
            max_contracts_buyable = min(floor_market_no_vol, range_market_yes_vol, ceiling_market_yes_vol)
            if sum([floor_market_no_ask/100, range_market_yes_ask/100, ceiling_market_yes_ask/100])  + calculateKalshiFee(max_contracts_buyable, floor_market_no_ask)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, range_market_yes_ask)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, ceiling_market_yes_ask)/max_contracts_buyable < 1:
                
                mod_capital = orderbook.get_mod_capital()
                max_order_capital = (floor_market_no_ask/100 + range_market_yes_ask/100 + ceiling_market_yes_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, floor_market_no_ask) + calculateKalshiFee(max_contracts_buyable, range_market_yes_ask) + calculateKalshiFee(max_contracts_buyable, ceiling_market_yes_ask)
            
                trade_volume = max_contracts_buyable if mod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, mod_capital, floor_market_no_ask, range_market_yes_ask, ceiling_market_yes_ask) 

                first_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'no', floor_market_no_ask)
                second_edge_order = placeKalshiMarketOrder(account, range_market, trade_volume, 'yes', range_market_yes_ask)
                third_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'yes', ceiling_market_yes_ask)
                send_trade_update('no/yes/yes', 'Range/Above', trade_volume)
                
                orderbook.trackPositions(PositionType.ModArbOrder, trade_volume, '1', first_edge_order, second_order_response=second_edge_order, third_order_response=third_edge_order) 

                logging.info(f'Made an order for range/above arb of volume {trade_volume} at prices {floor_market_no_ask/100} and {range_market_yes_ask/100} and {ceiling_market_yes_ask}')

"""
Runs EOD strategy
    safari: true if we are using safari to get the NDX price, false if Chrome
    market size: size of the range market
    middle_range_percent: size of middle trading range as a percent of the market size
    arb_value: maximum combined cost to go ahead with arb
    ask_high: highest price at which we will buy middle
    percent_change: the max percent we will allow on change in day's index value before we don't allow trades
    loss_floor: if kalshi drops by this much, we will try to sell off
"""
def run_eod(account: ExchangeClient, safari: bool, orderbook: Orderbook, NDXopen: int, current_datetime: dt, months_array: list[str], market_size:int=100, middle_range_percent:int=50, arb_value:int=98, ask_high:int=97, percent_change:int=2, loss_floor:int=10):
    #get current NDX price and working capital
    current_index_price = getNDXCurrentPrice(safari)
    
    #get markets above, middle, below
    low_market, current_market, high_market = getEodMarkets(account, current_datetime, months_array, current_index_price)
    
    #get midpoint
    current_market_midpoint = current_market.get_midpoint()
    
    #check if NDX is in middle range
    in_middle_range = abs(current_index_price-current_market_midpoint) < (market_size/2)*(middle_range_percent/100)
    
    #run buying steps: can buy middle or buy the edge
    if not in_middle_range:
        is_above_midpoint = current_index_price - current_market_midpoint > 0
        current_ask, current_volume = current_market.get_best_yes_ask(volume=True)
        closest_range_ask, closest_range_volume = high_market.get_best_yes_ask(volume=True) if is_above_midpoint else low_market.get_best_yes_ask(volume=True)
        logging.info(f'Considering an edge buy with current market at {current_ask}, closest market at {closest_range_ask}')
        
        if current_ask + closest_range_ask < arb_value and current_ask > 3 and closest_range_ask > 3:
            max_contracts_buyable = min(current_volume, closest_range_volume)
            
            eod_capital = orderbook.get_eod_capital()
            max_order_capital = (current_ask/100)*max_contracts_buyable + (closest_range_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, current_ask) + calculateKalshiFee(max_contracts_buyable, closest_range_ask)

            trade_volume = max_contracts_buyable if eod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, eod_capital, current_ask, closest_range_ask) 
            
            first_edge_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', current_ask)
            second_edge_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, trade_volume, 'yes', closest_range_ask)
            send_trade_update('yes', f'{current_ask} and {closest_range_ask}', trade_volume)
            
            orderbook.trackPositions(PositionType.EodArbOrder, trade_volume, 'yes', first_edge_order, second_order_response=second_edge_order) 

            logging.info(f'Made an order for EOD edge arb of volume {trade_volume} at prices {current_ask} and {closest_range_ask}')
    else:
        current_ask, current_volume = current_market.get_best_yes_ask(volume=True)
        if current_ask < ask_high and current_ask > 20:
            if 100*(abs(NDXopen-current_index_price)/NDXopen) < percent_change:
                logging.info(f'Considering a middle buy with current market at {current_ask}, percent change at {percent_change}')
                
                eod_capital = orderbook.get_eod_capital()
                max_order_capital = (current_ask/100)*current_volume + calculateKalshiFee(current_volume, current_ask)
                
                trade_volume = current_volume if eod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodMiddleOrder, eod_capital, current_ask)
        
                middle_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', current_ask)
                orderbook.trackPositions(PositionType.EodMiddleOrder, trade_volume, 'yes', middle_order)
                send_trade_update('yes', current_ask, trade_volume)
                
                logging.info(f'Made an order for EOD middle trade of volume {trade_volume} at price {current_ask}')
        
    #if bought, run risk management steps
    if not in_middle_range and orderbook.check_eod_middle():
        logging.info('Market has left the middle range and we have middle contracts that are not risk managed')
        is_above_midpoint = current_index_price - current_market_midpoint > 0
        current_ask, current_ask_volume = current_market.get_best_yes_ask(volume=True)
        current_bid, current_bid_volume = current_market.get_best_yes_bid(volume=True)
        closest_range_ask, closest_range_volume = high_market.get_best_yes_ask(volume=True) if is_above_midpoint else low_market.get_best_yes_ask(volume=True)
        
        max_price_position = orderbook.get_max_price_open_position(PositionType.EodMiddleOrder)
        max_position_price = max_price_position.get_price()
        max_position_amount = max_price_position.get_amount()
        
        min_price_position = orderbook.get_min_price_open_position(PositionType.EodMiddleOrder)
        min_position_price = min_price_position.get_price()
        min_position_amount = min_price_position.get_amount()
        
        #arb on middle contracts if we are in end range
        if abs(current_index_price - current_market_midpoint) > 20:
            logging.info(f'Considering loss arb on middle contracts at current index price {current_index_price} and market midpoint of {current_market_midpoint} with position/closest prices of {min_position_price}/{closest_range_ask}')

            if min_position_price + closest_range_ask + calculateKalshiFee(closest_range_volume, closest_range_ask)/closest_range_volume <= 99:
                late_arb_amount = min(closest_range_volume, min_position_amount)
                buy_late_arb_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, late_arb_amount, 'yes', closest_range_ask)
                orderbook.trackPositions(PositionType.EodLateArbOrder, late_arb_amount, 'yes', buy_late_arb_order, past_order_to_update=min_price_position)
                send_trade_update('yes', closest_range_ask, trade_volume)
                
                logging.info(f'Buying next position over to arb, with closest range price of {closest_range_ask} and position price of {min_position_price} at volume of {late_arb_amount}.')
                
        #if cost plummeting then sell
        elif current_ask < max_position_price - loss_floor:
            logging.info(f'Considering selling on middle contracts to mitigate losses at {current_ask} and position price {max_position_price}')
            sell_loss = current_bid - max_position_price
            buy_again_loss = 100 - max_position_price - closest_range_ask
            
            if sell_loss > buy_again_loss:
                buy_no_amount = min(current_bid_volume, max_position_amount)
                buy_no_order = placeKalshiMarketOrder(account, current_market, buy_no_amount, 'no', 100-current_bid)
                orderbook.trackPositions(PositionType.EodReverseMiddleOrder, buy_no_amount, 'no', buy_no_order, past_order_to_update=max_price_position)
                send_trade_update('no', 100-current_bid, trade_volume)
                
                logging.info(f'Sold on middle contracts to mitigate losses for volume of {buy_no_amount} at price {100-current_bid}')
            
            else:
                logging.info(f'Considering buying closest range to arb losses away, with closest range price of {closest_range_ask}')
                buy_another_yes_amount = min(closest_range_volume, max_position_amount)
                buy_another_yes_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, buy_another_yes_amount, 'yes', closest_range_ask)
                orderbook.trackPositions(PositionType.EodLateArbOrder, buy_another_yes_amount, 'yes', buy_another_yes_order, past_order_to_update=max_price_position)
                send_trade_update('yes', closest_range_ask, trade_volume)
                
                logging.info(f'Bought edge contract to mitigate losses with volume of {buy_another_yes_amount} for {closest_range_ask}')
    else:
        logging.info(f'Market is still safely in the middle range')

"""
Runs our strategies for the day. Holder for our three strategy functions and some logging.
"""
def run_strategies(account: ExchangeClient, orderbook: Orderbook, current_time: time, NDXopen: int, current_datetime: dt, months_array: list[str], safari: bool, page_reloaded: bool) -> None:
    
    if current_time > time(9,30,0) and current_time < time(9,47,0):
        logging.info('Trading day has begun, but we are waiting for first price to load for BOD strategy')
        sleeper.sleep(60)

    if current_time > time(9,47, 0) and current_time < time(9, 50, 0):
        logging.info(f'Trying to run beginning of day strategy with ${orderbook.get_bod_capital()} in capital')
        run_bod(account, orderbook, current_datetime, months_array, NDXopen)
                    
    # elif current_time > time(9, 50, 0) and current_time < time(15, 50, 0):
    #     logging.info(f'Trying to run middle of day arb strategy with ${orderbook.get_mod_capital()} in capital')
    #     run_all_day_arbitrage(account, orderbook, current_datetime, months_array)
    
    elif current_time > time(15, 45, 0) and current_time < time(15,50,0):
        if not page_reloaded:
            page_reloaded = True
            webbrowser.get('open -a /Applications/Google\ Chrome.app %s').open('https://kalshi.com/markets/nasdaq100/nasdaq-range') 
    
    elif current_time > time(15, 50, 0) and current_time < time(16, 0, 0):
        logging.info(f'Trying to run end of day strategy with ${orderbook.get_eod_capital()} in capital')
        run_eod(account, safari, orderbook, NDXopen, current_datetime, months_array)

### OPERATOR ###

def operate_kalshi(safari:bool=True) -> None:
    
    bod_capital = int(input("Enter how much to place in BOD strategy today, as an int. Default is 25: "))
    mod_capital = int(input("Enter how much to place in MOD strategy today, as an int. Default is 0: "))
    eod_capital = int(input("Enter how much to place in EOD strategy today, as an int. Default is 50 "))

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
        logging.exception(f'Cannot connect to kalshi server/cannot get balance: {error}.')
    
    #create the day's orderbook
    orderbook = Orderbook(bod_capital, mod_capital, eod_capital)
    logging.info(f'Created orderbook, with bod_capital of ${bod_capital}, mod_capital of ${mod_capital}, and eod_capital of ${eod_capital}.')
    
    months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
    
    got_open = False
    sent_log = False
    page_reloaded = False

    while True:
        current_datetime = dt.now()
        current_time = current_datetime.time()
        
        if current_datetime.today().weekday() < 5:
            if current_time < time(16,0,0):
                if current_time > time(9,30,0):
                    
                    if not got_open and current_time > time(9, 47, 0):
                        NDXopen = getIndexOpen()
                        got_open = True
                    else:
                        NDX_open = 0
                    
                    try:
                        run_strategies(account, orderbook, current_time, NDXopen, current_datetime, months_array, safari, page_reloaded)
                    except Exception as error:
                        print('An error occurred running strategies: \n', error)
                        logging.exception(f'An error occurred running strategies: {error}')
                        sleeper.sleep(60)
                
                else:
                    print(f'Current Time is: {current_time}. It is not yet time to trade.')
                    logging.info(f'It is not yet time to trade. Will check again in 1 minute.')
                    sleeper.sleep(60)     
            elif current_time > time(16,0,0) and current_time < time(16,6,0):
                if not sent_log:
                    os.system("killall -9 'Google Chrome'")
                    send_log()
                    sent_log = True
            else:
                print(f'Current Time is {current_time}. The trading day is over.')
                logging.info(f'The trading day is over. Will check again in 10 minutes.')
                sleeper.sleep(600)
        else:
            print(f'Current Time is {current_time}. It is currently the weekend.')
            logging.info(f'It is currently the weekend. Will check in again in 8 hours.')
            sleeper.sleep(60*60*8)
                  
if __name__ == "__main__":
    operate_kalshi()
    #fix trading error here