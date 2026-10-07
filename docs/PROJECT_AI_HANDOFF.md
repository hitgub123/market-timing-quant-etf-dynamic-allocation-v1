# 项目交接说明（供后续 AI 维护）

**状态核对日：2026-10-07（Asia/Tokyo）。** 本文是导航和待办说明，不是新的协议、审计结论或授权。接手时必须以当时的 Git 状态和下列原始证据重新核对；不要把本文的日期、测试数或工作分支 HEAD 当作永久不变的事实。

## 一句话结论

本项目已完成并冻结 Phase 0–8D 的历史量化研究，结论是“值得做无本金的前瞻性纸上验证，但证据不足以实盘部署”。纸上验证协议仍是待审草案，尚无正式前瞻性观测。当前卡在**免费行情源 Tiingo 的 PRE_START 来源验收**：账户和数据字段能力已验证，2026-10-06 的发布时延观测也取得了数据，但轮询次数与较早冻结的约束存在冲突，且响应诊断元数据不完整。当前机械门禁为 `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`；**不能宣告来源通过，不能启动纸上交易时钟。**

## 1. 项目是什么

仓库 `market-timing-quant-etf-dynamic-allocation-v1` 研究美国 ETF 的机械择时/配置规则，包括 QQQ 的 200 日均线、杠杆 ETF 持有、税后与交易成本核算，并以严格的样本外和统计审计评估。历史研究的终点是 Phase 8D，不是自动投资系统，也不是交易建议。

拟议的唯一主前瞻模型为 `FIXED_MA200_QQQ_TO_QLD`：用已完成交易日的 QQQ 分红/拆股调整收盘价计算 200 个观测值的简单均线，收盘决策，最早在下一合格交易日开盘执行；高于均线持有 QLD，否则持有现金。历史模型假设包括 0 bps 佣金、5 bps 滑点及简化税务规则。**这些不是在此阶段可重新优化的参数。** 每周主观察、其他频率影子观察只是待冻结的纸上协议设计，不能说历史研究选出了每周频率。

## 2. 哪些工作已经结束

| 边界 | 已确认状态 | 首要依据 |
|---|---|---|
| Phase 0–8D 历史研究 | 外部审计接受，Research v1.0 冻结 | `reports/research_v1_freeze_manifest.json`、`docs/RESEARCH_V1_FROZEN.md` |
| 研究版本 | 标签 `research-v1.0-final`，冻结提交 `2b2bf987f2e00540412d263a8ef39566af1d1e2a` | 冻结清单及其 SHA-256 伴随文件 |
| Phase 8D 总结 | `PROMISING_BUT_INSUFFICIENT`；仅允许准备无本金前瞻验证，不构成实盘建议 | `reports/runs/20260915_phase8d_final_research_verdict/phase8d_final_research_verdict.md` |
| 前瞻协议 | `DRAFT FOR AUDIT — NOT FROZEN`；尚未实施，未采集正式观测 | `docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md` |
| 来源准备 | `SOURCE_NOT_READY_FOR_FINAL_FREEZE` | `docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md` |

冻结清单包含规范运行 ID、原始 Parquet 快照和接受产物的哈希。不要修改 Phase 0–8D 代码、原始数据、规范报告、冻结清单或已接受的经济路径。`README.md` 的概览可能滞后于 Phase 8D；上述冻结清单和审计报告优先。

## 3. 免费数据源走到了哪里

| 候选 | 已观察到的事实 | 目前角色 |
|---|---|---|
| Alpha Vantage Free | 所需账户权限没有通过既有验收 | 不是当前执行依赖 |
| EODHD Free | 历史字段/原始字节能力通过；2026-10-01 的 PRE_START 观测在既定 +15 分钟截止前未取得目标日记录 | 未接受为权威来源；不得拿该失败观测替 Tiingo 背书 |
| Massive Basic Free | 可作核对，但其拆股调整数据不能替代要求的分红调整收盘价 | 仅核对来源，不是权威信号来源 |
| Tiingo Free | QQQ、QLD 各返回 438 个完整交易日（2025-01-02 至 2026-10-01），原始/调整 OHLCV、股息、拆股字段俱全；四份账户响应原始字节在 Git 外归档并可精确重建 | 账户能力通过，**来源验收尚未通过** |

Tiingo 对 2026-10-06 交易日的观测：16:00 美东（次日 05:00 日本）两只 ETF 均无该日记录；17:30 美东（06:30 日本）两只均有完整记录；18:00、19:00、20:00 美东的后续检查也有记录。实际发布时间只能定位在两次观测之间，不能冒充精确发布时间或确定性 SLA。十次响应的原始字节先在仓库外存档、再解析，已做哈希重建。细节见 `reports/tiingo_free_account_acceptance.json`、`reports/tiingo_prestart_latency_evidence.json` 和 `reports/paper_trading_tiingo_free_account_acceptance_audit.md`。

**阻塞原因不是“Tiingo 没有数据”。** `docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md` 保留了“最多四次轮询”的已接受约束，而后来的 Tiingo 专项计划没有明确废止它；实际预先固定并执行了五个时点、每时点两个标的，共十个请求。既有诊断记录还缺少该次响应的安全速率限制头；最后返回日期可从原始响应重建，缺失的头不能事后捏造。无论数据出现得多早，都不能倒删第五时点、事后改变“四次”的含义或自行将门禁改为 PASS。须先由外部来源审计裁定这些问题；现存观测保留为原样证据。

## 4. 下一步，按门禁顺序执行

1. **接手核对，不变更结果。** 确认工作树、HEAD 和 `research-v1.0-final` 标签；阅读本文件第 6 节列出的规范证据；检查冻结清单哈希、来源门禁和测试状态。本文写成时工作树干净、`main` HEAD 为 `fe4aa90d9f1b8c7da9eea0b27b92f0fb2ef16df5`。后续提交会改变 HEAD，不能因此认定冻结研究被改变。
2. **请求外部来源审计先裁定原有观测。** 明确“四次轮询”是总请求数还是每标的/每时点的次数、Tiingo 专项计划是否具备覆盖效力、响应头缺失是否是致命缺口，以及若需重观测应保留哪些基线/首次可用性证据。裁定须写成可追溯记录，不能由 AI 为了通过验收追认旧观测。
3. **仅在裁定要求重观测时，设计新的 PRE_START 测量。** 对一个未来、尚未开盘的美国交易日，事前固定标的、轮询时点、总请求预算、截止时间、预期交易日与时区、成功/失败分类、外部原始字节归档、允许记录的安全响应头和 `returned_last_date`。如“四次”被裁定为总请求数，可提出 QQQ/QLD 各两次请求的方案，但是否足以测量首次可用性及是否满足合同须先获审计确认；不能把这个例子当作已批准计划。网络断开或漏检必须原样记录，不能补造时间戳。
4. **运行性能盲的来源验收。** 仅检查账户权限、字段、可用历史、发布时延、请求限额、原始响应可重建性、权限/保密及跨源核对；不计算 MA200、信号、收益、回测或最佳来源。保留每次结果，包括失败结果。按既定门禁机械分类，不强求 PASS。
5. **若来源门禁真实通过，仍需外部来源审计与单独的最终冻结。** 再依现有协议完成权威来源/适配器、不可变快照重建、核对与分歧处理、运行环境、隔离 dry-run、实现验收、阈值/日程/起点审批、最终接受清单及独立审计。只有这些门禁都满足，才能讨论正式前瞻观测及其起始时间；不能倒填开始时间。实盘部署属于更远且独立的决策。

在第 2–4 步等待外部裁定或下一交易日时，可以做只读核查、整理非策略性的验收测试/观测准备，但不得启动引擎、调度器、正式纸上观测、36 个月时钟或 Phase 9。不要因为日期过去了就重放旧交易日来伪装实时发布证据。

## 5. 接手 AI 的操作与安全边界

- 在 WSL 的**正确仓库** `/home/cc/projects/market-timing-quant-etf-dynamic-allocation-v1` 工作；不要误用同级的 `/home/cc/projects/market-timing-quant`。先运行 `pwd`、`git status --short`、`git rev-parse HEAD`，并查看仓库内适用的 `AGENTS.md`（如有）。
- 每次真正修改仓库都要独立、可解释地 Git 提交；保留用户及其他任务的未提交修改，不能覆盖。只读调查或待审方案不要求为了“有进度”而改文件。
- API 凭据只在授权的运行进程环境中读取；仅报告存在与否。不得打印、记录、散列、序列化、写入仓库或提交密钥，也不得将密钥放入 URL。原始供应商响应放在 Git 外的私有目录，仓库只保存脱敏证据与哈希；迁移至其他主机时，Git 仓库**不包含**这些原始响应，必须单独验证可访问性。
- 不得改 MA200、调仓频率、成本/税务语义、历史研究或已冻结来源角色来迎合某供应商。免费来源要求不等于可以降低证据标准。若合格的免费源无法通过，应报告阻塞，而不是静默切换、拼接供应商历史或宣布通过。
- 新观测或账户请求需用户明确委托且符合已冻结方案；本交接文档本身**不授权**联网、API 请求、交易或创建正式观察。

## 6. 从哪里读，以及如何复核

优先阅读：

1. `reports/research_v1_freeze_manifest.json`、`reports/research_v1_freeze_manifest.sha256`、`docs/RESEARCH_V1_FROZEN.md`：历史冻结边界。
2. `reports/runs/20260915_phase8d_final_research_verdict/phase8d_final_research_verdict.md`：研究结论与未解决限制。
3. `docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md`：拟议纸上验证；注意所有 `PROPOSED_NOT_FROZEN` 项。
4. `docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md`、`docs/PAPER_TRADING_TIINGO_FREE_ACCEPTANCE_PLAN.md`：相互冲突的观测约束。
5. `reports/paper_trading_tiingo_free_account_acceptance_audit.md` 及两份 Tiingo 证据 JSON：账户能力、实际观测、缺口和当前门禁。
6. `docs/PAPER_TRADING_DATA_SOURCE_SPEC.md`、`docs/PAPER_TRADING_OPERATIONAL_RUNBOOK.md`、`docs/PAPER_TRADING_ENVIRONMENT_SPEC.md`、`docs/PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md`、`docs/PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md`：后续冻结与实现验收依赖。

截至本文核对，上一轮来源审计报告记录了专门测试 34/34、来源与前瞻治理测试 225/225、全套 pytest 630/630、密钥泄漏扫描 PASS。这是**当时的报告结果**，不是接手后的自动保证。可在不触发 API 的前提下从仓库根目录执行 `pytest -q`；来源相关测试位于 `tests/test_tiingo_free_account_acceptance.py`、`tests/test_tiingo_prestart_latency_audit.py`、`tests/test_paper_trading_source_acceptance.py` 等文件。检查文档和产物时注意不要让命令输出或异常栈泄漏凭据。

## 7. 正确的当前状态标签

历史研究：**Research v1.0 已冻结，Phase 0–8D 完成。**

前瞻协议：**草案，尚未 Final Freeze；无正式纸上观测。**

Tiingo 来源门禁：`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`。

项目下一动作：**外部裁定现有 Tiingo 观测的轮询预算/诊断缺口；若要求重观测，先冻结新的合规测量方案，再在未来交易日执行。**
