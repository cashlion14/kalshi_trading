# Algorithmic Trading on Kalshi

Jake Jones and Nikhil Kakarla

Our goal is to begin trading systemmatically on Kalshi, an event contract exchange. 

**Quickstart**
1. Make venv with  ```python -m venv env``` on Windows or ```python3 -m venv env``` on Mac
2. Activate venv with ```env/Scripts/activate``` on Windows or ```source env/bin/activate``` on Mac
3. Download packages with ```pip install -r requirements.txt```

**Steps:**
1. Infrastructure building
2. Idea generation
3. Strategy programming
4. Paper trading
5. Live Trading

**Infrastructure Building:**
    
Use Python library BackTrader: https://www.backtrader.com/ to backtest & trade. Use cloud service to run server. Use Kalshi API: https://kalshi.com/api? to connect to exchange.

**Trading Strategies:**
1. Single-market arbitrage
    a. Prices lower at beginning of day, buy early and look for no later
2. High freuquency trading
    a. At EOD if we are away from boundary, just buy up the 96 markets
3. ML predictions
4. Options hedging
5. Rebate farming
6. Volatility hedging

https://medium.com/@mlblogging.k/10-awesome-books-for-quantitative-trading-fc0d6aa7e6d8
https://wrds-www.wharton.upenn.edu/
https://www.openassetpricing.com/
https://www.fullerthalerfunds.com/


NEXT STRATEGY: ARB BETWEEN RANGE AND ABOVE BELOW
GET A BOUND ON STOCHASTIC PROCESS