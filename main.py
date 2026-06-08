import requests
import math
import datetime
import os
import json

# ============ 极简交易系统配置 ============
CRASH_THRESHOLD = -15.0  # 买入：单日暴跌 15% (黑天鹅抄底)
AHR999_BOTTOM = 0.45     # 买入：Ahr999 抄底线
AHR999_WARN = 1.2        # 卖出：高估警戒线 (仅提示)
AHR999_DEEP = 0.3        # 深底：极度低估二级预警线
# ----- 逃顶核按钮条件 -----
ESCAPE_AHR999 = 1.5      # 逃顶条件 A：Ahr999 > 1.5
ESCAPE_FGI = 85          # 逃顶条件 C：贪婪指数 >= 85 (极度疯狂泡沫)
# ==========================================
STATE_FILE = "state.json"

def load_state():
    """加载上次运行状态"""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_ahr999": None}

def save_state(state):
    """保存运行状态"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_btc_data():
    """获取过去400天的K线(用于Pi周期) 和 24小时涨跌幅"""
    kline_urls = ["https://api.binance.us/api/v3/klines", "https://api.binance.com/api/v3/klines"]
    ticker_urls = ["https://api.binance.us/api/v3/ticker/24hr", "https://api.binance.com/api/v3/ticker/24hr"]

    klines, price_change = None, 0.0

    # 获取 400 天 K线
    for url in kline_urls:
        try:
            res = requests.get(url, params={"symbol": "BTCUSDT", "interval": "1d", "limit": 400}, timeout=10).json()
            if isinstance(res, list) and len(res) >= 350:
                klines = res
                break
        except: continue

    # 获取单日涨跌幅
    for url in ticker_urls:
        try:
            res = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=10).json()
            if 'priceChangePercent' in res:
                price_change = float(res['priceChangePercent'])
                break
        except: continue

    return klines, price_change

def calculate_indicators(klines):
    try:
        closes = [float(day[4]) for day in klines]
        current_price = closes[-1]

        # 计算均线
        ma_200 = sum(closes[-200:]) / 200
        ma_111 = sum(closes[-111:]) / 111
        ma_350 = sum(closes[-350:]) / 350

        # 1. 计算 Ahr999
        days_since_genesis = (datetime.date.today() - datetime.date(2009, 1, 3)).days
        exp_val = 10 ** (5.84 * math.log10(days_since_genesis) - 17.01)
        ahr999 = (current_price / ma_200) * (current_price / exp_val)

        # 2. 计算 Pi 周期交叉率 (当值 >= 1.0 时，说明111日线向上击穿了350日线*2，逃顶条件 B 触发)
        pi_cross_ratio = ma_111 / (ma_350 * 2)

        return ahr999, pi_cross_ratio, current_price
    except Exception as e:
        print(f"指标计算异常: {e}")
        return None, None, None

def get_fear_greed_index():
    try:
        data = requests.get("https://api.alternative.me/fng/", timeout=10).json()['data'][0]
        trans = {"Extreme Fear": "极度恐惧 🥶", "Fear": "恐惧 😨", "Neutral": "中立 😐", "Greed": "贪婪 😏", "Extreme Greed": "极度贪婪 🤑"}
        return int(data['value']), trans.get(data['value_classification'], data['value_classification'])
    except:
        return 50, "未知"

def send_wxpusher(title, content_html, summary):
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")
    if not app_token or not uid: return
    requests.post("https://wxpusher.zjiecode.com/api/send/message", json={
        "appToken": app_token, "content": content_html, "summary": summary, "contentType": 2, "uids": [uid]
    })

def check_crossing(last_val, curr_val):
    """
    检测 AHR999 穿越预设阈值，返回需要触发的通知列表。
    每次穿越只在下一次穿越发生前触发一次（通过比较 last_val 和 curr_val 实现）。
    """
    notifications = []
    if last_val is None:
        return notifications  # 首次运行，不触发任何穿越通知

    # 向下穿越 0.45
    if last_val >= AHR999_BOTTOM and curr_val < AHR999_BOTTOM:
        notifications.append(("below_0.45", "⚠️ AHR999 跌破抄底线",
            f"""<h2>⚠️ AHR999 已跌破 0.45</h2>
            <p><b>当前 AHR999:</b> <span style="color:#ff6600; font-size:24px; font-weight:bold;">{curr_val:.4f}</span></p>
            <p><b>说明：</b>状态已经低于 0.45，进入低估区间，可开始关注分批买入机会。</p>""",
            f"AHR999 跌破 0.45: {curr_val:.4f}"))

    # 向下穿越 0.3
    if last_val >= AHR999_DEEP and curr_val < AHR999_DEEP:
        notifications.append(("below_0.3", "🔴 AHR999 已低于 0.3",
            f"""<h2>🔴 AHR999 已低于 0.3</h2>
            <p><b>当前 AHR999:</b> <span style="color:#cc0000; font-size:24px; font-weight:bold;">{curr_val:.4f}</span></p>
            <p><b>说明：</b>已低于 0.3，进入极度低估区间，历史罕见低价。</p>""",
            f"AHR999 低于 0.3: {curr_val:.4f}"))

    # 向上穿越 0.3
    if last_val < AHR999_DEEP and curr_val >= AHR999_DEEP:
        notifications.append(("above_0.3", "🟡 AHR999 回升至 0.3 以上",
            f"""<h2>🟡 AHR999 已回升至 0.3 以上</h2>
            <p><b>当前 AHR999:</b> <span style="color:#ff9900; font-size:24px; font-weight:bold;">{curr_val:.4f}</span></p>
            <p><b>说明：</b>已脱离极度低估区间（>0.3），但仍在抄底线以下。</p>""",
            f"AHR999 回升超过 0.3: {curr_val:.4f}"))

    # 向上穿越 0.45
    if last_val < AHR999_BOTTOM and curr_val >= AHR999_BOTTOM:
        notifications.append(("above_0.45", "🟢 AHR999 回升至 0.45 以上",
            f"""<h2>🟢 AHR999 已回升至 0.45 以上</h2>
            <p><b>当前 AHR999:</b> <span style="color:#00b050; font-size:24px; font-weight:bold;">{curr_val:.4f}</span></p>
            <p><b>说明：</b>已脱离抄底区间，进入定投/震荡区间。</p>""",
            f"AHR999 回升超过 0.45: {curr_val:.4f}"))

    return notifications

if __name__ == "__main__":
    klines, change_pct = get_btc_data()
    if not klines: exit()

    ahr999, pi_ratio, current_price = calculate_indicators(klines)
    fgi_value, fgi_class = get_fear_greed_index()

    if ahr999 is None: exit()

    # 加载上次状态
    state = load_state()
    last_ahr999 = state.get("last_ahr999")

    print(f"👉 AHR999: {ahr999:.4f} | Pi率: {pi_ratio:.4f} | FGI: {fgi_value} | 涨跌: {change_pct}%")

    # ================= 底部穿越通知（边缘触发，每条仅发一次）=================
    crossings = check_crossing(last_ahr999, ahr999)
    for key, title, html, summary in crossings:
        send_wxpusher(title, html, summary)
        print(f"穿越通知发送: {key}")

    # ================= 卖出/逃顶逻辑 (最高优先级) =================

    # 逃顶条件判定
    cond_a = ahr999 >= ESCAPE_AHR999
    cond_b = pi_ratio >= 1.0  # Pi周期交叉
    cond_c = fgi_value >= ESCAPE_FGI

    # 满足任意2个及以上，触发核按钮大逃亡！
    if (cond_a + cond_b + cond_c) >= 2:
        triggers = []
        if cond_a: triggers.append("AHR999 突破 1.5")
        if cond_b: triggers.append("Pi 周期指标发生死亡交叉")
        if cond_c: triggers.append("市场极度癫狂 (FGI >= 85)")

        title = "☢️ 核按钮预警：启动 4-3-3 黄金大逃亡！"
        html = f"""
        <h2 style="color:#8b0000;">{title}</h2>
        <p><b>执行指令：</b>立刻拔网线走人，无情抛售！</p>
        <p><b>触发原因 (满足2项及以上)：</b><br><span style="color:red; font-weight:bold;">{ ' / '.join(triggers) }</span></p>
        <hr>
        <ul>
            <li><b>当前 AHR999:</b> {ahr999:.4f}</li>
            <li><b>Pi 周期临近度:</b> {pi_ratio*100:.1f}% (≥100%即交叉)</li>
            <li><b>贪婪指数:</b> {fgi_value} ({fgi_class})</li>
            <li><b>BTC 价格:</b> $ {current_price:.2f}</li>
        </ul>
        <p><i>注：不要留恋最后一块铜板，落袋为安是唯一的生存法则。</i></p>
        """
        send_wxpusher(title, html, "☢️ 紧急逃顶指令触发！")
        print("核按钮触发！已发送通知。")
        save_state({"last_ahr999": ahr999})
        exit() # 只要逃顶触发了，就不再向下判断任何抄底逻辑

    elif ahr999 > AHR999_WARN:
        # 仅高估，未触发核按钮
        title = "🔴 风险预警：进入高估区"
        html = f"""
        <h2>{title}</h2>
        <p><b>当前 AHR999:</b> <span style="color:#ff0000; font-size:24px; font-weight:bold;">{ahr999:.4f}</span></p>
        <p><b>操作建议：</b>停止定投。准备好子弹和交易所账户，静待逃顶核按钮触发。</p>
        """
        send_wxpusher(title, html, f"风险预警: AHR999达 {ahr999:.4f}")
        print("高估预警发送。")

    # ================= 买入/抄底逻辑 =================

    elif change_pct <= CRASH_THRESHOLD:
        title = "🚨 极恐预警：单日暴跌超 15%！"
        html = f"""
        <h2>{title}</h2>
        <p><b>24小时跌幅:</b> <span style="color:red; font-size:26px; font-weight:bold;">{change_pct}%</span></p>
        <p><b>当前 BTC 价格:</b> $ {current_price:.2f}</p>
        <hr>
        <p><b>操作建议：</b>黑天鹅降临！极具性价比的带血筹码已出现，请根据纪律打出子弹！</p>
        """
        send_wxpusher(title, html, f"暴跌预警: {change_pct}%")
        print("暴跌预警发送。")

    else:
        print("市场在 0.45 ~ 1.2 之间震荡，未暴跌，保持静默死守。")

    # 保存本次状态
    save_state({"last_ahr999": ahr999})
