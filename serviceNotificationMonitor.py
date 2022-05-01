import logging
import asyncio

import os
from aiogram import Bot, Dispatcher, executor, types

from middlewares import *
from messageHandler import *
from dbQueries import *
from pymemcache.client import base
import time

API_TOKEN = os.getenv('TELTOKEN', 'NONE_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)

async def send_message(user_id, msg):
    await bot.send_message(user_id, msg)


async def main():
    init_time = time.time()
    client = base.Client(('127.0.0.1', 11211)) # TODO: add yml config
    while True:
        notify_time = (init_time - time.time()) // 60
        user_notifies = fetchall('user_notifies', ['stock_name', 'telegram_id', 'target_value', 'notify_time'])
        for n in user_notifies:
            if n['notify_time'] != 0 and notify_time % n['notify_time'] == 0:
                value = client.get(n['stock_name']).decode()
                await send_message(n['telegram_id'], '{0} current price: {1}'.format(n['stock_name'], value))
        await asyncio.sleep(60)
    await bot.session.close() 


if __name__ == '__main__':
    executor.asyncio.run(main()) # TODO: fix closing error