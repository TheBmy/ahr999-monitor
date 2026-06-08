# ahr999-monitor

一个针对 AHR999 指标的实时监控工具，用于比特币投资决策辅助。集成贪婪恐惧指数(FGI)和Pi周期指标，自动识别市场底部和顶部。

## 📋 项目介绍

**ahr999-monitor** 是一个 Python 开发的自动化监控系统，用于实时跟踪 AHR999 指标、Fear & Greed Index(FGI)、Pi周期等多个指标，自动识别抄底和逃顶机会，并通过 WXPusher 推送实时预警。

### 核心指标说明

| 指标 | 说明 | 数据来源 |
|------|------|--------|
| **AHR999** | 复合指标，结合比特币价格和200周移动平均线 | 链上数据计算 |
| **Pi周期交叉率** | 111日均线 / (350日均线×2)，≥1.0时触发交叉信号 | K线数据计算 |
| **FGI(贪婪恐惧指数)** | 市场情绪指数(0-100)，反映市场心理状态 | alternative.me API |
| **24h涨跌幅** | 单日价格变动百分比，≤-15%触发极恐预警 | Binance API |

## ✨ 主要功能

- 📊 **实时监控** - 持续追踪 AHR999、Pi周期、FGI 等多维度指标
- 🎯 **自动交易信号** - 智能识别抄底和逃顶机会
- 🔴 **核按钮预警** - 满足2项及以上逃顶条件，触发紧急通知
- 🟢 **底部穿越通知** - AHR999 穿越 0.45/0.3 阈值时各发送一次通知，不重复骚扰
- ☢️ **高估风险** - AHR999 > 1.2 时发送风险提示
- 🚨 **黑天鹅预警** - 24h暴跌≤-15%时立即通知
- 📲 **WXPusher推送** - 集成微信实时消息推送
- 💾 **状态持久化** - 通过 state.json 记录上次运行状态，实现跨天穿越检测

## 🎮 交易规则

### 逃顶/卖出逻辑 (最高优先级)

**核按钮触发条件** (满足任意2项及以上):
- **条件A**: AHR999 ≥ 1.5
- **条件B**: Pi周期交叉率 ≥ 1.0 (111日线突破350日线×2)
- **条件C**: FGI ≥ 85 (市场极度疯狂泡沫)

触发时发送紧急卖出指令！

**高估预警** (AHR999 > 1.2):
- 发送风险提示，建议停止定投（水平触发，每天推送）

### 底部穿越通知 (边缘触发，每条仅发一次)

| 穿越方向 | 条件 | 说明 |
|----------|------|------|
| ⚠️ 跌破 0.45 | 上次 ≥0.45 → 本次 <0.45 | 进入低估区间 |
| 🔴 跌破 0.3 | 上次 ≥0.3 → 本次 <0.3 | 进入极度低估区间 |
| 🟡 回升至 0.3+ | 上次 <0.3 → 本次 ≥0.3 | 脱离极度低估 |
| 🟢 回升至 0.45+ | 上次 <0.45 → 本次 ≥0.45 | 脱离底部区间 |

每条通知仅在下一次穿越发生前触发一次，通过比较 `state.json` 中上次 AHR999 值实现。

### 其他买入/抄底逻辑

- **极恐预警** (24h跌幅 ≤ -15%): 黑天鹅事件，打出子弹（水平触发）
- **平稳区间** (0.45 ~ 1.2): 保持静默

## 🚀 快速开始

### 环境要求

- Python 3.7+
- 网络连接

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/TheBmy/ahr999-monitor.git
cd ahr999-monitor

# 安装依赖
pip install requests
```

### 配置环境变量

设置 WXPusher 推送参数 (可选，不设置则仅打印到控制台):

```bash
export WXPUSHER_APP_TOKEN=your_app_token
export WXPUSHER_UID=your_uid
```

或在系统环境变量中配置。

### 运行

```bash
# 单次执行
python main.py

# 定时执行 (推荐配置 Cron 或 GitHub Actions)
# 例: 每小时执行一次
0 * * * * cd /path/to/ahr999-monitor && python main.py
```

## 📁 项目结构

```
ahr999-monitor/
├── README.md              # 项目说明文档
├── main.py               # 主程序，包含所有监控逻辑
├── state.json            # 状态持久化文件（记录上次 AHR999 值）
└── .github/
    └── workflows/        # GitHub Actions 工作流
```

## 🔧 核心配置参数

在 `main.py` 中修改以下参数调整策略:

```python
CRASH_THRESHOLD = -15.0   # 买入：单日暴跌阈值 (%)
AHR999_BOTTOM = 0.45      # 买入：AHR999 抄底线
AHR999_DEEP = 0.3         # 买入：深底二级预警线
AHR999_WARN = 1.2         # 卖出：高估警戒线
ESCAPE_AHR999 = 1.5       # 逃顶：AHR999 临界值
ESCAPE_FGI = 85           # 逃顶：FGI 临界值
```

## 📊 数据来源

| 来源 | 用途 | URL |
|------|------|-----|
| Binance API | K线数据(400天)、24h涨跌幅 | api.binance.com / api.binance.us |
| alternative.me | Fear & Greed Index | api.alternative.me/fng/ |

## 🤖 自动化部署

### 使用 GitHub Actions (推荐)

项目已配置 `.github/workflows/run.yml`，每天北京时间 8:17 自动运行一次。运行后自动提交 `state.json` 以保持状态持久化。

> **注意**: 需要在仓库 Settings → Actions → General → Workflow permissions 中勾选 "Read and write permissions"，否则 workflow 无法自动提交 state.json。

### 使用 Cron + systemd

```bash
# 创建定时任务
crontab -e

# 添加每天执行一次
17 8 * * * /usr/bin/python3 /path/to/main.py
```

## ⚠️ 免责声明

- 本项目仅供学习和研究使用
- 任何基于本项目数据做出的投资决策，使用者需自行承担风险和责任
- 过去的表现不代表未来的结果
- 市场瞬息万变，指标仅供参考，不构成投资建议

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📝 许可证

MIT License

## 📧 联系方式

- GitHub: [@TheBmy](https://github.com/TheBmy)

---

**最后更新**: 2026-06-08
