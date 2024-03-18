from datetime import datetime as dt
from enum import Enum

# arb strategy:
# at the end of the day, you have two markets, high and low
# when there is little time left and it's in the edge the price will probably be in these markets
# when this happens you can have multiple kinds of arb:
# buying yes has most arb gone
# buying yes is same as selling no
# so you can buy the yes of one and sell the no other other (selling no also normally has higher price)


# the other kind is during the day, across markets
# when you look at range and above/below
# you can look at the market the price is in and the market above it
#the range should be equal to the price difference of the above markets
#what you can do it you can sell the range, buy the lower above and sell the higher above

#yes bid at 25
#no ask at 75

class TradeSignal(Enum):
    BUY_LOW_YES = 1
    BUY_HIGH_YES = 2
    BUY_LOW_NO = 3
    BUY_HIGH_NO = 4
    SELL_LOW_YES = 5
    SELL_HIGH_YES = 6
    SELL_LOW_NO = 7
    SELL_HIGH_NO = 8

#check that time is correct before you run this function
def range_to_range_arb_checker(low_yes_bid, low_yes_ask, low_no_bid, low_no_ask, high_yes_bid, high_yes_ask, high_no_bid, high_no_ask):
    
    #can have it between two yes asks
    if low_yes_ask + high_yes_ask < 100:
        return (TradeSignal.BUY_HIGH_YES, TradeSignal.BUY_LOW_YES)
    
    #can have it between the yes ask and the no bid of markets next to each other
    if low_yes_ask + high_no_bid < 100:
        return (TradeSignal.BUY_LOW_YES, TradeSignal.SELL_HIGH_NO)
    
    if high_yes_ask + low_no_bid < 100:
        return (TradeSignal.BUY_HIGH_YES, TradeSignal.SELL_LOW_NO)
    
    
    pass



def range_to_above_arb_checker():
    pass


    