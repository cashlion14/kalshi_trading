# from __future__ import (absolute_import, division, print_function,
#                         unicode_literals)

# import backtrader as bt
# import backtrader.feeds as btfeeds

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
import backtrader.feeds as btfeeds

import csv
import datetime
import argparse


# datapath = 'data_storage/kalshi_data/INXDU-23AUG15-T4499.99_2023-08-15 09:00:00_2023-08-15 10:23:20.csv'
datapath = 'data_storage/kalshi_data/INXD/23/DEC/20/INXD-23DEC20-B4687.csv'


class TestStrategy(bt.Strategy):

    count = 0

    def log(self, txt=None, dt=None):
        ''' Logging function for this strategy'''
        
        if txt:
            print(txt)
            return
        
        logString = ''
        # logString += str(self.date) + ' ' + str(self.time)
        logString += str(self.datetime.date()) + ' ' + str(self.datetime.time())
        logString += "\t| Ask: " +  str(self.data.open[0]) + "\t| Vol: " + str(self.data.volume[0])
        
        print(logString)
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None
        
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] < self.dataclose[-1]:
                    # current close less than previous close

                    if self.dataclose[-1] < self.dataclose[-2]:
                        # previous close less than the previous close

                        # BUY, BUY, BUY!!! (with default parameters)
                        self.log('BUY CREATE, %.2f' % self.dataclose[0])

                        # Keep track of the created order to avoid a 2nd order
                        self.order = self.buy()

        else:

            # Already in the market ... we might sell
            if len(self) >= (self.bar_executed + 5):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()




if __name__ == '__main__':
    
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000.0)
                        

    data = btfeeds.GenericCSVData(
        dataname=datapath,
        datetime=0, #numbers are the index of the CSV file where the information is located
        open=2,
        high=2,
        low=2,
        close=2,
        volume=4,
        openinterest=-1,
        dtformat=('%Y-%m-%d %H:%M:%S'), #datetime format should be standard
        timeframe=bt.TimeFrame.Minutes, #converts from days to minutes/seconds for the time
        compression=60,
    )


    cerebro.addstrategy(TestStrategy)
    cerebro.adddata(data)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())