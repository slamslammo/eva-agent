# 12. 工程验证与不变量测试

## 12.1 heartbeat-first

如果前面各章定义的是完整实现方案的结构，那么这一章讨论的就是：**如何验证这些结构真的成立，而不是只停留在文档叙述里。**

EVA-agent 的验证不能退化成零散测试列表。因为系统最关键的不是某个函数对不对，而是若干工程不变量是否真的由结构保证。因此，本章的组织方式不按模块功能分，而按不变量分。

第一条必须验证的不变量，就是 **heartbeat-first**。

这条验证要回答的不是“有没有 heartbeat 字段”，而是：
- ordinary work 是否会长期阻塞 `tick`；
- `tick` / `turn` 的优先级边界是否真实存在；
- 在存在复杂 deliberation、长时 tool execution 或外部压力时，heartbeat 是否仍能维持最低 cadence；
- 当生命级边界收紧时，系统是否真的会优先收缩 ordinary work。

也就是说，heartbeat-first 的验证重点不是观察值存在，而是调度主权是否成立。一个系统即使记录了 heartbeat 时间戳，如果普通工作仍可无限期挤压 heartbeat，它就没有满足这一不变量。

因此，这一类验证往往需要：
- 结构检查：`tick` / `turn` 是否真的分离；
- 行为检查：高负载或长路径下 heartbeat 是否仍保持边界；
- 长跑检查：长期运行下 heartbeat 是否持续成立，而不是只在短测里看起来正常。

## 12.2 instance validity

第二类必须验证的是 **instance validity**。这条不变量回答的是：系统是否真的有能力判断“我是不是还合法的我”。

验证重点不在于某个布尔值叫不叫 `instance_valid`，而在于支撑它的结构是否可靠：
- `lock` 是否真的约束了单实例持有；
- `generation` 是否能区分新旧实例；
- `lease` 是否会在心跳失效后自然过期；
- downstream 是否只能读取合法性投影，而不能自行宣布自己仍然有效。

这类验证至少要覆盖两种层面：
- **结构层**：实例身份机制是否存在、是否分层、是否有明确 owner；
- **行为层**：在竞争持有、替换实例、心跳丢失等情况下，系统是否真的切换到 invalid posture，并阻止后续 ordinary release。

如果 instance validity 只是一条软约定，那么连续性边界就是假的；系统仍可能在旧实例、重复实例或失效实例上继续推进行为。

## 12.3 read-only drive

第三类验证围绕 **drive as internal context** 展开。这里的关键不变量是：drive 必须是 L2 的主状态，L3 与更高层只能读取其广播面，而不能直接改写它。

因此，验证重点不是“系统里有没有 drive_state”，而是：
- `drive_state` 与 `drive_broadcast` 是否区分清楚；
- L2 是否是 drive update 的唯一 owner；
- L3 是否只能读取 `drive_broadcast`；
- compatibility path 或 higher layer 是否存在反向改写 drive 主状态的漏洞。

也就是说，read-only drive 的验证本质上是一类 owner boundary test。只要高层还能直接把 drive 当作普通变量重写，L2 就不再是内部环境层，drive 也会立即退化成 planner 的策略参数。

因此，这类测试要检查的不只是值是否变化正确，更是**谁有权改、谁只能读**。

## 12.4 anchor pre-generative restriction

第四类验证围绕 Anchor System 展开，重点是不变量：**约束必须发生在候选生成之前。**

这条验证最容易被做假。因为很多系统会在末端加一个 deny / validator，看起来也能“拦住不允许动作”。但这不等于 pre-generative restriction 成立。

真正需要验证的是：
- candidate generation 面对的是否已经是 `A'(s)` 而不是完整 `A(s)`；
- capability restriction 与 parameter-domain restriction 是否在生成前生效；
- 系统是否存在“先生成完整候选，再后置删减”仍作为主路径的情况；
- reflex path 是否也遵守基本 Anchor 限制，而不是变成越权豁免通道。

因此，这类测试往往需要同时结合：
- 接口验证：candidate generator 的输入面是什么；
- 轨迹验证：不允许域是否曾真实进入候选形成过程；
- 结构验证：后置 deny 是否只是 defense-in-depth，而非主约束位置。

只有这样，才能证明 Anchor 真的是 pre-generative structural restriction，而不是换了名字的 safety filter。

## 12.5 mediator-only side effects

第五类验证围绕 **reasoning ≠ release** 与 **mediator-only side effects** 展开。

完整实现必须满足：任何普通 side effect 都只能经过 `mediator -> tool edge` 路径越过外部边界。因此验证重点应是：
- reasoning core 是否存在直接触发 external executor 的路径；
- peer circuit / mediator 是否真的是 release gate；
- tool edge 是否真的是唯一合法 execution boundary；
- 是否有 helper、脚本、兼容层等旁路偷偷绕开 mediator。

这类验证的难点在于，它经常不是值错了，而是边界偷偷漏了一个洞。也正因为如此，mediator-only side effects 的验证应特别重视：
- 调用路径审查；
- side effect 出口枚举；
- release log 与 execution log 的一致性；
- reflex-exempt path 与 ordinary mediated path 的明确区分。

如果这一不变量失守，那么 default inhibition、reasoning / release 分离、audit 可追踪性都会一起失守。

## 12.6 audit / memory 分层

第六类验证围绕 **audit 与 memory 分层** 展开。

EVA-agent 要求：
- append-only event / audit stream 用于事实回放；
- cognitive / episodic memory 用于 salience-weighted experience shaping；
- learning / habit artifacts 用于结果回流后的结构沉淀。

因此，验证重点不是“有没有几种 jsonl 文件”，而是这些数据轨的语义是否真的分开：
- audit 是否保持 append-only；
- cognitive memory 是否不是简单复制 audit；
- retrieval 是否读取的是 memory substrate，而不是直接拿 audit 当知识库；
- learning / habit artifacts 是否保持为 bounded adaptation，而不是混回主审计轨或主状态轨。

这是一类非常关键的数据层级验证。因为只要 audit 与 memory 混写，系统就会同时失去两件事：事实保真与经验塑形。

## 12.7 长跑验证与结构验证

把前面几类验证收束起来，可以看到 EVA-agent 的验证至少分成两大类：

### 结构验证

结构验证关注的是：owner 边界、调用边界、输入输出面、数据轨分层是否按架构成立。例如：
- `tick` / `turn` 是否分离；
- `drive_state` 与 `drive_broadcast` 是否分离；
- candidate generation 是否真的读取 restricted domain；
- tool edge 是否真是唯一合法 side effect 出口；
- audit / memory / learning artifacts 是否真的分轨。

这类验证通常可以在较短时间内进行，因为它关注的是结构是否存在。

### 长跑验证

长跑验证关注的是：这些结构在持续运行中是否真的不坍塌。例如：
- 长时间负载下 heartbeat-first 是否仍成立；
- 长时间运行后 instance validity 与 lease 机制是否仍可靠；
- drive 是否随时间正常 update / decay / recovery，而不是越跑越漂移；
- release / outcome / memory / habit 的闭环是否在长时间尺度上维持 bounded 形态，而不是越学越扩权。

这类验证不能靠一次短测完成，因为 EVA-agent 的许多关键主张本来就发生在持续存在与持续学习的时间尺度上。

因此，本章真正想强调的是：EVA-agent 的验证不能被写成“跑几个单测就行”。它必须始终回扣不变量，并同时覆盖**结构是否成立**与**结构能否长期成立**。只有这样，前面各章里定义的完整实现方案，才不只是纸面架构，而是可被工程证明的存在结构。

一个更实际的判断标准是：当这些不变量被破坏时，系统必须能被明确地判断为**架构失真**，而不是只表现为“结果没那么理想”。例如：
- ordinary work 能长期挤压 tick，说明 heartbeat-first 失守；
- 非法实例仍能继续 ordinary release，说明 instance validity 失守；
- 高层可直接改写 drive 主状态，说明 read-only drive 失守；
- 不允许域曾真实进入 candidate formation，说明 anchor pre-generative restriction 失守；
- side effect 可绕过 mediator / tool edge，说明 release boundary 失守；
- cognitive memory 只是复制 audit，说明 audit / memory 分层失守。

下一章将从验证转向部署形态，说明这样一套以长期在线和持续存在为前提的系统，应以怎样的工程基线被运行起来。
