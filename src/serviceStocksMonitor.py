#!/usr/bin/env python
# -*- coding: utf-8 -*-
from src.dbQueries import *
import time
import requests
from pymemcache.client import base

stocks = fetchall('stocks', ['stock_name'])
stocks_name = [i['stock_name'] for i in stocks]

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
    client = base.Client(('127.0.0.1', 11211)) # TODO: CREATE add yml config
    try:
        client.get(".") # check memcached
    except ConnectionRefusedError as err:
        logger.fatal("Memcahed error refused connection!")
        exit()
    except Exception as err:
        logger.fatal(err)
        exit()

    while True:
        r = requests.get(url) # TODO: ??? maybe logging
        r.encoding = 'utf-8'
        j = r.json()

        for i in j['marketdata']['data']:
            if i[0] in stocks_name:
                client.set(i[0], i[1])
        time.sleep(60)
    return

if __name__ == '__main__':
    main()