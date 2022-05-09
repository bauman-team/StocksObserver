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
import time

API_TOKEN = os.environ['TELTOKEN']

# Configure logging
logger = logging.getLogger('telegramNotificationService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='info.log', mode='a')
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

# TODO: CREATE ? not working days (and StocksMonitor)

async def main():
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
        notify_time = (init_time - time.time()) // 60
        user_notifies = fetchall('user_notifies', ['stock_name', 'telegram_id', 'target_value', 'notify_time'])
        for n in user_notifies:
            if n['notify_time'] != 0 and notify_time % n['notify_time'] == 0:
                value = client.get(n['stock_name'])
                if value != None:
                    await send_message(n['telegram_id'], '{0} current price: {1}'.format(n['stock_name'], value.decode()))
        await asyncio.sleep(60)
    await bot.session.close() 


if __name__ == '__main__':
    executor.asyncio.run(main()) # TODO: fix closing error
    