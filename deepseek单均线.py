#encoding:gbk  # 指定文件编码为GBK，兼容中文字符

# 导入必要的库
import numpy as np  # 导入数值计算库numpy，用于数组运算
import pandas as pd  # 导入数据处理库pandas，用于数据分析和时序数据处理

def init(ContextInfo):
    # 初始化函数，策略启动时执行一次
    
    # 交易标的设置
    ContextInfo.tradestock = '000001.SZ'  # 设置交易标的为平安银行
    ContextInfo.set_universe([ContextInfo.tradestock])  # 设置股票池，只包含指定的一只股票
    ContextInfo.accountid = '55003498'  # 设置交易账户ID
    
    # 策略参数初始化
    ContextInfo.MA_period = 20       # 均线周期参数，使用20日均线
    ContextInfo.vol_filter = 1.5     # 成交量过滤倍数，要求成交量大于均值1.5倍才考虑买入
    ContextInfo.stop_loss = 0.95     # 止损点设置，价格低于买入价95%(即跌幅5%)时止损
    ContextInfo.position = 0         # 记录当前仓位状态，0表示空仓
    ContextInfo.entry_price = 0      # 记录买入价格，用于计算止损点和加仓条件
    ContextInfo.vol_period = 5       # 成交量均线周期，用于判断成交量放大情况

def handlebar(ContextInfo):
    # 主策略函数，每个交易周期（通常为每天）执行一次
    try:
        # 数据获取部分
        # 计算需要获取的历史数据长度，确保足够计算技术指标
        period = max(ContextInfo.MA_period, ContextInfo.vol_period) + 5  # 取最大周期并额外增加5天防止数据不足
        
        # 分别获取收盘价和成交量数据
        close_data = ContextInfo.get_history_data(period, '1d', 'close')  # 获取日线收盘价数据
        volume_data = ContextInfo.get_history_data(period, '1d', 'volume')  # 获取日线成交量数据
        
        # 数据完整性检查
        if ContextInfo.tradestock not in close_data or ContextInfo.tradestock not in volume_data:
            # 如果数据中不存在指定的股票代码，输出错误并终止本次执行
            print(f"[ERROR] {ContextInfo.tradestock} not found in historical data")
            return
        
        # 提取特定股票的价格和成交量序列
        close_prices = close_data[ContextInfo.tradestock]  # 收盘价序列
        volumes = volume_data[ContextInfo.tradestock]  # 成交量序列
        
        # 数据长度校验
        if len(close_prices) < ContextInfo.MA_period or len(volumes) < ContextInfo.vol_period:
            # 如果数据长度不足以计算指标，输出警告并终止本次执行
            print(f"[WARNING] 数据不足，需求{ContextInfo.MA_period}天，实际{len(close_prices)}天")
            return

        # 技术指标计算
        # 计算MA20移动平均线，使用pandas的rolling方法
        MA20 = pd.Series(close_prices).rolling(ContextInfo.MA_period).mean().values
        # 计算近期成交量均值，用于判断量能变化
        vol_ma = pd.Series(volumes[-ContextInfo.vol_period:]).mean()
        
        # 当前市场状态变量提取
        current_close = close_prices[-1]  # 最新收盘价
        current_vol = volumes[-1]  # 最新成交量
        prev_close = close_prices[-2]  # 前一天收盘价
        prev_ma = MA20[-2]  # 前一天MA值
        current_ma = MA20[-1]  # 当前MA值

        # 账户信息获取
        total_asset = get_totalvalue(ContextInfo.accountid, 'STOCK')  # 获取账户可用资金
        
        # 风控：止损检查（优先级高于交易信号）
        if ContextInfo.position > 0 and current_close < ContextInfo.entry_price * ContextInfo.stop_loss:
            # 如果持有仓位且价格跌破止损线，执行平仓操作
            order_target_value(ContextInfo.accountid, ContextInfo.tradestock, 0, ContextInfo)
            ContextInfo.position = 0  # 更新仓位状态为空仓
            print(f"[止损] 价格{current_close:.2f}低于入场价{ContextInfo.entry_price:.2f}的{ContextInfo.stop_loss*100}%")

        # 买入信号判断（同时考虑均线金叉和量能放大）
        buy_signal = (
            prev_close < prev_ma and  # 前一天收盘价在均线下方
            current_close > current_ma and  # 当前收盘价突破均线上方（金叉形成）
            current_vol > vol_ma * ContextInfo.vol_filter  # 成交量放大，大于均值的1.5倍
        )
        
        # 卖出信号判断（均线死叉）
        sell_signal = prev_close >= prev_ma and current_close < current_ma  # 价格从均线上方跌破均线（死叉形成）

        # 交易执行逻辑
        if buy_signal:  # 如果出现买入信号
            if ContextInfo.position == 0:  # 如果当前无仓位，首次建仓
                target_value = total_asset * 0.5  # 以50%资金建仓
                order_target_value(ContextInfo.accountid, ContextInfo.tradestock, target_value, ContextInfo)
                ContextInfo.position = 0.5  # 记录当前仓位为50%
                ContextInfo.entry_price = current_close  # 记录入场价格
                print(f"[建仓] 价格{current_close:.2f} 仓位50%")
                
            elif ContextInfo.position < 1 and current_close > ContextInfo.entry_price * 1.03:  
                # 如果已有仓位且行情向好（价格上涨3%以上），执行加仓
                target_value = total_asset * 0.8  # 加仓至80%
                order_target_value(ContextInfo.accountid, ContextInfo.tradestock, target_value, ContextInfo)
                ContextInfo.position = 0.8  # 更新仓位状态为80%
                print(f"[加仓] 价格{current_close:.2f} 仓位80%")

        elif sell_signal and ContextInfo.position > 0:  # 如果出现卖出信号且持有仓位
            # 执行全部清仓操作
            order_target_value(ContextInfo.accountid, ContextInfo.tradestock, 0, ContextInfo)
            ContextInfo.position = 0  # 更新仓位状态为空仓
            print(f"[清仓] 价格{current_close:.2f}下穿MA20")

    except Exception as e:  # 捕获并处理可能的异常
        print(f"[ERROR] 发生异常：{str(e)}")  # 打印异常信息便于调试

def get_totalvalue(accountid, datatype):
    """获取账户可用资金余额"""
    try:
        result = 0  # 初始化结果变量
        # 调用API获取账户详情信息
        resultlist = get_trade_detail_data(accountid, datatype, "ACCOUNT")
        # 遍历结果列表，获取可用资金余额
        for obj in resultlist:
            result = obj.m_dBalance  # 提取可用资金余额属性
        return result  # 返回可用资金金额
    except Exception as e:
        # 异常处理，如API调用失败
        print(f"[ERROR] 获取账户信息失败：{str(e)}")
        return 0  # 异常情况下返回0