import backtrader as bt

'''
Takes in the path name of a csv file and creates a data feed
'''
def csv_to_feed(pathname: str) -> bt.feed.CSVDataBase:
    return bt.feeds.GenericCSVData(dataname=pathname)


'''
The wrapper call to the backtester
'''
def back_tester(strategy: bt.Strategy, datafeeds: list) -> None:
    
    cerebro = bt.Cerebro()
    
    cerebro.addstrategy(strategy)
    
    for index, feed in enumerate(datafeeds):
        cerebro.adddata(feed, name=f'datafeed{index}')

    cerebro.broker.setcash(100000.0)
    
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    cerebro.run()
    
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    

if __name__ == "__main__":
    pass