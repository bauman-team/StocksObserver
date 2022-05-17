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
        return r.json()['marketdata']['data']