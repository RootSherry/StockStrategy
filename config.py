import json
import os

root_path = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径
print(root_path)
# json_path = root_path + '/rocket.json'  # json文件的路径
json_path = os.path.join(root_path, "rocket_plan.json")  # json文件的路径
# 葫芦ID，在rocket_plan.json文件内的hid配置，获取地址：https://www.quantclass.cn/login
# apiKey，在rocket_plan.json文件内的api_key配置，获取地址：https://www.quantclass.cn/login
with open(json_path, mode='r', encoding='utf8') as f:
    json_config = json.load(f)
    robot_api = json_config['robot_api']
    hid = json_config['hid']
    api_key = json_config['api_key']

product = 'stock-chip-distribution'  # 产品ID，详见：http://www.quantclass.cn/data/api
date_time = '2023-05-17'  # 数据日期，支持获取最近30个自然日的数据，None表示最近，获取指定日期案例：'2022-07-19'

all_data_path = os.path.join(root_path, "stock_data/数据")   # 全量数据路径
print(all_data_path)

strategy_result_path = '/root/chatgpt-on-wechat/plugins/stock/stock_data/策略'  # 策略最新结果保存路径

multi_process = True  # 是否并行

data_white_list = [ 'stock-trading-data-pro', 'stock-equity','stock-analyst-ranking','xcf-analyst-ranking',
                   'stock-ind-element-equity', 'stock-fin-data-xbx']  # 数据白名单，将需要下载的数据放在列表内，如果为空不会下载任何数据。

data_white_list_dict = {
    'stock-trading-data-pro': '股票历史全息日线数据',
    'stock-equity': 'QuantClass选股策略汇总',
    'stock-analyst-ranking': '分析师评级数据',
    'stock-ind-element-equity': '指数成分股资金曲线',
    'stock-fin-data-xbx': '邢不行财务数据',
    'xcf-analyst-ranking':'新财富历年明星分析师排行'
}
# small-market-value

strategy_white_list = [
    # 策略ID，策略周期，选股数量
    # 资金流事件策略
    ['money-flow', '3天', 3],
    # 伽利略选股策略
    ['galileo', '周', 3],
    # 小市值选股策略
    ['small-market-value', '周', 3],
    # 量价相关性选股策略
    ['price-volume-corr-stock', '周', 3],
    # 低价股选股策略
    ['low-price-stock', '周', 3],
    # 反过度自信选股策略
    ['anti-over-confidence-stock', '周', 3],
    # 科技三杰选股策略
    ['three-musketeers-new', '周', 3],
    # 笛卡尔选股策略
    ['descartes', '周', 3],
    # 哥白尼选股策略
    ['copernicus', '周', 3],
    # 资金流选股策略
    ['xbx-s-001', '周', 3],
    # 创造191选股策略
    ['rocket-quants-191', '周', 3],
    # 缩量选股策略
    ['low-volume-stock', '周', 3],
    # 流动性溢价选股策略
    ['unliquidity', '周', 3],
    # 费迪南估值选股策略
    ['Ferdinand', '周', 3],
    # 费迪南成长选股策略
    ['Ferdinand-growth', '周', 3],
    # 拿破仑事件策略
    ['Napoleon-pro', '5天', 0],
    # 俾斯麦事件策略
    ['Bismarck', '5天', 3],
]


proxies = {}  # 代理信息

index_list = ['sh000016', 'sh000300','sh000001','sh000905','sh000852']  # 需要更新的指数列表
# 正常股票sz000001, 上证指数：sh000001, 沪深300：sh000300, ETF sh510500, 中证500：sh000905, 中证1000：sh000852,上证50：sh000016,创业板指：sz399006

# 数据获取模式，共三种
# all：获取所有指定数据和上次运行抓取失败数据
# new：只获取所有指定的数据
# error：只获取上次运行抓取失败的数据
mode = 'all'
