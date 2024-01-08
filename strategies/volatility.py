import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import yfinance as yf
from scipy.stats import norm
from datetime import datetime as dt
from dateutil import parser
import itertools
import calendar

# Pricing Based on Implied Volatily (NOT INVESTMENT ADVICE, JUST FOR DEMONSTRATION PURPOSES)
def vol_by_strike(polymdl, K):
    return np.poly1d(polymdl)(K)

def binary_put(S, K, T, r, sigma, Q=1):
    N = norm.cdf
    return np.exp(-r*T)* N(-d2(S,K,T,r,sigma)) *Q

def d2(S, K, T, r, sigma):
    return (np.log(S/K) + (r- sigma**2 / 2)*T) /  (sigma*np.sqrt(T))

def binary_call(S, K, T, r, sigma, Q=1):
    N = norm.cdf
    return np.exp(-r*T)* N(d2(S,K,T,r,sigma)) *Q

exp_date = '2022-12-02'
NSDQ100 = yf.Ticker("^NDX")
calls, puts = NSDQ100.option_chain(exp_date)
puts= puts[~puts.inTheMoney]
calls= calls[~calls.inTheMoney]
options = pd.concat([puts,calls]).reset_index()
vol_vals = options.impliedVolatility.values #volatility values
K_vals = options.strike.values #Strikes 

new_K_vals = np.arange(K_vals.min(), K_vals.max(),10) # new higher resolution strikes
poly = np.polyfit(K_vals,vol_vals,3) #create implied vol fit
new_vol_vals = np.poly1d(poly)(new_K_vals) # fit model to new higher resolution strikes

fig, ax1 = plt.subplots(1, 1,figsize=(15,10))

## implied volatility curves
ax1.plot(new_K_vals, new_vol_vals)
ax1.set_title('Implied Volatility of NASDAQ100 on ' + exp_date)
ax1.set_xlabel('$K$')
ax1.set_ylabel('Implied Vol')

# signup at kalshi.com to create an account and get data access
from KalshiClientsBaseV2 import ExchangeClient

prod_email = "" # change these to be your personal credentials
prod_password = "" # (for extra security, we recommend using a config file)

prod_api_base = "https://trading-api.kalshi.com/trade-api/v2"
exchange_client = ExchangeClient(exchange_api_base=prod_api_base, email = prod_email, password = prod_password)

# Pricing Based on Kalshi Contracts
kalshi_ticker = 'NASDAQ100W-' + exp_date[2:4]+calendar.month_abbr[int(exp_date[5:7])].upper()+ exp_date[-2:]

event_response = exchange_client.get_event(event_ticker=kalshi_ticker)

def clean_int(str) -> int:
    return int(round(float(str.replace(',',''))))

kalshi_stats = {"lower": [],"upper":[],"implied_probability":[]}

n_markets = len(event_response['markets'])
for index in range(n_markets):
    market = event_response['markets'][index]
    strikes = market['subtitle'].split(' ')
    probability = market['last_price']
    if index == 0:
        lower, upper = 0, clean_int(strikes[0])
    elif index == n_markets - 1:
        lower, upper = clean_int(strikes[0]), int(100000)
    else:
        lower, upper = clean_int(strikes[0]), clean_int(strikes[-1])

    kalshi_stats['lower'].append(lower)
    kalshi_stats['upper'].append(upper)
    kalshi_stats['implied_probability'].append(probability)

pd.DataFrame(kalshi_stats)

len_kalshi_stats = len(kalshi_stats['lower'])
constraints = {str(kalshi_stats['lower'][k]) + '-' + str(kalshi_stats['upper'][k]) : [kalshi_stats['lower'][k],kalshi_stats['upper'][k], kalshi_stats['implied_probability'][k]] for k in range(len_kalshi_stats)}

## Implied Probability Distribution
PsT = []  # market implied probabilities
for i in range(1, len(binaries)):
    p = binaries[i] -binaries[i-1]
    PsT.append(p)
PsT =np.array(PsT)

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = iter(item for item in prop_cycle.by_key()['color'])

fig, ax3 = plt.subplots(1, 1,figsize=(25,10))
ax3.plot(new_K_vals[1:], PsT, color='black')

for key in constraints:
    try:
        facecolor = next(colors)
    except StopIteration:
        colors = iter(item for item in prop_cycle.by_key()['color'])
        facecolor = next(colors)
    bucket = constraints[key]
    lower, upper = bucket[0], bucket[1]
    ax3.fill_between(new_K_vals[1:], PsT, where=((new_K_vals[1:] < upper)& (new_K_vals[1:] >= lower)),
                      facecolor=facecolor,alpha=0.9 ) 

ax3.set_xlabel('$S_T$')
ax3.set_ylabel('$\mathbb{P}$')
ax3.set_title('Probability Intervals for NASDAQ100')
ax3.set_xlim([S-200,S+200])

buckets = []
options_implied_fv = []
kalshi_fv = []

for constraint in constraints:
    idx = np.argwhere((new_K_vals[1:] <= constraints[constraint][1]) & (new_K_vals[1:] > constraints[constraint][0]))
    options_implied_fv.append(round(PsT[idx].sum(),2))
    kalshi_fv.append(constraints[constraint][2])
    buckets.append(constraint)

implied_FVs = pd.DataFrame(index=buckets,data=options_implied_fv,columns=['Price']).iloc[4:9]
kalshi_FVs = pd.DataFrame(index=buckets,data=kalshi_fv,columns=['Price']).iloc[4:9]

fig, ax4 = plt.subplots(1, 1,figsize=(25,10))

## Implied Binary Probabilities
ax4.bar(implied_FVs.index,implied_FVs.Price*100, label = 'Options Implied Value')
ax4.bar(kalshi_FVs.index,kalshi_FVs.Price*100, label = 'Kalshi Implied Value')

ax4.set_title('Implied Fair Values')
ax4.set_ylabel('Price')
ax4.set_xlabel('Kalshi Buckets')
ax4.legend()