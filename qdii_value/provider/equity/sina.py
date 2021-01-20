# Partial code from https://github.com/fasionchan/finance by Chen Yanfei


import requests
import datetime
from functools import partial
from decimal import Decimal
import os
import json


def RET_N(a): return None


# +----------+
#    search
# +----------+
SEARCH_URL = 'https://suggest3.sinajs.cn/suggest/type=%s&key=%s&name='

SEARCH_TYPES = {'11': "A 股", '12': "B 股", '13': "权证", '14': "期货", '15': "债券", '21': "开基",
                '22': "ETF", '23': "LOF", '24': "货基", '25': "QDII", '26': "封基", '31': "港股", '32': "窝轮",
                '33': "港指", '41': "美股", '42': "外期", '71': "外汇", '72': "基金", '73': "新三板", '74': "板块",
                '75': "板块", '76': "板块", '77': "板块", '78': "板块", '79': "板块", '80': "板块", '81': "债券",
                '82': "债券", '85': "期货", '86': "期货", '87': "期货", '88': "期货", '100': "指数", '101': "基金",
                '102': "指数", '103': "英股", '104': "国债", '105': "ETF", '106': "ETF", '107': "MSCI", '111': "A股",
                '120': "债券",
                }

SEARCH_FIELDS = ['name', 'type', 'code', 'code_full', 'name_cn']

SEARCH_TYPE_ID = {
    '11': lambda p: p['code_full'],
    '31': lambda p: 'hk' + p['code_full'],
    '41': lambda p: 'gb_'
}


def search(kw, types=[]):
    results = []
    raw = requests.get(SEARCH_URL % (','.join(types), kw)
                       ).text.split('"')[1].split(';')
    for line in raw:
        data = line.split(',')
        r = dict(zip(SEARCH_FIELDS, data))
        r['code_full'] = r['type'] + '#' + r['code_full']
        r['type'] = SEARCH_TYPES.get(r['type'])
        results.append(r)
    return results

# +----------+
#   realtime
# +----------+
REALTIME_URL = 'http://hq.sinajs.cn/?list=%s'

CN_STATUS = {
    '00': None,
    '01': '临停1H',
    '02': '停牌',
    '03': '停牌',
    '04': '临停',
    '05': '停1/2',
    '07': '暂停',
    '-1': '无记录',
    '-2': '未上市',
    '-3': '退市'
}

REALTIME_FIELDS = {
    '11': [('name', str), ('opening', Decimal), ('last_closing', Decimal),
           ('closing', Decimal), ('highest', Decimal), ('lowest', Decimal),
           ('buy', Decimal), ('sell', Decimal), ('volume', Decimal), ('deal', Decimal),
           ('buy1_v', Decimal), ('buy1_p', Decimal), ('buy2_v', Decimal), ('buy2_p', Decimal), 
           ('buy3_v', Decimal), ('buy3_p', Decimal), ('buy4_v', Decimal), ('buy4_p', Decimal), 
           ('buy5_v', Decimal), ('buy5_p', Decimal),
           ('sell1_v', Decimal), ('sell1_p', Decimal), ('sell2_v', Decimal), ('sell2_p', Decimal), 
           ('sell3_v', Decimal), ('sell3_p', Decimal), ('sell4_v', Decimal), ('sell4_p', Decimal), 
           ('sell5_v', Decimal), ('sell5_p', Decimal),
           ('date', str), ('time', str), ('status', CN_STATUS.get)
           ],
    '31': [('name_en', str), ('name', str), ('opening', Decimal),
           ('last_closing', Decimal), ('highest', Decimal), ('lowest', Decimal),
           ('closing', Decimal), ('delta', Decimal), ('percent', Decimal),
           ('buy', Decimal), ('sell', Decimal), ('volume', Decimal), ('deal', Decimal),
           ('pe', Decimal), ('yield_w', Decimal), ('52w_high', Decimal),
           ('52w_low', Decimal), ('date', str), ('time', str)
           ],
    '41': [('name', str), ('closing', Decimal), ('percent', Decimal), ('time', str),
           ('delta', Decimal), ('opening', Decimal), ('highest', Decimal),
           ('lowest', Decimal), ('52w_highest', Decimal), ('52w_lowest', Decimal), 
           ('volume', Decimal), ('avg_vol', Decimal), ('total_share', Decimal), 
           ('eps', str), ('pe', str), ('', RET_N), ('beta', Decimal), 
           ('dividend', str), ('income', str), ('shares', Decimal), ('', RET_N),
           ('after_hour_price', Decimal), ('after_hour_percent', Decimal),
           ('after_hour_delta', Decimal), ('after_hour_datetime', str), ('datetime', str),
           ('last_closing', Decimal), ('after_hour_volume', Decimal)
           ],
    '71': [('time', str), ('', RET_N), ('', RET_N), ('last_closing', Decimal), ('', RET_N),
           ('opening', Decimal), ('highest', Decimal), ('lowest', Decimal), ('closing', Decimal),
           ('name', str), ('', RET_N), ('', RET_N), ('', RET_N), ('market_maker', str),
           ('', RET_N), ('', RET_N), ('', RET_N), ('date', str)
           ]
}


def realtime_api(*l):
    raw = requests.get(REALTIME_URL % (','.join(l),)).text
    return [line.split('"')[1].split(',')
            for line in raw.split('\n') if line]


def parse_symbol_11(symbol): return symbol
def parse_symbol_31(symbol): return 'rt_hk%s' % (symbol.upper())
def parse_symbol_41(symbol): return 'gb_%s' % (symbol.lower())
def parse_symbol_71(symbol): return 'fx_s%s' % (symbol.lower())


def parse_symbol(symbol):
    typ, code = symbol.split('#')
    symbol = globals()[f'parse_symbol_{typ}'](code)
    return symbol, REALTIME_FIELDS[typ]


def realtime(*symbols):
    results = []
    f_symbols_pair = [parse_symbol(symbol) for symbol in symbols]
    f_symbols = [p[0] for p in f_symbols_pair]
    fmts = [p[1] for p in f_symbols_pair]
    data = realtime_api(*f_symbols)
    for symbol in zip(symbols, data, fmts):
        pairs = zip(symbol[2], symbol[1])
        kvs = [(key, cls(value)) for (key, cls), value in pairs]
        kvs.append(('code_full', symbol[0]))
        results.append(dict(kvs))
    return results


# +----------+
#    history
# +----------+
DECOMPRESSER_JS = None
HISTORY_URL_HK = 'https://finance.sina.com.cn/stock/hkstock/{}/klc_kl.js'
HISTORY_URL_CN = 'https://finance.sina.com.cn/realstock/company/{}/hisdata_klc2/klc_kl.js'
def TO_FIX_2(f): return Decimal(f).quantize(Decimal("0.00"))

# till last exchange day
def history_cnhk(url, code, limit=21):
    global DECOMPRESSER_JS, HISTORY_URL_HK
    try:
        import STPyV8
    except ImportError:
        raise Exception('需要手动安装 STPyV8 才能解析数据.')
    if not DECOMPRESSER_JS:
        with open(os.path.dirname(__file__) + '/sina_decompress.js', 'r') as js:
            DECOMPRESSER_JS = js.read()
    with STPyV8.JSContext() as ctxt:
        decompress = ctxt.eval(DECOMPRESSER_JS)
        compressed = requests.get(url.format(code)).text.split('\n')[0].split('\"')[1]
        ret = json.loads(decompress(compressed))
        return [{
            'date': i['date'],
            'open': TO_FIX_2(i['open']),
            'high': TO_FIX_2(i['high']),
            'low': TO_FIX_2(i['low']),
            'close': TO_FIX_2(i['close']),
            'volume': TO_FIX_2(i['volume']),
        } for i in ret[-limit:]]


HISTORY_URL_US = 'http://stock.finance.sina.com.cn/usstock/api/json.php/US_MinKService.getDailyK?symbol={}'
US_DAILY_CONVERT = lambda d, o, h, l, c, v, **kwargs: {
    'date': str(d),
    'open': Decimal(o),
    'high': Decimal(h),
    'low': Decimal(l),
    'close': Decimal(c),
    'volume': Decimal(v),
}

# 139 days
def history_us(code, limit=21):
    return [US_DAILY_CONVERT(**data) for data in requests.get(HISTORY_URL_US.format(code)).json()[-limit:]]


HISTORY_URL_FX = 'https://vip.stock.finance.sina.com.cn/forex/api/jsonp.php/%20/NewForexService.getDayKLine?symbol={}'
FX_DAILY_CONVERT = lambda d, o, l, h, c, *args: {
    'date': str(d),
    'open': Decimal(o),
    'low': Decimal(l),
    'high': Decimal(h),
    'close': Decimal(c),
}


def history_fx(code, limit=21):
    return [FX_DAILY_CONVERT(*data.split(',')) for data in requests.get(HISTORY_URL_FX.format(code)).text.split('\n')[1][3:-3].split('|')][-limit:]


HISTORY_PROCESSER = {
    '11': partial(history_cnhk, HISTORY_URL_CN),
    '31': partial(history_cnhk, HISTORY_URL_HK),
    '41': history_us,
    '71': history_fx,
}


def history(symbol, **kwargs):
    typ, code = symbol.split('#')
    return HISTORY_PROCESSER[typ](code, **kwargs)

# +----------+
#     test
# +----------+

def test():
    # print(search('腾讯'))
    # print(search('平安'))
    # print(search('msft'))
    # print(search('00909'))
    # print(search('usdcnh'))

    print(realtime('31#00358', '11#sz000002', '41#bili', '71#usdcnh'))
    print(history('11#sh688111'))
    print(history('71#usdcnh'))


if __name__ == '__main__':
    test()
