import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report

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
