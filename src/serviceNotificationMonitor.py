#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import os
from aiogram import Bot, executor
import aiogram

from middlewares import *
from messageHandler import *
from dbQueries import *
from pymemcache.client import base
from pymemcache import MemcacheError
import time

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
        exit(1)


async def main():
    """for stock_name in stocks_names:
        print(stock_name)"""
    init_time = time.time()
    client = base.Client(('127.0.0.1', 11211)) # TODO: CREATE add yml config
    try:
        client.get(".") # check memcached
    except MemcacheError as err:
        logger.fatal("Memcahed error refused connection!")
        exit(1)

    while True:
        user_target_notifies = fetchall('user_notifications', ['id', 'stock_name', 'telegram_id', 'target_value', 'target_grow'])
        user_notifies = fetchall_unique('user_notifications', ['stock_name', 'telegram_id'])
        for stock_name in stocks_names:
            value = client.get(stock_name)
            if value != None:
                value = value.decode()
                tup = value[1:-1].split(',')
                curr_y = float(tup[0])
                next_y = float(tup[1])
                pred_time = tup[2][2:-1]
                pred_str = "РОСТ" if next_y > curr_y else "ПАДЕНИЕ"
                accuracy = round(float(tup[3]) * 100, 4) if (tup[3][1:] != 'None') else None
                print(stock_name, next_y, curr_y, pred_time, round((next_y - curr_y) / curr_y * 100, 4), accuracy)
                message = f"Акция {stock_name}\n" \
                          f"Текущая цена: {curr_y} руб\n" \
                          f"Прогноз на {pred_time}: {pred_str}\n[ {next_y} руб" \
                          f"({round((next_y - curr_y) / curr_y * 100, 4)}%) ]"
                if accuracy:
                    message += f"\nТочность прогнозов для {stock_name}: {accuracy}%"
                for n in user_notifies:
                    if n['stock_name'] == stock_name:
                        await send_message(n['telegram_id'], message)
                client.delete(stock_name)
            curr_value = client.get(stock_name+"_curr")
            if curr_value != None:
                curr_value = float(curr_value.decode())
                for n in user_target_notifies:
                    if n['stock_name'] == stock_name and (n['target_value'] <= curr_value and n['target_grow'] or n['target_value'] >= curr_value and not n['target_grow']):
                        delete('user_notifications', n['id'])
                        await send_message(n['telegram_id'], f"Акция {n['stock_name']} достигла целевой цены: {n['target_value']} руб")
        deleted_stocks = client.get("deleted_stocks")
        if deleted_stocks != None:
            deleted_stocks = deleted_stocks.decode()
            deleted_stocks_names = deleted_stocks[1:-1].replace("'", "").split(', ')
            for stock_name in deleted_stocks_names:
                await send_message(n['telegram_id'], f"Акция {stock_name} удалена из мониторинга!")
            client.delete("deleted_stocks")
        added_stocks = client.get("added_stocks")
        if added_stocks != None:
            added_stocks = added_stocks.decode()
            added_stocks_names = added_stocks[1:-1].replace("'", "").split(', ')
            for stock_name in added_stocks_names:
                await send_message(n['telegram_id'], f"Акция {stock_name} стала доступна для мониторинга!")
            client.delete("added_stocks")
        time.sleep(1)
    await bot.session.close()


if __name__ == '__main__':
    executor.asyncio.run(main())
    
    
