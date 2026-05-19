# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Phase 2 V0 — observation_tools 黑盒子查看器 — 已完成

### 状态
- **全部 7 个子切片落地**：V0-a（骨架）→ V0-b（reader+builder）→ V0-c（HTTP server）→ V0-d（前端骨架）→ V0-e（链路详情）→ V0-f（时间轴 + drive 折线）→ V0-g（smoke + closeout）
- 回归：**445 / 446 测试通过**（1 个 pre-existing `l2_drive` 失败，在 `main` 上也存在，无关）
- 新增 31 个测试，全部通过
- E2E smoke：用 `validation-runs/phase1.7-live-smoke/runtime/`（211 turns）启动 viewer，链路、详情、时间轴全部正常
- 完整 progress 报告：`maintainer/development/v0-progress.md`

### 启动方式
```bash
python -m observation_tools \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --port 8080
```
浏览器打开 `http://127.0.0.1:8080`。

### 下一步
- **Phase 3** —— 6h Crafter 长跑（用户驱动；现在 viewer 也已就绪，长跑时可实时观察）
- **D-6** —— 长跑数据出来后的 post-run 分析
- **V1 候选**（待长跑反馈决定）：Crafter plugin（9×7 grid + 生命条 + inventory）、跨 turn 趋势页、events 链路集成
