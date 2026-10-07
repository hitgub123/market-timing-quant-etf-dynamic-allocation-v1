# Tiingo PRE_START 重观测方案 V2（已冻结）

**状态：** `FROZEN` —— 冻结后不得修改；本文件本身不授权 API 请求，
执行需用户单独立项委托。
**依据：** `docs/PAPER_TRADING_TIINGO_SOURCE_ADJUDICATION_20261007.md`；
草案 `docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V2_DRAFT.md`
（2026-10-07 用户批准）。
**边界：** 来源验收的性能盲重观测；不计算 MA200、信号、收益、回测或
来源优劣；不创建引擎、调度器、正式观测、36 个月时钟或 Phase 9。

## 冻结记录

- 冻结方式：本文件 + `schemas/source_acceptance/tiingo_prestart_latency_evidence_20261007.schema.json`
  + `scripts/tiingo_prestart_latency_observer_v2.py` 同一提交冻结。
- 冻结时刻早于目标交易日美东 9:30 开盘（见下）。
- 目标交易日解析：冻结时刻 2026-10-07T06:56Z 之后、尚未开盘的第一个
  NYSE 常规交易日 = **2026-10-07**（`pandas-market-calendars` NYSE 日历核验，
  当日 13:30Z 开盘，未来；10-08/09/12 亦为交易日，10-10/11 为周末）。
- 配套证据文件命名：`reports/tiingo_prestart_latency_evidence_20261007.json`
 （不得覆盖 2026-10-06 旧证据）。

## 冻结合同

| 项 | 冻结值 |
|---|---|
| 目标交易日 `SESSION` | `2026-10-07` |
| 开盘 `SESSION_OPEN` | `2026-10-07T13:30:00Z`（美东 9:30，EDT=UTC-4，已核验） |
| 标的 | `QQQ`、`QLD` |
| 轮询时点（UTC） | Poll 1：`2026-10-07T21:30:00Z`（美东 17:30，文档化常规更新）；Poll 2：`2026-10-08T00:00:00Z`（美东 20:00，文档化修正窗口结束 = 冻结的发布边界/截止时间） |
| 总请求预算 | **4**（2 时点 × 2 标的，**总数**；脚本启动时断言 `len(SCHEDULE)*len(SYMBOLS)==4`，超预算直接拒绝执行） |
| 请求 | `GET https://api.tiingo.com/tiingo/daily/{symbol}/prices?startDate=2026-10-07&endDate=2026-10-07&resampleFreq=daily`，头 `Authorization: Token $TIINGO_API_KEY`、`Accept: application/json`，超时 30 秒 |
| 顺序 | 每时点到点后先 QQQ 后 QLD 串行；单个时点的首个请求若晚于计划时刻 300 秒发出，记为 `OBSERVATION_COMPROMISED` 并终止（exit 4） |
| 成功分类 | `VALID_SESSION`：HTTP 200 且恰好 1 条 `date` 为 2026-10-07 的记录，且全部 REQUIRED 字段非空 |
| 失败分类 | `SESSION_UNAVAILABLE_OR_INVALID`（200 但无匹配/字段缺失）；`INVALID_JSON`；`TRANSPORT_ERROR`（记异常类名） |
| REQUIRED 字段 | `date, open, high, low, close, volume, adjOpen, adjHigh, adjLow, adjClose, adjVolume, divCash, splitFactor` |
| 原始归档 | 原始字节**先**写入 `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-07/`（`poll_{01,02}_{QQQ,QLD}.raw`，0600）再解析；SHA-256 + 重建校验 |
| 每次轮询记录 | `poll, symbol, scheduled_at, requested_at, received_at, http_status, content_type, safe_headers, returned_last_date, raw_file, raw_bytes, raw_sha256, raw_reconstruction, row_count, classification`（`TRANSPORT_ERROR` 时为 `error_class` + 全 null 头/日期，不含原始字节字段） |
| `safe_headers` allow-list | `date`、`content-type`、`x-ratelimit-limit/-remaining/-reset`、`ratelimit-limit/-remaining/-reset`，缺席记 null，绝不捏造、不记认证类头 |
| `returned_last_date` | 响应记录的最大 `date`，无记录为 null |
| 凭证边界 | 仅从执行进程环境读 `TIINGO_API_KEY`；不打印/记录/散列/提交/入 URL；仅报告存在与否 |
| 中断恢复 | 仅当已记录轮询为 0、归档目录为空、恢复启动早于 Poll 1 时刻、且 SESSION/时点/标的/预算不变时允许恢复；其余一律 `OBSERVATION_COMPROMISED`，不得补造时间戳 |

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

## 执行委托

本冻结文件不授权 API 请求。执行需用户明确委托；委托时执行人运行
`scripts/tiingo_prestart_latency_observer_v2.py`（环境变量
`TIINGO_API_KEY` 由用户授权的进程环境提供），
按第 9 节产出证据 JSON 并提交审计。
