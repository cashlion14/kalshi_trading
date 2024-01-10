import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import yfinance as yf
from scipy.stats import norm
from datetime import datetime as dt
from dateutil import parser
import itertools
import calendar
from client import ExchangeClient, start_kalshi_api
import os, os.path
import scipy
from scipy.interpolate import make_interp_spline
from statsmodels.nonparametric.smoothers_lowess import lowess


"""Uses code from the websites 
        "https://reasonabledeviations.com/2020/10/01/option-implied-pdfs/"
        "https://reasonabledeviations.com/2020/10/10/option-implied-pdfs-2/"

    Attempt is to use options prices on the S&P500 to create an implied PDF
    We could then compare this pdf/cdf to the kalshi prices and look for arbitrage opporunties

    Returns:
        _type_: _description_
"""




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


#pull from yahoo finance
exp_date = '2024-01-10'
SAP500 = yf.Ticker("^NDX")
data = SAP500.option_chain(exp_date)
calls = data.calls
print(calls)

#max and min range to pull the data from
minRange = 16000
maxRange = 17300

#get prices at different strike values
vol_vals = calls.impliedVolatility.values #volatility values
strike_vals = calls.strike.values #Strikes
unfilteredPrices = calls.lastPrice.values
pdUnfilteredPrices = pd.DataFrame(unfilteredPrices)

#try weighted averages of the prices
weightedAverageprices = pdUnfilteredPrices.rolling(window=7).mean()

#use lowess smoothing to smooth the prices (best approach so far)
lowessRawPrices = np.array(unfilteredPrices)
lowessRawStrikes =  np.array(strike_vals)
lowessResult = lowess(lowessRawPrices, lowessRawStrikes, frac=0.1)

#clip the prices to the usable range
clippedPrices1 = calls[calls.strike.values >= minRange]
clippedPrices = clippedPrices1.lastPrice.values[clippedPrices1.strike.values <= maxRange]

#clip the strike vals and lowess prices to the same usable range
lowessPrices = []
strike_vals = []
for lowess in lowessResult:
    if lowess[0] >= minRange and lowess[0] <= maxRange:
        strike_vals.append(lowess[0])
        lowessPrices.append(lowess[1])

print(len(strike_vals),len(clippedPrices),len(lowessPrices))


#IDEAS THAT I TRIED AND DID NOT WORK
# interpolate to create smooth curve from values and take derivatives
# poly = scipy.interpolate.CubicSpline(strike_vals,lowessPrices)
    # poly = np.polyfit(strike_vals,prices,7) #create implied vol fi
# polyDeriv = poly.derivative(nu=2)
    # polyActual = np.poly1d(poly)
    # polyDerivCoeffs = polyActual.deriv(m=2)
    # polyDeriv = np.poly1d(polyDerivCoeffs)(strike_vals)
# X_Y_Spline = make_interp_spline(strike_vals,prices)
# X_ = np.linspace(min(strike_vals), max(strike_vals), 500)
# Y_ = X_Y_Spline(X_)


#only include every 6th price in order to smooth out the cubic splines
simplifiedStrikes = []
simplifiedPrices = []
for i in range(len(strike_vals)):
    if i % 3 == 0:
        simplifiedStrikes.append(strike_vals[i])
        simplifiedPrices.append(lowessPrices[i])


#fit cubic spline and derivative 
poly = scipy.interpolate.interp1d(simplifiedStrikes, simplifiedPrices, kind="cubic",
                                 fill_value="extrapolate")

polyDeriv = poly._spline.derivative(nu=1)


#plot results
fig, ax0 = plt.subplots(1, 1,figsize=(15,10))
ax0.scatter(strike_vals,clippedPrices,label="actual prices")
ax0.scatter(strike_vals,lowessPrices,label="Lowess smoothed Data")
ax0.plot(strike_vals,poly(strike_vals),label ="fitted cubic spline")
ax0.set_title('PDF of S&P from implied option volatility ' + exp_date)
ax0.set_xlabel('Strike Price')
ax0.set_ylabel('Price')

fig, ax1 = plt.subplots(1, 1,figsize=(15,10))
ax1.plot(strike_vals,polyDeriv(strike_vals),label="actual prices")
ax1.set_title('PDF of S&P from implied option volatility ' + exp_date)
ax1.set_xlabel('Strike Price')
ax1.set_ylabel('Price')


plt.legend()
plt.show()



print('starting kalshi')

#Get Kalshi Ranges
exchange_client = start_kalshi_api()
kalshi_ticker = 'INXD-' + exp_date[2:4]+calendar.month_abbr[int(exp_date[5:7])].upper()+ exp_date[-2:]
print(kalshi_ticker)
event_response = exchange_client.get_event(event_ticker=kalshi_ticker)
print('pulled from kalshi')


#clean Kalshi Data
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
upperLowerPairs = [(kalshi_stats['lower'][i],kalshi_stats['upper'][i]) for i in range(len(kalshi_stats['upper']))]




#Get different probabilities
kalshiProbabilities = kalshi_stats['implied_probability']
optionsProbabilities = []
actualFunction = np.poly1d(polyDerivCoeffs)
for pair in upperLowerPairs:
    antiderivative = np.polyint(polyDerivCoeffs)
    areaUnderCurve = antiderivative(4850) - antiderivative(pair[0])
    optionsProbabilities.append(float(areaUnderCurve))

print(kalshiProbabilities)
print(optionsProbabilities)