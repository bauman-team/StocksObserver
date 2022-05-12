import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from dbQueries import *
import time
import requests
from pymemcache.client import base
from keras.models import load_model
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
import joblib
import datetime
import pandas as pd
import numpy as np
import apimoex
from dateutil.relativedelta import relativedelta
from sklearn.preprocessing import MinMaxScaler
import xmltodict
import logging
from threading import Thread


stocks = fetchall('stocks', ['stock_name'])
stocks_names = [i['stock_name'] for i in stocks]

# Configure logging
logger = logging.getLogger('stocksMonitorService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='../info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

logger.info("Start logging")

stat_logger = logging.getLogger('statistics')
stat_logger.setLevel(logging.INFO)
stat_file_handler = logging.FileHandler(filename='../statistics.log', mode='a')
stat_file_handler.setLevel(logging.INFO)
stat_logger.addHandler(stat_file_handler)
formatter = logging.Formatter('%(message)s')
stat_file_handler.setFormatter(formatter)
stat_map = {}
model_path = "../models/"
scaler_path = "../scalers/"

url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'


def save_stat(client):
    while True:
        if (datetime.datetime.now().time() > datetime.time(10, 30)) and (datetime.datetime.now().time() <= datetime.time(18, 50)):
            while datetime.datetime.now().minute % 10 != 0:
                time.sleep((9 - datetime.datetime.now().minute % 10) * 60 + (59 - datetime.datetime.now().second) + (1 - datetime.datetime.now().microsecond / 1000000))
            pred_time = datetime.datetime.now().strftime("%H:%M %d.%m.%y")
            print("-----------------")
            print(pred_time)
            print(stat_map)
            print("-----------------")
            curr_prices = {}
            if pred_time in stat_map:
                for stock_name in stocks_names:
                    curr_prices[stock_name] = float(client.get(stock_name + "_curr").decode())
                stat_logger.info(f"{pred_time}")
                for stock_name in stocks_names:
                    init, pred = stat_map[datetime.datetime.now().strftime("%H:%M %d.%m.%y")][stock_name]
                    real = curr_prices[stock_name]
                    is_right = int((pred - init) * (real - init) > 0)
                    log_string = f"{stock_name}: init={init} real={real} pred={pred} is_right={is_right}"
                    stat_logger.info(log_string)
                del stat_map[pred_time]
        time.sleep(60)

def scanning_price(client):
    while True:
        r = requests.get(url)
        r.encoding = 'utf-8'
        j = r.json()
        for i in j['marketdata']['data']:
            if i[0] in stocks_names:
                client.set(i[0] + "_curr", i[1])
        time.sleep(1 - datetime.datetime.now().microsecond / 1000000)

def create_new_model(stock_name, lags=20, epochs=10, debug_info=False):
    if not os.path.exists(scaler_path):
        os.makedirs(scaler_path)

    start_date = datetime.datetime.today() - relativedelta(years=1)
    with requests.Session() as session:
        data = pd.DataFrame(
            apimoex.get_board_candles(session, security=stock_name, interval=10, columns=('begin', 'close'),
                                      start=start_date))
        rng = range(2 + (data.shape[0] % 3), data.shape[0], 3)
        data = data.iloc[rng]

        scaler = MinMaxScaler()
        scaler.fit(data['close'].values.reshape(-1, 1))
        scaled_data = pd.Series(scaler.transform(data['close'].values.reshape(-1, 1)).flatten())

        x_data = list()
        y_data = list()
        for i in range(0, scaled_data.shape[0] - lags):
            x_data.append(scaled_data[i:i + lags])
            y_data.append(scaled_data[i + lags])
        x_data = np.array(x_data).reshape(len(x_data), lags, 1)
        y_data = np.array(y_data).reshape(-1, 1)

        model = Sequential()
        model.add(LSTM(units=60, input_shape=(lags, 1), return_sequences=True))
        model.add(LSTM(units=50, input_shape=(lags, 1), return_sequences=False))
        model.add(Dense(units=1))
        model.compile(optimizer='adam', loss='mean_absolute_error')
        history = model.fit(x_data, y_data, batch_size=200, epochs=epochs, verbose=0)

        model.save(f"{model_path}{stock_name}.h5")
        joblib.dump(scaler, f"{scaler_path}{stock_name}.save")

        if debug_info:
            print(f"Created model for {stock_name}")

def make_predictions(client, debug_info=False):
    if debug_info:
        counter = 1
    rnd = 4
    start = (datetime.date.today() - relativedelta(month=1)).strftime('%Y-%m-%d')
    for stock_name in stocks_names:
        model = load_model(f'{model_path}{stock_name}.h5')
        scaler = joblib.load(f"{scaler_path}{stock_name}.save")
        lgs_num = model.input_shape[1]
        with requests.Session() as session:
            last_data = pd.DataFrame(apimoex.get_board_candles(session, security=stock_name, interval=10, start=start))
            while (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") + relativedelta(
                    minutes=10)) < datetime.datetime.now():
                print(f"Свеча для {stock_name} ещё не пришла")
                time.sleep(1)
                last_data = pd.DataFrame(
                    apimoex.get_board_candles(session, security=stock_name, interval=10, start=start))

        rng = range(last_data.shape[0] + 1 - lgs_num * 3, last_data.shape[0] - 1, 3)
        input_data = np.array([last_data.iloc[i]['close'] for i in rng]).reshape(-1, 1)
        last_real_x = np.array(scaler.transform(input_data)).reshape(1, lgs_num, 1)
        next_y = round(scaler.inverse_transform(model.predict(last_real_x))[0][0], rnd)
        curr_y = last_data.iloc[-1]['close']
        pred_time = (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") +
                     relativedelta(minutes=30)).strftime("%H:%M %d.%m.%y")
        client.set(stock_name, (curr_y, next_y, pred_time, rnd))

        print(pred_time, stat_map.keys())
        if pred_time not in stat_map.keys():
            stat_map[pred_time] = {}
        stat_map[pred_time][stock_name] = (curr_y, next_y)

        if debug_info:
            print(counter, stock_name, (curr_y, next_y, pred_time, rnd))
            print()
            counter += 1
    if debug_info:
        print('All predicted')


def is_moex_work(target_date):
    r = requests.get('https://iss.moex.com/iss/engines/stock.xml')
    dict_data = xmltodict.parse(r.content)
    target_date_str = target_date.strftime('%Y-%m-%d')
    is_work_day1 = dict_data['document']['data'][1]['rows']['row'][target_date.weekday()]['@is_work_day']
    is_work_day2 = '-1'
    for row in dict_data['document']['data'][2]['rows']['row']:
        if row['@date'] == target_date_str:
            is_work_day2 = row['@is_work_day']
            break
    return (is_work_day2 == '1') or (is_work_day1 == '1' and is_work_day2 == '-1')


def main():
    client = base.Client(('127.0.0.1', 11211)) # TODO: CREATE add yml config
    try:
        client.get(".") # check memcached
    except ConnectionRefusedError as err:
        logger.fatal("Memcahed error refused connection!")
        exit()
    except Exception as err:
        logger.fatal(err)
        exit()

    scan_thread = Thread(target=scanning_price, args=(client,))
    scan_thread.start()
    time.sleep(1)
    stat_thread = Thread(target=save_stat, args=(client,))
    stat_thread.start()

    while True:
        models_update_if_necessary()
        if is_moex_work(datetime.datetime.today()):
            if (datetime.datetime.now().time() > datetime.time(10, 10)) and (datetime.datetime.now().time() < datetime.time(18, 22)):
                while datetime.datetime.now().minute % 10 != 1:
                    time.sleep(1)
                make_predictions(client, debug_info=True)
        time.sleep(60)
    return

def need_update_model(stock_name):
    if (not os.path.exists(f"{model_path}{stock_name}.h5")) or (not os.path.exists(f"{scaler_path}{stock_name}.save")):
        return True

    last_modify_model = datetime.datetime.fromtimestamp(os.path.getmtime(f"{model_path}{stock_name}.h5"))
    last_modify_scaler = datetime.datetime.fromtimestamp(os.path.getmtime(f"{scaler_path}{stock_name}.save"))
    last_modify = min(last_modify_model, last_modify_scaler)
    now_datetime = datetime.datetime.now()

    temp_date = last_modify.date() + relativedelta(days=1)
    while temp_date < now_datetime.date():
        if is_moex_work(temp_date):
            return True
        temp_date += relativedelta(days=1)

    work_last = is_moex_work(last_modify)
    work_now = is_moex_work(now_datetime)

    if (last_modify.date() == now_datetime.date()) and work_now:
        return last_modify.time() < datetime.time(18, 51) and now_datetime.time() >= datetime.time(18, 51)

    return (work_last and (last_modify.time() < datetime.time(18, 51))) or (work_now and (now_datetime.time() >= datetime.time(18, 51)))

def models_update_if_necessary():
    for stock_name in stocks_names:
        if need_update_model(stock_name):
            create_new_model(stock_name, debug_info=True)

if __name__ == '__main__':
    main()