# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins.stock.common import *
from common.log import logger
from plugins.stock.config import *
from plugins import *
from plugins.stock.BaseDataApi import BaseDataApi

base_data_api = BaseDataApi(api_key=api_key, hid=hid, all_data_path=all_data_path,
                            strategy_result_path=strategy_result_path)

@plugins.register(
    name="StockStrategy",
    desire_priority=0,
    namecn="股票策略",
    desc="一个插件用于获取特定股票策略的结果",
    version="1.0",
    author="Root",
)
class StockStrategy(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.base_data_api = BaseDataApi(api_key=api_key, hid=hid, all_data_path=all_data_path,
                                         strategy_result_path=strategy_result_path)
        logger.info("[stock_strategy] inited")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        strategy_name_dict = {
            '低价小市值': 'low-price-small-market-value',
            '量价相关性': 'price-volume-corr-stock',
            '小市值': 'small-market-value',
            '伽利略': 'galileo',
            '财务基本面小市值': 'small-market-value-and-fin',
            '反过度自信': 'anti-over-confidence-stock',
            '费迪南w': 'Ferdinand-WangYang',
            '费迪南x': 'Ferdinand-XiaoXiaoZhi',
            '低价股': 'low-price-stock',
            # '星边系选股001': 'xbx-s-001',
            '费迪南': 'Ferdinand',
            '费迪南Q': 'Ferdinand-QuanQiuRen',
            '中证1000小市值': 'small-market-value-limit',
            '费迪南成长': 'Ferdinand-growth',
            '哥白尼': 'copernicus',
            '流动性溢价': 'unliquidity',
            '北上七侠': 'seven-knights',
            '低估值高分红': 'low-valuation-high-dividend',
            '笛卡尔': 'descartes',
            '皮尔逊': 'pearson',
            '低估值': 'low-valuation',
            '缩量': 'low-volume-stock',
            '创造191': 'rocket-quants-191',
            '筹码分布': 'chip-distribution',
            '小市值基本面过滤': 'small-market-value-filter',
            '量价小市值': 'small-market-value-price-volume-corr',
            '科技三杰': 'three-musketeers-new',
            '资金流': 'money-flow',
            '散户反买': 'retail-investors',
            '萨拉丁': 'Saladin',
            '筹码集中度': 'chip-concentration',
            '拿破仑': 'Napoleon-pro',
            '俾斯麦': 'Bismarck',
            '北上高频': 'event-nf-flow',
            '北上七侠事件': 'seven-knights-event',
            '资金流z': 'money-flow-zhen',
            '资金流t': 'money-flow-TianXingZhe',
            '资金流q': 'money-flow-QiGuai',
            '萨拉丁d': 'DingGuoQing',
            '萨拉丁h': 'HuangJinMieMieYang',
            '萨拉丁l': 'lzhh',
            '香农': 'shannon'
        }


        content = e_context["context"].content
        logger.debug("[stock_strategy] on_handle_context. content: %s" % content)
        clist = content.split(maxsplit=3)  # 分割为4个部分: $A, 策略名, 持仓周期, 选股数量
    
        if clist[0] == "$A":
            if len(clist) == 4:
                strategy_name, period, select_count = clist[1], clist[2], clist[3]
                if strategy_name in strategy_name_dict:  # 检查策略名是否在字典中
                    strategy_name = strategy_name_dict[strategy_name]  # 如果在字典中，将策略名更新为字典中的值
                else:
                    message = "策略不存在，请检查"  # 如果不在字典中，返回错误消息
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = message
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                    return  # 退出函数，不再继续处理
                strategy_result = self.base_data_api.get_strategy_result(strategy_name, period, select_count)
                print(strategy_result)
                if isinstance(strategy_result, dict) and strategy_result.get('code') == 200:
                    message = self.format_result(strategy_result)
                else:
                    message = strategy_result  # 直接将 strategy_result 赋值给 message
            else:
                message = "格式错误，请输入 $A 策略名 持仓周期 选股数量"
        else:
            return  # 如果输入不以 "$A" 开头，直接返回，不做任何处理
    
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = message
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

    def format_result(self, result):
        # 格式化结果为易读的格式
        message = f"选股时间: {result['select_time']}\n"
        message += f"购买时间: {result['buy_time']}\n"
        message += "选股结果:\n"
        for stock in result['result']:
            message += f"{stock['name']} ({stock['symbol']})\n"
        return message

    def get_help_text(self, verbose=False, **kwargs):
        short_help_text = " 发送特定指令获取最新的策略选股结果。"

        if not verbose:
            return short_help_text
        help_text = (
            "输入$A 策略名 持仓周期 选股数量，我会为你提供相应策略的选股结果\n\n"
            "示例：$A 哥白尼 周 3，$A 资金流 2天 2\n"
            "选股策略：周期第一天开盘买入，最后一天收盘卖出（比如周一-周五），由因子筛选和排序选出\n"
            "事件策略：资金分为n份，持仓n日，每份第一日开盘买入，第n日收盘卖出，每天都有更新，由特定事件触发选出\n\n"
            "选股策略支持：换仓周期：周、月、自然月，选股数量：3、10、30\n"
            "事件策略支持：换仓周期：2天、5天、10天，选股数量：2、5、10\n\n"
            "选股策略名列表（不包含括号内内容）：\n"
            "香农（仅自然月）、伽利略、小市值基本面过滤、财务基本面小市值、量价小市值、低价小市值、小市值、反过度自信、低价股、"
            "费迪南、费迪南Q、费迪南w、费迪南x、中证1000小市值、费迪南成长、哥白尼、流动性溢价、北上七侠、低估值高分红、笛卡尔、"
            "皮尔逊、低估值、缩量、创造191、筹码分布、量价相关性、科技三杰\n\n"
            "事件策略名列表：\n"
            "资金流t、资金流q、资金流z、资金流、散户反买、萨拉丁、筹码集中度、拿破仑、俾斯麦、北上高频、北上七侠、"
            "萨拉丁d、萨拉丁h、萨拉丁l\n"
        )
        return help_text
