# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple
import sqlite3
import requests
import logging
import pandas as pd
import apimoex
from dateutil.relativedelta import relativedelta
import datetime

# Configure logging
logger = logging.getLogger('dbQueries')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'
conn = sqlite3.connect('sqlite_python.db')
cursor = conn.cursor()

def CreateDB():
    try:
        sqlite_connection = sqlite3.connect('sqlite_python.db')
        sqlite_create_table_users = '''CREATE TABLE users (
	        			telegram_id INTEGER PRIMARY KEY);'''
        sqlite_create_table_stocks = '''CREATE TABLE stocks (stock_name VARCHAR(8) PRIMARY KEY);'''


        sqlite_create_table_user_notifies = '''CREATE TABLE user_notifies (
		        		id INTEGER PRIMARY KEY AUTOINCREMENT,
			        	stock_name VARCHAR(8) REFERENCES stocks (stock_name),
				        telegram_id INTEGER REFERENCES users (telegram_id),
				        target_value INTEGER,
                        notify_time INTEGER);'''

        cursor = sqlite_connection.cursor()
        cursor.execute(sqlite_create_table_stocks)
        cursor.execute(sqlite_create_table_users)
        cursor.execute(sqlite_create_table_user_notifies)
        sqlite_connection.commit()
        print("ok")

        cursor.close()

    except sqlite3.Error as error:
        print("Error sqlite", error)
    finally:
        if (sqlite_connection):
            sqlite_connection.close()
            print("Connection closed")

def AddUser(telegram_id: int):
    try:
        cursor.execute('INSERT INTO users (telegram_id) VALUES ({0});'.format(telegram_id))
        conn.commit()
        logger.info("Added new user!")
    except sqlite3.Error as err:
        logger.info("This user is exist!")

def AddStock(stock_name: str):
    cursor.execute('INSERT INTO stocks (stock_name) VALUES (\'{0}\');'.format(stock_name))
    conn.commit()

def AddNotification(telegram_id: int, stock_name: str, target_value=0, notify_time=0):
    cursor.execute('INSERT INTO user_notifies (stock_name, telegram_id, target_value, notify_time) VALUES (\'{0}\', {1}, {2}, {3});'.format(stock_name, telegram_id, target_value, notify_time))
    conn.commit()

def DropNotification(telegram_id: int, stock_name: str):
    cursor.execute('DELETE FROM user_notifies WHERE stock_name = \'{0}\' AND telegram_id = {1};'.format(stock_name, telegram_id))
    conn.commit()

def DropAllNotification(telegram_id: int):
    cursor.execute('DELETE FROM user_notifies WHERE telegram_id = {0};'.format(telegram_id))
    conn.commit()

def DropUser(telegram_id: int):
    DropAllNotification(telegram_id)
    cursor.execute('DELETE FROM users WHERE telegram_id = {0};'.format(telegram_id))
    conn.commit()

### initiate DB
if __name__ == '__main__':
    r = requests.get(url)
    r.encoding = 'utf-8'
    j = r.json()
    CreateDB()
    start = (datetime.date.today() - relativedelta(months=1)).strftime('%Y-%m-%d')
    with requests.Session() as session:
        for i in j['marketdata']['data']:
            if i[1] != None:
                last_data = pd.DataFrame(
                    apimoex.get_board_candles(session, security=i[0], interval=24, columns=("begin", "value"),
                                              start=start))
                if last_data['value'].min() > 10000000:
                    AddStock(i[0])


def insert(table: str, column_values: Dict):
    columns = ', '.join( column_values.keys() )
    values = [tuple(column_values.values())]
    placeholders = ", ".join( "?" * len(column_values.keys()) )
    cursor.executemany(
        f"INSERT INTO {table} "
        f"({columns}) "
        f"VALUES ({placeholders})",
        values)
    conn.commit()


def fetchall(table: str, columns: List[str]) -> List[Tuple]:
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result


def delete(table: str, row_id: int) -> None:
    row_id = int(row_id)
    cursor.execute(f"delete from {table} where id={row_id}")
    conn.commit()


def get_cursor():
    return 