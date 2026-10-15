# Tiingo PRE_START 重观测方案 V5（已冻结）

**状态：** `FROZEN` —— 冻结后不得修改；本文件本身不授权 API 请求。
执行委托：用户 2026-10-16 明确指示"继续"（此前 2026-10-09 已提供
TIINGO_API_KEY 并要求长期保存，不再删除；key 存于 `~/.tiingo_api_key`，0600；
2026-10-16 复核 key 文件仍在）。
**依据：** `docs/PAPER_TRADING_TIINGO_SOURCE_ADJUDICATION_20261007.md`；
V4 冻结 `docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V4_FROZEN.md`
（2026-10-13 独立审计裁定为 `VOID`：见下"与 V4 的差异"第 1 条；门禁未变）。
**边界：** 来源验收的性能盲重观测；不计算 MA200、信号、收益、回测或
来源优劣；不创建引擎、调度器、正式观测、36 个月时钟或 Phase 9。

## 与 V4 的差异（仅以下两处，其余合同条款逐字相同）

1. **`SESSION_OPEN` 修正为下个交易日的开盘**：V4 把 `SESSION_OPEN` 填成目标
   交易日当天的开盘（`2026-10-12T13:30:00Z`），而轮询时点（21:30Z、次日 00:00Z）
   恒晚于当天开盘，导致单轮询脚本按自身 `start >= session_open` 规则必然拒绝
   执行，2026-10-13 独立审计裁定 V4 为 `VOID`（冻结方案内在矛盾，非运维事故；
   详见 `docs/PAPER_TRADING_TIINGO_V4_OBSERVATION_VERDICT_20261013.md`）。
   V5 的 `SESSION_OPEN` 为 **2026-10-19T13:30:00Z**（下周一美东 9:30 开盘，
   真正的 prestart 截止：周五的日线数据必须在下周一开盘前可用）。
   冻结前已做门禁/时点自洽模拟：Poll 1 启动（~21:29Z）与 Poll 2 启动（~23:59Z）
   均早于 `SESSION_OPEN`，两档门禁均可满足（模拟记录见冻结提交说明）。
2. **目标交易日顺延至 2026-10-16（周五）**：冻结时刻（2026-10-16 上午，JST）
   之后首个未开盘 NYSE 常规交易日；2026-10-16 为周五、2026-10-19 为周一，
   均非 NYSE 假日（2026 年 10 月无 NYSE 休市日），为正常交易日。

## 冻结记录

- 冻结方式：本文件 + `schemas/source_acceptance/tiingo_prestart_latency_evidence_20261016.schema.json`
  + `scripts/tiingo_prestart_latency_poll_once_v5.py` 同一提交冻结。
- 冻结时刻早于目标交易日美东 9:30 开盘（见下）。
- 目标交易日解析：冻结时刻 2026-10-16T00:0xZ（约，JST 09:0x）之后、尚未开盘的第一个
  NYSE 常规交易日 = **2026-10-16**（星期五；当日 13:30Z 开盘，未来）。
- 配套证据文件命名：`reports/tiingo_prestart_latency_evidence_20261016.json`
 （不得覆盖 2026-10-06 / 2026-10-07 / 2026-10-09 / 2026-10-12 旧证据）。

## 冻结合同

| 项 | 冻结值 |
|---|---|
| 目标交易日 `SESSION` | `2026-10-16` |
| 开盘 `SESSION_OPEN` | `2026-10-19T13:30:00Z`（下周一美东 9:30，EDT=UTC-4；真正的 prestart 截止。V4 教训：此处不得填目标交易日当天开盘） |
| 标的 | `QQQ`、`QLD` |
| 轮询时点（UTC） | Poll 1：`2026-10-16T21:30:00Z`（美东 17:30，文档化常规更新；= 日本时间 10-17 06:30）；Poll 2：`2026-10-17T00:00:00Z`（美东 20:00，文档化修正窗口结束 = 冻结的发布边界/截止时间；= 日本时间 10-17 09:00） |
| 总请求预算 | **4**（2 时点 × 2 标的，**总数**；脚本启动时断言 `len(SCHEDULE)*len(SYMBOLS)==4`，超预算直接拒绝执行；Poll 2 运行另断言已有恰好 2 条 Poll 1 记录，否则判 compromised） |
| 请求 | `GET https://api.tiingo.com/tiingo/daily/{symbol}/prices?startDate=2026-10-16&endDate=2026-10-16&resampleFreq=daily`，头 `Authorization: Token $TIINGO_API_KEY`、`Accept: application/json`，超时 30 秒，**TLS 强制 1.2**（`ssl.SSLContext` min=max=TLSv1_2；2026-10-10 已诊断本机 TLS 1.3 握手挂起） |
| 顺序 | 每轮询由 cron 在计划时刻前 1 分钟触发，脚本等待到点后先 QQQ 后 QLD 串行；单个时点的首个请求若晚于计划时刻 300 秒发出，记为 `OBSERVATION_COMPROMISED` 并终止（exit 4） |
| 成功分类 | `VALID_SESSION`：HTTP 200 且恰好 1 条 `date` 为 2026-10-16 的记录，且全部 REQUIRED 字段非空 |
| 失败分类 | `SESSION_UNAVAILABLE_OR_INVALID`（200 但无匹配/字段缺失）；`INVALID_JSON`；`TRANSPORT_ERROR`（记异常类名） |
| REQUIRED 字段 | `date, open, high, low, close, volume, adjOpen, adjHigh, adjLow, adjClose, adjVolume, divCash, splitFactor` |
| 原始归档 | 原始字节**先**写入 `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-16/`（`poll_{01,02}_{QQQ,QLD}.raw`，0600）再解析；SHA-256 + 重建校验 |
| 每次轮询记录 | `poll, symbol, scheduled_at, requested_at, received_at, http_status, content_type, safe_headers, returned_last_date, raw_file, raw_bytes, raw_sha256, raw_reconstruction, row_count, classification`（`TRANSPORT_ERROR` 时为 `error_class` + 全 null 头/日期，不含原始字节字段） |
| `safe_headers` allow-list | `date`、`content-type`、`x-ratelimit-limit/-remaining/-reset`、`ratelimit-limit/-remaining/-reset`，缺席记 null，绝不捏造、不记认证类头 |
| `returned_last_date` | 响应记录的最大 `date`，无记录为 null |
| 凭证边界 | 仅从执行进程环境读 `TIINGO_API_KEY`；不打印/记录/散列/提交/入 URL；仅报告存在与否。key 由用户要求长期保存在 `~/.tiingo_api_key`（0600） |
| 中断恢复 | 本形态无"恢复"概念：Poll 1 要求归档目录不存在（否则拒绝）；Poll 2 要求证据存在且恰好含 2 条 Poll 1 记录且状态为 `IN_PROGRESS`，否则记 `OBSERVATION_COMPROMISED`（`compromise_reason=poll2-precondition-failed`），不得补造时间戳 |

## 门禁判定（机械执行）

记 `first_valid[s]` 为某标的首次 `VALID_SESSION` 的轮询序号，无则为 None。

- **LATENCY_PASS**：两标的的 `first_valid` 均非 None（由构造均 ≤ 20:00 ET）。
- **LATENCY_FAIL**：干净执行但任一标的两档轮询均无 `VALID_SESSION`。
- **OBSERVATION_COMPROMISED**：任何传输/解析错误、漏检、迟到超限、中断 → 不做通过/失败判定，需重新冻结后再测。

`LATENCY_PASS` 仅满足延迟单项；来源门禁进入 `SOURCE_ACCEPTANCE_PASS`
仍需一次对照本冻结方案 + 配套 schema 的独立证据审计，审计通过前
不得推进 Final Freeze。

## 性能盲与非正式边界

`fixture_status=PRE_START_NONOFFICIAL_SOURCE_EVIDENCE`；
`official_observation_created=false`、`performance_calculated=false`、
`source_promoted=false`。不启动纸上交易时钟。

## 执行计划（冻结后创建）

- 一次性 cron `tiingo-poll1-20261016`：2026-10-16T21:29:00Z（= 日本时间 10-17 06:29）触发，
  `POLL_INDEX=1` 运行 `scripts/tiingo_prestart_latency_poll_once_v5.py`
 （`TIINGO_API_KEY` 由 `~/.tiingo_api_key` 注入执行进程环境）。
- 一次性 cron `tiingo-poll2-20261016`：2026-10-16T23:59:00Z（= 日本时间 10-17 08:59）触发，
  `POLL_INDEX=2`。
- 一次性 cron `tiingo-final-check-20261016`：2026-10-17T00:30:00Z（= 日本时间 10-17 09:30），
  只读收尾检查（不修复、不重跑）。
- 证据归档：`reports/tiingo_prestart_latency_evidence_20261016.json`，
  由审计步骤对照 schema 校验后归档。
