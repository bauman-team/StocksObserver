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
import warnings
warnings.filterwarnings('ignore')

stocks = fetchall('stocks', ['stock_name'])
stocks_names = [i['stock_name'] for i in stocks]

# Configure logging
logger = logging.getLogger('stocksMonitorService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

logger.info("Start logging")


def main():
    client = base.Client(('127.0.0.1', 11211)) # TODO: add yml config
    try:
        client.get(".") # check memcached
    except ConnectionRefusedError as err:
        logger.fatal("Memcahed error refused connection!")
        exit()
    except Exception as err:
        logger.fatal(err)
        exit()

    model_ticker = "POSI"
    intr = 10
    lgs_num = 24
    model_path = "models/"
    scaler_path = "scalers/"
    model = keras.models.load_model(f'{model_path}{model_ticker}.h5')
    rnd = 4
    while True:
        """while (datetime.datetime.now().minute % 10 != 5):
            time.sleep(10)"""
        start = (datetime.date.today() - relativedelta(month=2)).strftime('%Y-%m-%d')
        for stock_name in stocks_names:
            scaler = joblib.load(f"{scaler_path}{stock_name}.save")
            print(stock_name)
            with requests.Session() as session:
                last_data = pd.DataFrame(apimoex.get_board_candles(session, security=stock_name, interval=10, start=start))
                print(last_data)
                inpit_data = np.array([last_data.iloc[i]['close'] for i in range(last_data.shape[0] + 1 - lgs_num*3, last_data.shape[0] - 1, 3)]).reshape(-1, 1)
                last_real_x = np.array(scaler.transform(inpit_data)).reshape(1, lgs_num, 1)
                next_y = scaler.inverse_transform(model.predict(last_real_x))[0][0]
            pred_time = (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") + relativedelta(
                minutes=30)).strftime("%H:%M %d.%m.%y")
            next_y = round(next_y, rnd)
            curr_y = last_data.iloc[-1]['close']
            print(inpit_data)
            print((curr_y, next_y, pred_time, rnd))
            client.set(stock_name, (curr_y, next_y, pred_time, rnd))
        """
        r = requests.get(url) # TODO: ??? maybe logging
        r.encoding = 'utf-8'
        j = r.json()

        for i in j['marketdata']['data']:
            if i[0] in stocks_name:
                client.set(i[0], i[1])
        time.sleep(60)"""
        time.sleep(60)  # for debug only
    return

if __name__ == '__main__':
    main()