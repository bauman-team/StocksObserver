from dbQueries import fetchall
import datetime
from dateutil.relativedelta import relativedelta
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import joblib
from keras.models import load_model
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
import os
import time
from statistics import Stat
from moex import Moex


stocks_names = [i['stock_name'] for i in fetchall('stocks', ['stock_name'])]


class ForecastSystem:
    __model_path = "../models/"
    __scaler_path = "../scalers/"
    __min_steps = Moex.get_min_steps(stocks_names)

    @classmethod
    def __create_new_model(cls, stock_name, lags=20, epochs=10, debug_info=False):
        if not os.path.exists(cls.__scaler_path):
            os.makedirs(cls.__scaler_path)

        start_date = datetime.datetime.today() - relativedelta(years=1)
        data = Moex.get_candle_closing_prices(stock_name, 10, start_date)
        if data is not None:
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

            model.save(f"{cls.__model_path}{stock_name}.h5")
            joblib.dump(scaler, f"{cls.__scaler_path}{stock_name}.save")

            if debug_info:
                print(f"Created model for {stock_name}")
        else:
            print(f"Не удалось создать модель для {stock_name}")

    @classmethod
    def make_predictions(cls, client, debug_info=False):
        if debug_info:
            counter = 1
        start = (datetime.date.today() - relativedelta(month=1)).strftime('%Y-%m-%d')
        accuracy = Stat.get_accuracy_for_all_stocks()

        for stock_name in stocks_names:
            model = load_model(f'{cls.__model_path}{stock_name}.h5')
            scaler = joblib.load(f"{cls.__scaler_path}{stock_name}.save")
            lgs_num = model.input_shape[1]
            last_data = Moex.get_candle_closing_prices(stock_name, 10, start)
            if last_data is not None:
                while (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") +
                       relativedelta(minutes=10)) < datetime.datetime.now():
                    print(f"Свеча для {stock_name} ещё не пришла")
                    time.sleep(1)
                    last_data = Moex.get_candle_closing_prices(stock_name, 10, start)
                    if last_data is None:
                        break

                if last_data is None:
                    print(f"Не удалось построить прогноз для {stock_name}")
                    continue

                rng = range(last_data.shape[0] + 1 - lgs_num * 3, last_data.shape[0] - 1, 3)
                input_data = np.array([last_data.iloc[i]['close'] for i in rng]).reshape(-1, 1)
                last_real_x = np.array(scaler.transform(input_data)).reshape(1, lgs_num, 1)
                next_y = scaler.inverse_transform(model.predict(last_real_x))[0][0]

                step_str = str(cls.__min_steps[stock_name])
                if float(cls.__min_steps[stock_name]).is_integer():
                    next_y = round(round(next_y / cls.__min_steps[stock_name]) * cls.__min_steps[stock_name])
                else:
                    if '.' in step_str:
                        precision = len(step_str) - step_str.find('.') - 1
                    else:
                        precision = int(step_str[step_str.find('e') + 2:])
                    next_y = round(round(next_y / cls.__min_steps[stock_name]) * cls.__min_steps[stock_name], precision)

                curr_y = last_data.iloc[-1]['close']
                pred_time = (datetime.datetime.strptime(last_data.iloc[-1]['begin'], "%Y-%m-%d %H:%M:%S") +
                             relativedelta(minutes=30)).strftime("%H:%M %d.%m.%y")

                if stock_name in accuracy.keys():
                    client.set(stock_name, (curr_y, next_y, pred_time, accuracy[stock_name]))
                else:
                    client.set(stock_name, (curr_y, next_y, pred_time, None))
                Stat.save_prediction(pred_time, stock_name, curr_y, next_y)

                if debug_info:
                    print(counter, stock_name, (curr_y, next_y, pred_time))
                    counter += 1
            else:
                print(f"Не удалось построить прогноз для {stock_name}")

    @classmethod
    def __need_update_model(cls, stock_name):
        if (not os.path.exists(f"{cls.__model_path}{stock_name}.h5")) or (
        not os.path.exists(f"{cls.__scaler_path}{stock_name}.save")):
            return True

        last_modify_model = datetime.datetime.fromtimestamp(os.path.getmtime(f"{cls.__model_path}{stock_name}.h5"))
        last_modify_scaler = datetime.datetime.fromtimestamp(os.path.getmtime(f"{cls.__scaler_path}{stock_name}.save"))
        last_modify = min(last_modify_model, last_modify_scaler)
        now_datetime = datetime.datetime.now()

        temp_date = last_modify.date() + relativedelta(days=1)
        while temp_date < now_datetime.date():
            if Moex.is_work_at(temp_date):
                return True
            temp_date += relativedelta(days=1)

        work_last = Moex.is_work_at(last_modify)
        work_now = Moex.is_work_at(now_datetime)

        if (last_modify.date() == now_datetime.date()) and work_now:
            return last_modify.time() < datetime.time(18, 51) and now_datetime.time() >= datetime.time(18, 51)

        return (work_last and (last_modify.time() < datetime.time(18, 51))) or (
                work_now and (now_datetime.time() >= datetime.time(18, 51)))

    @classmethod
    def models_update_if_necessary(cls):
        for stock_name in stocks_names:
            if cls.__need_update_model(stock_name):
                cls.__create_new_model(stock_name)

