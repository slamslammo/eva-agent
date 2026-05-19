# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Phase 2 V1 — observation_tools Crafter plugin — 已完成

### 状态
- **全部 4 个子切片落地**：V1-a（extractor 后端）→ V1-b（前端渲染）→ V1-c（浏览器截图验证）→ V1-d（closeout）
- 回归：**457 / 458 测试通过**（1 个 pre-existing `l2_drive` 失败，与 V1 无关）
- 新增 12 个测试（Crafter extractor + plugin hook 集成）
- E2E smoke：用 `validation-runs/phase1.7-live-smoke/runtime/`（211 turns）启动 viewer，浏览器截图确认 Crafter section 完整渲染（生命体征 / 库存 / 工具 / 紧缺资源 / 视野感知 / 本 turn 变化 / 维度状态）
- 完整 progress 报告：`maintainer/development/v1-progress.md`

### 启动方式
```bash
python -m observation_tools \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --port 28391
```
浏览器打开 `http://127.0.0.1:28391`，默认选最末 -1 的 turn（避开末位 off-by-one）。

### V0 → V1 累计成果
- V0 黑盒子查看器：核心 L1 → L2 → L3 → mediator → 动作链路全展开 + 顶部时间轴 + drive 折线 + turn 列表
- V1 Crafter plugin：场景特定 vitals / inventory / local_view 等观察数据接入

### 用户反馈记录（V1 截图验证时）
- "整体视觉效果不好"：bar 对比度低、时间轴折线对比度低、整体信息密度可以提升
- 用户决定：先把 Crafter plugin 内容完成（已做），等基于一个具体长跑跑起来再做整体视觉优化
- 已记入 `v1-progress.md` 的 "V2 候选优先级" 第 1 项

### 下一步
- **Phase 3**：6h Crafter 长跑（用户驱动；viewer 已就绪可实时观察）
- **D-6**：长跑数据出来后的 post-run 分析
- **V2 整体视觉优化**：等长跑跑起来再统一调整
