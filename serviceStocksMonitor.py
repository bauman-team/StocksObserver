from dbQueries import *
import time
import requests
from pymemcache.client import base

stocks = fetchall('stocks', ['stock_name'])
stocks_name = [i['stock_name'] for i in stocks]
#url = 'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST'



def main():
    client = base.Client(('127.0.0.1', 11211)) # TODO: add yml config
    while True:
        r = requests.get(url)
        r.encoding = 'utf-8'
        j = r.json()
        #parsed_string = json.loads(j)
        for i in j['marketdata']['data']:
            if i[0] in stocks_name:
                client.set(i[0], i[1])
        time.sleep(60)
    return 

if __name__ == '__main__':
    main()