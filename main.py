import requests
import math
import datetime
import os

# ================= 配置区 =================
ALERT_THRESHOLD = 2.0  # 建议先设为 2.0 方便测试，测试成功收到微信后再改回 1.2
# =========================================

def get_btc_klines():
    # 备用 API 列表。优先使用 binance.us，因为 GitHub 服务器多在美国
    api_urls = [
        "https://api.binance.us/api/v3/klines",
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines"
    ]
    params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 200}

    for url in api_urls:
        try:
            print(f"正在尝试请求接口: {url}")
            response = requests.get(url, params=params, timeout=10).json()
            # 检查返回的是否是正常的数据列表
            if isinstance(response, list) and len(response) == 200:
                print("✅ 成功获取行情数据！")
                return response
            else:
                print(f"⚠️ 接口返回异常数据: {response}")
        except Exception as e:
            print(f"❌ 接口请求失败: {e}")
            continue
            
    return None

def calculate_ahr999():
    try:
        klines = get_btc_klines()
        if not klines:
            print("所有行情接口均无法访问，计算终止。")
            return None, None

        # 提取每天的收盘价
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
        print(f"计算过程发生异常: {e}")
        return None, None

def send_wxpusher_notification(ahr999, price):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    
    if not app_token or not uid:
        print("未配置 WxPusher 的 Token 或 UID，无法发送通知。")
        return

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
        "summary": f"AHR999提醒: 当前指数 {ahr999:.4f}",
        "contentType": 2, 
        "uids": [uid]
    }
    
    response = requests.post(url, json=data).json()
    if response.get("code") == 1000:
        print("✅ WxPusher 微信通知发送成功！")
    else:
        print(f"❌ 微信通知发送失败: {response}")

if __name__ == "__main__":
    ahr999, current_price = calculate_ahr999()
    
    if ahr999 is not None:
        print(f"👉 当前 AHR999: {ahr999:.4f}, 当前价格: $ {current_price:.2f}")
        if ahr999 <= ALERT_THRESHOLD:
            print("达到阈值，准备发送微信通知...")
            send_wxpusher_notification(ahr999, current_price)
        else:
            print(f"未达到提醒阈值 (<= {ALERT_THRESHOLD})，暂不通知。")
