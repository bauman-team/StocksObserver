#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dbQueries import *
from pymemcache.client import base
from pymemcache import MemcacheError


def sub_to_notifications(user_id: int, raw_message: str):
    client = base.Client(('127.0.0.1', 11211)) # TODO: CREATE add yml config
    # no ping memcached because it used 
    message = raw_message.split(' ')
    stock_name = message[0][1:] if message[0][0] in "+-" else message[0]
    if stock_name in stocks_names:
        if raw_message[0] == '+':
            try:
                message[1] = float(message[1].replace(',','.'))
                try:
                    curr_value = float(client.get(stock_name+"_curr").decode())
                    AddNotification(user_id, stock_name, message[1], curr_value < message[1])
                except Exception:
                    return "service isn't working"
            except Exception:
                AddNotification(user_id, stock_name)
            return "added"
        elif raw_message[0] == '-':
            try:
                message[1] = float(message[1].replace(',','.'))
                DropNotification(user_id, stock_name, False, message[1])
            except Exception:
                DropNotification(user_id, stock_name, True)
            return "droped"
        else: # TODO: CREATE short information
            try:
                curr_value = float(client.get(stock_name+"_curr").decode())
                return f"Акция {stock_name}\nТекущая цена: {curr_value} руб"
            except Exception:
                return "service isn't working"
    return "error msg"
