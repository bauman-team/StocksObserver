from dbQueries import *

stocks = fetchall('stocks', ['stock_name'])
stocks_name = [i['stock_name'] for i in stocks]

def sub_to_notifications(user_id: int, raw_message: str):
    stock = raw_message[1:].split(' ')
    if stock[0] in stocks_name:
        if len(stock) > 1 and raw_message[0] == '+':
            DropNotification(user_id, stock[0])
            try:
                stock[1] = int(stock[1])
            except Exception as err:
                return "error msg"
            try:
                stock[2] = int(stock[2])
                AddNotification(user_id, stock[0], stock[1], stock[2])
            except Exception as err:
                AddNotification(user_id, stock[0], stock[1])
            return "added"
        elif raw_message[0] == '-':
            DropNotification(user_id, stock[0])
            return "droped"
        elif raw_message[0] == '?':
            return stock[0]+" info"
    return "error msg"
