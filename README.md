# Algorithmic Trading on Kalshi

Elie Cuevas, Jake Jones

Our goal is to begin trading systemmatically on Kalshi, an event contract exchange. 

**Quickstart**
1. Make venv with  ```python -m venv env```
2. Activate venv with ```env/Scripts/activate``` 
3. Download packages with ```pip install requirements.txt```

**Steps:**
1. Infrastructure building
2. Idea generation
3. Strategy programming
4. Paper trading
5. Live Trading

**Infrastructure Building:**
    
Use Python library BackTrader: https://www.backtrader.com/ to backtest & trade. Use cloud service to run server. Use Kalshi API: https://kalshi.com/api? to connect to exchange.

**Idea Generation:**
1. Market making
2. HFT (get ahead of S&P contract changes)
3. EOD/Microstructure trades (look for patterns at open, close, etc)
4. Hedge options using Kalshi exchange
5. Find further ideas here: https://medium.com/@mlblogging.k/10-awesome-books-for-quantitative-trading-fc0d6aa7e6d8
