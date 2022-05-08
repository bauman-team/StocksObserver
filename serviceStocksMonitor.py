import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from dbQueries import *
import time
import requests
from pymemcache.client import base
from keras.models import load_model
import joblib
import datetime
import pandas as pd
import numpy as np
import apimoex
from dateutil.relativedelta import relativedelta


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
    model_path = "models/"
    scaler_path = "scalers/"
    rnd = 4

    """min_values = {}
    with requests.Session() as session:
        start = (datetime.date.today() - relativedelta(months=1)).strftime('%Y-%m-%d')
        for stock_name in stocks_names:
            last_data = pd.DataFrame(apimoex.get_board_candles(session, security=stock_name, interval=24, columns=("begin", "value"), start=start))
            min_values[stock_name] = last_data['value'].min()
    sorted_dict = dict(sorted(min_values.items(), key=lambda x: x[1]))
    for elem in sorted_dict.items():
        print(elem)
    time.sleep(600)"""
    while True:
        counter = 1
        """while (datetime.datetime.now().minute % 10 != 5):
            time.sleep(10)"""
        start = (datetime.date.today() - relativedelta(month=1)).strftime('%Y-%m-%d')
        for stock_name in stocks_names:
            model = load_model(f'{model_path}{stock_name}.h5')
            lgs_num = model.input_shape[1]
            scaler = joblib.load(f"{scaler_path}{stock_name}.save")
            # print(stock_name)
            with requests.Session() as session:
                last_data = pd.DataFrame(apimoex.get_board_candles(session, security=stock_name, interval=10, start=start))
                """if (last_data.shape[0] < 1026):
                    print("!!!!!!!!!!!", stock_name, last_data.shape[0])"""
            rng = range(last_data.shape[0] + 1 - lgs_num * 3, last_data.shape[0] - 1, 3)
            input_data = np.array([last_data.iloc[i]['close'] for i in rng]).reshape(-1, 1)
            last_real_x = np.array(scaler.transform(input_data)).reshape(1, lgs_num, 1)
            next_y = scaler.inverse_transform(model.predict(last_real_x))[0][0]
            pred_time = (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") + 
                         relativedelta(minutes=30)).strftime("%H:%M %d.%m.%y")
            next_y = round(next_y, rnd)
            curr_y = last_data.iloc[-1]['close']
            # print(input_data)
            print(counter, stock_name, (curr_y, next_y, pred_time, rnd))
            counter += 1
            client.set(stock_name, (curr_y, next_y, pred_time, rnd))
        """
        r = requests.get(url) # TODO: ??? maybe logging
        r.encoding = 'utf-8'
        j = r.json()

        for i in j['marketdata']['data']:
            if i[0] in stocks_name:
                client.set(i[0], i[1])
        time.sleep(60)"""
        print('END')
        time.sleep(60)  # for debug only
    return

if __name__ == '__main__':
    main()