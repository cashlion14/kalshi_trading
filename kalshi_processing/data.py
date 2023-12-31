from datetime import datetime as dt
import csv
from client import ExchangeClient, start_kalshi_api

'''
Creates a csv with kalshi data for a given account, yes market, and time range (EST).
Saves the csv to the data_storage folder.
Assumes range is in the past (market not currently open) and is <= 1 day.
'''
def create_csv(account: ExchangeClient, market: str, start_date: dt, end_date: dt) -> None:
    
    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())
    
    data = account.get_market_history(ticker=market, limit=1000, min_ts=start_timestamp, max_ts=end_timestamp)
    data_dict = data['history']
    
    field_names = ['datetime', 'bid', 'ask', 'open_interest', 'volume']
    csv_name = f'data_storage/{market}_{start_date}_{end_date}.csv'
    
    with open(csv_name, 'w') as file:
        writer = csv.DictWriter(file, fieldnames = field_names)
        writer.writeheader()
        
        for entry in data_dict:
            modified_entry = {}
            modified_entry['datetime'] = dt.fromtimestamp(entry['ts']).replace(microsecond=0)
            modified_entry['bid'] = entry['yes_bid']
            modified_entry['ask'] = entry['yes_ask']
            modified_entry['open_interest'] = entry['open_interest']
            modified_entry['volume'] = entry['volume']
            writer.writerow(modified_entry)

    
if __name__ == "__main__":
    exchange_client = start_kalshi_api()
    # create_csv(exchange_client, 'INXDU-23AUG15-T4499.99', dt.fromtimestamp(1692104400), dt.fromtimestamp(1692109400))
    # create_csv(exchange_client, 'INXDU-23DEC29-T4749.99', dt(2023, 12, 29, 9, 0, 1), dt(2023, 12, 29, 13, 0, 0))