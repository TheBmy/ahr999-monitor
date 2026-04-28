# ============================================
# AHR999 Bitcoin 市场指标监控系统
# 功能：监控 BTC 估值，发送市场预警通知
# ============================================

import requests  # HTTP 请求库
import math  # 数学库（对数计算）
import datetime  # 日期时间库
import os  # 环境变量库

# ============================================
# 获取比特币 K 线数据
# ============================================
def get_btc_klines():
    """
    从币安 API 获取 BTC/USDT 的 200 天日线数据
    
    返回值:
        list: K 线数据列表（每条包含 [时间, 开盘价, 最高价, 最低价, 收盘价, ...]）
        None: 如果所有 API 都失败则返回 None
    """
    # 币安 API 地址列表（多个备用地址，用于容错）
    api_urls = [
        "https://api.binance.us/api/v3/klines",
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines"
    ]
    
    # 请求参数：交易对、时间周期、返回数量
    params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 200}
    
    # 尝试每个 API 地址
    for url in api_urls:
        try:
            # 发送 GET 请求，10秒超时，返回 JSON 数据
            response = requests.get(url, params=params, timeout=10).json()
            
            # 验证响应数据是否有效（列表且有 200 条数据）
            if isinstance(response, list) and len(response) == 200:
                return response  # 成功则返回
        except Exception:
            # 如果该 API 失败，继续尝试下一个
            continue
    
    # 所有 API 都失败，返回 None
    return None

# ============================================
# 计算 AHR999 指数
# ============================================
def calculate_ahr999():
    """
    AHR999 是比特币估值指标，综合考虑价格与历史增长趋势
    
    公式: AHR999 = (当前价格 / 200日均线) × (当前价格 / 指数模型值)
    
    返回值:
        tuple: (ahr999 指数值, 当前 BTC 价格)
               如果计算失败返回 (None, None)
    """
    try:
        # 获取 K 线数据
        klines = get_btc_klines()
        if not klines:
            return None, None

        # 提取所有收盘价（K 线数据中索引 4 是收盘价）
        closes = [float(day[4]) for day in klines]
        
        # 获取最新的 BTC 价格（最后一条数据）
        current_price = closes[-1]
        
        # 计算 200 日移动平均线
        ma_200 = sum(closes) / len(closes)

        # -------- 计算 AHR999 的指数模型部分 --------
        # Bitcoin 创世日期（中本聪挖出第一个区块）
        genesis_date = datetime.date(2009, 1, 3)
        
        # 今天的日期
        today = datetime.date.today()
        
        # 计算距创世以来的天数
        days_since_genesis = (today - genesis_date).days

        # 通过对数模型计算合理估值
        # 公式: exp_val = 10 ^ (5.84 * log10(days) - 17.01)
        # 这个模型反映了 BTC 长期增长趋势
        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)
        
        # 计算最终的 AHR999 值
        # 分子部分：价格/200日均线（越高说明越贵）
        # 分母部分：价格/指数增长值（修正长期增长因素）
        ahr999 = (current_price / ma_200) * (current_price / exp_val)
        
        return ahr999, current_price
    
    except Exception as e:
        # 打印错误信息便于调试
        print(f"AHR999计算异常: {e}")
        return None, None

# ============================================
# 获取加密货币恐惧贪婪指数
# ============================================
def get_fear_greed_index():
    """
    从 Alternative.me API 获取每日恐惧贪婪指数
    指数范围 0-100，反映市场情绪
    
    返回值:
        tuple: (指数数值, 中文分类描述)
               例如: (35, "恐惧 😨")
    """
    # 使用 Alternative.me 免费公开 API
    try:
        url = "https://api.alternative.me/fng/"
        
        # 获取最新数据
        response = requests.get(url, timeout=10).json()
        
        # 提取第一条数据（最新数据）
        data = response['data'][0]
        
        # 获取指数数值（0-100）
        value = int(data['value'])
        
        # 获取英文分类标签
        classification = data['value_classification']
        
        # 创建中英文翻译字典
        trans = {
            "Extreme Fear": "极度恐惧 🥶",      # 0-25
            "Fear": "恐惧 😨",                  # 25-45
            "Neutral": "中立 😐",               # 45-55
            "Greed": "贪婪 😏",                 # 55-75
            "Extreme Greed": "极度贪婪 🤑"      # 75-100
        }
        
        # 返回数值和中文描述
        return value, trans.get(classification, classification)
    
    except Exception as e:
        # 如果获取失败，返回未知
        print(f"恐惧贪婪指数获取失败: {e}")
        return "未知", "未知"

# ============================================
# 发送微信推送通知
# ============================================
def send_wxpusher_notification(ahr999, price, fgi_value, fgi_class, zone_type):
    """
    通过 WXPusher 服务发送格式化的微信通知
    
    参数:
        ahr999: AHR999 指数值
        price: 当前 BTC 价格
        fgi_value: 恐惧贪婪指数数值
        fgi_class: 恐惧贪婪指数分类
        zone_type: 区间类型 - "bottom"(低估) 或 "top"(高估)
    """
    # 从环境变量读取 WXPusher 配置
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")  # 应用 Token
    uid = os.environ.get("WXPUSHER_UID")  # 用户 ID
    
    # 如果环境变量未设置，直接返回（不发送）
    if not app_token or not uid:
        return

    # -------- 根据估值区间设置不同的提示文案 --------
    if zone_type == "bottom":
        # 低估区间：鼓励购买
        title = "🚨 AHR999 极度低估 (抄底预警)"
        advice = "目前处于【0.45以下】的极度低估区间，历史罕见，建议果断买入！"
        ahr_color = "#00b050"  # 绿色（买入信号）
    else:
        # 高估区间：提示风险
        title = "🔥 AHR999 估值偏高 (风险预警)"
        advice = "目前处于【1.2以上】的高估区间，定投应暂停，可考虑逢高分批减仓！"
        ahr_color = "#ff0000"  # 红色（卖出信号）

    # 生成 HTML 格式的通知内容（可在微信中展示格式化文本）
    content = f"""
    <h2>{title}</h2>
    <p><b>当前 AHR999 指数:</b> <span style="color:{ahr_color}; font-size:24px; font-weight:bold;">{ahr999:.4f}</span></p>
    <p><b>当前 BTC 价格:</b> $ {price:.2f}</p>
    <hr>
    <p><b>恐惧贪婪指数:</b> <span style="font-size:20px; font-weight:bold;">{fgi_value}</span> ({fgi_class})</p>
    <p><b>操作建议:</b> {advice}</p>
    <p><i>时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i></p>
    """
    
    # WXPusher API 地址
    url = "https://wxpusher.zjiecode.com/api/send/message"
    
    # 构建请求数据
    data = {
        "appToken": app_token,          # 应用 Token
        "content": content,              # 消息内容（HTML 格式）
        "summary": f"市场异动: AHR999={ahr999:.2f}, 贪婪指数={fgi_value}",  # 消息摘要
        "contentType": 2,                # 内容类型 2 表示 HTML
        "uids": [uid]                    # 目标用户 ID
    }
    
    # 发送 POST 请求
    requests.post(url, json=data)
    print("微信通知已发送！")

# ============================================
# 主程序入口
# ============================================
if __name__ == "__main__":
    print("开始获取数据...")
    
    # 计算 AHR999 和获取当前价格
    ahr999, current_price = calculate_ahr999()
    
    # 获取恐惧贪婪指数
    fgi_value, fgi_class = get_fear_greed_index()
    
    # 如果计算成功
    if ahr999 is not None:
        # 输出当前指标
        print(f"👉 AHR999: {ahr999:.4f} | 价格: ${current_price:.2f} | 恐惧贪婪: {fgi_value}({fgi_class})")
        
        # -------- 核心逻辑：判断是否触发通知 --------
        # 触发条件 1：AHR999 < 0.45（极度低估，历史底部）
        if ahr999 < 0.45:
            print("触发【抄底】条件，发送通知...")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, "bottom")
        
        # 触发条件 2：AHR999 > 1.2（明显高估，风险警告）
        elif ahr999 > 1.2:
            print("触发【高估】条件，发送通知...")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, "top")
        
        # 常规区间：无需通知
        else:
            print("当前指标在 0.45 ~ 1.2 之间（常规区间），不发送通知。")
