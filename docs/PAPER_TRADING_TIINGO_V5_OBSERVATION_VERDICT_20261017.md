# Tiingo PRE_START 重观测 V5 裁定：LATENCY_PASS（2026-10-17）

- 冻结：`2ff899a`（`docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V5_FROZEN.md`）
- 配套：`schemas/source_acceptance/tiingo_prestart_latency_evidence_20261016.schema.json`、
  `scripts/tiingo_prestart_latency_poll_once_v5.py`
- 目标交易日：2026-10-16（周五）；`SESSION_OPEN` = 2026-10-19T13:30:00Z（下周一开盘，真正的 prestart 截止；V4 自矛盾 bug 已修复）
- 裁定日期：2026-10-17 JST
- 裁定方：Muse（独立审计；执行与审计分离——执行由一次性 cron 触发，审计逐项复核原始证据）

## 执行记录

| 档 | 计划时刻（UTC） | 实际请求时刻 | 结果 |
|---|---|---|---|
| Poll 1 | 2026-10-16T21:30:00Z | QQQ +0.0s，QLD +0.8s | 2/2 `VALID_SESSION`（HTTP 200） |
| Poll 2 | 2026-10-17T00:00:00Z | QQQ +0.0s，QLD +1.3s | 2/2 `VALID_SESSION`（HTTP 200） |

- 请求总数 4/4（= 冻结预算，无超发）；迟到熔断（300s）未触发。
- 4 个 `.raw` 原始响应文件齐备，SHA-256 与字节数均与证据记录一致，
  重建校验通过；内容抽查：每份恰好 1 条 `date=2026-10-16` 记录，
  13 个 REQUIRED 字段全部非空。
- 证据 `status=OBSERVATION_COMPLETE`；`credential_value_stored=false`
 （key 未落盘）；`performance_calculated=false`；
  `official_observation_created=false`；`source_promoted=false`。
- 响应头：rate-limit 类 allow-list 头本次未返回（记 null，非捏造）；
  `content-type=application/json` 正常。

## 审计方法

1. 独立读取 `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-16/latency_evidence.json`
  （不依赖执行方转述）。
2. `jsonschema` Draft 2020-12 形式校验通过（配套 schema）。
3. 逐项核对冻结合同：SESSION / SESSION_OPEN / SCHEDULE / 标的 / 预算 /
   请求 URL 与头 / 超时 / TLS 1.2 / 原始归档 / 凭证边界——全部一致。
4. 独立重算全部 4 个原始文件的 SHA-256 并抽查解析内容。
5. 门禁判定机械执行（见下），不引入审计方主观判断。

## 机械分类

- `first_valid[QQQ] = 1`，`first_valid[QLD] = 1`（两标的均在 Poll 1 即有效）。
- 无 `TRANSPORT_ERROR` / `INVALID_JSON` / `SESSION_UNAVAILABLE_OR_INVALID`；
  无迟到超限；无中断。
- **判定：`LATENCY_PASS`**。

## 含义与边界

- `LATENCY_PASS` 仅满足**延迟单项**：Tiingo 在美东 17:30（文档化常规更新）
  时点已提供 2026-10-16 的 QQQ、QLD 日线数据（20:00 档复核一致）。
- 按冻结方案，来源门禁进入 `SOURCE_ACCEPTANCE_PASS` 仍需**本次独立证据审计**
  通过——本裁定即为该审计：证据与冻结方案 + 配套 schema 逐项一致，
  **审计通过**。
- 本裁定不推进 Final Freeze、不启动纸上交易时钟、不创建引擎/调度器/Phase 9；
  后续步骤仍需用户明确授权。
- 归档证据：`reports/tiingo_prestart_latency_evidence_20261016.json`
 （本文件为其配套裁定）。
