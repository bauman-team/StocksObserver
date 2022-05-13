#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import os
from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import filters
from aiogram.types import InputFile

from middlewares import *
from messageHandler import *

admins_ids_map = []
with open("../admins.txt", "r") as f:
    raw_text = f.read()
    for i in raw_text.split('\n'):
        try:
            admins_ids_map.append(int(i))
        except Exception:
            continue

API_TOKEN = os.environ['TELTOKEN']

# Configure logging
logger = logging.getLogger('telegramBotHandlerService')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='../info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

logger.info("Start logging")

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(middleware = AccessMiddleware(admins_ids_map))

# Initialize buttons
list_of_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
list_of_buttons.add(*["/search", "/list", "/help"])
list_of_buttons.add("/clear")

list_admin_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
list_admin_buttons.add(*["/search", "/list", "/help"])
list_admin_buttons.add("/clear")
list_admin_buttons.add(*admin_buttons)


help_massage = utils.markdown.text(
    "Hi!",
    "I'm StocksObserverBot!\n",
    "To add a stock to monitoring:",
    "+YNDX",
    "or",
    "+YNDX 3000",
    "(here 3000 is the target value)\n",
    "To delete a stock from monitoring:",
    "-YNDX",
    "or",
    "-YNDX 3000\n",
    "To get short info about stock:",
    "YNDX\n",
    "You can also view a list of all the stocks added to the monitoring:",
    "/list\n",
    "To clear notification list:",
    "/clear\n",
    "Powered by bauman-team.",
    "version 0.9",
    sep="\n"
)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    AddUser(message.from_user.id)
    if message.from_user.id in admins_ids_map:
        await message.answer(help_massage, reply_markup=list_admin_buttons)
    else:
        await message.answer(help_massage, reply_markup=list_of_buttons)

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    await message.answer(help_massage)

@dp.message_handler(commands=['list'])
async def send_monitoringList(message: types.Message):
    user_stocks = []
    row = fetchall('user_notifications', ['stock_name', 'telegram_id', 'target_value'])
    for i in row:
        if i['telegram_id'] == message.from_user.id:
            user_stocks.append([i['stock_name'], i['target_value']])
    await message.answer(user_stocks)

@dp.message_handler(commands=['clear'])
async def send_question_clear(message: types.Message):
    accept_button = types.InlineKeyboardMarkup()
    accept_button.add(types.InlineKeyboardButton(text="Accept drop all", callback_data="notifications_clear_accept"))
    accept_button.add(types.InlineKeyboardButton(text="Decline", callback_data="notifications_clear_decline"))
    await message.reply("Warning! Do you want to drop all notifications?", reply_markup=accept_button)

@dp.message_handler(commands=['log', 'statistics'])
async def send_question_clear(message: types.Message):
    file_name = message.get_command()[1:]
    file = InputFile(path_or_bytesio=f"../{'info' if file_name == 'log' else file_name}.log")
    await message.reply_document(file)

@dp.message_handler()
async def add_to_monitoringList(message: types.Message):
    await message.answer(sub_to_notifications(message.from_user.id, message.text))


@dp.callback_query_handler(filters.Text(startswith="notifications_clear_"))
async def drop_all_user_notifications(call: types.CallbackQuery):
    action = call.data.split('_')[2]
    if action == "accept":
        DropAllNotification(call.from_user.id)
        await call.message.answer("Notifications cleared!")
    await call.message.delete()
    await call.answer()

# TODO: CREATE add endpoints for take subscription
# TODO: CREATE add column to db about subscription
# TODO: CREATE add middleware (it exist, but not used)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)