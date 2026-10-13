# Tiingo V3 重观测执行裁定：OBSERVATION_COMPROMISED（2026-10-10）

- 状态：草案（未提交、未冻结），待用户阅后确认再决定提交/推送。
- 裁定范围：`docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V3_FROZEN.md`
  （冻结提交 `f223ad9`，目标交易日 SESSION=2026-10-09，轮询预算 4）。
- 裁定人：Muse（项目持续维护 AI，兼独立审计职责）。

## 事实时间线（均为可查记录）

1. 2026-10-09 12:32 JST（10-09 03:32Z）：用户重新提供 `TIINGO_API_KEY`，
   明确要求长期保存、不再删除（key 现存 `~/.tiingo_api_key`，0600）。
   该提供视为对本次重测的执行委托。
2. 2026-10-09 12:33 JST（03:33:46Z）：观测进程启动，开盘前检查通过
   （`PRESTART_ELIGIBLE=TRUE`）。
3. 10-09 下午：观测进程被运行时替换终止两次（与 V2 相同的死法），
   按冻结恢复条款重启，恢复检查通过；当时已记录轮询为 0，证据链干净，
   10-10 06:30 / 09:00 两档轮询不受影响。
4. 2026-10-10 06:20 JST（10-09 21:20:21Z）：一次性看门狗（已修复为防自匹配
   `pgrep` 写法）检测到进程死亡并重启，恢复检查通过
   （`observer_resumed_at: 2026-10-09T21:20:21.762350Z`）。
5. Poll 1（计划 `2026-10-09T21:30:00Z` = 10-10 06:30 JST）：
   - QQQ：`requested_at 2026-10-09T21:30:00.007170Z` →
     `TRANSPORT_ERROR`（`TimeoutError`，脚本请求超时 30 秒）；
   - QLD：`requested_at 2026-10-09T21:30:30.248925Z` →
     `TRANSPORT_ERROR`（`TimeoutError`）。
   两次均 `safe_headers` 全 null、`returned_last_date` null；
   按合同 `TRANSPORT_ERROR` 不含原始字节字段，无 `.raw` 归档文件。
6. 06:31–09:00 JST 之间：进程再次死亡（疑为 VM 替换；确切死亡时刻未知）。
   Poll 2（计划 `2026-10-10T00:00:00Z` = 10-10 09:00 JST）**未执行**，
   无轮询记录。
7. 2026-10-10 09:30 JST 收尾检查：进程已死亡；证据文件
   `~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-09/latency_evidence.json`
   仅含开盘前记录 + 2 条 `TRANSPORT_ERROR` 轮询记录，`status` 停留在
   `IN_PROGRESS`（观测进程未写出终止状态）；归档目录无 `.raw` 文件，
   无 V3 配套证据 JSON（`schemas/source_acceptance/` 下无
   `tiingo_prestart_latency_evidence_20261009.json` 归档产物）。
8. 凭证按用户 10-09 指示保留，未销毁；4 个请求预算中 2 个已发出
   （均超时、无响应数据）。

## 冻结合同适用

- 门禁判定条："`OBSERVATION_COMPROMISED`：任何传输/解析错误、漏检、
  迟到超限、中断 → 不做通过/失败判定，需重新冻结后再测。"
  Poll 1 两次 `TRANSPORT_ERROR` 已触发该条，机械判定，无需再看 Poll 2。
- 中断恢复条：仅当已记录轮询为 0、归档目录为空、恢复启动早于 Poll 1 时刻、
  且 SESSION/时点/标的/预算不变时允许恢复；其余一律
  `OBSERVATION_COMPROMISED`，不得补造时间戳。
  - 已记录轮询为 2（非 0）✗
  - 归档目录非空（证据文件存在）✗
  - → 不满足恢复条件 → 判定 `OBSERVATION_COMPROMISED`。

## 裁定

- 本次重观测判为 **`OBSERVATION_COMPROMISED`**：
  不做 LATENCY_PASS / LATENCY_FAIL 判定（冻结合同"门禁判定"条）。
- 来源门禁维持 `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`。
- 目标 SESSION=2026-10-09 的冻结文件就执行而言已作废；
  重新观测需为新的目标交易日重新冻结（冻结时刻早于目标交易日美东
  9:30 开盘），冻结内容可复用 V3 设计（三件套已验证），但 SESSION、
  轮询时刻与配套证据文件名须随新目标日更新。
- 冻结与执行均仍需用户明确批准/委托；本裁定文件本身不授权任何 API 请求。

## 教训（记入流程）

1. 防自匹配 `pgrep` 修复已验证有效：06:20 看门狗正确检出死亡并重启，
   V2 的误报存活 bug 未复发。看门狗本身没问题。
2. 未被守护的窗口是 06:31→09:00（两轮询之间）：没有轮询间恢复检查。
   下一版设计应让每个轮询时点各自被独立的持久调度持有
   （每档一个 runonce），或在两档之间加一次恢复检查；
   一个长休眠进程横跨两档等于把两个时点绑在同一个 VM 生存期上。
3. Poll 1 两次 `TimeoutError` 的原因未确定（VM 网络路径或 Tiingo 端均可能），
   不做归因；V4 草案可记录超时处置问题，但合同变更需用户审阅。

## 下一步（待用户决定）

- 选项 A：为新的目标交易日重新冻结并执行。
  最早可选 SESSION=2026-10-12（周一；NYSE 在 Columbus Day 正常开市，
  已核验 2026 交易日历），冻结须在 **10-11（周日）22:30 JST**
  （美东周一 9:30 开盘）前完成；或选 10-13（周二），冻结截止
  10-12 22:30 JST。轮询为目标日次日 06:30/09:00 JST。
  执行仍需用户明确委托（key 已在机器上长期保存，无需重新提供）。
- 选项 B：暂缓，冻结设计保留，随时可再启动。

注：V2 的失败裁定草案（`docs/PAPER_TRADING_TIINGO_REOBSERVATION_OBSERVATION_VERDICT_20261008.md`）
仍为未提交草案，可与本草案一并审阅。
