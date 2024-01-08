from datetime import datetime as dt
from client import start_kalshi_api

def check_arbitrage():
    account = start_kalshi_api()
    should_print = True
    
    while dt.now() < dt(2024, 1, 8, 16, 0, 0):
    
        markets = account.get_markets(limit=1000, status='open')['markets']
        
        for market in markets:
            if market['yes_ask'] + market['no_ask'] < 100:
                print(f'found an arb opportunity on {market['ticker']} at {dt.now()} with prices {market['yes_ask']} and {market['no_ask']}')

        
        if str(dt.now().minute)[-1] == '0' and should_print:
            print(f'still running at {dt.now()}')
            should_print = False
        
        if str(dt.now().minute)[-1] == '1':
            should_print = True
        
    print('done')




if __name__ == "__main__":
    check_arbitrage()