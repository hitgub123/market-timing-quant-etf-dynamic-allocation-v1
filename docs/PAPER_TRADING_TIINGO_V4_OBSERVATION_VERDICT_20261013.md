# Tiingo PRE_START 重观测 V4 裁定（2026-10-13）

- 冻结：`74991ed`（`docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V4_FROZEN.md`）
- 裁定日期：2026-10-13 JST
- 裁定方：Muse（独立审计）

## 执行记录

| 档 | 计划时刻 | 实际 | 结果 |
|---|---|---|---|
| Poll 1 | 2026-10-13 06:29 JST（= 2026-10-12T21:29Z） | cron 准时触发，脚本 exit 2 | `PRESTART_ELIGIBLE=FALSE`，零请求 |
| Poll 2 | 2026-10-13 08:59 JST（= 2026-10-12T23:59Z） | cron 准时触发，脚本 exit 2 | `POLL2_PRECONDITION=FALSE (no evidence)`，按设计拒绝，零请求 |

证据文件 `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-12/latency_evidence.json` 不存在；
归档目录从未创建；外部 API 请求总数 0；polls 记录数 0。

## 根因：冻结方案内在矛盾（非运维事故）

`scripts/tiingo_prestart_latency_poll_once_v4.py`（V4 新脚本，V3 观察者无此门）第 155–162 行：

```python
if poll_index == 1:
    ...
    if start >= session_open:
        print("PRESTART_ELIGIBLE=FALSE", flush=True)
        return 2
```

冻结值：`SESSION_OPEN = 2026-10-12T13:30:00Z`（周一开盘），而冻结的轮询时点为
`2026-10-12T21:30:00Z` 与 `2026-10-13T00:00:00Z`——两者恒晚于 `SESSION_OPEN`。
因此 Poll 1 在计划时刻**按脚本自身规则必然被拒**，Poll 2 随之因无证据被拒。
V4 的观测在冻结时即已不可能执行；与传输错误、漏检、迟到、中断无关。

设计意图复核：V4（沿 V2/V3）观测的是周一（2026-10-12）日线数据在 Tiingo
的可用延迟（文档化 17:30 ET 常规更新、20:00 ET 修正窗口结束），其
"prestart" 实指**周二开盘前**数据必须可用。资格门的正确参照应为
`2026-10-13T13:30:00Z`（周二开盘），而非周一开盘。冻结把 `SESSION_OPEN`
填成周一开盘（"已核验"仅核验了时刻本身，未发现与轮询时点的矛盾），
是本次作废的直接原因。

## 机械分类

按冻结"门禁判定"节：

- `LATENCY_PASS`：要求两标的 `first_valid` 均非 None——零观测，不满足。
- `LATENCY_FAIL`：要求"干净执行但任一标的两档轮询均无 `VALID_SESSION`"——
  本次零请求、未执行观测，不构成"干净执行"，不适用。
- `OBSERVATION_COMPROMISED`：要求传输/解析错误、漏检、迟到超限或中断——
  均未发生，不适用。

**裁定：本次观测 VOID（作废）**——冻结方案内在矛盾导致观测未能执行，
不产生关于 Tiingo 延迟的任何通过/失败判定。后果等同 compromised
（不做判定、需重新冻结后再测），但原因必须如实记录为方案缺陷，
而非运维事故；否则下一次冻结会重复同一 bug。

## 门禁状态

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE` 维持不变。

## 后续建议（待用户授权）

V5 重新冻结：`SESSION=2026-10-13`（周二），轮询时点
`2026-10-13T21:30:00Z`（= 10-14 06:30 JST）与 `2026-10-14T00:00:00Z`
（= 10-14 09:00 JST），`SESSION_OPEN` 修正为 `2026-10-14T13:30:00Z`
（周三开盘，真正的 prestart 截止）。其余冻结值（4 请求预算、TLS 1.2、
schema、单轮询 cron 形态）不变。新一轮 live 观测需用户明确授权。
