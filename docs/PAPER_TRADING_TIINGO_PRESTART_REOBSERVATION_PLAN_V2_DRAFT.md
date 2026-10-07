# Tiingo PRE_START 重观测方案 V2（草案，未冻结）

**状态：** `DRAFT` —— 未冻结，不授权任何 API 请求、观测执行或门禁推进。
**依据：** `docs/PAPER_TRADING_TIINGO_SOURCE_ADJUDICATION_20261007.md`
（2026-10-06 观测不满足冻结的四次轮询预算，门禁维持
`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`，需重观测）。
**边界：** 本方案是来源验收的性能盲重观测准备，不是正式纸上观测；
不计算 MA200、信号、收益、回测或来源优劣；不创建引擎、调度器、
正式观测、36 个月时钟或 Phase 9。

## 1. 目标

对一个未来、尚未开盘的美国交易日，用**总请求数 ≤ 4** 的冻结预算，
测量 Tiingo 免费端点在文档化发布边界（美东 17:30 更新、
20:00 修正窗口结束）内是否返回该交易日的 QQQ / QLD 完整记录。
只回答"是否在边界内可用"，不做任何性能推断。

## 2. 冻结合同（草案值，冻结时逐项落定）

| 项 | 冻结值 |
|---|---|
| 目标交易日 | 规则见第 3 节：冻结提交时刻之后、尚未开盘的第一个 NYSE 常规交易日；冻结时记录解析出的具体日期 |
| 标的 | `QQQ`、`QLD`（与账户验收一致） |
| 轮询时点（美东） | Poll 1：17:30（文档化常规更新）；Poll 2：20:00（文档化修正窗口结束 = 本次冻结的发布边界/截止时间） |
| 轮询时点（UTC） | 冻结时按 `America/New_York` 换算并记录（10 月为 EDT=UTC-4；11 月起 EST=UTC-5，冻结人必须核验，不许硬编码偏移） |
| 总请求预算 | **4**（2 时点 × 2 标的，**总数**，非每标的；此为最严口径，冻结后不得重新解释） |
| 请求 | `GET https://api.tiingo.com/tiingo/daily/{symbol}/prices?startDate={SESSION}&endDate={SESSION}&resampleFreq=daily`，头 `Authorization: Token $TIINGO_API_KEY`、`Accept: application/json`，超时 30 秒 |
| 顺序 | 每个时点到点后先 QQQ 后 QLD，串行；单个时点的首个请求必须在计划时刻之后 300 秒内发出，否则记为 compromised（第 8 节） |
| 成功分类 | `VALID_SESSION`：HTTP 200 且恰好 1 条 `date` 等于目标交易日的记录，且全部 REQUIRED 字段非空 |
| 失败分类 | `SESSION_UNAVAILABLE_OR_INVALID`：HTTP 200 但无匹配记录或记录字段缺失；`INVALID_JSON`：响应非 JSON；`TRANSPORT_ERROR`：异常（记录异常类名，不记录堆栈中的秘密） |
| REQUIRED 字段 | `date, open, high, low, close, volume, adjOpen, adjHigh, adjLow, adjClose, adjVolume, divCash, splitFactor`（与账户验收一致） |
| 原始归档 | 每次响应的原始字节**先**写入仓库外私有目录 `~/.local/share/market-timing-quant/tiingo-prestart-latency/{SESSION}/` 再解析；文件名 `poll_{01,02}_{QQQ,QLD}.raw`；记录 SHA-256 并做重建校验 |
| 每次轮询记录 | `poll, symbol, scheduled_at, requested_at, received_at, http_status, content_type, safe_headers, returned_last_date, raw_file, raw_bytes, raw_sha256, raw_reconstruction, row_count, classification`；`error_class` 仅在 `TRANSPORT_ERROR` 时记录 |
| `safe_headers` allow-list | 仅记录 `date`、`content-type` 及以下存在即记、缺席即记为 null 的头：`x-ratelimit-limit / -remaining / -reset`、`ratelimit-limit / -remaining / -reset`；绝不记录认证类头；缺席的头不得捏造 |
| `returned_last_date` | 响应记录中的最大 `date`（`YYYY-MM-DD`），无记录时为 null；可从原始字节重建，不得事后编造 |
| 凭证边界 | 仅从执行进程环境读取 `TIINGO_API_KEY`；不得打印、记录、散列、序列化、写入仓库、提交或放入 URL；仅报告存在与否 |
| 免费额度兼容 | 4 个请求远低于文档化 50/小时、1000/天上限 |

## 3. 目标交易日解析规则

目标交易日 = 冻结提交时间戳之后、开盘时间（美东 9:30）尚未到来的
第一个 NYSE 常规交易日，以 `pandas-market-calendars` 的 NYSE 日历判定
（含半日交易日；半日不影响本方案，因轮询锚定美东时钟而非收盘相对时间）。

冻结时执行人必须运行日历核验并记录解析出的 `SESSION`（`YYYY-MM-DD`）、
`SESSION_OPEN`（UTC）与两档轮询的 UTC 时刻，该记录为冻结的一部分。
示例（仅示例，非冻结值）：若冻结于 2026-10-07 美东开盘前，
目标为 2026-10-07，轮询 UTC 为 `2026-10-07T21:30:00Z` / `2026-10-08T00:00:00Z`。

## 4. 门禁判定（机械执行，无自由裁量）

记 `first_valid[s]` 为某标的首次出现 `VALID_SESSION` 的轮询序号，
无则记为 None。

- **LATENCY_PASS**：`first_valid[QQQ]` 与 `first_valid[QLD]` 均非 None
 （由构造，两者必然 ≤ 20:00 ET，即文档化发布边界内）。
- **LATENCY_FAIL**：干净执行（无传输/解析错误、无 compromised），
  但任一标的在两档轮询均无 `VALID_SESSION`。
- **OBSERVATION_COMPROMISED**：任一 `TRANSPORT_ERROR` / `INVALID_JSON`、
  漏检、时点被移动/重复、或第 8 节的中断情形 → 不做通过/失败判定，
  门禁不动，需按第 9 节重新冻结后再测。

`LATENCY_PASS` 仅满足延迟单项；来源门禁进入 `SOURCE_ACCEPTANCE_PASS`
仍需一次独立的证据审计（对照本冻结方案 + schema 逐项核验），
审计通过前不得推进 Final Freeze。

## 5. 性能盲

观测过程不得计算 MA200、信号、收益、回测或任何来源优劣比较。
字段完备性校验属于验收本身，不属于性能计算。

## 6. 非正式观测边界

本次为 `PRE_START_NONOFFICIAL_SOURCE_EVIDENCE`，不是正式纸上观测；
不启动纸上交易时钟；`official_observation_created=false`、
`performance_calculated=false`、`source_promoted=false`。

## 7. 证据 schema

既有 `schemas/source_acceptance/tiingo_prestart_latency_evidence.schema.json`
为 2026-10-06 单次观测硬编码（`expected_session`、`schedule_utc`、
`polls` 限定 10 条均为 const），**不能**复用于新观测。
冻结时必须新建配套 schema 文件
`schemas/source_acceptance/tiingo_prestart_latency_evidence_{YYYYMMDD}.schema.json`，
要求：

- 冻结输入为 const：`artifact`、`expected_session`、`schedule_utc`、
  `session_open_at`、`symbols`、`total_request_budget: 4`、
  `fixture_status: PRE_START_NONOFFICIAL_SOURCE_EVIDENCE`、
  `official_observation_created: false`、`performance_calculated: false`、
  `source_promoted: false`、`raw_archive_outside_repository: true`、
  `credential_present: true`、`credential_value_stored: false`；
- 结果字段为类型约束：`polls` 恰为 4 条（`minItems=maxItems=4`）；
  `poll ∈ {1,2}`；`raw_file` 模式 `^poll_0[1-2]_(QQQ|QLD)\.raw$`；
  `classification ∈ {VALID_SESSION, SESSION_UNAVAILABLE_OR_INVALID, TRANSPORT_ERROR, INVALID_JSON}`；
  `TRANSPORT_ERROR` 时要求 `error_class` 且不要求原始字节字段，
  其余分类要求完整的原始字节/哈希/重建字段；
  `safe_headers` 为固定 allow-list 对象、`returned_last_date` 为
  日期字符串或 null；
- 新证据 JSON 文件命名
  `reports/tiingo_prestart_latency_evidence_{YYYYMMDD}.json`，
  不得覆盖 2026-10-06 的旧证据文件。

## 8. 中断与恢复

仅当以下**全部**成立时允许恢复，且恢复不改变 SESSION、时点、
标的、预算与截止时间：已记录轮询数为 0、私有归档目录为空、
恢复启动早于 Poll 1 计划时刻。恢复的时间戳与原因原样记录。
其余任何中断、漏检、补检一律记为 `OBSERVATION_COMPROMISED`，
不得补造时间戳，不得事后追加轮询。

## 9. 冻结程序

1. 用户批准本草案（即冻结授权）。
2. 起草方按第 3 节解析目标交易日，填入 UTC 时点，写出最终方案文档
   （状态改为 `FROZEN`）、配套 schema 文件，并按本合同改写观测脚本
   （`scripts/tiingo_prestart_latency_observer.py` 的 V2 版或新文件，
   仅替换 SESSION / SCHEDULE / 记录字段，不碰请求语义与分类口径）。
3. 三者同一提交冻结；提交时间戳必须早于目标交易日美东 9:30 开盘。
4. 冻结后、执行前，需用户**明确委托**联网观测；本草案与冻结方案本身
   均不授权 API 请求，委托必须单独立项。

## 10. 后续

观测完成后：证据 JSON 对照冻结方案 + schema 做独立审计；
`LATENCY_PASS` 且审计通过 → 门禁可进入 `SOURCE_ACCEPTANCE_PASS`
（仍待最终冻结流程）；`LATENCY_FAIL` → 门禁不动，是否换来源另行决策；
`OBSERVATION_COMPROMISED` → 重新走第 9 节。
