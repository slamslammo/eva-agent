# Stage H Follow-ups

本文档记录 **Stage H review closeout** 后确认的非阻塞 follow-up。

## 1. PressureType 应提升为 framework 一级概念

- **Status**: open
- **Why it matters**: H-0F 已把 `pressure_type` 放进 `DimensionSpec`，但 framework 当前仍接受任意字符串，无法验证 scenario 注册的 pressure-type 语义是否稳定一致。
- **Current limitation**: Linux 与 Crafter 现在都能通过同一 seam 注入 pressure type，但 framework 无法声明合法集合，也无法阻止语义漂移。
- **Suggested direction**: 后续在 framework 定义 `PressureType` enum / protocol，并在 scenario activation 或 dimension registration 时做校验。

## 2. pressure_id 当前只在单-scenario 激活假设下稳定

- **Status**: open
- **Why it matters**: 当前 `pressure_id` 由 `pressure-{pressure_type}-{reason}` 构造，在单一 active scenario 下可接受，但如果未来做跨 scenario 横向对比，同 type 同 reason 会有命名空间冲突。
- **Current limitation**: framework 现在默认一次只激活一个 scenario，因此不会立刻出错，但 stability-metrics 若要做跨 scenario 聚合会受限。
- **Suggested direction**: 若未来引入跨 scenario pressure comparison，再在 `pressure_id` 中显式带入 `scenario_name` 前缀。

## 3. Crafter outcome confidence 仍是占位实现

- **Status**: open
- **Why it matters**: Crafter outcome observer 当前仍使用 hardcoded `0.75 / 0.4` confidence，不是由实际 outcome uncertainty 计算出来的置信度。
- **Current limitation**: learning record 会保留 confidence，但该值目前只表达粗粒度占位判断，不具备 Linux 路径那样的语义强度。
- **Suggested direction**: 在后续实验硬化中，让 Crafter confidence 从 `OutcomeVector.uncertainty` 或更细粒度 observation delta 派生。

## 4. `local_view_state -> safety` 是当前的单-drive 简化

- **Status**: open
- **Why it matters**: `local_view_state` 同时携带 threat / resource / utility 信息，但当前 drive mapping 与 pressure-type mapping 都把它压到 `safety`，这是一种有意但狭窄的简化。
- **Current limitation**: acquisition / capability 相关的 local-view 信号不会直接作为独立 drive feed 进入当前 Crafter shaping。
- **Suggested direction**: 后续若扩展 Crafter scenario richness，可把 local-view 拆成更细的 dimension 或明确引入多-drive projection 语义。

## 5. Crafter compatibility bridge candidate widening — identified post-Stage-H, resolved in Round 1.A

- **Status**: resolved (Round 1.A)
- **Why it matters**: Stage H intentionally narrowed the Crafter compatibility bridge to emit a fixed 3-candidate set (`noop` / `sleep` / `do`) to focus the stage on framework-boundary validation. This narrowing was correct for Stage H's goal but was **not scheduled** as a Stage H followup — it became a forgotten constraint after Stage I closed.
- **Symptom surfaced**: post-Stage-I, the Crafter agent could not unlock any of the 22 Crafter achievements because it had no path to `chop` / `place_*` / `make_*` actions, and the existing `CRAFTER_STARTUP_PRIOR_DEFINITIONS` priors were effectively dead code in the selection path.
- **Resolution**: Round 1.A widened the compatibility bridge to resolve concrete actions inside the existing 3-profile vocabulary, wired inherited priors and habit bias into selection, and surfaced profile provenance via the scenario-owned `posture` token. See `maintainer/development/round-1a-progress.md` for the full slice-by-slice record.
- **Related observation**: a follow-up identified during Round 1.A — the L3 mediator's profile choice under sustained avatar degradation is stabilize-dominated. Round 1.A's widening is structurally complete but runtime expression of the wider escalate / observe surfaces depends on Round 1.B (exploration drive / v0.6.1 §4) to unlock non-stabilize profile selection.
