import logging as lg
import datetime
import time
from dbQueries import fetchall
from moex import Moex


stocks_names = [i['stock_name'] for i in fetchall('stocks', ['stock_name'])]


class Stat:
    __stat_map = {}

    __stat_logger = lg.getLogger('statistics')
    __stat_logger.setLevel(lg.INFO)
    __stat_file_handler = lg.FileHandler(filename='../statistics.log', mode='a')
    __stat_file_handler.setLevel(lg.INFO)
    __stat_logger.addHandler(__stat_file_handler)
    __stat_file_handler.setFormatter(lg.Formatter('%(message)s'))

    @classmethod
    def save_prediction(cls, pred_time, stock_name, init_price, pred_price):
        if pred_time not in cls.__stat_map.keys():
            cls.__stat_map[pred_time] = {}
        cls.__stat_map[pred_time][stock_name] = {'init_price': init_price, 'pred_price': pred_price}

    @classmethod
    def logging(cls, client):
        while True:
            if Moex.is_work_today() and \
                (datetime.datetime.now().time() > datetime.time(10, 30)) and \
                (datetime.datetime.now().time() <= datetime.time(18, 50)):
                while datetime.datetime.now().minute % 10 != 0:
                    time.sleep(
                        (9 - datetime.datetime.now().minute % 10) * 60 + (59 - datetime.datetime.now().second) + (
                            1 - datetime.datetime.now().microsecond / 1000000))
                pred_time = datetime.datetime.now().strftime("%H:%M %d.%m.%y")
                if pred_time in cls.__stat_map:
                    cls.__stat_logger.info(f"{pred_time}")
                    curr_prices = cls.__get_current_prices()
                    for stock_name in stocks_names:
                        init_price = cls.__stat_map[pred_time][stock_name]['init_price']
                        pred_price = cls.__stat_map[pred_time][stock_name]['pred_price']
                        curr_price = curr_prices[stock_name]
                        is_right = int((pred_price - init_price) * (curr_price - init_price) > 0)
                        log_string = f"{stock_name}: init={init_price} curr={curr_price} pred={pred_price} is_right={is_right}"
                        cls.__stat_logger.info(log_string)
                    del cls.__stat_map[pred_time]
            time.sleep(60)

    @classmethod
    def __get_current_prices(cls, client):
        return {stock_name: float(client.get(stock_name + "_curr").decode()) for stock_name in stocks_names}