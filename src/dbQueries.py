#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple
import psycopg2
import requests
import logging
import pandas as pd
import apimoex
from dateutil.relativedelta import relativedelta
import datetime
import os

DB_USER = os.environ['DBUSER']
DB_PASSWORD = os.environ['DBPASSWORD']

# Configure logging
logger = logging.getLogger('dbQueries')
logger.setLevel(logging.INFO)
fileLogHandler = logging.FileHandler(filename='../info.log', mode='a')
fileLogHandler.setLevel(logging.INFO)
logger.addHandler(fileLogHandler)
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s: %(message)s')
fileLogHandler.setFormatter(formatter)

url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'
conn = psycopg2.connect("dbname='stocks_observer_bot_db' user='{0}' password='{1}' sslmode='disable'".format(DB_USER, DB_PASSWORD))
cursor = conn.cursor()

def CreateDB():
    try:
        postgresql_connection = psycopg2.connect("dbname='stocks_observer_bot_db' user='{0}' password='{1}' sslmode='disable'".format(DB_USER, DB_PASSWORD))
        postgresql_create_table_users = '''CREATE TABLE users (
                                telegram_id BIGINT NOT NULL PRIMARY KEY,
                                subscription_activate_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                subscription_expires_in INTEGER NOT NULL DEFAULT 0);'''

        postgresql_create_table_stocks = '''CREATE TABLE stocks (
                                    stock_name VARCHAR(8) NOT NULL PRIMARY KEY,
                                    description VARCHAR(5000));'''

        postgresql_create_table_user_notifications = '''CREATE TABLE user_notifications (
		        		                    id BIGSERIAL NOT NULL PRIMARY KEY,
			        	                    stock_name VARCHAR(8) NOT NULL REFERENCES stocks (stock_name),
				                            telegram_id BIGINT NOT NULL REFERENCES users (telegram_id),
				                            target_value DOUBLE PRECISION NOT NULL DEFAULT 0,
                                            target_grow BOOLEAN NOT NULL);'''
        # TODO: CREATE add trigger for unique pair user-value
        # TODO: CREATE table (user_id, token_paid_accept)

        cursor = postgresql_connection.cursor()
        cursor.execute(postgresql_create_table_stocks)
        cursor.execute(postgresql_create_table_users)
        cursor.execute(postgresql_create_table_user_notifications)
        postgresql_connection.commit()
        print("ok")

        cursor.close()

    except psycopg2.Error as error:
        print("Error sqlite", error)
    finally:
        if (postgresql_connection):
            postgresql_connection.close()
            print("Connection closed")

def AddUser(telegram_id: int):
    try:
        cursor.execute('INSERT INTO users (telegram_id) VALUES ({0})'.format(telegram_id))
        logger.info("Added new user!")
    except psycopg2.Error as err:
        logger.info("This user is exist!")
    finally:
        conn.commit()

def AddStock(stock_name: str):
    try:
        print('INSERT INTO stocks (stock_name) VALUES (\'{0}\')'.format(stock_name))
        cursor.execute('INSERT INTO stocks (stock_name) VALUES (\'{0}\')'.format(stock_name))
    finally:
        conn.commit()
        update_stocks_names_list()
        print(stocks_names)

def AddNotification(telegram_id: int, stock_name: str, target_value=0., target_grow=False):
    cursor.execute("INSERT INTO user_notifications (stock_name, telegram_id, target_value, target_grow) VALUES ('{0}', {1}, {2}, {3})".format(stock_name, telegram_id, target_value, target_grow))
    conn.commit()

def DropNotification(telegram_id: int, stock_name: str, drop_all=False, target_value=0.):
    if drop_all:
        cursor.execute("DELETE FROM user_notifications WHERE stock_name = '{0}' AND telegram_id = {1};".format(stock_name, telegram_id))
    else:
        cursor.execute("DELETE FROM user_notifications WHERE stock_name = '{0}' AND telegram_id = {1} AND target_value = {2}".format(stock_name, telegram_id, target_value))
    conn.commit()

def DropAllNotification(telegram_id: int):
    cursor.execute('DELETE FROM user_notifications WHERE telegram_id = {0}'.format(telegram_id))
    conn.commit()

def DropUser(telegram_id: int):
    DropAllNotification(telegram_id)
    cursor.execute('DELETE FROM users WHERE telegram_id = {0}'.format(telegram_id))
    conn.commit()

def DropStock(stock_name: str):
    cursor.execute(f"DELETE FROM user_notifications WHERE stock_name = '{stock_name}'")
    conn.commit()
    cursor.execute(f"DELETE FROM stocks WHERE stock_name = '{stock_name}'")
    conn.commit()
    update_stocks_names_list()

### initiate DB
if __name__ == '__main__':
    """r = requests.get(url)
    r.encoding = 'utf-8'
    j = r.json()
    CreateDB() 
    DropStocks()"""
    
    with open("../list_of_monitoring_stocks.txt", "r") as f:  # TODO: CHANGE move to Stocks monitor
        raw_text = f.read()
        for i in raw_text.split('\n'):
            if i != '':
                try:
                    AddStock(i)
                except Exception:
                    continue

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


def fetchall_unique(table: str, columns: List[str]) -> List[Tuple]:
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT DISTINCT {columns_joined} FROM {table}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result


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
    cursor.execute(f"DELETE FROM {table} WHERE id={row_id}")
    conn.commit()


def update_stocks_names_list():
    global stocks_names 
    stocks_names = [i['stock_name'] for i in fetchall('stocks', ['stock_name'])]


def get_cursor():
    return


# Initialize stocks list
try:
    update_stocks_names_list()
except Exception:
    logger.fatal("Stocks list is not initialized!")
    exit(1)
logger.info("Stocks list is initialized.")
