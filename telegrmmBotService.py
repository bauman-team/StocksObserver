import logging

import os
from aiogram import Bot, Dispatcher, executor, types

from middlewares import *
from messageHandler import *


API_TOKEN = os.getenv('TELTOKEN', 'NONE_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'info'])
async def send_welcome(message: types.Message):

    AddUser(message.from_user.id)
    await message.reply("""Hi!\nI'm StocksObserverBot!\nTo add a stock to monitoring:
    \n+YNDX 3000 15\n(here 3000 is the target value, and 15 is the period of automatic price notifications)
    \n\nTo delete a stock from monitoring:\n-YNDX\n\nYou can also view a list of all the stocks added to the monitoring:
    \n\\list\n\nPowered by mikhail-xnor.""")

@dp.message_handler(commands=['list'])
async def send_monitoringList(message: types.Message):
    user_stocks = []
    row = fetchall('user_notifies', ['stock_name', 'telegram_id', 'target_value', 'notify_time'])
    for i in row:
        if i['telegram_id'] == message.from_user.id:
            user_stocks.append([i['stock_name'], i['target_value'], i['notify_time']])
    await message.reply(user_stocks)


@dp.message_handler()
async def add_to_monitoringList(message: types.Message):
    
    await message.answer(sub_to_notifications(message.from_user.id, message.text))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)