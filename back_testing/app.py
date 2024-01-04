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


datapath = 'data_storage/kalshi_data/INXDU-23AUG15-T4499.99_2023-08-15 09:00:00_2023-08-15 10:23:20.csv'


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
        

    def __init__(self):
        #Initialize close date and time arguments
        self.dataclose = self.datas[0].close
        self.datetime = self.datas[0].datetime
        

    def next(self):
        
        #Quick start instructions are at https://www.backtrader.com/docu/quickstart/quickstart/
        
        #access current value at this time step
        currentValue = self.dataclose[0]
        
        #access previous values (from the past)
        previousTimeStepValue = self.dataclose[-1]
        
        #buy stock at this timestep
        self.buy()
        
        #log however you want
        self.log()




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