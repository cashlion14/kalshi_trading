import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta

def get_market_days(start_date: dt, end_date: dt) -> list:
    df = pd.read_csv("data_storage/market_data/market_days.csv", )
    
    #conversion to allow between comparison
    df['market_open']= pd.to_datetime(df['market_open']).dt.tz_convert(None)
    
    #find all market days within range
    df = df[df['market_open'].between(start_date, end_date+timedelta(1))]
    days = df['market_open'].to_list()
    
    #change format and return
    for index, day in enumerate(days):
        days[index] = day.date()
    return days

def get_stock_info(df, year, month, day, buy_minute):
    df = df[df['Time'].between(dt(year, month, day, 9, 30, 0), dt(year, month, day, 16, 00, 0))]
    
    close = df['Last'].to_list()[0]
    opens = df['Open'].to_list()
    open = opens[-1]
    
    try:
        df = df[df['Time'].between(dt(year, month, day, 15, buy_minute, 0), dt(year, month, day, 15, buy_minute, 0))]
        buy_minute_price = df['Open'].to_list()[0]
    except:
        # print(year, month, day)
        return 0, 0, 0 
    
    return open, close, buy_minute_price

def get_log_reg_data():
    spx_prices = pd.read_csv('data_storage/market_data/combined_spx.csv')
    spx_prices['Time']= pd.to_datetime(spx_prices['Time'])

    market_days = get_market_days(dt(2023, 5, 20, 9, 30, 0), dt(2023, 12, 31, 16, 0, 0))

    df = pd.DataFrame(columns=['Day', 'S&P Open','S&P Price 5 Before Close','% Change','Distance from Edge','Outcome'])

    for index, day in enumerate(market_days):
        op, close, price_at_buy_min = get_stock_info(spx_prices, 2023, day.month, day.day, 52)
        
        if op == 0 and close == 0 and price_at_buy_min == 0:
            continue
        
        decider = float(str(price_at_buy_min)[2:])
        first_two = str(price_at_buy_min)[:2]
        
        if decider < 25:
            range_low = int(first_two + '00')
            range_high = float(first_two + '24.99')
        elif decider < 50:
            range_low = int(first_two + '25')
            range_high = float(first_two + '49.99')
        elif decider < 75:
            range_low = int(first_two + '50')
            range_high = float(first_two + '74.99')
        else:
            range_low = int(first_two + '75')
            range_high = float(first_two + '99.99')
            
        distance_from_edge = min(abs(range_low - price_at_buy_min), abs(range_high - price_at_buy_min))

        if close <= range_high and close >= range_low:
            ended_in_range = 1
        else:
            ended_in_range = 0
        
        df2 = pd.DataFrame([{'Day': str(day), 'S&P Open': op, 'S&P Price 5 Before Close': price_at_buy_min, '% Change': 100*(price_at_buy_min-op)/op, 'Distance from Edge': distance_from_edge, 'Outcome': ended_in_range}])
        
        df = pd.concat([df if not df.empty else None,df2])
        df.reset_index() 
    df.to_csv('back_testing/stock_data.csv', index=False)
    return df

"""
Get the X and y dataframes for use in models
"""
def get_data(file_path, features, target):
    df = pd.read_csv(file_path)
    y = df[target].astype(float)
    X = df[features].astype(float)
    return X, y

"""
Create a logistic regression model to predict whether the S&P will end within a specified range
"""
def logistic_regression(file_path, features, target):
    X, y = get_data(file_path, features, target)
    X = sm.add_constant(X)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)

    model = sm.Logit(y_train, X_train).fit()

    print(model.summary())
    
    predictions = (model.predict(X_test) > 0.5).astype(int)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Accuracy: {accuracy:.2f}")

    print("Classification Report:")
    print(classification_report(y_test, predictions))


"""
Create a knn model to predict whether the S&P will end within a specified range
"""
def knn(file_path, features, target, n):
    X, y = get_data(file_path, features, target)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)

    knn_classifier = KNeighborsClassifier(n_neighbors=n)
    knn_classifier.fit(X_train, y_train)

    predictions = knn_classifier.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    print(f"Accuracy: {accuracy:.2f}")

    print("Classification Report:")
    print(classification_report(y_test, predictions))

if __name__ == "__main__":
    filepath = "back_testing/stock_data.csv"
    target = 'Outcome'
    features = ['S&P Open','S&P Price 5 Before Close','% Change','Distance from Edge']
    
    logistic_regression(filepath, features, target)
    knn(filepath, features, target, 3)
