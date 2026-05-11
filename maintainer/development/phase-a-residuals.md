# Phase A Residuals

本文档记录 **Phase A closeout 后经架构师 review 确认、但未在 Phase A 内部继续处理的 residuals**。

它的职责不是重开 Phase A，也不是改写 Phase A 的已完成结论，而是把已经确认的 residual debt 单独落账，并明确后续 handoff 去向。

## 1. 当前状态

- Phase A 保持 **已完成基线** 结论不变
- 下列 residuals 是在 **Phase A A-1 ~ A-8 完整 review** 中识别出的后续清理项
- 这些项不要求回滚或重做 Phase A
- 它们的 cleanup owner 已 handoff 到 **Stage G — v0.6 capability landing**

## 2. Residual 1：framework fallback 仍直接知道 Linux scenario

- **位置**：`eva/scenario_bundle.py`
- **当前现象**：`get_active_runtime_scenario()` 在未显式 activation 时，会直接 import `scenarios.linux_runtime` 并将其作为 fallback
- **为什么它是 residual**：
  - Phase A 的主目标是完成 framework / scenario / runner 的边界分离，并在行为等价下完成收口
  - 当前 fallback 虽然保住了兼容启动与测试通过，但它仍让 framework module 直接知道一个 concrete scenario
  - 因此它应被理解为 compatibility convenience，而不是长期 canonical framework behavior
- **Phase A 为什么未在当时继续处理**：
  - Phase A 以 behavior-equivalence closeout 为优先
  - 该 fallback 未阻断 A-1 ~ A-8 的结构分离完成
  - 因而在 closeout 时接受其作为 transitional seam 保留
- **后续处理要求**：
  - Stage G 从 `G-0 residual clearance` 开始
  - `eva/scenario_bundle.py` 应删除 Linux fallback
  - 当未 activate scenario 即访问 scenario-dependent framework seam 时，应抛出明确错误，而不是静默回退到 Linux

## 3. Residual 2：framework anchor surface 仍保留 import-time scenario-shaped exports

- **位置**：`eva/anchor/domain_restriction.py`
- **当前现象**：模块 import 时即读取 active scenario anchor bundle，并把 `OBSERVE_FIRST_PROFILE`、`STABILIZE_FIRST_PROFILE`、`ESCALATE_FIRST_PROFILE`、`HIGH_RISK_ESCALATION_REASONS`、`COMPATIBILITY_RELEASE_IMPACT` 作为 framework-level names 暴露
- **为什么它是 residual**：
  - Phase A 已把 Linux-specific anchor policy owner 迁到 `scenarios/linux_runtime/anchors/`
  - 但 framework module public surface 仍保留 scenario-shaped compatibility exports
  - 这意味着 boundary 已显著收紧，但还没有完全达到“framework 不暴露 concrete scenario vocabulary”的更干净状态
- **Phase A 为什么未在当时继续处理**：
  - 该做法在行为兼容层面可接受
  - 它没有阻断 A-5 / A-7 / A-8 的 closeout 与文档同步
  - 因而在 Phase A closeout 中被接受为 transitional compatibility seam
- **后续处理要求**：
  - Stage G `G-0 residual clearance` 需要移除 import-time constant binding 与 framework re-export
  - framework 内部若需要这些值，应在 point-of-use 通过 active scenario lookup 获取
  - 这些 Linux-specific names 不应继续出现在 framework module `__all__` 中

## 4. Handoff 规则

- 这两个 residual 不重开 Phase A 实施
- Phase A 历史文档维持原编号与完成叙事
- 后续 cleanup、验证与进一步 capability landing 统一进入：
  - `maintainer/development/stage-g-v0.6-capability-landing-startup-instruction.md`
- Stage G 的首个 slice `G-0` 就是对这两个 residual 的定点清理

## 5. 与其他文档的关系

- Phase A 已完成事实：`maintainer/development/phase-a-progress.md`
- Phase A A-1 ~ A-8 结构历史：`maintainer/development/phase-a-refactor-progress.md`
- 当前 canonical 组织边界：`maintainer/development/module-organization-contract.md`
- 当前后续 maintainer 规划入口：`maintainer/development/stage-g-v0.6-capability-landing-startup-instruction.md`
