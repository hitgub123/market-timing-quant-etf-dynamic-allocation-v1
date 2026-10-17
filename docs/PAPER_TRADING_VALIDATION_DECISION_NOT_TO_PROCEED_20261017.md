# 决定：不启动前瞻纸上验证（2026-10-17）

- **决定人：** 用户（2026-10-17 JST，亲述"不值得跑"）
- **决定内容：** 不推进 `paper-validation-v1.0-final` 协议的前瞻纸上验证；
  不建纸上引擎，不跑 dry-run，不启动 36 个月观测时钟。
- **用户理由原话：** "这个策略看起来很一般啊。综合收益和回撤比，没有比qqq好的策略吗" →
  "不值得跑"。
- **事实依据（供追溯）：** Phase 8D 冻结报告 `phase8d_final_research_verdict.md`——
  FIXED_MA200 周频税后 Calmar 0.50 vs QQQ 0.57；16 条主路径无一条满足冻结的
  QQQ 统治力标准（收益更高且回撤不更深）；总 verdict `PROMISING_BUT_INSUFFICIENT`。

## 后果

- 冻结的协议（`paper-validation-v1.0-final`，提交 `e50e0b9`）作为记录保留，
  不产生任何观测义务。
- 未创建引擎、调度器、正式观测、时钟或 Phase 9；无任何待清理的运行中任务。
- Tiingo 数据源验收结论（`SOURCE_ACCEPTANCE_PASS`，V5 `LATENCY_PASS`）保留为
  独立事实，不因本决定改变。
- 本决定可逆：用户未来可重新授权（需新协议版本或新冻结）后再议。

## 项目状态

历史研究冻结（`research-v1.0-final`）不受影响。本项目回到"研究已冻结、无前瞻验证"
状态；后续如有新方向（新策略、新数据源），另行立项讨论。
