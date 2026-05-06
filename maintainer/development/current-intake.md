# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Stage E working-memory Anthropic advisory integration closeout
- **Goal**: 已完成在不改变 release authority 的前提下，把 working-memory advisory seam 真实接入 Anthropic `claude-sonnet-4-6`，补上 degraded fallback，并新增独立 LLM advisory audit 轨道。
- **Change type**: feature closeout

## Ownership

- **Layer**: `l3_deliberation`
- **Canonical owner**: `eva/l3_deliberation/memory/working_memory_model_client.py` 与 `eva/l3_deliberation/reasoning/working_memory.py` 的 working-memory advisory seam
- **Touched current files**: `eva/l3_deliberation/memory/working_memory_model_client.py`, `eva/l3_deliberation/memory/working_memory_adapter.py`, `eva/l3_deliberation/reasoning/working_memory.py`, `eva/kernel/config.py`, `eva/kernel/state.py`, `eva/kernel/main.py`, related tests, `README.md`, `docs/current-status.md`, `maintainer/development/roadmap.md`, `maintainer/development/phase-c-progress.md`
- **Owner class**: stable

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 Stage E 新 feature slice，不属于当前 codebase realignment 的 R1/R2/R3 收敛动作

## Boundary check

- **Affected contracts**: working-memory advisory request/response schema、runtime advisory source selection、append-only runtime audit persistence
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**: 改动限定在既有 working-memory adapter/model-client seam 与 runtime append-only persistence surface；不扩张 mediator、tool edge 或 transitional action path 的长期职责

## Verification

- **Freeze tests**: `tests/l3_deliberation/memory/test_working_memory_adapter.py`, `tests/l3_deliberation/memory/test_working_memory_model_client.py`, `tests/l3_deliberation/reasoning/test_working_memory.py`, `tests/l3_deliberation/tool_edge/test_executors.py`, `tests/l3_deliberation/peer_circuit/test_mediator.py`, `tests/integration/test_main_runtime.py`
- **Additional tests**: Anthropic client request shaping、LLM failure fallback、独立 audit file persistence、advisory-only schema bound、bounded advisory score participation
- **Need full regression?** yes

## Docs sync

- **Docs to update**:
  - `README.md`
  - `docs/current-status.md`
  - `maintainer/development/current-intake.md`
  - `maintainer/development/roadmap.md`
  - `maintainer/development/phase-c-progress.md`
- **Docs actually needed for this change**: `README.md`, `docs/current-status.md`, `maintainer/development/current-intake.md`, `maintainer/development/roadmap.md`, `maintainer/development/phase-c-progress.md`

## Go / no-go

- **Can implementation start now?** yes
- **If no, what must be clarified first?**:

## Intake status

- 当前状态：**已完成（实现、验证与文档同步已落账；待下一项 intake 覆盖）**
