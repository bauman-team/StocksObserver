from hashlib import new
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from dbQueries import fetchall, AddStock, DropStock
import time
from pymemcache.client import base
from pymemcache import MemcacheError
import datetime
import logging
from threading import Thread
from statistics import Stat
from moex import Moex
from forecastSystem import ForecastSystem

# Configure logging
logger = logging.getLogger('stocksMonitorService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='../info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)
logger.info("Start logging")

stocks_names = [i['stock_name'] for i in fetchall('stocks', ['stock_name'])]


def scanning_price(client):
    while True:
        current_prices = Moex.get_current_stocks_prices()
        if current_prices is not None:
            for i in current_prices:
                if (i[0] in stocks_names) and (i[1] is not None):
                    client.set(i[0] + "_curr", i[1])
        else:
            print(f"Не удалось получить текущие цены акций")
        time.sleep(1 - datetime.datetime.now().microsecond / 1000000)


def main():
    client = base.Client(('127.0.0.1', 11211))  # TODO: CREATE add yml config
    try:
        client.get(".")  # check memcached
    except MemcacheError as err:
        logger.fatal("Memcached error refused connection!")
        exit(1)

    try:
        with open("../list_of_monitoring_stocks.txt", "r") as f:
            actual_stocks_list = f.read().split('\n')
            actual_stocks_list = [i for i in actual_stocks_list if i != '']
            drop_stocks_list = [i for i in stocks_names if i not in actual_stocks_list]
            new_stocks_list = [i for i in actual_stocks_list if i not in stocks_names]

            for i in drop_stocks_list:
                DropStock(i)
                logger.info(f"Drop stock from monitoring: {i}")
            if drop_stocks_list != []:
                client.set("deleted_stocks", drop_stocks_list)
            
            for i in new_stocks_list:
                AddStock(i)
                logger.info(f"Added new stock to monitoring: {i}")
            if new_stocks_list != []:
                client.set("added_stocks", new_stocks_list)

        logger.info("Stocks list up to date.")
    except Exception:
        logger.error("Error, not found file with list of monitoring stocks!")

    scan_thread = Thread(target=scanning_price, args=(client,))
    scan_thread.start()
    time.sleep(2)
    stat_thread = Thread(target=Stat.logging, args=(client,))
    stat_thread.start()

    while True:
        ForecastSystem.models_update_if_necessary()
        if Moex.is_work_today():
            if (datetime.datetime.now().time() > datetime.time(10, 10)) and \
                (datetime.datetime.now().time() < datetime.time(18, 22)):
                while datetime.datetime.now().minute % 10 != 1:
                    time.sleep(1)
                ForecastSystem.make_predictions(client, debug_info=True)
        time.sleep(60)
    return


if __name__ == '__main__':
    main()