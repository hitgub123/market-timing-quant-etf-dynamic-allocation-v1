# Tiingo PRE_START 重观测方案 V4（已冻结）

**状态：** `FROZEN` —— 冻结后不得修改；本文件本身不授权 API 请求。
执行委托：用户 2026-10-10 明确指示"修复网络再测试"（此前 2026-10-09 已提供
TIINGO_API_KEY 并要求长期保存，不再删除；key 存于 `~/.tiingo_api_key`，0600）。
**依据：** `docs/PAPER_TRADING_TIINGO_SOURCE_ADJUDICATION_20261007.md`；
V3 冻结 `docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V3_FROZEN.md`
（2026-10-10 收尾检查机械判定为 `OBSERVATION_COMPROMISED`：第一档两标的
`TRANSPORT_ERROR` 超时、第二档进程死亡零执行；门禁未变）。
**边界：** 来源验收的性能盲重观测；不计算 MA200、信号、收益、回测或
来源优劣；不创建引擎、调度器、正式观测、36 个月时钟或 Phase 9。

## 与 V3 的差异（仅以下三处，其余合同条款逐字相同）

1. **目标交易日顺延至 2026-10-12（周一）**：NYSE 在 Columbus Day（10-12）
   不休市（NYSE 固定假日表无此日），为正常交易日；冻结时刻（2026-10-10）
   之后首个未开盘 NYSE 常规交易日。
2. **强制 TLS 1.2**：2026-10-10 诊断确认——本机经 egress 代理向
   `api.tiingo.com:443` 发起 CONNECT 隧道成功（200），但默认 TLS 1.3
   握手无响应、两侧请求 30 秒超时；改用 TLS 1.2 后认证请求 <1 秒返回
   HTTP 200（curl 与 Python urllib 独立验证，含有效载荷解析）。
   V3 的超时失败模式根因为此，非 Tiingo 服务宕机。
3. **执行形态改为 cron 单轮询**：V2/V3 的长休眠进程在 3 天内被运行时替换
   终止 4 次以上（含看门狗成功恢复的两次）；runtime cron 不随 VM 替换死亡。
   每档轮询由独立的一次性 cron 在计划时刻前 1 分钟触发单轮询脚本，
   脚本到点执行 2 个请求后即退出，无长休眠、无看门狗。

## 冻结记录

- 冻结方式：本文件 + `schemas/source_acceptance/tiingo_prestart_latency_evidence_20261012.schema.json`
  + `scripts/tiingo_prestart_latency_poll_once_v4.py` 同一提交冻结。
- 冻结时刻早于目标交易日美东 9:30 开盘（见下）。
- 目标交易日解析：冻结时刻 2026-10-10T03:3xZ（约，JST 12:3x）之后、尚未开盘的第一个
  NYSE 常规交易日 = **2026-10-12**（星期一；Columbus Day NYSE 开市，当日 13:30Z 开盘，未来）。
- 配套证据文件命名：`reports/tiingo_prestart_latency_evidence_20261012.json`
 （不得覆盖 2026-10-06 / 2026-10-07 / 2026-10-09 旧证据）。

## 冻结合同

| 项 | 冻结值 |
|---|---|
| 目标交易日 `SESSION` | `2026-10-12` |
| 开盘 `SESSION_OPEN` | `2026-10-12T13:30:00Z`（美东 9:30，EDT=UTC-4，已核验） |
| 标的 | `QQQ`、`QLD` |
| 轮询时点（UTC） | Poll 1：`2026-10-12T21:30:00Z`（美东 17:30，文档化常规更新；= 日本时间 10-13 06:30）；Poll 2：`2026-10-13T00:00:00Z`（美东 20:00，文档化修正窗口结束 = 冻结的发布边界/截止时间；= 日本时间 10-13 09:00） |
| 总请求预算 | **4**（2 时点 × 2 标的，**总数**；脚本启动时断言 `len(SCHEDULE)*len(SYMBOLS)==4`，超预算直接拒绝执行；Poll 2 运行另断言已有恰好 2 条 Poll 1 记录，否则判 compromised） |
| 请求 | `GET https://api.tiingo.com/tiingo/daily/{symbol}/prices?startDate=2026-10-12&endDate=2026-10-12&resampleFreq=daily`，头 `Authorization: Token $TIINGO_API_KEY`、`Accept: application/json`，超时 30 秒，**TLS 强制 1.2**（`ssl.SSLContext` min=max=TLSv1_2） |
| 顺序 | 每轮询由 cron 在计划时刻前 1 分钟触发，脚本等待到点后先 QQQ 后 QLD 串行；单个时点的首个请求若晚于计划时刻 300 秒发出，记为 `OBSERVATION_COMPROMISED` 并终止（exit 4） |
| 成功分类 | `VALID_SESSION`：HTTP 200 且恰好 1 条 `date` 为 2026-10-12 的记录，且全部 REQUIRED 字段非空 |
| 失败分类 | `SESSION_UNAVAILABLE_OR_INVALID`（200 但无匹配/字段缺失）；`INVALID_JSON`；`TRANSPORT_ERROR`（记异常类名） |
| REQUIRED 字段 | `date, open, high, low, close, volume, adjOpen, adjHigh, adjLow, adjClose, adjVolume, divCash, splitFactor` |
| 原始归档 | 原始字节**先**写入 `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-12/`（`poll_{01,02}_{QQQ,QLD}.raw`，0600）再解析；SHA-256 + 重建校验 |
| 每次轮询记录 | `poll, symbol, scheduled_at, requested_at, received_at, http_status, content_type, safe_headers, returned_last_date, raw_file, raw_bytes, raw_sha256, raw_reconstruction, row_count, classification`（`TRANSPORT_ERROR` 时为 `error_class` + 全 null 头/日期，不含原始字节字段） |
| `safe_headers` allow-list | `date`、`content-type`、`x-ratelimit-limit/-remaining/-reset`、`ratelimit-limit/-remaining/-reset`，缺席记 null，绝不捏造、不记认证类头 |
| `returned_last_date` | 响应记录的最大 `date`，无记录为 null |
| 凭证边界 | 仅从执行进程环境读 `TIINGO_API_KEY`；不打印/记录/散列/提交/入 URL；仅报告存在与否。key 由用户要求长期保存在 `~/.tiingo_api_key`（0600），不再用后删除 |
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

## 执行计划（待冻结批准后创建）

- 一次性 cron `tiingo-poll1-20261012`：2026-10-13T06:29:00+09:00 触发，
  `POLL_INDEX=1` 运行 `scripts/tiingo_prestart_latency_poll_once_v4.py`
 （`TIINGO_API_KEY` 由 `~/.tiingo_api_key` 注入执行进程环境）。
- 一次性 cron `tiingo-poll2-20261012`：2026-10-13T08:59:00+09:00 触发，
  `POLL_INDEX=2`。
- 一次性 cron `tiingo-final-check-20261012`：2026-10-13T09:30:00+09:00，
  只读收尾检查（不修复、不重跑）。
- 证据归档：`reports/tiingo_prestart_latency_evidence_20261012.json`，
  由审计步骤对照 schema 校验后归档。
