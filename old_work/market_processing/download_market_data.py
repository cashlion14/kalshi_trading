import yfinance as yf
from datetime import datetime as dt
import time
import os

'''
real market information gathering

Approach 1: For (ticker) in the last 30 days #TODO line 1#, obtain prices every 30 minutes

ONLY RUN ONCE TO COLLECT DATA
'''


def download_market_data(ticker: str) -> None:
    tickerino = yf.Ticker(ticker)
    start_date = dt(
        year = 2023,
        month = 12,
        day = 4,
        hour = 17,
        minute = 30
    )

    end_date = dt(
        year = 2023,
        month = 12, 
        day = 18
    )

    history = tickerino.history(
        interval = "30m",
        start = start_date,
        end = end_date
    )

    os.makedirs('./data_storage/market_data', exist_ok=True)
    history.to_csv(f'./data_storage/market_data/{ticker}_history.csv')

if __name__ == "__main__":
    download_market_data("^NDX")

