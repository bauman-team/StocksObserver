import logging
import asyncio

import os
from aiogram import Bot, Dispatcher, executor, types

from middlewares import *
from messageHandler import *
from dbQueries import *
from pymemcache.client import base
import time, datetime

API_TOKEN = os.getenv('TELTOKEN', 'NONE_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)

async def send_message(user_id, msg):
    await bot.send_message(user_id, msg)

stocks = fetchall('stocks', ['stock_name'])
stocks_names = [i['stock_name'] for i in stocks]

async def main():
    client = base.Client(('127.0.0.1', 11211)) # TODO: add yml config
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
                print(stock_name, next_y, curr_y, pred_time)
                for n in user_notifies:
                    if n['stock_name'] == stock_name:
                        await send_message(n['telegram_id'], f"Акция {n['stock_name']}\nТекущая цена: {curr_y} руб\nПрогноз на {pred_time}: {pred_str}\n[ {next_y} руб ({round((next_y - curr_y) / curr_y * 100, rnd)}%) ]")
                client.delete(stock_name)
        time.sleep(1)
    await bot.session.close()


if __name__ == '__main__':
    executor.asyncio.run(main()) # TODO: fix closing error