#encoding:gbk

# 导入外部程序包
import numpy as np  # 主要用于科学计算的Python包
import pandas as pd  # 建立在numpy和其他众多第三方库基础上的python包

# 初始化模块
def init(ContextInfo):
    # 设定股票池，即要操作的股票
    ContextInfo.tradestock = '000001.SZ'
    ContextInfo.set_universe(['000001.SZ'])
    # 设定账号
    ContextInfo.accountid = '55003498'
    # 设定均线长度
    ContextInfo.MA_period = 20
    # 其他初始化操作




# 基本运行模块
def handlebar(ContextInfo):
    # 获取股票收盘价序列
    close = ContextInfo.get_history_data(ContextInfo.MA_period + 1, 'ld', 'close')[ContextInfo.tradestock]
    # 计算移动均线
    MA20 = pd.Series(close).rolling(window=20, center=False).mean().values
    # 判断买入条件满足则买入
    if close[-2] < MA20[-2] and close[-1] > MA20[-1]:
        # 获取账户资金
        totalvalue = get_totalvalue(ContextInfo.accountid, 'STOCK')  # (账号，商品类型)
        # 下单全仓买入
        order_target_value(ContextInfo.tradestock, totalvalue, ContextInfo, ContextInfo.accountid)
    # 判断卖出条件满足则卖出
    if close[-2] >= MA20[-2] and close[-1] < MA20[-1]:
        # 下单全部卖出
        order_target_value(ContextInfo.tradestock, 0, ContextInfo, ContextInfo.accountid)
		
# 获取账户资金
def get_totalvalue(accountid, datatype):  # （账号，商品类型）# 调用模块：获取账户资金
    result = 0  # 设置值为0
    resultlist = get_trade_detail_data(accountid, datatype, "ACCOUNT")  # （账号，商品类型，账户类型）
    for obj in resultlist:
        result = obj.m_dBalance  # 账户可用资金余额
    return result