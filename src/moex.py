import apimoex
import pandas as pd
import requests
import xmltodict
import datetime
from dateutil.relativedelta import relativedelta

class Moex:

    __url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?' \
            'iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'

    @classmethod
    def is_work_at(cls, target_date):  # TODO: CHANGE try catch for requests
        r = requests.get('https://iss.moex.com/iss/engines/stock.xml')
        dict_data = xmltodict.parse(r.content)
        target_date_str = target_date.strftime('%Y-%m-%d')
        is_work_day1 = dict_data['document']['data'][1]['rows']['row'][target_date.weekday()]['@is_work_day']
        is_work_day2 = '-1'
        for row in dict_data['document']['data'][2]['rows']['row']:
            if row['@date'] == target_date_str:
                is_work_day2 = row['@is_work_day']
                break
        return (is_work_day2 == '1') or (is_work_day1 == '1' and is_work_day2 == '-1')

    @classmethod
    def is_work_today(cls):
        return cls.is_work_at(datetime.datetime.today())

    @classmethod
    def get_last_working_day(cls):
        temp_date = datetime.datetime.today().date()
        while not cls.is_work_at(temp_date):
            temp_date -= relativedelta(days=1)
        return temp_date

    @classmethod
    def get_candle_closing_prices(cls, stock_name, interval, start):
        with requests.Session() as session:
            try:
                return pd.DataFrame(
                    apimoex.get_board_candles(session, security=stock_name, interval=interval, columns=('begin', 'close'), start=start))
            except Exception as err:
                print("Получен некорректный ответ от apimoex")
                print(err)
                return None


    @classmethod
    def get_current_stocks_prices(cls):
        r = requests.get(cls.__url)
        r.encoding = 'utf-8'
        try:
            return r.json()['marketdata']['data']
        except Exception as err:
            print("Получен некорректный ответ от API биржи")
            print(err)
            return None

    @classmethod
    def get_min_steps(cls, stocks_names):
        steps = {}
        for stock_name in stocks_names:
            try:
                step = None
                url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{stock_name}.xml"
                dict_data = xmltodict.parse(requests.get(url).content)
                rows = dict_data['document']['data'][0]['rows']['row']
                if type(rows) == list:
                    for row in rows:
                        if row['@BOARDID'] == 'TQBR':
                            step = float(row['@MINSTEP'])
                            break
                else:
                    if rows['@BOARDID'] == 'TQBR':
                        step = float(rows['@MINSTEP'])
            except Exception as err:
                print("Получен некорректный ответ от API биржи")
                print(err)
            finally:
                steps[stock_name] = step
        return steps

    """@classmethod
    def get_stocks_levels(cls, stocks_names=None):
        levels = {}
        if stocks_names is None:
            stocks_names = [elem[0] for elem in requests.get(cls.__url).json()['marketdata']['data']]
        for stock_name in stocks_names:
            try:
                level = None
                url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{stock_name}.xml"
                dict_data = xmltodict.parse(requests.get(url).content)
                rows = dict_data['document']['data'][0]['rows']['row']
                if type(rows) == list:
                    for row in rows:
                        if row['@BOARDID'] == 'TQBR':
                            level = int(row['@LISTLEVEL'])
                            break
                else:
                    if rows['@BOARDID'] == 'TQBR':
                        level = int(row['@LISTLEVEL'])
            except Exception as err:
                print("Получен некорректный ответ от API биржи")
                print(err)
            finally:
                levels[stock_name] = level
        return levels"""
