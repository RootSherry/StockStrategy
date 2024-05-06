import datetime
import json
import logging as log
import os
import requests

from plugins.StockStrategy.config import proxies, robot_api, root_path

# region 发送日志相关
log_path = root_path + '/data/log/'
log.basicConfig(filename=log_path + '%s_日志.log' % datetime.datetime.now().strftime('%Y-%m-%d'), level=log.INFO)


def record_log(msg, log_type='info', send=False, robot_type='info'):
    """
    记录日志
    :param msg:日志信息
    :param log_type: 日志类型
    :param send: 是否要发送
    :param robot_type: 发送的机器人类别
    :return:
    """
    time_str = datetime.datetime.strftime(datetime.datetime.now(), "%H:%M:%S")
    log_msg = time_str + ' --> ' + msg
    if log_type == 'info':
        log.info(msg=log_msg)
        if send:
            try:
                send_message(msg, robot_type=robot_type)
            except Exception as err:
                log.info(msg='发送错误信息失败')


# endregion

# region 消息发送相关

# 发送信息
def send_message(content, robot_type='info'):
    # content: str, msg
    # robot_type: str, 'norm_robot' 常规消息推送 or 'warn_robot' 异常警告推送
    print(content)

    msg = {
        'msgtype': 'text',
        'text': {'content': content},
    }

    headers = {"Content-Type": "application/json;charset=utf-8"}
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=' + robot_api[robot_type]['secret']
    body = json.dumps(msg)
    requests.post(url, data=body, headers=headers, timeout=10, proxies=proxies)

# endregion
