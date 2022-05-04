from dbQueries import *
import time
import requests
from pymemcache.client import base
import keras
import joblib
import datetime
import pandas as pd
import numpy as np
import apimoex
from dateutil.relativedelta import relativedelta

stocks = fetchall('stocks', ['stock_name'])
stocks_name = [i['stock_name'] for i in stocks]
#url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'



def main():
    client = base.Client(('127.0.0.1', 11211)) # TODO: add yml config
    while True:
        ticker = "YNDX"
        lags = 6
        model = keras.models.load_model(f'models/{ticker}.h5')
        scaler = joblib.load(f"scalers/{ticker}.save")
        start = (datetime.date.today() - relativedelta(months=1)).strftime('%Y-%m-%d')
        with requests.Session() as session:
            data = pd.DataFrame(apimoex.get_board_candles(session, security=ticker, interval=10, start=start))
            last_real_x = np.array(scaler.transform(data.iloc[-lags:]['close'].values.reshape(-1, 1))).reshape(1, lags, 1)
            y_pred = scaler.inverse_transform(model.predict(last_real_x))[0][0]
        print(y_pred)
        client.set(ticker, y_pred)
        time.sleep(60)
    return 

if __name__ == '__main__':
    main()