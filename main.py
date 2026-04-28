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
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 200}
        response = requests.get(url, params=params).json()

        closes = [float(day[4]) for day in response]
        current_price = closes[-1]
        ma_200 = sum(closes) / len(closes)

        genesis_date = datetime.date(2009, 1, 3)
        today = datetime.date.today()
        days_since_genesis = (today - genesis_date).days

        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)

        ahr999 = (current_price / ma_200) * (current_price / exp_val)
        
        return ahr999, current_price
    except Exception as e:
        print(f"计算出错: {e}")
        return None, None

def send_wxpusher_notification(ahr999, price):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    
    if not app_token or not uid:
        print("未配置 WxPusher 的 Token 或 UID，无法发送通知。")
        return

    # 生成判断文案
    if ahr999 < 0.45:
        advice = "🚨 属于【抄底区间】，极其罕见的买入机会！"
    else:
        advice = "💰 属于【定投区间】，适合分批买入！"

    content = f"""
    <h2>⚠️ AHR999 指标触发提醒</h2>
    <p><b>当前 AHR999 指数:</b> <span style="color:red; font-size:22px;">{ahr999:.4f}</span></p>
    <p><b>当前 BTC 价格:</b> $ {price:.2f}</p>
    <p><b>操作建议:</b> {advice}</p>
    <hr>
    <p><i>时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i></p>
    """
    
    url = "https://wxpusher.zjiecode.com/api/send/message"
    data = {
        "appToken": app_token,
        "content": content,
        "summary": f"AHR999提醒: 当前指数 {ahr999:.4f}", # 微信聊天列表展示的摘要
        "contentType": 2, # 2表示发送HTML格式
        "uids": [uid]
    }
    
    response = requests.post(url, json=data).json()
    if response.get("code") == 1000:
        print("WxPusher 微信通知发送成功！")
    else:
        print(f"通知发送失败: {response}")

if __name__ == "__main__":
    ahr999, current_price = calculate_ahr999()
    
    if ahr999 is not None:
        print(f"当前 AHR999: {ahr999:.4f}, 当前价格: {current_price}")
        if ahr999 <= ALERT_THRESHOLD:
            send_wxpusher_notification(ahr999, current_price)
        else:
            print("未达到提醒阈值，暂不通知。")
