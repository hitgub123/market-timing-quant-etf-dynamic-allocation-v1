# MarketTimingQuant --- 美国指数/杠杆 ETF 动态配置研究与实现规范

**版本：v1.0 FROZEN**\
**冻结日期：2026-09-13**\
**基础货币：USD**\
**状态：可直接进入编码与 Phase 1 数据审计**

> 目的：本文件既是研究报告，也是实现规格（Specification）。除非数据源客观不可得或发现定义矛盾，开发阶段不得临时改变核心研究规则。任何新增策略、参数或指标必须作为新实验加入，不得覆盖本规范中的基准实验。

------------------------------------------------------------------------

# 0. 最终投资框架结论

总资产分为两个完全独立的层级。

## 0.1 Core Portfolio：约 60%

Core **不进入 MarketTimingQuant
模型**，不做择时，不由本项目产生交易信号。

当前可继续使用的长期核心资产包括：

-   楽天・S&P 500 类低成本指数基金
-   楽天・NASDAQ-100 类指数基金
-   楽天・All Country 类全球指数基金

Core 的任务是长期复利、NISA
免税空间利用和降低整个家庭资产组合对主动模型失败的依赖。

本项目不得把 Core 的资金、收益、税费或持仓混入 Active Portfolio 的回测。

## 0.2 Active Portfolio：约 20%--40%

本项目只研究 Active Portfolio。

可交易风险资产固定为：

-   `SPY`：S&P 500，1x
-   `QQQ`：Nasdaq-100，1x
-   `SSO`：S&P 500 **每日** 2x
-   `QLD`：Nasdaq-100 **每日** 2x
-   `TQQQ`：Nasdaq-100 **每日** 3x
-   `CASH`：美元现金，Risk-Off

其中：

-   Benchmark：`SPY`, `QQQ`
-   主要增强工具：`SSO`, `QLD`
-   高风险战术工具：`TQQQ`
-   Risk-Off：`USD CASH`
-   `SPMO`：**完全排除，不进入数据、回测、优化或实盘候选**
-   半导体 ETF：**本研究完全排除**

------------------------------------------------------------------------

# 1. 核心研究问题

本项目不是寻找"过去 CAGR 最高的 ETF"。

核心问题是：

> 能否利用 SPY / QQQ / SSO / QLD / TQQQ
> 与美元现金，在严格无前视偏差、考虑交易成本与税收影响的条件下，构造出相对于
> Buy & Hold SPY / QQQ 更好的 CAGR--Max Drawdown 权衡？

最终重点寻找两类策略。

## Goal A --- Dominance

最严格目标：

-   `CAGR > QQQ Buy & Hold`
-   `MaxDD <= QQQ Buy & Hold`

如果同时满足，称为 **QQQ Dominance Candidate**。

## Goal B --- Aggressive Efficient Strategy

现实的高收益目标：

-   `CAGR >= QQQ CAGR + 3 percentage points`
-   `MaxDD <= 45%`

## Goal C --- High CAGR Candidate

辅助目标：

-   `CAGR >= 25%`
-   `MaxDD <= 50%`

Goal A 最重要。Goal B/C 不能替代 Goal
A，只用于寻找风险收益前沿上的其他有效策略。

------------------------------------------------------------------------

# 2. 为什么不直接长期全仓杠杆 ETF

`SSO / QLD / TQQQ`
的杠杆目标是**每日收益倍数**，不是长期累计收益简单乘以 2 或 3。

因此：

-   QLD ≠ "长期 QQQ × 2"
-   SSO ≠ "长期 SPY × 2"
-   TQQQ ≠ "长期 QQQ × 3"

长期结果受以下因素影响：

-   每日复利路径
-   波动率拖累（volatility drag）
-   融资/衍生成本
-   管理费
-   极端回撤
-   市场趋势持续性

因此本研究必须使用真实 ETF 的实际价格/总收益序列；不得用
`2 * QQQ daily return` 替代真实 QLD，也不得用 `3 * QQQ daily return`
替代真实 TQQQ，除非明确处于单独的 Synthetic Stress Test。

------------------------------------------------------------------------

# 3. 账户与货币假设

## 3.1 Base Currency

固定：

``` yaml
base_currency: USD
fx_module: disabled
```

所有 Active Portfolio 结果均以美元计价。

不计算：

-   USD/JPY 汇率收益
-   日元换汇成本
-   日元资产负债匹配
-   美元兑换回日元的收益/损失

原因：Active Portfolio
的美元卖出后继续作为美元资产持有，并用于未来重新购买美股。

## 3.2 NISA

NISA Core 不进入模型。

因此本项目不需要模拟：

-   NISA 年度额度
-   NISA 成长投资枠限制
-   NISA 免税额度消耗
-   NISA 内交易税务

## 3.3 Taxable Account

Active Portfolio 按日本课税账户研究。

资本利得税率参数：

``` yaml
capital_gains_tax_rate: 0.20315
```

但必须同时输出：

1.  `pre_tax`
2.  `after_tax_simplified`

税务模型详见第 12 节。

------------------------------------------------------------------------

# 4. Risk-Off 定义

Primary Risk-Off 固定为：

``` text
USD CASH
```

主模型假设：

``` yaml
cash_annual_return: 0.0
```

即 Risk-Off 期间美元现金收益固定为 0%。

这样是故意采取保守假设，避免策略因为某些年份较高的短期美债利率而虚增
Alpha。

本版本不使用：

-   10Y US Treasury
-   10Y JGB
-   长久期债券 ETF
-   黄金
-   商品
-   日元现金

原因：Risk-Off
的任务是关闭股票风险，而不是把股票风险替换成利率、久期、汇率或商品风险。

未来可以增加 `1–3 Month US T-Bill` 作为 **Sensitivity Test**，但不得替代
Cash=0% 主实验。

------------------------------------------------------------------------

# 5. 数据时间范围

## 5.1 Live ETF Main Backtest

主真实 ETF 回测：

``` text
2006-06-21 → latest available trading day
```

原则：

-   SPY、QQQ、SSO、QLD 从主回测开始使用；
-   TQQQ 只从其真实上市后才允许进入交易候选；
-   TQQQ 上市前不得生成虚构 TQQQ 交易。

这样可以保留 2007--2009 全球金融危机。

## 5.2 TQQQ Live Period

另设完全一致资产池比较：

``` text
2010-02-11 → latest
```

该区间用于：

-   SPY
-   QQQ
-   SSO
-   QLD
-   TQQQ

之间的同区间比较。

## 5.3 Synthetic Long-History Stress Test

单独建立：

``` text
2000-01-03 → latest
```

目的：让策略经历互联网泡沫。

允许根据底层指数/ETF的日收益构造：

``` text
Synthetic 2x
Synthetic 3x
```

但必须明确标记：

``` yaml
data_type: synthetic
```

Synthetic 数据只能用于：

-   压力测试
-   参数稳定性验证
-   极端熊市研究

不得与真实 ETF Live Track Record 混合后宣称为真实历史收益。

------------------------------------------------------------------------

# 6. 原始数据要求

每个真实 ETF 至少需要：

``` text
date
open
high
low
close
adjusted_close
volume
dividend
split
```

如果数据源提供 Total Return series，应同时保存。

所有原始数据必须保存原样，不得直接覆盖。

建议目录：

``` text
data/
├── raw/
│   ├── SPY.csv
│   ├── QQQ.csv
│   ├── SSO.csv
│   ├── QLD.csv
│   └── TQQQ.csv
├── processed/
├── synthetic/
└── audit/
```

------------------------------------------------------------------------

# 7. 数据审计 Gate

任何回测开始前必须通过 Data Audit。

检查：

### 7.1 日期

-   日期严格递增
-   无重复交易日
-   周末/节假日不强制补值
-   不允许无理由 forward-fill ETF 收盘价

### 7.2 OHLC

必须满足：

``` text
low <= open <= high
low <= close <= high
high >= low
```

### 7.3 Return Outlier

对极端日收益：

``` text
abs(daily_return) > 30%
```

自动进入 audit report。

不得自动删除。

必须检查：

-   split
-   reverse split
-   数据错误
-   杠杆 ETF 的真实极端行情

### 7.4 Missing Data

输出：

``` text
missing_days.csv
data_audit_report.md
```

### 7.5 Adjusted Price

策略收益优先使用能够正确处理：

-   dividend
-   split

的 total-return-compatible 数据。

交易信号若基于 Close，则必须明确是 raw close 还是 adjusted
close，并全项目保持一致。

推荐：

``` yaml
signal_price: adjusted_close
return_price: adjusted_close
```

------------------------------------------------------------------------

# 8. Benchmark

必须始终计算以下 Buy & Hold：

``` text
SPY
QQQ
SSO
QLD
TQQQ（仅真实存在区间）
```

以及：

``` text
100% CASH
```

Benchmark 不允许择时。

初始资金统一：

``` yaml
initial_capital: 100000 USD
```

初始金额只是方便阅读，不影响百分比指标。

------------------------------------------------------------------------

# 9. 回测时间与防前视规则

这是强制规则。

如果信号使用 `t` 日收盘数据，则最早只能在：

``` text
t+1
```

执行。

禁止：

``` text
使用 t 日 Close 计算信号
+
按 t 日 Close 成交
```

除非策略明确证明现实中该信号在收盘前已完全可得，否则视为 look-ahead
bias。

默认执行规则：

``` yaml
signal_time: market_close_t
execution_time: next_trading_day_open
```

如果 next open 数据质量不足，可增加：

``` text
next_close
```

作为敏感性实验，但不得替代主模型。

------------------------------------------------------------------------

# 10. 调仓频率

用户目标是 1 周至 3 个月。

冻结候选：

``` text
Weekly
Monthly
Bi-Monthly
Quarterly
```

具体定义：

``` yaml
weekly: first_trading_day_of_week
monthly: first_trading_day_of_month
bimonthly: first_trading_day_every_2_months
quarterly: first_trading_day_of_calendar_quarter
```

信号使用上一交易日已经完成的数据。

Daily Rebalance：

``` text
EXCLUDED FROM PRIMARY SEARCH
```

原因：

-   增加噪声
-   增加换手
-   增加税负
-   更容易过拟合

可在后续独立研究，不进入 v1 主实验。

------------------------------------------------------------------------

# 11. 交易成本

交易成本必须参数化。

主回测至少运行：

``` yaml
commission_bps: 0
slippage_bps: 5
```

并做敏感性测试：

``` text
0 bps
5 bps
10 bps
20 bps
```

每次买卖都计算：

``` text
transaction_cost =
traded_notional * (commission_bps + slippage_bps) / 10000
```

不得因为券商当前手续费低就永久假设交易成本为零。

------------------------------------------------------------------------

# 12. 税务模型

必须同时输出税前与简化税后结果。

## 12.1 Pre-Tax

``` yaml
tax_mode: none
```

用于判断策略本身是否存在 Alpha。

## 12.2 Simplified Japan Taxable

``` yaml
tax_mode: simplified_japan_taxable
capital_gains_tax_rate: 0.20315
```

使用 realized gain accounting。

每次卖出：

``` text
realized_gain = proceeds - allocated_cost_basis
```

如果：

``` text
realized_gain > 0
```

先使用累计 loss pool 抵扣。

剩余正收益：

``` text
tax = taxable_realized_gain * 0.20315
```

如果亏损：

``` text
loss_pool += abs(realized_loss)
```

### 成本基础

v1 固定使用：

``` yaml
cost_basis_method: average_cost
```

### 税款扣除

为了保守：

``` yaml
tax_payment_timing: immediate_on_realization
```

即产生应税已实现收益时立即从现金扣税。

这不是完整日本报税模拟，而是用于评估高换手策略的税负敏感度。

最终报告必须明确标注：

``` text
Simplified Tax Model — not tax filing calculation
```

------------------------------------------------------------------------

# 13. Portfolio Engine

允许同时持有多个 ETF。

约束：

``` yaml
long_only: true
shorting: false
external_margin: false
total_weight_max: 1.0
min_weight: 0.0
```

注意：

持有 QLD/TQQQ 本身已经包含产品内部杠杆，但组合层面：

``` text
ETF weights sum <= 100%
```

不得再使用券商融资把 ETF 权重提高到 \>100%。

例如允许：

``` text
50% QQQ
30% QLD
20% CASH
```

不允许：

``` text
100% QLD
50% TQQQ
```

------------------------------------------------------------------------

# 14. Phase 0 --- Buy & Hold Baseline

第一步禁止择时。

分别计算：

``` text
100% SPY
100% QQQ
100% SSO
100% QLD
100% TQQQ
100% CASH
```

输出所有核心指标。

这是整个项目的不可修改 baseline。

------------------------------------------------------------------------

# 15. Phase 1 --- Static Allocation Efficient Frontier

先证明"静态组合"能做到什么，再研究择时。

## 15.1 两资产扫描

必须扫描：

``` text
SPY + SSO
SPY + QLD
QQQ + SSO
QQQ + QLD
SSO + QLD
QQQ + CASH
QLD + CASH
SSO + CASH
```

权重：

``` text
0%, 5%, 10%, ..., 100%
```

例如：

``` text
QQQ 100 / QLD 0
QQQ 95 / QLD 5
...
QQQ 0 / QLD 100
```

## 15.2 三资产扫描

重点：

``` text
SPY + QQQ + SSO
SPY + QQQ + QLD
QQQ + SSO + QLD
QQQ + QLD + CASH
SPY + SSO + CASH
```

权重步长：

``` yaml
weight_step: 0.10
```

所有权重之和必须等于 1。

## 15.3 Rebalance

分别测试：

``` text
Monthly
Quarterly
```

不要一开始搜索所有频率，以控制 multiple testing。

## 15.4 输出

生成：

``` text
static_frontier.csv
static_frontier_pre_tax.png
static_frontier_after_tax.png
```

横轴：

``` text
Max Drawdown
```

纵轴：

``` text
CAGR
```

标出：

``` text
SPY
QQQ
SSO
QLD
```

------------------------------------------------------------------------

# 16. Phase 2 --- Simple Trend Filter

只有 Phase 1 完成后才进入。

首先只研究一个最简单信号：

``` text
200-day moving average
```

## Strategy 2A --- QQQ Trend

``` text
if QQQ close > QQQ MA200:
    hold QQQ
else:
    hold CASH
```

## Strategy 2B --- QLD Trend

信号仍使用底层 QQQ：

``` text
if QQQ close > QQQ MA200:
    hold QLD
else:
    hold CASH
```

不得使用 QLD 自身 MA200 作为主版本。

原因：信号应尽量来自未杠杆底层市场。

## Strategy 2C --- SSO Trend

``` text
if SPY close > SPY MA200:
    hold SSO
else:
    hold CASH
```

------------------------------------------------------------------------

# 17. Phase 3 --- Parameter Stability

只有 MA200 基准完成后才能搜索邻域。

MA 参数：

``` text
150
175
200
225
250
```

目的不是找到"最佳 MA"。

目标是判断：

> 策略是否在一个宽参数区域内都有效。

如果只有：

``` text
MA = 187
```

特别好，而附近参数明显失败，则视为高过拟合风险。

输出：

``` text
ma_parameter_surface.csv
ma_stability_heatmap.png
```

------------------------------------------------------------------------

# 18. Phase 4 --- Absolute Momentum

测试：

``` text
6M
9M
12M
```

定义使用交易日近似：

``` text
6M  = 126 trading days
9M  = 189 trading days
12M = 252 trading days
```

绝对动量：

``` text
momentum_N = price_t / price_(t-N) - 1
```

基础规则：

``` text
if momentum_N > 0:
    Risk-On
else:
    CASH
```

分别用于：

``` text
SPY -> SSO
QQQ -> QLD
```

------------------------------------------------------------------------

# 19. Phase 5 --- Relative Momentum

比较：

``` text
SPY
QQQ
```

不得比较杠杆 ETF 自身的历史动量来决定谁更强。

计算：

``` text
momentum_SPY
momentum_QQQ
```

如果两者都 \<= 0：

``` text
CASH
```

否则选择动量更强的底层。

第一版：

``` text
SPY strongest -> SPY
QQQ strongest -> QQQ
```

第二版：

``` text
SPY strongest -> SSO
QQQ strongest -> QLD
```

这样可以直接检验：

> "相对动量 + 2x" 是否比 Buy & Hold QQQ 提供更好的风险收益。

------------------------------------------------------------------------

# 20. Phase 6 --- Volatility Targeting

只有前面简单策略完成后才允许加入。

Realized volatility：

``` text
daily_return = close_t / close_(t-1) - 1

realized_vol_20 =
std(last 20 daily returns) * sqrt(252)
```

测试窗口：

``` text
20
40
60 trading days
```

目标波动率只允许使用宽网格：

``` text
10%
15%
20%
25%
30%
```

目标风险权重：

``` text
risk_weight = target_vol / realized_vol
```

并限制：

``` text
0 <= risk_weight <= 1
```

剩余权重放 CASH。

禁止组合层额外融资。

------------------------------------------------------------------------

# 21. Phase 7 --- Dynamic Leverage State Machine

这是项目最终重点之一。

状态定义必须由**底层 SPY / QQQ 的趋势、动量和波动率**决定，而不是由杠杆
ETF 自身走势决定。

状态：

``` text
RISK_OFF
NORMAL
LEVERAGED
AGGRESSIVE
```

资产映射：

``` text
RISK_OFF   -> CASH
NORMAL     -> SPY and/or QQQ
LEVERAGED -> SSO and/or QLD
AGGRESSIVE -> limited TQQQ allocation
```

### 重要

v1 不预先写死诸如：

``` text
VIX < 18
RSI > 70
```

这样的经验阈值。

状态规则必须从前面已经通过 OOS 验证的简单因子组合构建。

优先级：

``` text
Trend
→ Absolute Momentum
→ Relative Momentum
→ Realized Volatility
```

禁止为了提高历史 CAGR 随意增加技术指标。

------------------------------------------------------------------------

# 22. TQQQ 解锁规则

TQQQ **最后才进入研究**。

在以下条件全部满足前，不允许优化 TQQQ：

1.  QQQ/QLD 动态模型已完成；
2.  已有完整 Walk-Forward；
3.  已完成参数稳定性测试；
4.  QLD 策略在 OOS 中相对 QQQ 有改善；
5.  已完成交易成本敏感性；
6.  已完成税后结果。

TQQQ 进入后，初始最大组合权重：

``` yaml
tqqq_max_weight: 0.20
```

敏感性测试：

``` text
5%
10%
15%
20%
```

v1 禁止：

``` text
100% TQQQ dynamic strategy
```

作为最终推荐策略。

可以计算其 benchmark，但不能因为历史收益高而自动成为候选。

------------------------------------------------------------------------

# 23. Walk-Forward / OOS

任何参数策略必须进行 Out-of-Sample 验证。

禁止：

``` text
2006–2026 全样本找最佳参数
→ 再报告同一段历史表现
```

推荐主方案：

``` text
Expanding Window Walk-Forward
```

初始训练：

``` text
2006-06-21 → 2012-12-31
```

之后：

``` text
Train: all history available before test year
Test: next 1 calendar year
```

例如：

``` text
Train 2006–2012 -> Test 2013
Train 2006–2013 -> Test 2014
...
Train 2006–2025 -> Test 2026 YTD
```

最终 OOS Equity Curve 必须由所有 Test 段拼接得到。

所有核心结论以：

``` text
OOS result
```

为主。

Full Sample 只能作为描述性结果。

------------------------------------------------------------------------

# 24. Parameter Selection

训练窗口内禁止单纯最大化 CAGR。

默认 objective：

``` text
maximize Calmar Ratio
```

但加入约束：

``` text
minimum CAGR
maximum acceptable MaxDD
```

并同时保存：

``` text
CAGR
MaxDD
Sharpe
Sortino
Calmar
```

如果多个参数性能接近：

> 选择更简单、更慢、更接近参数区域中心的方案。

禁止选择孤立尖峰参数。

------------------------------------------------------------------------

# 25. 核心绩效指标

每个策略必须计算：

## Return

``` text
CAGR
Total Return
Annual Return
Monthly Return
```

CAGR：

``` text
CAGR = (EndingValue / StartingValue)^(365.25 / calendar_days) - 1
```

## Risk

``` text
Annualized Volatility
Max Drawdown
Worst Day
Worst Week
Worst Month
Worst Calendar Year
```

Drawdown：

``` text
running_peak_t = max(equity_0 ... equity_t)
drawdown_t = equity_t / running_peak_t - 1
```

``` text
MaxDD = min(drawdown_t)
```

## Risk-Adjusted

``` text
Sharpe
Sortino
Calmar
Ulcer Index
```

Calmar：

``` text
Calmar = CAGR / abs(MaxDD)
```

## Recovery

``` text
Max Drawdown Start
Max Drawdown Trough
Recovery Date
Recovery Trading Days
Time Under Water
```

## Stability

``` text
Rolling 1Y Return
Rolling 3Y CAGR
Rolling 5Y CAGR
Rolling 10Y CAGR
Rolling 1Y MaxDD
```

## Trading

``` text
Number of Trades
Annual Turnover
Average Holding Period
Win Rate
Tax Paid
Transaction Costs
```

------------------------------------------------------------------------

# 26. Efficient Frontier

最终核心图：

``` text
X = abs(Max Drawdown)
Y = CAGR
```

越靠：

``` text
左上
```

越理想。

必须标注：

``` text
SPY
QQQ
SSO
QLD
TQQQ
```

以及所有通过 OOS Gate 的策略。

建立 Pareto Frontier。

如果策略 A：

``` text
CAGR_A >= CAGR_B
AND
MaxDD_A <= MaxDD_B
```

且至少一个严格优于，则 B 被 A 支配。

最终优先研究 **non-dominated strategies**。

------------------------------------------------------------------------

# 27. QQQ Dominance Gate

策略只有满足以下 OOS 条件才可以称为：

``` text
QQQ Dominance Candidate
```

必须同时：

``` text
CAGR_strategy > CAGR_QQQ
MaxDD_strategy <= MaxDD_QQQ
```

此外要求：

``` text
Calmar_strategy > Calmar_QQQ
```

如果只提高 CAGR 但 MaxDD 明显恶化：

``` text
NOT DOMINANT
```

如果只降低 MaxDD 但 CAGR 下降：

``` text
DEFENSIVE IMPROVEMENT
```

不要混淆。

------------------------------------------------------------------------

# 28. Robustness Tests

最终候选必须经历：

### 28.1 Transaction Cost

``` text
0 / 5 / 10 / 20 bps
```

### 28.2 Execution Delay

``` text
Next Open
Next Close
Signal + 2 Trading Days
```

### 28.3 Rebalance Frequency

``` text
Weekly
Monthly
Quarterly
```

### 28.4 Parameter Perturbation

所有关键参数：

``` text
-20%
-10%
base
+10%
+20%
```

附近都必须保持合理表现。

### 28.5 Start-Date Perturbation

回测起点分别向后移动：

``` text
3 months
6 months
12 months
24 months
```

避免结果依赖某个幸运起点。

### 28.6 Tax

``` text
Pre-tax
20.315% simplified taxable
```

------------------------------------------------------------------------

# 29. Regime Analysis

至少单独报告：

``` text
2007–2009 Global Financial Crisis
2011 Risk-Off
2015–2016
2018 Q4
2020 COVID Crash
2022 Rate-Hike Bear Market
2023–latest Growth/AI Bull Market
```

Synthetic Stress Test 额外报告：

``` text
2000–2002 Dot-com Crash
```

每个 regime 输出：

``` text
Return
MaxDD
Worst Month
Recovery Time
Turnover
```

目标不是要求每个时期都跑赢，而是确认策略失败模式。

------------------------------------------------------------------------

# 30. 禁止事项

以下行为视为研究失败：

1.  Look-ahead bias
2.  Survivorship bias（在涉及股票池时；本 v1 主要为 ETF）
3.  用未来数据填补历史信号
4.  同日收盘信号、同日收盘成交
5.  找到最佳参数后只报告最佳参数
6.  隐藏失败策略
7.  只报告 CAGR 不报告 MaxDD
8.  只报告税前结果
9.  用 Synthetic 结果冒充真实 ETF 结果
10. 把 QLD/TQQQ 简化成长期 2x/3x QQQ
11. 因为某一段牛市表现漂亮而删除 2008/2022 等熊市
12. 为提高结果不断增加技术指标
13. 在看到 OOS 后反复修改规则再称其为 OOS
14. 将 60% Core Portfolio 纳入模型优化
15. 加入 SPMO
16. 加入半导体 ETF

------------------------------------------------------------------------

# 31. 软件架构

推荐 Python 项目结构：

``` text
market_timing_quant/
│
├── config/
│   ├── base.yaml
│   ├── costs.yaml
│   └── experiments.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   └── audit/
│
├── src/
│   ├── data_loader.py
│   ├── data_audit.py
│   ├── indicators.py
│   ├── signals.py
│   ├── portfolio.py
│   ├── execution.py
│   ├── tax.py
│   ├── backtest.py
│   ├── metrics.py
│   ├── walk_forward.py
│   ├── optimization.py
│   ├── robustness.py
│   └── reporting.py
│
├── tests/
│   ├── test_data.py
│   ├── test_execution.py
│   ├── test_tax.py
│   ├── test_metrics.py
│   ├── test_no_lookahead.py
│   └── test_portfolio.py
│
├── experiments/
│   ├── phase0_buy_hold.py
│   ├── phase1_static_frontier.py
│   ├── phase2_ma200.py
│   ├── phase3_ma_stability.py
│   ├── phase4_absolute_momentum.py
│   ├── phase5_relative_momentum.py
│   ├── phase6_vol_target.py
│   ├── phase7_dynamic_leverage.py
│   └── phase8_tqqq.py
│
└── reports/
    ├── tables/
    ├── figures/
    └── final/
```

------------------------------------------------------------------------

# 32. 配置文件基准

`config/base.yaml` 至少包含：

``` yaml
base_currency: USD
initial_capital: 100000

assets:
  benchmark:
    - SPY
    - QQQ

  leveraged:
    - SSO
    - QLD
    - TQQQ

  risk_off:
    - CASH

excluded:
  - SPMO
  - semiconductor_etfs

cash:
  annual_return: 0.0

portfolio:
  long_only: true
  external_margin: false
  max_total_weight: 1.0
  tqqq_max_weight: 0.20

execution:
  signal_time: close
  fill_time: next_open
  slippage_bps: 5
  commission_bps: 0

tax:
  capital_gains_rate: 0.20315
  cost_basis: average
  payment_timing: immediate

backtest:
  live_start: "2006-06-21"
  tqqq_common_start: "2010-02-11"
  synthetic_start: "2000-01-03"

rebalance:
  primary:
    - weekly
    - monthly
    - quarterly
```

------------------------------------------------------------------------

# 33. 单元测试最低要求

代码不得只依赖"图看起来正常"。

必须测试：

## No Look-Ahead

人为构造价格序列，确保：

``` text
signal(t)
```

绝不会影响：

``` text
execution <= t
```

## Drawdown

人工 equity：

``` text
100 -> 120 -> 60 -> 90
```

必须得到：

``` text
MaxDD = -50%
```

## Tax

测试：

``` text
+1000 gain
-400 loss
+500 gain
```

确认 loss pool 正确抵扣。

## Transaction Cost

固定交易金额，检查 bps 成本精确。

## Portfolio Weight

任何日期：

``` text
sum(weights) <= 1 + floating_point_tolerance
```

## TQQQ Availability

TQQQ 上市前：

``` text
weight_TQQQ == 0
```

必须强制成立。

------------------------------------------------------------------------

# 34. 每个实验必须输出

每次 experiment 生成唯一 `run_id`。

例如：

``` text
20260913_153000_phase2_qld_ma200
```

保存：

``` text
config_snapshot.yaml
metrics_pre_tax.csv
metrics_after_tax.csv
equity_curve.csv
drawdown.csv
positions.csv
trades.csv
tax_ledger.csv
parameter_results.csv
```

图表：

``` text
equity_curve.png
drawdown.png
rolling_returns.png
rolling_maxdd.png
cagr_maxdd_scatter.png
```

这样任何结果都可以复现。

------------------------------------------------------------------------

# 35. 实验执行顺序

严格按以下顺序：

``` text
Phase 0
Buy & Hold Benchmark
        ↓
Phase 1
Static Allocation / Efficient Frontier
        ↓
Phase 2
MA200 Simple Trend
        ↓
Phase 3
MA Parameter Stability
        ↓
Phase 4
Absolute Momentum
        ↓
Phase 5
Relative Momentum
        ↓
Phase 6
Volatility Targeting
        ↓
Phase 7
Dynamic Leverage
        ↓
Walk-Forward / OOS
        ↓
Robustness Tests
        ↓
Tax / Cost Stress
        ↓
Phase 8
TQQQ Limited Tactical Allocation
        ↓
Final Pareto Frontier
```

不得提前跳到复杂模型。

------------------------------------------------------------------------

# 36. MVP 首轮实验

如果现在开始写代码，第一轮只实现以下内容：

### MVP-1

下载、清洗并审计：

``` text
SPY
QQQ
SSO
QLD
TQQQ
```

### MVP-2

实现：

``` text
Buy & Hold
CASH
transaction costs
metrics
```

### MVP-3

验证：

``` text
SPY / QQQ / SSO / QLD
2006–latest
```

和：

``` text
SPY / QQQ / SSO / QLD / TQQQ
2010–latest
```

### MVP-4

实现：

``` text
QQQ MA200 -> QQQ / CASH
QQQ MA200 -> QLD / CASH
SPY MA200 -> SSO / CASH
```

### MVP-5

输出：

``` text
CAGR
MaxDD
Calmar
Sharpe
Sortino
Recovery
Turnover
```

### MVP-6

画：

``` text
CAGR vs MaxDD
```

只有这些全部正确后，才进入参数搜索。

------------------------------------------------------------------------

# 37. 第一批必须回答的问题

MVP 完成后，报告首先回答：

### Q1

``` text
Buy & Hold QLD
```

相比：

``` text
Buy & Hold QQQ
```

多获得多少 CAGR？

多承担多少 MaxDD？

### Q2

``` text
Buy & Hold SSO
```

相比：

``` text
Buy & Hold SPY
```

多获得多少 CAGR？

多承担多少 MaxDD？

### Q3

``` text
QLD + MA200 Risk-Off
```

能否保留 QLD 的大部分 CAGR，同时显著降低 MaxDD？

### Q4

``` text
SSO + MA200 Risk-Off
```

是否比 QLD 方案拥有更好的 Calmar？

### Q5

有没有策略满足：

``` text
CAGR > QQQ
AND
MaxDD <= QQQ
```

如果没有，必须明确回答：

``` text
No Dominance Found
```

而不是继续调参直到找到一个。

------------------------------------------------------------------------

# 38. 最终策略选择原则

最终不选择：

``` text
最高 CAGR
```

而从 OOS Pareto Frontier 中选择。

优先级：

1.  是否通过 QQQ Dominance Gate
2.  OOS CAGR
3.  OOS MaxDD
4.  Calmar
5.  参数稳定性
6.  税后收益
7.  Turnover
8.  Recovery Time
9.  执行简单程度

如果两个策略表现接近：

> 永远选择规则更简单、交易更少、参数更稳定的那个。

------------------------------------------------------------------------

# 39. 实盘前额外 Gate

任何策略进入真实资金前必须：

-   完成 Live ETF OOS
-   完成 2000--2002 Synthetic Stress Test
-   完成 2008 Crisis 检验
-   完成 2020 Crash 检验
-   完成 2022 Bear Market 检验
-   通过 20 bps 成本压力
-   通过 +1 日执行延迟
-   参数附近无崩溃
-   税后仍具有合理优势
-   明确最大可能回撤
-   明确连续亏损时间
-   明确 TQQQ 最大权重

随后应先进行：

``` text
paper trading / shadow portfolio
```

再考虑真实资金。

------------------------------------------------------------------------

# 40. 当前投资层面的最终结论

在研究结果出来前，不因为历史 CAGR 而大幅修改 60% Core。

当前逻辑：

``` text
TOTAL ASSETS
│
├── ~60% CORE
│   ├── S&P 500
│   ├── Nasdaq-100
│   └── All Country
│
│   Buy & Hold
│   NISA 优先
│   不进入模型
│
└── ~20–40% ACTIVE
    │
    ├── SPY / QQQ
    │      1x
    │
    ├── SSO / QLD
    │      2x enhancement
    │
    ├── TQQQ
    │      <= 20% of Active in v1
    │      tactical only
    │
    └── USD CASH
           Risk-Off
           0% assumed return
```

研究结果可能最终证明：

-   QLD 值得长期持有；
-   SSO 的风险收益比更好；
-   简单 QQQ Buy & Hold 已经很难击败；
-   MA200 有效；
-   MA200 无效；
-   动态杠杆有效；
-   动态杠杆税后无效；
-   TQQQ 没有增加风险调整后收益。

**所有这些结果都允许。**

研究目标不是证明某个预设观点，而是找出经得住
OOS、税费、熊市和参数扰动后仍然存在的收益来源。

------------------------------------------------------------------------

# 41. Definition of Done

项目 v1 只有同时满足以下条件才算完成：

-   [ ] 5 个 ETF 数据审计完成
-   [ ] Buy & Hold benchmark 完成
-   [ ] Static Efficient Frontier 完成
-   [ ] MA200 完成
-   [ ] MA stability 完成
-   [ ] Absolute Momentum 完成
-   [ ] Relative Momentum 完成
-   [ ] Volatility Targeting 完成
-   [ ] Dynamic Leverage 完成
-   [ ] TQQQ Tactical 完成
-   [ ] Walk-Forward OOS 完成
-   [ ] Pre-tax / After-tax 均完成
-   [ ] Transaction-cost sensitivity 完成
-   [ ] Execution-delay sensitivity 完成
-   [ ] Parameter stability 完成
-   [ ] Regime analysis 完成
-   [ ] Synthetic 2000 Dot-com stress test 完成
-   [ ] Pareto Frontier 完成
-   [ ] QQQ Dominance Gate 完成
-   [ ] 所有 run 可复现
-   [ ] 单元测试通过
-   [ ] 最终报告明确说明是否找到真正支配 QQQ/SPY 的策略

------------------------------------------------------------------------

## Frozen Decisions Summary

``` yaml
project: MarketTimingQuant ETF Dynamic Allocation

base_currency: USD
fx: disabled

core_portfolio:
  approximate_weight: 0.60
  included_in_model: false

active_assets:
  - SPY
  - QQQ
  - SSO
  - QLD
  - TQQQ

excluded:
  - SPMO
  - semiconductor_etfs

risk_off:
  asset: USD_CASH
  annual_return: 0.0

benchmark:
  - SPY
  - QQQ

primary_focus:
  - SSO
  - QLD
  - TQQQ

leverage:
  portfolio_external_margin: false
  tqqq_initial_max_weight: 0.20

rebalance_horizon:
  minimum: weekly
  maximum: quarterly

taxable_account:
  simplified_capital_gains_tax_rate: 0.20315

primary_objective:
  CAGR: maximize
  MaxDrawdown: constrain_and_minimize

gold_standard:
  CAGR_above_QQQ: true
  MaxDD_not_worse_than_QQQ: true

research_principle:
  - simplicity_first
  - no_lookahead
  - live_data_first
  - walk_forward_OOS
  - parameter_stability
  - report_failures
  - tax_and_cost_aware
```

**END OF FROZEN SPECIFICATION**
