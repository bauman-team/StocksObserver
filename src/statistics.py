import logging as lg
import datetime
import time
from dbQueries import fetchall
from moex import Moex
import pandas as pd
import numpy as np


stocks_names = [i['stock_name'] for i in fetchall('stocks', ['stock_name'])]


class Stat:

    @classmethod
    def __create_logger(cls):
        cls.__stat_map = {}

        cls.__stat_logger = lg.getLogger('statistics')
        cls.__stat_logger.setLevel(lg.INFO)
        cls.__stat_file_handler = lg.FileHandler(filename='../statistics.log', mode='a')
        cls.__stat_file_handler.setLevel(lg.INFO)
        cls.__stat_logger.addHandler(cls.__stat_file_handler)
        cls.__stat_file_handler.setFormatter(lg.Formatter('%(message)s'))

    @classmethod
    def save_prediction(cls, pred_time, stock_name, init_price, pred_price):
        if pred_time not in cls.__stat_map.keys():
            cls.__stat_map[pred_time] = {}
        cls.__stat_map[pred_time][stock_name] = {'init_price': init_price, 'pred_price': pred_price}

    @classmethod
    def logging(cls, client):
        cls.__create_logger()
        while True:
            try:
                if Moex.is_work_today() and \
                    (datetime.datetime.now().time() > datetime.time(10, 30)) and \
                    (datetime.datetime.now().time() <= datetime.time(18, 50)):
                    while datetime.datetime.now().minute % 10 != 0:
                        time.sleep(
                            (9 - datetime.datetime.now().minute % 10) * 60 + (59 - datetime.datetime.now().second) + (
                                1 - datetime.datetime.now().microsecond / 1000000))
                    pred_time = datetime.datetime.now().strftime("%H:%M %d.%m.%y")
                    print("pred_time:", pred_time)
                    print("__stat_map keys:", cls.__stat_map.keys())
                    if pred_time in cls.__stat_map:
                        curr_prices = cls.__get_current_prices(client)
                        print("curr_prices:", curr_prices)
                        for stock_name in cls.__stat_map[pred_time].keys():
                            if stock_name in curr_prices.keys():
                                init_price = cls.__stat_map[pred_time][stock_name]['init_price']
                                pred_price = cls.__stat_map[pred_time][stock_name]['pred_price']
                                curr_price = curr_prices[stock_name]
                                is_right = int((pred_price - init_price) * (curr_price - init_price) > 0)
                                log_string = f"{pred_time},{stock_name},{init_price},{curr_price},{pred_price},{is_right}"
                                print(log_string)
                                cls.__stat_logger.info(log_string)
                            else:
                                print(f"Текущая цена для акции {stock_name} не найдена")
                        del cls.__stat_map[pred_time]
                time.sleep(60)
            except Exception as err:
                print(err)

    @classmethod
    def __get_current_prices(cls, client):
        current_prices = {}
        for stock_name in stocks_names:
            curr_price = client.get(stock_name + "_curr")
            if curr_price != None:
                current_prices[stock_name] = float(curr_price.decode())
        return current_prices

    @classmethod
    def get_summary_accuracy(cls, target_date=None):
        with open('../statistics.log', 'r') as stat_file:
            if not target_date:
                res = [int(line.rstrip()[-1]) for line in stat_file]
            else:
                res = [int(line.rstrip()[-1]) for line in stat_file if
                       datetime.datetime.strptime(line.rstrip().split(',')[0], "%H:%M %d.%m.%y").date() == target_date]
        accuracy = None
        if res != []:
            accuracy = sum(res) / len(res)
            """print(f"Верных прогнозов за " + (f"{target_date}" if target_date else "всё время") + f": {round(accuracy * 100, 4)}%")
        else:
            print(f"Нет прогнозов" + f" за {target_date}" if target_date else "")"""
        return accuracy

    @classmethod
    def get_accuracy_for(cls, target_stock_name, target_date=None):
        stock_stat_map = {}
        stock_accuracy = None
        with open('../statistics.log', 'r') as stat_file:
            for line in stat_file:
                split_line = line.rstrip().split(',')
                pred_datetime = datetime.datetime.strptime(split_line[0], "%H:%M %d.%m.%y")
                stock_name = split_line[1]
                if stock_name != target_stock_name or (target_date and pred_datetime.date() != target_date):
                    continue
                is_right = int(split_line[5][-1])
                stock_stat_map[pred_datetime] = is_right
        if stock_stat_map != {}:
            stock_accuracy = sum(stock_stat_map.values()) / len(stock_stat_map.values())
            """print(f"Верных прогнозов для {stock_name} за " + (f"{target_date}" if target_date else "всё время") + f": "
                                                                                f"{round(stock_accuracy * 100, 4)}%")
        else:
            print(f"Нет статистики прогнозов для {target_stock_name}" + f" за {target_date}" if target_date else "")"""
        return stock_accuracy

    @classmethod
    def get_accuracy_for_all_stocks(cls, target_date=None):
        history_stat_map = {}
        stocks_accuracies = {}
        with open('../statistics.log', 'r') as stat_file:
            for line in stat_file:
                split_line = line.rstrip().split(',')
                pred_datetime = datetime.datetime.strptime(split_line[0], "%H:%M %d.%m.%y")
                if target_date and pred_datetime.date() != target_date:
                    continue
                stock_name = split_line[1]
                is_right = int(split_line[5][-1])

                if stock_name not in history_stat_map.keys():
                    history_stat_map[stock_name] = {}
                history_stat_map[stock_name][pred_datetime] = is_right

        if history_stat_map != {}:
            for stock_name, stock_stat_map in history_stat_map.items():
                stock_accuracy = sum(stock_stat_map.values()) / len(stock_stat_map.values())
                stocks_accuracies[stock_name] = stock_accuracy
                """print(f"Верных прогнозов для {stock_name} за " + (
                    f"{target_date}" if target_date else "всё время") + f": {round(stock_accuracy * 100, 4)}%")
        else:
            print(f"Нет статистики прогнозов" + f" за {target_date}" if target_date else "")"""
        return stocks_accuracies

    @classmethod
    def save_report_to_file(cls, file_name):
        start = datetime.datetime.now()

        last_working_day = Moex.get_last_working_day()
        last_working_day_str = last_working_day.strftime("%d.%m.%y")

        accuracies = cls.get_accuracy_for_all_stocks()
        summary_accuracy = cls.get_summary_accuracy()

        last_accuracies = cls.get_accuracy_for_all_stocks(last_working_day)
        last_summary_accuracy = cls.get_summary_accuracy(last_working_day)

        with open(file_name, 'w') as stat_file:
            if last_summary_accuracy is not None:
                stat_file.write(f"Статистика правильных прогнозов за {last_working_day_str}\n\n")
                for stock_name, accuracy in sorted(last_accuracies.items()):
                    stat_file.write(f"Акция {stock_name}: {round(accuracy * 100, 4)}%\n")
                stat_file.write(f"\nВсего верных прогнозов за {last_working_day_str}: {round(last_summary_accuracy * 100, 4)}%\n\n\n\n")
            if summary_accuracy is not None:
                stat_file.write("Статистика правильных прогнозов за всё время\n\n")
                for stock_name, accuracy in sorted(accuracies.items()):
                    stat_file.write(f"Акция {stock_name}: {round(accuracy * 100, 4)}%\n")
                stat_file.write(f"\nВсего верных прогнозов: {round(summary_accuracy * 100, 4)}%")
            else:
                stat_file.write(f"\nНет статистики")

        print((datetime.datetime.now() - start).microseconds / 1000, "ms")

    """@classmethod
    def save_report_to_file2(cls, file_name):
        start = datetime.datetime.now()

        data = pd.read_csv('../statistics.csv')
        data['date'] = pd.to_datetime(data['date'])

        last_working_day = Moex.get_last_working_day()
        last_working_day_str = last_working_day.strftime("%d.%m.%y")

        accuracies = data.groupby('stock_name')['is_right'].mean().apply(lambda x: round(x * 100, 4))
        summary_accuracy = round(data['is_right'].mean() * 100, 4)

        last_accuracies = data[data['date'].dt.date == last_working_day].groupby('stock_name')['is_right'].mean().apply(lambda x: round(x * 100, 4))
        last_summary_accuracy = round(data[data['date'].dt.date == last_working_day]['is_right'].mean() * 100, 4)

        with open(file_name, 'w') as stat_file:
            if not pd.isnull(last_summary_accuracy):
                stat_file.write(f"Статистика правильных прогнозов за {last_working_day_str}\n\n")
                for stock_name, accuracy in sorted(last_accuracies.iteritems()):
                    stat_file.write(f"Акция {stock_name}: {accuracy}%\n")
                stat_file.write(f"\nВсего верных прогнозов за {last_working_day_str}: {last_summary_accuracy}%\n\n\n\n")
            if not pd.isnull(summary_accuracy):
                stat_file.write("Статистика правильных прогнозов за всё время\n\n")
                for stock_name, accuracy in sorted(accuracies.iteritems()):
                    stat_file.write(f"Акция {stock_name}: {accuracy}%\n")
                stat_file.write(f"\nВсего верных прогнозов: {summary_accuracy}%")
            else:
                stat_file.write(f"\nНет статистики")

        print((datetime.datetime.now() - start).microseconds / 1000, "ms")"""
