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
import math
from email_sender import send_email_update

### KALSHI CLASS REPRESENTATIONS ###

"""
A Kalshi Market containing information about a given range market
    bids and asks: structured as a list of price-volume tuples, [(price, vol), (price, vol), ...]
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

    def get_ticker(self):
        return self.ticker

    def get_midpoint(self):
        return self.midpoint
    
    def get_range_floor(self):
        return self.midpoint - self.size/2
    
    def get_range_ceiling(self):
        return self.midpoint + self.size/2
            
class MarketType(Enum):
    Range = 1
    Above = 2

"""
Represents the positions that we currently have
    each position is indexed by market, price, and volume
    positions is a dictionary within a dictionary
    the outer dictionary maps ticker to a dictionary containing yes and no
    within the inner dictionary, map yes & no string to a list
    list contains price-volume tuples [(price, vol), (price, vol), ...]
"""
class Orderbook:
    def __init__(self, bod_cap, mod_cap, eod_cap):
        self.bod_contracts = []
        self.mod_contracts = []
        self.starting_capital = (bod_cap, mod_cap, eod_cap)
        self.bod_capital  = bod_cap
        self.mod_capital = mod_cap
        self.eod_capital = eod_cap/2
        self.eod_reserve_capital = eod_cap/2
        
        #split into 'edge' and 'middle' lists
        self.eod_middle_contracts = []
        self.eod_arb_contracts = []
        
        #my edge contracts are a certain kind of risk management so I want those tagged (out of range)
        #middle contracts I need to watch
    
    def get_bod_capital(self):
        return self.bod_capital
    
    def set_bod_capital(self, amount):
        self.bod_capital += amount
    
    def get_mod_capital(self):
        return self.mod_capital
    
    def set_mod_capital(self, amount):
        self.mod_capital += amount
    
    def get_eod_capital(self):
        return self.eod_capital
    
    def set_eod_capital(self, amount):
        self.eod_capital += amount
    
    def set_bod_capital(self, amount):
        self.bod_capital += amount
        
    def set_eod_reserve_capital(self, amount):
        self.eod_reserve_capital += amount
    
    def get_market_positions(self, ticker: str, yes_market: bool):
        pass
    
    def total_open_portfolio():
        pass
    
    #return True if we have open eod middle positions
    def check_eod_middle(self):
        if len(self.get_eod_middle_contracts()) > 0:
            for position in self.get_eod_middle_contracts():
                if position.get_current_risk_management():
                    return True
        return False

    
    def update_orderbook(account):
        print(account.get_positions(settlement_status="unsettled"))
        
    def get_eod_middle_contracts(self):
        return self.eod_middle_contracts

    def get_bod_contracts(self):
        return self.bod_contracts

    def add_eod_middle_contract(self, position):
        self.eod_middle_contracts.append(position)
        
    def add_eod_arb_contracts(self, positions):
        self.eod_arb_contracts.append(positions)
        
    def add_mod_arb_contracts(self, positions):
        self.mod_contracts.append(positions)
        
    def add_bod_contract(self, position):
        self.bod_contracts.append(position)
        
    def remove_eod_middle_contract(self, position):
        to_delete = -1
        for index, past_position in enumerate(self.get_eod_middle_contracts()):
            if position.equal(past_position):
                to_delete = index
        
        if to_delete < 0:
            raise Exception('Trying to update orderbook to reflect turning middle buy into edge arb, could not find order to move')
        else:
            del self.get_eod_middle_contracts()[index]
        
    def get_max_price_open_position(self, position_type):
        if position_type == PositionType.EodMiddleOrder:
            return max(self.get_eod_middle_contracts(), key = lambda position : position.get_price() if position.get_current_risk_management() else -1)
    
    def get_min_price_open_position(self, position_type):
        if position_type == PositionType.EodMiddleOrder:
            return min(self.get_eod_middle_contracts(), key = lambda position : position.get_price() if position.get_current_risk_management() else 100000)
        
    
    
    """
    Take in a position and add it to the correct tracker in the order book
    """
    def trackPositions(self, position_type, amount, side, order_response, second_order_response=None, third_order_response=None, past_order_to_update=None):
        if position_type == PositionType.EodMiddleOrder:
            if order_response['order']['status'] == 'executed':
                
                price = order_response['order'][f'{side}_price']
                position = Position(amount, price, order_response['order']['ticker'], PositionType.EodMiddleOrder)
                
                self.add_eod_middle_contract(position)
                self.set_eod_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price/100)))
                
            elif order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')
        
        elif position_type == PositionType.EodArbOrder:
            if order_response['order']['status'] == 'executed' and second_order_response['order']['status'] == 'executed':
                
                first_order_price = order_response['order'][f'{side}_price']
                first_position = Position(amount, first_order_price, order_response['order'][f'ticker'], PositionType.EodArbOrder)
                
                second_order_price = second_order_response['order'][f'{side}_price']
                second_position = Position(amount, second_order_price, second_order_response['order'][f'ticker'], PositionType.EodArbOrder)
                
                self.add_eod_arb_contracts((first_position, second_position))
                
                self.set_eod_capital(-1 * (amount*(first_order_price/100) + calculateKalshiFee(amount, first_order_price/100)))
                self.set_eod_capital(-1 * (amount*(second_order_price/100) + calculateKalshiFee(amount, second_order_price/100)))
            
            elif order_response['order']['status'] == 'canceled' and second_order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Only one side of arb order could be completed')
            
        elif position_type == PositionType.EodLateArbOrder:
            
            #this is if buying the next one over with fee is less than 99 so we can arb
            if order_response['order']['status'] == 'executed':
                
                price = order_response['order'][f'{side}_price']
                position = Position(amount, price, order_response['order']['ticker'], PositionType.EodLateArbOrder)
                position.update_risk_management()
                self.add_eod_middle_contract(position)
                self.set_eod_reserve_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price/100)))

                if past_order_to_update.get_amount() > amount:
                    unmanaged_position = Position(past_order_to_update.get_amount() - amount, past_order_to_update.get_price(), past_order_to_update.get_ticker(), PositionType.EodMiddleOrder)
                    self.add_eod_middle_contract(unmanaged_position)
                    past_order_to_update.set_amount(amount)
                
                past_order_to_update.update_risk_management()
                    
            elif order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')
            
        elif position_type == PositionType.EodReverseMiddleOrder:
            if order_response['order']['status'] == 'executed':
                
                price = order_response['order'][f'{side}_price']
                
                self.set_eod_capital(amount*((100-price)/100) - calculateKalshiFee(amount, price/100))
                
                if past_order_to_update.get_amount() > amount:
                    unmanaged_position = Position(past_order_to_update.get_amount() - amount, past_order_to_update.get_price(), past_order_to_update.get_ticker(), PositionType.EodMiddleOrder)
                    self.add_eod_middle_contract(unmanaged_position)
                    past_order_to_update.set_amount(amount)
                
                past_order_to_update.update_risk_management()
                 
            elif order_response['order']['status'] == 'canceled':
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
                
                self.set_mod_capital(-1 * (amount*(first_order_price/100) + calculateKalshiFee(amount, first_order_price/100)))
                self.set_mod_capital(-1 * (amount*(second_order_price/100) + calculateKalshiFee(amount, second_order_price/100)))
                self.set_mod_capital(-1 * (amount*(third_order_price/100) + calculateKalshiFee(amount, third_order_price/100)))
            
            elif order_response['order']['status'] == 'canceled' and second_order_response['order']['status'] == 'canceled' and third_order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Only one side of arb order could be completed')
        
        elif position_type == PositionType.BodOrder:
            if order_response['order']['status'] == 'executed':
                
                price = order_response['order'][f'{side}_price']
                position = Position(amount, price, order_response['order']['ticker'], PositionType.BodOrder)
                
                self.add_bod_contract(position)
                
                self.set_eod_capital(-1 * (amount*(price/100) + calculateKalshiFee(amount, price/100)))
                
            elif order_response['order']['status'] == 'canceled':
                raise Exception('Order was cancelled')
            else:
                raise Exception('Order was not canceled or excecuted')

"""
Represents a position we have taken in the market
"""
class Position:
    def __init__(self, amount, price, ticker, position_type):
        self.amount = amount
        self.price = price
        self.ticker = ticker
        self.position_type = position_type
        self.risk_managed = False
    
    def update_risk_management(self):
        self.risk_managed = True
        
    def get_current_risk_management(self):
        return self.risk_managed
    
    def get_price(self):
        return self.price
    
    def get_amount(self):
        return self.amount
    
    def set_amount(self, amount):
        self.amount = amount
    
    def get_ticker(self):
        return self.ticker
    
    def get_position_type(self):
        return self.position_type
    
    def equal(self, other):
        return self.get_amount() == other.get_amount() and self.get_price() == other.get_price() and self.get_current_risk_management() == other.get_current_risk_management() and self.get_ticker() == other.get_ticker() and self.get_position_type() == other.get_position_type()

    def set_position_type(self, position_type):
        self.position_type = position_type

"""
Represents the different types of orders a may position may fall under, i.e. which strategy the position is used for
"""
class PositionType(Enum):
    BodOrder = 1
    ModArbOrder = 2
    EodArbOrder = 3
    EodMiddleOrder = 4
    EodLateArbOrder = 5
    EodReverseMiddleOrder = 6
    
class Strategy(Enum):
    Bod = 1
    ModArb = 2
    Eod = 3

### UTILITY FUNCTIONS ###

"""
Get NDX Open Price
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
def placeKalshiMarketOrder(account, market: KalshiMarket, amount, side, max_price):
    ticker = market.get_ticker()
    order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'limit',
                    'action':'buy',
                    f'{side}_price': max_price,
                    'side':side,
                    'count': amount}
    return account.create_order(**order_params)

def getKalshiMarkets(account, strategy: Strategy, current_datetime, months_array, current_index_price=None):
    
    if strategy == Strategy.Eod:
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
    
    if strategy == Strategy.ModArb:
        
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
       
    if strategy == Strategy.Bod:
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
Calculates the total fee related to the Kalshi order. Fee only applies if order is immediate.
    APPLIES ONLY TO NASDAQ AND SPX MARKETS
    amount: number of contracts
    price: price of the contract from 0 -> 1
"""
def calculateKalshiFee(amount, price):
    return math.ceil(100*(0.035 * amount * price * (1-price)))/100

#price betwen 0 and 1
def calculateVolumeToTrade(position_type, eod_capital, current_price, closest_price=None, third_price=None):
    if position_type == PositionType.EodMiddleOrder:
        numerator = eod_capital - 0.01
        denominator = current_price + 0.035 * current_price * (1-current_price)
        return math.floor(numerator/denominator)
    
    elif position_type == PositionType.EodArbOrder:
        numerator = eod_capital - 0.02
        den_one = (current_price + closest_price)
        den_two = 0.035*current_price*(1-current_price)
        den_three = 0.035*closest_price*(1-closest_price)
        return math.floor(numerator/(den_one+den_two+den_three))
    
    elif position_type == PositionType.ModArbOrder:
        numerator = eod_capital - 0.03
        den_one = (current_price + closest_price + third_price)
        den_two = 0.035*current_price*(1-current_price)
        den_three = 0.035*closest_price*(1-closest_price)
        den_four = 0.035*third_price*(1-third_price)
        return math.floor(numerator/(den_one+den_two+den_three+den_four))
    
    elif position_type == PositionType.BodOrder:
        numerator = eod_capital - 0.01
        denominator = current_price + 0.035 * current_price * (1-current_price)
        return math.floor(numerator/denominator)
        
### STRATEGIES ### 

def run_bod(account, orderbook: Orderbook, current_datetime, months_array):
    #get the current market and buy it up to 42 percent
    current_market = getKalshiMarkets(account, Strategy.Bod, current_datetime, months_array)
    current_market_ask = current_market.get_best_yes_ask()
    
    bod_capital = orderbook.get_bod_capital() * 0.42
    if len(orderbook.get_bod_contracts()) == 0:
        trade_volume = calculateVolumeToTrade(PositionType.BodOrder, bod_capital, current_market_ask/100)
        bod_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', 47)
        send_email_update('yes', current_market_ask, trade_volume)

        orderbook.trackPositions(PositionType.BodOrder, trade_volume, 'yes', bod_order) 
        logging.info(f'Made an order for Bod contract of amount {trade_volume} at price {current_market_ask} on market {current_market.get_ticker()}')
    
def run_all_day_arbitrage(account, orderbook, current_datetime, months_array):
    range_markets, above_markets = getKalshiMarkets(account, Strategy.ModArb, current_datetime, months_array)
    
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
            if sum([floor_market_yes_ask/100, range_market_no_ask/100, ceiling_market_no_ask/100]) + calculateKalshiFee(max_contracts_buyable, floor_market_yes_ask/100)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, range_market_no_ask/100)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, ceiling_market_no_ask/100)/max_contracts_buyable < 2:
            
                mod_capital = orderbook.get_mod_capital()
                max_order_capital = (floor_market_yes_ask/100 + range_market_no_ask/100 + ceiling_market_no_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, floor_market_yes_ask/100) + calculateKalshiFee(max_contracts_buyable, range_market_no_ask/100) + calculateKalshiFee(max_contracts_buyable, ceiling_market_no_ask/100)
            
                trade_volume = max_contracts_buyable if mod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, mod_capital, floor_market_yes_ask/100, range_market_no_ask/100, ceiling_market_no_ask/100) 
            
                first_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'yes', floor_market_yes_ask)
                second_edge_order = placeKalshiMarketOrder(account, range_market, trade_volume, 'no', range_market_no_ask)
                third_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'no', ceiling_market_no_ask)
                send_email_update('yes/no/no', 'Range/Above', trade_volume)
                
                
                orderbook.trackPositions(PositionType.ModArbOrder, trade_volume, '2', first_edge_order, second_order_response=second_edge_order, third_order_response=third_edge_order) 

                logging.info(f'Made an order for range/above arb of volume {trade_volume} at prices {floor_market_yes_ask/100} and {range_market_no_ask/100} and {ceiling_market_no_ask}')
            
            logging.info(f'Testing arbitrage opportunity 2, <$1, with a floor market no of {floor_market_no_ask}, a range market yes of {range_market_yes_ask} and a ceiling market yes of {ceiling_market_yes_ask}.')
            max_contracts_buyable = min(floor_market_no_vol, range_market_yes_vol, ceiling_market_yes_vol)
            if sum([floor_market_no_ask/100, range_market_yes_ask/100, ceiling_market_yes_ask/100])  + calculateKalshiFee(max_contracts_buyable, floor_market_no_ask/100)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, range_market_yes_ask/100)/max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, ceiling_market_yes_ask/100)/max_contracts_buyable < 1:
                
                mod_capital = orderbook.get_mod_capital()
                max_order_capital = (floor_market_no_ask/100 + range_market_yes_ask/100 + ceiling_market_yes_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, floor_market_no_ask/100) + calculateKalshiFee(max_contracts_buyable, range_market_yes_ask/100) + calculateKalshiFee(max_contracts_buyable, ceiling_market_yes_ask/100)
            
                trade_volume = max_contracts_buyable if mod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, mod_capital, floor_market_no_ask/100, range_market_yes_ask/100, ceiling_market_yes_ask/100) 

                first_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'no', floor_market_no_ask)
                second_edge_order = placeKalshiMarketOrder(account, range_market, trade_volume, 'yes', range_market_yes_ask)
                third_edge_order = placeKalshiMarketOrder(account, floor_market, trade_volume, 'yes', ceiling_market_yes_ask)
                send_email_update('no/yes/yes', 'Range/Above', trade_volume)
                
                orderbook.trackPositions(PositionType.ModArbOrder, trade_volume, '1', first_edge_order, second_order_response=second_edge_order, third_order_response=third_edge_order) 

                logging.info(f'Made an order for range/above arb of volume {trade_volume} at prices {floor_market_no_ask/100} and {range_market_yes_ask/100} and {ceiling_market_yes_ask}')
        
def run_eod(account, orderbook: Orderbook, NDXopen, current_datetime, months_array, market_size=100, middle_range_percent=50, arb_value=98, ask_high=97, percent_change=2, loss_floor=10):
    #get current NDX price and working capital
    current_index_price = getNDXCurrentPrice()
    
    #get markets above, middle, below
    low_market, current_market, high_market = getKalshiMarkets(account, Strategy.Eod, current_datetime, months_array, current_index_price)
    
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
        
        if current_ask + closest_range_ask < arb_value:
            max_contracts_buyable = min(current_volume, closest_range_volume)
            
            eod_capital = orderbook.get_eod_capital()
            max_order_capital = (current_ask/100)*max_contracts_buyable + (closest_range_ask/100)*max_contracts_buyable + calculateKalshiFee(max_contracts_buyable, current_ask/100) + calculateKalshiFee(max_contracts_buyable, closest_range_ask/100)

            trade_volume = max_contracts_buyable if eod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodArbOrder, eod_capital, current_ask/100, closest_range_ask/100) 
            
            first_edge_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', current_ask)
            second_edge_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, trade_volume, 'yes', closest_range_ask)
            send_email_update('yes', f'{current_ask} and {closest_range_ask}', trade_volume)
            
            orderbook.trackPositions(PositionType.EodArbOrder, trade_volume, 'yes', first_edge_order, second_order_response=second_edge_order) 

            logging.info(f'Made an order for EOD edge arb of volume {trade_volume} at prices {current_ask} and {closest_range_ask}')
    else:
        current_ask, current_volume = current_market.get_best_yes_ask(volume=True)
        if current_ask < ask_high:
            if 100*(abs(NDXopen-current_index_price)/NDXopen) < percent_change:
                logging.info(f'Considering a middle buy with current market at {current_ask}, percent change at {percent_change}')
                
                eod_capital = orderbook.get_eod_capital()
                max_order_capital = (current_ask/100)*current_volume + calculateKalshiFee(current_volume, (current_ask/100))
                
                trade_volume = current_volume if eod_capital >= max_order_capital else calculateVolumeToTrade(PositionType.EodMiddleOrder, eod_capital, current_ask/100)
        
                middle_order = placeKalshiMarketOrder(account, current_market, trade_volume, 'yes', current_ask)
                orderbook.trackPositions(PositionType.EodMiddleOrder, trade_volume, 'yes', middle_order)
                send_email_update('yes', current_ask, trade_volume)
                
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

            if min_position_price + closest_range_ask + calculateKalshiFee(closest_range_volume, closest_range_ask/100)/closest_range_volume <= 99:
                late_arb_amount = min(closest_range_volume, min_position_amount)
                buy_late_arb_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, late_arb_amount, 'yes', closest_range_ask)
                orderbook.trackPositions(PositionType.EodLateArbOrder, late_arb_amount, 'yes', buy_late_arb_order, past_order_to_update=min_price_position)
                send_email_update('yes', closest_range_ask, trade_volume)
                
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
                send_email_update('no', 100-current_bid, trade_volume)
                
                logging.info(f'Sold on middle contracts to mitigate losses for volume of {buy_no_amount} at price {100-current_bid}')
            
            else:
                logging.info(f'Considering buying closest range to arb losses away, with closest range price of {closest_range_ask}')
                buy_another_yes_amount = min(closest_range_volume, max_position_amount)
                buy_another_yes_order = placeKalshiMarketOrder(account, high_market if is_above_midpoint else low_market, buy_another_yes_amount, 'yes', closest_range_ask)
                orderbook.trackPositions(PositionType.EodLateArbOrder, buy_another_yes_amount, 'yes', buy_another_yes_order, past_order_to_update=max_price_position)
                send_email_update('yes', closest_range_ask, trade_volume)
                
                logging.info(f'Bought edge contract to mitigate losses with volume of {buy_another_yes_amount} for {closest_range_ask}')
    else:
        logging.info(f'Market is still safely in the middle range')

def run_strategies(account, orderbook: Orderbook, current_time, NDXopen, current_datetime, months_array):
    
    if current_time > time(9,30,0) and current_time < time(9,46,0):
        logging.info('Trading day has begun, but we are waiting for first price to load for BOD strategy')

    if current_time > time(9,46, 0) and current_time < time(9,50, 0):
        logging.info(f'Trying to run beginning of day strategy with ${orderbook.get_bod_capital()} in capital')
        run_bod(account, orderbook, current_datetime, months_array)
                    
    elif current_time > time(9, 50, 0) and current_time < time(15, 50, 0):
        logging.info(f'Trying to run middle of day arb strategy with ${orderbook.get_mod_capital()} in capital')
        run_all_day_arbitrage(account, orderbook, current_datetime, months_array)
    
    elif current_time > time(15, 50, 0) and current_time < time(16, 0, 0):
        logging.info(f'Trying to run end of day strategy with ${orderbook.get_eod_capital()} in capital')
        run_eod(account, orderbook, NDXopen, current_datetime, months_array)

### OPERATOR ###

def operate_kalshi():
    
    #TODO add phone/email logging

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
    bod_capital = 25
    mod_capital = 50
    eod_capital = 25
    orderbook = Orderbook(25, 50, 25)
    logging.info(f'Created orderbook, with bod_capital of ${bod_capital}, mod_capital of ${mod_capital}, and eod_capital of ${eod_capital}.')
    
    months_array = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
    
    got_open = False

    while True:
        current_datetime = dt.now()
        current_time = current_datetime.time()
        
        if current_datetime.today().weekday() < 5:
            if current_time < time(16,0,0):
                if current_time > time(9,30,0):
                    
                    if not got_open:
                        if current_time < time(9, 50, 0):
                            NDXopen = getNDXCurrentPrice()
                        else:
                            NDXopen = getIndexOpen()
                        got_open = True
                    
                    try:
                        run_strategies(account, orderbook, current_time, NDXopen, current_datetime, months_array)
                    except Exception as error:
                        print('An error occurred running strategies: \n', error)
                        logging.warning(f'An error occurred running strategies: {error}')
                
                else:
                    print(f'Current Time is: {current_time}. It is not yet time to trade.')
                    logging.info(f'It is not yet time to trade. Will check again in 1 minute.')
                    sleeper.sleep(60)
            else:
                print(f'Current Time is {current_time}. The trading day is over.')
                logging.info(f'The trading day is over. Will check again in 5 minutes.')
                sleeper.sleep(300)
        else:
            print(f'Current Time is {current_time}. It is currently the weekend.')
            logging.info(f'It is currently the weekend. Will check in again in 8 hours.')
            sleeper.sleep(60*60*8)
                  
if __name__ == "__main__":
    #TODO clean up code
    # operate_kalshi()
    send_email_update('yes', 89, 1)
    