from client import start_kalshi_api
import uuid


def buyStock():
    account = start_kalshi_api()
    print('connected to kalshi')
    print(account.get_exchange_status())
    balance = account.get_balance()
    print(balance)
    positions = account.get_positions()
    print(positions)
    
    
    ticker = 'INX-24FEB14-B4962'
    order_params = {'ticker':ticker,
                    'client_order_id':str(uuid.uuid4()),
                    'type':'market',
                    'action':'buy',
                    'side':'no',
                    'count':1}
    account.create_order(**order_params)
    print('bought')
    # positions = account.get_positions()
    # print(positions)
    
    
    

if __name__ == "__main__":
    buyStock()