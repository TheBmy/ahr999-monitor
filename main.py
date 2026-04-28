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
    params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 200}
    for url in api_urls:
        try:
            response = requests.get(url, params=params, timeout=10).json()
            if isinstance(response, list) and len(response) == 200:
                return response
        except Exception:
            continue
    return None

def calculate_ahr999():
    try:
        klines = get_btc_klines()
        if not klines: return None, None

        closes = [float(day[4]) for day in klines]
        current_price = closes[-1]
        ma_200 = sum(closes) / len(closes)

        genesis_date = datetime.date(2009, 1, 3)
        today = datetime.date.today()
        days_since_genesis = (today - genesis_date).days

        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)
        ahr999 = (current_price / ma_200) * (current_price / exp_val)
        return ahr999, current_price
    except Exception as e:
        print(f"AHR999计算异常: {e}")
        return None, None

def get_fear_greed_index():
    # 使用 Alternative.me 免费公开 API
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10).json()
        data = response['data'][0]
        value = int(data['value'])
        classification = data['value_classification']
        
        # 将英文状态翻译为中文
        trans = {
            "Extreme Fear": "极度恐惧 🥶",
            "Fear": "恐惧 😨",
            "Neutral": "中立 😐",
            "Greed": "贪婪 😏",
            "Extreme Greed": "极度贪婪 🤑"
        }
        return value, trans.get(classification, classification)
    except Exception as e:
        print(f"恐惧贪婪指数获取失败: {e}")
        return "未知", "未知"

def send_wxpusher_notification(ahr999, price, fgi_value, fgi_class, zone_type):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    if not app_token or not uid: return

    # 根据区间设置不同的文案和颜色
    if zone_type == "bottom":
        title = "🚨 AHR999 极度低估 (抄底预警)"
        advice = "目前处于【0.45以下】的极度低估区间，历史罕见，建议果断买入！"
        ahr_color = "#00b050" # 绿色
    else:
        title = "🔥 AHR999 估值偏高 (风险预警)"
        advice = "目前处于【1.2以上】的高估区间，定投应暂停，可考虑逢高分批减仓！"
        ahr_color = "#ff0000" # 红色

    content = f"""
    <h2>{title}</h2>
    <p><b>当前 AHR999 指数:</b> <span style="color:{ahr_color}; font-size:24px; font-weight:bold;">{ahr999:.4f}</span></p>
    <p><b>当前 BTC 价格:</b> $ {price:.2f}</p>
    <hr>
    <p><b>恐惧贪婪指数:</b> <span style="font-size:20px; font-weight:bold;">{fgi_value}</span> ({fgi_class})</p>
    <p><b>操作建议:</b> {advice}</p>
    <p><i>时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i></p>
    """
    
    url = "https://wxpusher.zjiecode.com/api/send/message"
    data = {
        "appToken": app_token,
        "content": content,
        "summary": f"市场异动: AHR999={ahr999:.2f}, 贪婪指数={fgi_value}",
        "contentType": 2, 
        "uids": [uid]
    }
    requests.post(url, json=data)
    print("微信通知已发送！")

if __name__ == "__main__":
    print("开始获取数据...")
    ahr999, current_price = calculate_ahr999()
    fgi_value, fgi_class = get_fear_greed_index()
    
    if ahr999 is not None:
        print(f"👉 AHR999: {ahr999:.4f} | 价格: ${current_price:.2f} | 恐惧贪婪: {fgi_value}({fgi_class})")
        
        # 核心逻辑：小于0.45 或 大于1.2 才触发通知
        if ahr999 < 0.45:
            print("触发【抄底】条件，发送通知...")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, "bottom")
        elif ahr999 > 1.2:
            print("触发【高估】条件，发送通知...")
            send_wxpusher_notification(ahr999, current_price, fgi_value, fgi_class, "top")
        else:
            print("当前指标在 0.45 ~ 1.2 之间（常规区间），不发送通知。")
