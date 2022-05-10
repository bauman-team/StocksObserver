#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import asyncio

import os
from aiogram import Bot, Dispatcher, executor, types
import aiogram

from middlewares import *
from messageHandler import *
from dbQueries import *
from pymemcache.client import base
import time, datetime

API_TOKEN = os.environ['TELTOKEN']

# Configure logging
logger = logging.getLogger('telegramNotificationService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='../info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

logger.info("Start logging")

# Initialize bot
bot = Bot(token=API_TOKEN)

async def send_message(user_id, msg):
    try:
        await bot.send_message(user_id, msg)
    except aiogram.utils.exceptions.BotBlocked as err:
        DropUser(user_id)
        logger.info("Bot was blocked by user!") # TODO: drop row in the DB
    except Exception as err:
        logger.fatal(err)
        exit()

# TODO: CREATE handler target price

stocks = fetchall('stocks', ['stock_name'])
stocks_names = [i['stock_name'] for i in stocks]
# TODO: CREATE ? not working days (and StocksMonitor)


async def main():
    """for stock_name in stocks_names:
        print(stock_name)"""
    init_time = time.time()
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
        user_notifies = fetchall('user_notifies', ['stock_name', 'telegram_id', 'target_value', 'notify_time'])
        for stock_name in stocks_names:
            value = client.get(stock_name)
            if value != None:
                value = value.decode()
                tup = value[1:-1].split(',')
                curr_y = float(tup[0])
                next_y = float(tup[1])
                pred_time = tup[2][2:-1]
                rnd = int(tup[3])
                pred_str = "РОСТ" if next_y > curr_y else "ПАДЕНИЕ"
                print(stock_name, next_y, curr_y, pred_time, round((next_y - curr_y) / curr_y * 100, rnd))
                for n in user_notifies:
                    if n['stock_name'] == stock_name:
                        await send_message(n['telegram_id'], f"Акция {n['stock_name']}\nТекущая цена: {curr_y} руб\nПрогноз на {pred_time}: {pred_str}\n[ {next_y} руб ({round((next_y - curr_y) / curr_y * 100, rnd)}%) ]")
                client.delete(stock_name)
        time.sleep(1)
    await bot.session.close()
    

if __name__ == '__main__':
    executor.asyncio.run(main()) # TODO: fix closing error
    