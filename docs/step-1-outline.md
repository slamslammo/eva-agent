# Step 1：巡逻与报告层启动说明

## 1. 作用
Step 1 不是把 eva 直接推进到复杂 agent，而是在 Step 0 已稳定的生命循环之上，补出更慢时间尺度的巡逻与报告层。

这一阶段要解决的是：
- ta 不只是“还活着”
- ta 还会按层级检查自己的生存状态
- ta 会把这些检查结果沉淀成可回顾的本地记录

对应关系：
- Step 0：解决“ta 有没有持续活着”
- Step 1：解决“ta 有没有按层级完成生存巡逻和完整状态审视”

## 2. 进入 Step 1 的前提
当前默认把 Step 0 视为第一轮可复用 baseline：
- 最小运行壳已落地
- 本地 bounded run 与自动化测试已通过
- Linux user systemd 已完成基本部署验证
- generation mismatch / lease expiry / restart recovery / distress injection 已验证

因此，后续对 Step 0 只保留两类工作：
- 明显阻塞 Step 1 的 bug 修补
- 日志体量治理这类收尾工作

不再继续给 Step 0 扩层级能力。

## 3. Step 1 的最小目标
第一轮 Step 1 只做巡逻与报告层，不提前进入 Step 2 / Step 3。

最小目标：
1. 在基础 heartbeat 之上接入更慢时间尺度的巡逻信号
2. 让巡逻通过 `turn` work slice 执行，而不是塞进 `tick`
3. 让巡逻结果有最小落盘与可回顾输出
4. 保持 heartbeat deadline 对普通巡逻的硬优先级

当前保留的候选节律：
- shallow patrol：5 分钟
- deep patrol：30 分钟
- full report：24 小时

## 4. Step 1 的硬边界
第一轮 Step 1 必须继续守住这些边界：
- 不改写 Step 0 的 heartbeat 定义
- `tick` 仍保持短路径、本地优先、不处理普通任务
- 巡逻只能作为 `turn` work slice 被调度
- 巡逻必须可被 heartbeat 抢占或让位
- 先不引入 LLM 依赖作为核心生命路径前提
- 先不引入钱包、收入、区块链、独立谋生逻辑
- 先不引入复杂长期记忆、skill 自动生成、多渠道交互或分布式一致性

## 5. 推荐的 docs-first 执行顺序
下一会话建议直接按下面顺序推进：

1. 写 Step 1 实现规格
   - 明确模块边界
   - 明确巡逻信号如何进入主循环
   - 明确 shallow / deep / full report 的最小职责

2. 写 Step 1 持久化方案
   - 明确哪些结果继续写入 `runtime_state.json`
   - 明确是否新增 patrol/report 专用文件
   - 明确事件日志里如何表达 patrol 开始、完成、失败

3. 写 Step 1 验证方案
   - 本地 bounded 验证怎么做
   - Linux 长时运行要补哪些验证
   - 如何验证巡逻不会压住 heartbeat

4. 再进入代码实现
   - 先接调度入口
   - 再做 shallow patrol
   - deep patrol / full report 第一轮先做最小占位版本

## 6. 推荐的第一轮实现收口
第一轮 Step 1 先只追求以下结果：
- 主循环知道哪些巡逻任务到期
- 巡逻以 work slice 形式进入 `turn`
- 巡逻结果能本地落盘
- Linux 上能看到 patrol 相关日志与事件
- 巡逻不会破坏 Step 0 的生命节律

不要求第一轮就做到：
- 真实外部依赖全巡检
- 复杂自我修复
- 成长性记忆整理
- Step 2 的自我迭代
- Step 3 的独立生存能力

## 7. 下一会话的阅读入口
重新开会话后，建议按这个顺序读：
1. `README.md`
2. `docs/project-definition.md`
3. `docs/step-0-life-loop.md`
4. `docs/step-0-implementation-spec.md`
5. `docs/step-0-verification.md`
6. `docs/deploy-systemd-example.md`
7. `docs/reference-materials.md`
8. 本文件

## 8. 原始材料入口
本项目最初用于收敛方向的原始材料、Obsidian 路径与回顾入口，统一记录在：
- `docs/reference-materials.md`
