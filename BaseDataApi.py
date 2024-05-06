import os
import platform
import re
import shutil
import tarfile
import time
import traceback
import zipfile
from multiprocessing import cpu_count
from random import randint

import pandas as pd
import py7zr
import rarfile
from joblib import Parallel, delayed
from retrying import retry
from tqdm import tqdm

from plugins.StockStrategy.common import *


class BaseDataApi(object):

    def __init__(self, hid: str, api_key: str, all_data_path: str, strategy_result_path: str):
        """
        构建函数，实例化对象的时候传入的参数
        :param hid: 个人中心的uuid
        :param api_key: 人中心生成的apikey
        :param all_data_path: 全量数据保存的路径
        :param up_data_info: 更新数据的配置
        """
        self.url = 'https://api.quantclass.cn/api/data/'  # 获取数据的url
        self.api_key = api_key  # 个人中心生成的apikey
        self.hid = hid  # 个人中心的hid
        # 如果传入路径为空，默认保存在当前目录下
        if not all_data_path:
            all_data_path = './数据更新'
        self.all_data_path = all_data_path  # 全量数据保存的路径
        # 如果传入路径为空，默认保存在当前目录下
        if not strategy_result_path:
            strategy_result_path = './策略结果'
        self.strategy_result_path = strategy_result_path  # 最新策略结果保存路径

        # 定义请求头
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
            'content-type': 'application/json',
            'api-key': self.api_key
        }

        # 更新数据的配置
        self.up_data_info = self.request_data('GET', 'https://api.quantclass.cn/api/data/get-data-info').json()

        # 定义error的数据
        self.last_error_df = pd.DataFrame(columns=['product', 'date_time', 'error'])
        # 定义error的保存路径
        self.error_path = os.path.join(root_path, 'error.csv')
        if os.path.exists(self.error_path):  # 判断error路径是否存在
            # 如果存在直接读取数据
            self.last_error_df = pd.read_csv(self.error_path, encoding='gbk').drop_duplicates(
                subset=['product', 'date_time'])

        record_log(f'{"=" * 40}初始化成功{"=" * 40}')

    @retry(stop_max_attempt_number=5)
    def zip_uncompress(self, path, save_path):
        """
        解压zip
        :param path:
        :param save_path:
        :return:
        """
        f = zipfile.ZipFile(path)
        f.extractall(save_path)
        f.close()
        pass

    @retry(stop_max_attempt_number=5)
    def tar_uncompress(self, path, save_path):
        """
        解压tar格式
        :param path:
        :return:
        """
        f = tarfile.open(path)
        f.extractall(save_path)
        f.close()
        pass

    @retry(stop_max_attempt_number=5)
    def rar_uncompress(self, path, save_path):
        """
        :param path:
        :return:
        """
        # rar
        f = rarfile.RarFile(path)  # 待解压文件
        f.extractall(save_path)  # 解压指定文件路径
        f.close()
        pass

    @retry(stop_max_attempt_number=5)
    def uncompress(self, path, save_path):
        """
        解压7z
        :param path:
        :return:
        """
        # 7z
        f = py7zr.SevenZipFile(path, 'r')
        f.extractall(path=save_path)
        f.close()
        pass

    @retry(stop_max_attempt_number=5)
    def request_data(self, method, url, **kwargs) -> requests.models.Response:
        """
        请求数据
        :param method: 请求方法
        :param url: 请求的url
        :return:
        """

        res = requests.request(method=method, url=url, headers=self.headers, proxies=proxies, timeout=5, **kwargs)
        if res.status_code == 200:
            return res
        elif res.status_code == 404:
            if 'upyun' in url:
                # ===================  记录日志  ===================
                record_log(f'数据链接不存在', send=True, robot_type='waring', log_type='waring')
                # ===================  记录日志  ===================
                print('数据链接不存在')
            else:
                # ===================  记录日志  ===================
                record_log(f'请求参数错误', send=True, robot_type='waring', log_type='waring')
                # ===================  记录日志  ===================
                print('参数错误')
        elif res.status_code == 403:
            # ===================  记录日志  ===================
            record_log(f'无下载权限，请检查自己的下载次数与api-key', send=True, robot_type='waring', log_type='waring')
            # ===================  记录日志  ===================
            print('无下载权限，请检查自己的下载次数与api-key')
        elif res.status_code == 401:
            # ===================  记录日志  ===================
            record_log('超出当日下载次数', send=True, robot_type='waring', log_type='waring')
            # ===================  记录日志  ===================
            print('超出当日下载次数')
        elif res.status_code == 400:
            # ===================  记录日志  ===================
            record_log(f'下载时间超出限制', send=True, robot_type='waring', log_type='waring')
            # ===================  记录日志  ===================
            print('下载时间超出限制')
        elif res.status_code == 500:
            # ===================  记录日志  ===================
            record_log(f'服务器内部出现问题，请稍后尝试，{res.text}', send=True, robot_type='waring', log_type='waring')
            # ===================  记录日志  ===================
            print('服务器内部出现问题，请稍后尝试')
        else:
            # ===================  记录日志  ===================
            record_log(f'获取数据失败', send=True, robot_type='waring', log_type='waring')
            # ===================  记录日志  ===================
            print('获取数据失败')
        return res

    # region 文件交互
    @staticmethod
    def get_code_list_in_one_dir(path: str, end_with: str = 'csv') -> list:
        """
        从指定文件夹下，导入所有数据
        :param path:
        :param end_with:
        :return:
        """
        symbol_list = []

        # 系统自带函数os.walk，用于遍历文件夹中的所有文件
        for root, dirs, files in os.walk(path):
            if files:  # 当files不为空的时候
                for f in files:
                    if f.endswith(end_with):
                        symbol_list.append(os.path.join(root, f))

        return sorted(symbol_list)

    @staticmethod
    def judgment_system(data):
        """
        为了贴合Linux定时任务，当系统为Linux时不进行进度条显示
        :param data:
        :return:
        """
        if platform.system() == 'Linux':
            return data
        else:
            return tqdm(data)

    def read_file(self, path, product):
        """
        读取数据返回一个df
        :param path:
        :param product:
        :return:
        """
        # 获取文件类型，即.后面所有的字段
        file_type = path.split('.')[-1]
        all_df = pd.DataFrame()
        # 判断文件是否存在
        if os.path.exists(path):
            if file_type == 'csv':
                try:
                    all_df = pd.read_csv(path, encoding='gbk', skiprows=1,
                                         parse_dates=self.up_data_info[product]['parse_dates'])
                except:
                    all_df = pd.read_csv(path, encoding='gbk',
                                         parse_dates=self.up_data_info[product]['parse_dates'])

            elif file_type == 'pkl':
                all_df = pd.read_pickle(path)
            else:
                record_log('未匹配到读取代码')

        return all_df

    def concat_data(self, df_list, product):
        """
        把增量数据和全量数据合并
        :param df_list:
        :param product:
        :return:
        """
        # 把多个数据合并
        df = pd.concat(df_list, ignore_index=True)

        # 根据配置去重
        df.drop_duplicates(self.up_data_info[product]['duplicate_removal_column'], inplace=True,
                           keep=self.up_data_info[product]['keep'])
        # 排序
        df.sort_values(by=self.up_data_info[product]['duplicate_removal_column'], inplace=True)
        # 重新设置index
        df.reset_index(inplace=True, drop=True)

        return df

    def get_down_load_link(self, product, date_time):
        """
        根据指定的产品ID与时间构建下载链接
        :param product: 产品ID
        :param date_time: 数据时间
        :return:
        """
        return self.request_data(method='GET',
                                 url=self.url + f'/get-download-link/{product}-daily/{date_time}?uuid={self.hid}')

    def get_latest_data_time(self, product):
        """
        根据产品ID构建数据最新的日期的链接
        :param product:
        :return:
        """
        res = self.request_data(method='GET', url=self.url + f'fetch/{product}-daily/latest?uuid={self.hid}').text
        if 'HTML' in res:
            record_log('获取最新数据日期出错，请检查配置', send=True, robot_type='waring')
            return []
        return res.split(',')

    def save_file(self, file_url, file_name, path, save_path):
        """
        通过数据链接下载数据
        :param file_url:
        :param file_name:
        :param path:
        :param save_path:
        :return:
        """
        # 请求数据
        res = self.request_data(method='GET', url=file_url, stream=True)
        if res.status_code != 200:
            return False
        # 构建数据保存路径
        file_path = os.path.join(path, file_name)
        # 分块保存，避免某个文件太大导致内存溢出
        with open(file_path, mode='wb') as f:
            for chunk in res.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        # 判断文件类型进行不同的操作
        if file_name.split('.')[-1] == 'csv':
            shutil.copy(file_path, os.path.join(save_path, file_name))
        elif file_name.split('.')[-1] == 'zip':
            self.zip_uncompress(file_path, save_path)
        return True

    def update_by_group(self, file_path, all_data_path, product, multi_process=False, **kwargs):
        """
        遍历数据的每个group进行处理
        :param file_path:
        :param all_data_path:
        :param product:
        :param multi_process:
        :return:
        """

        # 更新数据的主函数，封装为函数便于并行
        def up(df_, file_name):
            # 根据股票代码拼接全量数据路径
            all_data_path_ = os.path.join(all_data_path, file_name + '.csv')
            # 获取路径
            mk_dir = all_data_path_ if not all_data_path_.endswith('csv') else os.path.split(all_data_path_)[0]
            if not os.path.exists(mk_dir):  # 判断路径是否存在
                # 如果路径不存在即创建，并设置全量的数据为空的
                os.makedirs(mk_dir)
                all_df = pd.DataFrame()
            else:
                # 读取数据
                all_df = self.read_file(all_data_path_, product)
            # 把全量数据与增量数据合并
            to_file_df = self.concat_data([all_df, df_], product)
            record_log(
                f'正在更新{file_name}的{product}数据，数据行数：{df_.shape[0]}行（增）、{all_df.shape[0]}行(全)、{to_file_df.shape[0]}行(新)，数据列数：{df_.shape[1]}列（增）、{all_df.shape[1]}列(全)、{to_file_df.shape[1]}列(新)',
                log_type='info')
            # 写出
            to_file_df.columns = pd.MultiIndex.from_tuples(
                zip(['数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx297'] + [''] * (
                        to_file_df.shape[1] - 1), to_file_df.columns))
            to_file_df.to_csv(all_data_path_, index=False, encoding='gbk')

        # 因为数据为一个csv，所以需要先读取逐行处理
        df = self.read_file(file_path, product)
        group = df.groupby(self.up_data_info[product]['group'])

        # 获取遍历的对象
        traverse_object = self.judgment_system(group.groups.values())

        # 开始并行或者串行读取所有增量数据
        if multi_process:  # 并行
            Parallel(n_jobs=max(cpu_count() - 1, 1))(
                delayed(up)(pd.DataFrame(df.loc[i]), df.loc[i[0], self.up_data_info[product]['group']]) for
                i in traverse_object)
        else:  # 串行
            for i in traverse_object:
                up(pd.DataFrame(df.loc[i]), df.loc[i[0], self.up_data_info[product]['group']])

    def update_by_file(self, all_data_path, product, multi_process=False, **kwargs):
        """
        遍历文件内的数据，每一个文件的处理
        :param all_data_path:
        :param product:
        :param multi_process:
        :param kwargs:
        :return:
        """

        # 更新数据的主函数，封装为函数便于并行
        def up(new_path, _save_path, all_data_path_):
            # 处理文件路径
            _save_path = _save_path.replace('\\', '/')
            new_path = new_path.replace('\\', '/')
            all_data_path_ = os.path.join(all_data_path_, re.findall('%s(.*)' % _save_path, new_path)[0][1:])
            if not os.path.exists(all_data_path_):  # 判断文件夹是否存在
                mk_dir = all_data_path_ if not all_data_path_.endswith('csv') else os.path.split(all_data_path_)[0]
                if not os.path.exists(mk_dir):
                    os.makedirs(mk_dir)
                record_log(f'{product}数据复制至{all_data_path_}', log_type='info')
                shutil.move(new_path, all_data_path_)
            else:
                all_df = self.read_file(all_data_path_, product)
                new_df = pd.DataFrame(self.read_file(new_path, product))

                df = self.concat_data([all_df, new_df], product)
                record_log(
                    f'正在更新{new_path}的{product}数据，数据行数：{new_df.shape[0]}行（增）、{all_df.shape[0]}行(全)、{df.shape[0]}行(新)，数据列数：{new_df.shape[1]}列（增）、{all_df.shape[1]}列(全)、{df.shape[1]}列(新)',
                    log_type='info')
                # 写出
                df.columns = pd.MultiIndex.from_tuples(
                    zip(['数据由邢不行整理，对数据字段有疑问的，可以直接微信私信邢不行，微信号：xbx297'] + [''] * (
                            df.shape[1] - 1), df.columns))
                df.to_csv(all_data_path_, index=False, encoding='gbk')

        # 获取所有增量数据
        save_path = kwargs['save_path']
        file_path_list = self.get_code_list_in_one_dir(save_path)

        # 获取遍历的对象
        traverse_object = self.judgment_system(file_path_list)

        # 开始并行或者串行读取所有增量数据
        if multi_process:  # 并行
            Parallel(n_jobs=max(cpu_count() - 2, 1))(
                delayed(up)(file_path, save_path, all_data_path) for file_path in
                traverse_object)
        else:  # 串行
            for file_path in traverse_object:
                up(file_path, save_path, all_data_path)

    @staticmethod
    def delete_history_data(path):
        """
        只保留7天内的数据，如果数据日期超过七天就进行删除
        :param path:
        :return:
        """
        now_time = datetime.datetime.now()
        file_list = os.listdir(path)
        for file in file_list:
            file_time = pd.to_datetime(file.split('.')[0])
            if file_time < now_time - datetime.timedelta(days=7):
                os.remove(os.path.join(path, file))

    def update_single_data(self, product, date_time=None, multi_process=False,
                           **kwargs) -> pd.DataFrame:
        """
        数据更新类主函数
        :param product: 产品ID
        :param date_time: 获取时间，如果是空自动获取最新的日期
        :param multi_process: 是否并行
        :return:
        """
        if not date_time:
            date_time = pd.DataFrame(self.get_latest_data_time(product))[0].max()

        ret_dict = {
            'product': [product],
            'date_time': [date_time],
            'error': [False]
        }

        if pd.to_datetime(date_time) <= (datetime.datetime.now() - datetime.timedelta(days=30)):
            print('所下载数据超过30天，直接跳过')
            record_log(f'下载数据：{product}，下载时间：{date_time}，所下载数据日期超过30天，直接跳过', log_type='info',
                       send=True,
                       robot_type='info')
            return pd.DataFrame(ret_dict)

        # 根据产品ID拼接全量数据路径
        all_data_path = os.path.join(self.all_data_path, product)
        if not os.path.exists(all_data_path):  # 判断文件夹是否存在
            os.mkdir(all_data_path)  # 不存在则创建
        path = os.path.join(self.all_data_path, 'temp', product)
        if not os.path.exists(path):  # 判断文件夹是否存在
            os.makedirs(path)  # 不存在则创建
        save_path = os.path.join(self.all_data_path, 'xbx_temporary_data', product)
        if not os.path.exists(save_path):  # 判断文件夹是否存在
            os.makedirs(save_path)  # 不存在则创建

        # ===================  记录日志  ===================
        record_log(f'开始获取{product}数据，日期为{date_time}')
        # ===================  记录日志  ===================

        get_file_url_res = self.get_down_load_link(product=product, date_time=date_time)
        if get_file_url_res.status_code != 200:
            record_log(f'{product}获取下载链接失败，返回状态码：{get_file_url_res.status_code}', send=True,
                       robot_type='waring')
            print(f'{product}获取下载链接失败，返回状态码：{get_file_url_res.status_code}')
            ret_dict['error'] = True
            return pd.DataFrame(ret_dict)
        file_url = get_file_url_res.text

        file_name = re.findall('%s.*?\/(.*?)\?' % product, file_url)[0]

        # ===================  记录日志  ===================
        record_log(f'开始保存{product}数据')
        # ===================  记录日志  ===================

        # 保存文件
        judge = self.save_file(file_url=file_url, file_name=file_name, path=path, save_path=save_path)
        if not judge:
            record_log(f'{product}保存失败', send=True, robot_type='waring')
            print(f'{product}保存失败，请检查下载链接')
            ret_dict['error'] = True
            return pd.DataFrame(ret_dict)
        print(f'{product}({date_time})保存成功')
        # 调用指定的代码对增量数据进行处理
        eval('self.' + self.up_data_info[product]['fun'])(all_data_path=all_data_path, product=product,
                                                          file_path=os.path.join(save_path, file_name),
                                                          save_path=save_path, multi_process=multi_process)
        shutil.rmtree(save_path)
        # ===================  记录日志  ===================
        record_log(f'{product}({date_time})数据写入完成')
        # ===================  记录日志  ===================

        # 判断历史下载文件是否还需要保留
        self.delete_history_data(path)
        return pd.DataFrame(ret_dict)

    def update_all_data(self, data_white_list, data_white_list_dict , mode='all', **kwargs):
        """
        批量更新数据
        :param data_white_list: 指定下载的数据
        :param mode:    指定下载模式
        :param kwargs:
        :return:
        """
        df_list = []

        # 如果下载模式是all或者new下载增量的数据
        if mode in ['all', 'new']:
            for product in data_white_list:
                record_log("开始更新:"+data_white_list_dict[product], send=True)
                if kwargs['date_time'] and (type(kwargs['date_time']) != 'list'):
                    date_time_list = kwargs['date_time'].split(',')
                else:
                    date_time_list = self.get_latest_data_time(product)

                for date_time in date_time_list:
                    condition = self.last_error_df['product'] == product
                    condition &= self.last_error_df['date_time'] == date_time
                    try:
                        date_time_ = kwargs['date_time']
                        del kwargs['date_time']
                        df = self.update_single_data(product, date_time=date_time, **kwargs)

                        df_list.append(df)
                    except Exception as e:
                        print(traceback.format_exc())
                        # ===================  记录日志  ===================
                        record_log(f'发生报错，错误信息为{e}，报错输出为{traceback.format_exc()}', send=True,
                                   robot_type='waring')
                        # ===================  记录日志  ===================
                        ret_dict = {
                            'product': [product],
                            'date_time': [date_time],
                            'error': [True]
                        }
                        df_list.append(pd.DataFrame(ret_dict))
                    kwargs['date_time'] = date_time_
        now_error_df = pd.DataFrame(columns=['product', 'date_time', 'error'])
        if df_list:
            now_error_df = pd.concat(df_list, ignore_index=True)
        now_error_df['code'] = 'now'
        self.last_error_df['code'] = 'last'
        error_df = pd.concat([now_error_df, self.last_error_df], ignore_index=True).drop_duplicates(
            subset=['product', 'date_time'], keep='first')
        # 如果下载模式是all或者error下载上次下载报错的数据
        if mode in ['all', 'error']:
            last_error_df = error_df[error_df['error'] & (error_df['code'] == 'last')]
            for i in last_error_df.index:
                product = last_error_df.loc[i]['product']
                date_time = last_error_df.loc[i]['date_time']
                kwargs['date_time'] = date_time
                condition = error_df['product'] == product
                condition &= error_df['date_time'] == date_time
                try:
                    code = self.update_single_data(product, **kwargs)
                    error_df.loc[condition, 'error'] = code.iloc[0]['error']
                except Exception as e:
                    print(traceback.format_exc())
                    # ===================  记录日志  ===================
                    record_log(f'发生报错，错误信息为{e}，报错输出为{traceback.format_exc()}', send=True,
                               robot_type='waring',
                               log_type='waring')
                    # ===================  记录日志  ===================

                    error_df.loc[condition, 'error'] = True

        if not error_df.empty:
            del error_df['code']
            error_df = error_df[error_df['error']]
            error_df.to_csv(self.error_path, encoding='gbk', index=False)
        record_log(f'所有数据更新完成', send=True)

    def update_stock_index(self, index_list):
        """
        更新指数数据
        :return:
        """

        def getDate():
            url = 'https://hq.sinajs.cn/list=sh000001'
            response = requests.get(url, headers={
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.62'
            }).text
            data_date = str(response.split(',')[-4])
            # 获取上证的指数日期
            return data_date

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36 Edg/97.0.1072.62'

        }
        for index in index_list:
            print(index)
            url = 'https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get'
            start_time = '1900-01-01'
            end_time = ''
            df_list = []
            while True:
                params = {
                    '_var': 'kline_dayqfq',
                    'param': f'{index},day,{start_time},{end_time},2000,qfq',
                    'r': f'0.{randint(10 ** 15, (10 ** 16) - 1)}',
                }
                res = requests.get(url, params=params, headers=headers)
                res_json = json.loads(re.findall('kline_dayqfq=(.*)', res.text)[0])
                if res_json['code'] == 0:
                    _df = pd.DataFrame(res_json['data'][index]['day'])
                    df_list.append(_df)
                    if _df.shape[0] <= 1:
                        break
                    end_time = _df.iloc[0][0]
                time.sleep(2)
            df = pd.concat(df_list, ignore_index=True)
            # ===对数据进行整理
            rename_dict = {0: 'candle_end_time', 1: 'open', 2: 'close', 3: 'high', 4: 'low', 5: 'amount', 6: 'info'}
            # 其中amount单位是手，说明数据不够精确
            df.rename(columns=rename_dict, inplace=True)
            df['candle_end_time'] = pd.to_datetime(df['candle_end_time'])
            df.drop_duplicates('candle_end_time', inplace=True)     # 去重
            df.sort_values('candle_end_time', inplace=True)
            df['candle_end_time'] = df['candle_end_time'].dt.strftime('%Y-%m-%d')
            if 'info' not in df:
                df['info'] = None
            df = df[['candle_end_time', 'open', 'high', 'low', 'close', 'amount', 'info']]
            start = datetime.datetime.now().strftime('%Y-%m-%d') + ' ' + '9:30'
            start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M")

            end = datetime.datetime.now().strftime('%Y-%m-%d') + ' ' + '15:00'
            end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M")
            now_time = datetime.datetime.now()
            if (now_time >= start) & (now_time <= end) & (pd.to_datetime(getDate()) == now_time):
                df = df[:-1]
            to_csv_path = self.all_data_path + '/index'
            if not os.path.exists(to_csv_path):  # 判断文件夹是否存在
                os.makedirs(to_csv_path)  # 不存在则创建
            df.to_csv(to_csv_path + '/%s.csv' % index, index=False, encoding='gbk')

    def get_strategy_result(self, strategy, period, select_count):
        """
        获取策略结果
        :param strategy: 策略名称
        :param period: 策略持仓时间，选股策略填'周'、'月'、'自然月'，事件策略填'x天'，与我们网页的参数贴合
        :param select_count:选股数量，若选择所有股票，填入0，与我们网页的参数贴合
        :return:
        """

        def up(_strategy, _strategy_df, _period, _select_count):
            period_dict = {
                '周': 'week',
                '月': 'month',
                '自然月': 'natural_month'
            }
            if '天' in _period:
                period_type = _period.replace('天', '')
            else:
                period_type = period_dict[_period]
            to_path = f'{self.strategy_result_path}'
            if not os.path.exists(to_path):  # 判断文件夹是否存在
                os.makedirs(to_path)  # 不存在则创建
            to_file_path = os.path.join(to_path, f'{_strategy.replace("-", "_")}_{period_type}_{select_count}.csv')

            if os.path.exists(to_file_path):
                old_df = pd.read_csv(to_file_path, encoding='gbk')
                _strategy_df = pd.concat([old_df, _strategy_df])
                _strategy_df.drop_duplicates(subset=['交易日期', '股票代码'], inplace=True)
            _strategy_df.to_csv(to_file_path, encoding='gbk', index=False)

        url = self.url + '/stock-result/service/%s' % strategy

        params = {
            'uuid': self.hid,
            'period_type': period,
            'select_stock_max_num': select_count
        }
        res = self.request_data('GET', url, params=params)
        if res.status_code != 200:
            return None
        res_json = res.json()
        code = res_json['code']
        if code == 200:
            df = pd.DataFrame(res_json['result']).rename(columns={'name': '股票名称', 'symbol': '股票代码'})
            df['交易日期'] = res_json['select_time']
            df['选股排名'] = 1
            df = df[['交易日期', '股票代码', '股票名称', '选股排名']]
            up(strategy, df, period, select_count)
            return res_json
        elif code == 1003:
            return f'{strategy}策略无获取权限'
        elif code == 1004:
            return f'{strategy}策略不存在'
        elif code == 1005:
            return f'{strategy}策略无数据'
        elif code == 1006:
            return f'{strategy}策略获取数据参数错误'
        return None
