from BaseDataApi import BaseDataApi
from common import *
from config import *

base_data_api = BaseDataApi(api_key=api_key, hid=hid, all_data_path=all_data_path,
                            strategy_result_path=strategy_result_path)

start_time = datetime.datetime.now()
# ===================  记录日志  ===================
record_log(f' -->开始更新数据', send=True)
# ===================  记录日志  ===================

# # 更新单个数据
# base_data_api.update_single_data(product=product, date_time=date_time, multi_process=multi_process)
# exit()
# 更新所有API数据
# record_log(f' -->开始更新白名单数据', send=True)
# base_data_api.update_all_data(multi_process=multi_process, data_white_list=data_white_list, mode=mode, data_white_list_dict=data_white_list_dict,
#                               date_time=date_time)

# # 更新指数数据
# record_log(f' -->开始更新指数数据', send=True)
# base_data_api.update_stock_index(index_list)

# 获取策略案例
for strategy_white in strategy_white_list:
    strategy_res = base_data_api.get_strategy_result(strategy=strategy_white[0], period=strategy_white[1],
                                                     select_count=strategy_white[2])
    print(strategy_res)

print('更新完成，消耗时间：', datetime.datetime.now() - start_time)
# ===================  记录日志  ===================
record_log(f' -->更新完成，消耗时间{datetime.datetime.now() - start_time}', send=True)
# ===================  记录日志  ===================
