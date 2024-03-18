from bs4 import BeautifulSoup as bs
import requests
import yfinance as yf

# headers = {
#     'Access-Control-Allow-Origin': '*',
#     'Access-Control-Allow-Methods': 'GET',
#     'Access-Control-Allow-Headers': 'Content-Type',
#     'Access-Control-Max-Age': '3600',
#     'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
#     }


# url = 'https://www.barchart.com/stocks/indices/sp/sp500'

# req = requests.get(url, headers)
# soup = bs(req.content, 'html.parser')

# print(soup)
# # header_element = soup.find(attrs={'id':'quote_val'})

# # print("Element with id: header: \n",header_element)

# # <span id="quote_val">4883.58</span>

# import requests
# headers = {
#     'Content-Type': 'application/json'
# }
# requestResponse = requests.get("https://api.tiingo.com/iex/?tickers=^spx&token=dd3c02d5c1675aca811004e29278483d6a3c2454", headers=headers)
# print(requestResponse.json())

data = yf.Ticker("^SPX").history(period="1d", interval="1m")

print(data)