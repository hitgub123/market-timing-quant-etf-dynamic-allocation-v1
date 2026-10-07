# Tiingo 来源验收外部裁定记录

**裁定日：** 2026-10-07（Asia/Tokyo）
**裁定方：** Muse（本仓库新的持续维护 AI）
**裁定对象：** 2026-10-06 Tiingo PRE_START publication observation
**性质：** 本文件是审计裁定记录，不是验收通过，不是 Final Freeze，不创建正式观测，不计算任何信号或收益。

## 独立性声明

裁定方未参与 2026-10-06 观测的设计与执行（观测方案冻结于提交
`229d6246423c1859191e3732196aad78ef317297`，中断恢复提交为
`29ed1f820dc04a18a213b605da86ef2392dc1b7a`，均为前任 AI 工作）。
本次裁定仅基于仓库内已提交证据做只读审查。

结构性说明：前任 AI 今后不可用，裁定方将同时承担本项目的后续维护，
"审计者"与"执行者"为同一 AI，弱于原有的双 AI 互审结构。为此本裁定
严格限定为机械门禁适用，不做任何自由裁量放行；每条结论均附证据索引，
以便用户或任何第三方复核。

## 依据证据

1. `docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md` —— "Latency gate" 节：
   "The check must stay within the accepted four-poll budget"（四次轮询预算）。
2. `docs/PAPER_TRADING_TIINGO_FREE_ACCEPTANCE_PLAN.md` —— 自认：
   "the pre-existing source-freeze readiness document requires an accepted
   four-poll budget, while this Tiingo-specific plan did not explicitly
   supersede it"（未明确废止旧约束）。
3. `reports/tiingo_prestart_latency_evidence.json` —— 实际执行：
   5 个固定轮询时点（2026-10-06T20:00/21:30/22:00/23:00Z、
   2026-10-07T00:00Z，即美东 16:00/17:30/18:00/19:00/20:00），
   QQQ/QLD 各 5 次，共 10 个请求；16:00 时点两标的均无当日记录，
   17:30 起均有完整记录。
4. `reports/paper_trading_tiingo_free_account_acceptance_audit.md`
   第 80–96 行 —— 承认四/五轮询冲突与响应头缺口，明确不断言通过。

## 逐项裁定

### 问题 1：「四次轮询」是总请求数，还是每标的 / 每时点？

**裁定：本案中无需确定，不影响结论。**

观测实际使用了 5 个轮询时点、10 个请求。在任何合理解释下均超出预算：
每标的 4 次（实际每标的 5 次）、总共 4 个时点（实际 5 个）、
总共 4 个请求（实际 10 个）。解释争议不改变"超出预算"这一事实。

为杜绝后患，新的测量方案必须明确采用最严口径——**总请求数 ≤ 4**
（例如 2 标的 × 2 时点），并在冻结时写死，不得留解释空间。

### 问题 2：Tiingo 专项计划是否具备覆盖（废止旧约束）效力？

**裁定：否。**

计划原文自认 "did not explicitly supersede it"，审计报告亦承认冲突未解决。
在没有明确废止记录的情况下，旧约束继续有效。事后把第五时点解释掉、
或重新定义"四次"含义，均属追认，本裁定不予采纳。

### 问题 3：响应头缺失是否为致命缺口？

**裁定：对"首次可用性"这一待测问题本身，非致命；但属程序性缺口，
新观测必须补齐。**

计划要求记录 `returned_last_date` 与安全速率限制头。实际观测记录了
`content_type` 而非 allow-list 速率头。`returned_last_date` 可从已归档的
原始响应字节重建；速率头无法事后重建，亦不得捏造。

鉴于问题 1、2 已使本次观测不能通过，本问题不独立决定成败。
新观测的冻结方案必须包含 allow-list 响应头的记录要求。

### 问题 4：若需重观测，应保留哪些基线 / 首次可用性证据？

**保留（原样，不得改写、不得删除）：**

- 10 份原始响应的私有归档
  （`~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-06/`，
  仓库外）——作为历史证据保留；
- 首次可用性区间观测事实（美东 16:00 缺席、17:30 已有）——仅可作为
  新方案设计的**非约束性先验**，不得作为验收证据引用；
- 账户能力验收结论（QQQ/QLD 各 438 个完整会话、原始/调整 OHLCV、
  股息拆股字段完备，`reports/tiingo_free_account_acceptance.json`）——
  不受本次裁定影响，继续有效。

**新观测的冻结要求**（执行前必须先冻结，缺一不可）：未来、尚未开盘的
美国交易日；标的；轮询时点与**总请求预算（≤ 4）**；截止时间；
预期交易日与时区；成功 / 失败分类；外部原始字节归档；
allow-list 安全响应头；`returned_last_date`。全程性能盲，
不计算 MA200、信号、收益或来源优劣。网络断开或漏检原样记录，
不得补造时间戳。

## 总裁定

- 2026-10-06 Tiingo 观测：数据采集事件本身记为 `OBSERVATION_COMPLETE`，
  但**不满足**冻结验收合同，**不得**作为来源通过的依据，
  不得倒填、追认或重命名为通过。
- 来源门禁维持：`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`。
- Tiingo 不得晋升为权威来源；不得启动纸上交易时钟、36 个月时钟、
  Final Freeze、引擎、调度器或 Phase 9。
- 下一步（按顺序）：冻结新的合规 PRE_START 测量方案 →
  在未来交易日执行 → 重新走来源验收。是否执行新的联网观测，
  需用户明确委托；本裁定本身不授权任何 API 请求。

## 复核指引

任一结论均可按"依据证据"所列文件独立复核。关键可验证事实：
证据 JSON 中 `polls` 数组共 10 条、`schedule_utc` 共 5 个时点；
计划文档中 "did not explicitly supersede it" 原文；
审计报告中 "We therefore do not assert `SOURCE_ACCEPTANCE_PASS`
without external adjudication" 原文。
