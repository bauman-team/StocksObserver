#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dbQueries import *

stocks = fetchall('stocks', ['stock_name'])
stocks_name = [i['stock_name'] for i in stocks]

def sub_to_notifications(user_id: int, raw_message: str):
    stock = raw_message[1:].split(' ')
    if stock[0] in stocks_name:
        if len(stock) >= 1 and raw_message[0] == '+':
            DropNotification(user_id, stock[0]) # TODO: delete
            try:
                stock[1] = int(stock[1])
                AddNotification(user_id, stock[0], stock[1]) # TODO: CREATE 4 param (grow?)
            except Exception as err:
                AddNotification(user_id, stock[0])
            return "added"
        elif raw_message[0] == '-':
            DropNotification(user_id, stock[0])
            return "droped"
        elif raw_message[0] == '?': # TODO: CREATE short information
            return stock[0]+" info"
    return "error msg"
