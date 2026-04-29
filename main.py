import requests
import math
import datetime
import os

def get_btc_klines():
    api_urls = [
        "https://api.binance.us/api/v3/klines",
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines"
    ]
    for url in api_urls:
        try:
            response = requests.get(url, params={"symbol": "BTCUSDT", "interval": "1d", "limit": 200}, timeout=10).json()
            if isinstance(response, list) and len(response) == 200:
                return response
        except:
            continue
    return None

def calculate_ahr999():
    try:
        klines = get_btc_klines()
        if not klines: return None, None
        closes = [float(day[4]) for day in klines]
        current_price = closes[-1]
        ma_200 = sum(closes) / len(closes)
        days_since_genesis = (datetime.date.today() - datetime.date(2009, 1, 3)).days
        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)
        ahr999 = (current_price / ma_200) * (current_price / exp_val)
        return ahr999, current_price
    except Exception as e:
        print(f"计算异常: {e}")
        return None, None

def get_fear_greed_index():
    try:
        data = requests.get("https://api.alternative.me/fng/", timeout=10).json()['data'][0]
        trans = {"Extreme Fear": "极度恐惧 🥶", "Fear": "恐惧 😨", "Neutral": "中立 😐", "Greed": "贪婪 😏", "Extreme Greed": "极度贪婪 🤑"}
        return int(data['value']), trans.get(data['value_classification'], data['value_classification'])
    except:
        return "未知", "未知"

def send_wxpusher_notification(ahr999, price, fgi_value, fgi_class, is_bottom):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    if not app_token or not uid: return

    title = "🚨 AHR999 抄底预警 (<0.45)" if is_bottom else "🔥 AHR999 风险预警 (>1.2)"
    advice = "属于极度低估区间，建议果断分批买入（加仓）！" if is_bottom else "属于高估区间，不建议买入，可考虑逢高减仓！"
    color = "#00b050" if is_bottom else "#ff0000"

    content = f"""
    <h2>{title}</h2>
    <p><b>当前 AHR999 指数:</b> <span style="color:{color}; font-size:24px; font-weight:bold;">{ahr999:.4f}</span></p>
    <p><b>当前 BTC 价格:</b> $ {price:.2f}</p>
    <hr>
    <p><b>恐惧贪婪指数:</b> <span style="font-size:20px; font-weight:bold;">{fgi_value}</span> ({fgi_class})</p>
    <p><b>操作建议:</b> {advice}</p>
    <p><i>时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i></p>
    """
    requests.post(
        "https://wxpusher.zjiecode.com/api/send/message", 
        json={"appToken": app_token, "content": content, "summary": f"市场异动: AHR999 {ahr999:.2f}", "contentType": 2, "uids": [uid]}
    )

if __name__ == "__main__":
    ahr999, current_price = calculate_ahr999()
    fgi_value, fgi_class = get_fear_greed_index()
    
    if ahr999 is not None:
        print(f"👉 当前 AHR999: {ahr999:.4f} | 价格: ${current_price:.2f} | 贪婪指数: {fgi_value}")
        if ahr999 < 0.45:
            print("触发底仓预警！发送通知。")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, is_bottom=True)
        elif ahr999 > 1.2:
            print("触发高估预警！发送通知。")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, is_bottom=False)
        else:
            print("处于定投区间 (0.45 ~ 1.2)，不发送打扰信息。")
