import requests
import math
import datetime
import os

# ================= 配置区 =================
# 你希望的阈值：例如 ahr999 < 0.45 属于抄底区间， < 1.2 属于定投区间
ALERT_THRESHOLD = 1.2  
# =========================================

def calculate_ahr999():
    try:
        # 1. 获取币安 BTC 历史每日价格 (免费免密钥)
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 200}
        response = requests.get(url, params=params).json()

        # 获取收盘价并计算 200日均线
        closes = [float(day[4]) for day in response]
        current_price = closes[-1]
        ma_200 = sum(closes) / len(closes)

        # 2. 计算比特币诞生天数 (创世区块: 2009-01-03)
        genesis_date = datetime.date(2009, 1, 3)
        today = datetime.date.today()
        days_since_genesis = (today - genesis_date).days

        # 3. 计算指数拟合价格 (公式: 10^(5.84 * log10(诞生天数) - 17.01))
        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)

        # 4. 计算 ahr999 指数 (公式: (当前价格/200日均线) * (当前价格/拟合价格))
        ahr999 = (current_price / ma_200) * (current_price / exp_val)
        
        return ahr999, current_price
    except Exception as e:
        print(f"计算出错: {e}")
        return None, None

def send_wechat_notification(ahr999, price):
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token:
        print("未配置 PUSHPLUS_TOKEN，无法发送通知。")
        return

    title = "⚠️ AHR999 定投/抄底 指标提醒"
    content = f"""
    <h3>已达到您设定的指标阈值！</h3>
    <ul>
        <li><b>当前 AHR999 指数:</b> <span style="color:red; font-size:20px;">{ahr999:.4f}</span></li>
        <li><b>设定的提醒阈值:</b> {ALERT_THRESHOLD}</li>
        <li><b>当前 BTC 价格:</b> $ {price:.2f}</li>
        <li><b>时间:</b> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
    </ul>
    <p><i>💡 提示：指数 < 0.45 为抄底区间；0.45 - 1.2 为定投区间；> 1.2 不推荐买入。</i></p>
    """
    
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": "html"
    }
    requests.post(url, json=data)
    print("微信通知已发送！")

if __name__ == "__main__":
    ahr999, current_price = calculate_ahr999()
    
    if ahr999 is not None:
        print(f"当前 AHR999: {ahr999:.4f}, 当前价格: {current_price}")
        # 如果当前指数低于设定的阈值，则发送微信通知
        if ahr999 <= ALERT_THRESHOLD:
            send_wechat_notification(ahr999, current_price)
        else:
            print("未达到提醒阈值，暂不通知。")
