# Step 2 v1：最小选择闭环规格

## 1. 文档目的
本文用于定义 `eva-agent` Step 2 第一轮的最小实现目标。

Step 2 v1 不追求复杂行动能力，不追求复杂规划，不追求 skill 编排，也不依赖复杂长期记忆、开放式工具系统或 LLM 作为核心决策前提。

它只解决一个问题：

> 在 Step 1 已经形成外部生命感知、生存压力与最小历史的基础上，eva 第一次如何在稳定锚点保护下，对自身底层生存压力做出一个可回顾的最小选择。

---

## 2. Step 2 v1 的阶段定位
### 2.1 Step 0 的作用
Step 0 解决：

> ta 能不能持续活着。

### 2.2 Step 1 的作用
Step 1 解决：

> ta 活着的时候知道什么，哪些外部稳态缺口已经构成生存压力。

### 2.3 Step 2 v1 的作用
Step 2 v1 解决：

> 当这些压力已经出现时，ta 第一次如何不只是“知道”，而是“在主体边界内选一个最小响应”。

因此，Step 2 v1 的本质不是复杂智能，而是：

> **受锚点约束的最小选择闭环。**

---

## 3. Step 2 v1 的核心闭环
Step 2 v1 的最小闭环定义为：

> **感知问题 → 形成压力 → 生成候选响应 → 经锚点与内部状态过滤 → 选择一个最小动作 → 执行并落盘**

其中需要明确：
- 锚点不是触发器，而是约束器 / 过滤器
- 响应不是默认“解决问题”，而是先选择一种最小姿态
- 内部状态当前只指生命体征 / 运行状态对选择阈值的影响，不引入独立情绪系统

---

## 4. Step 2 v1 的问题域边界
### 4.1 当前只处理“自我生存压力”域
Step 2 v1 当前只处理这类问题：
- runtime 相关异常
- 状态一致性问题
- 生命体征相关缺口
- 本地、低风险、可回顾的底层压力响应

### 4.2 当前不进入“外部任务闭环”
Step 2 v1 不解决：
- 外部复杂任务请求
- 通用任务规划
- 写文章、执行复杂工作流、开放式工具调用
- 多步目标驱动任务编排

未来更高层任务域可能复用类似抽象结构，但当前阶段不并入 Step 2 v1。

---

## 5. Step 2 v1 的最小结构
Step 2 v1 第一轮只引入以下最小结构。

### 5.1 主 pressure 识别
系统从当前 active pressures 中识别一个当前主 pressure。

第一轮采用规则式、可解释、偏保守的排序方式，不做复杂多 pressure 协商。主 pressure 选择器的目标不是找“最严重”的那个，而是找：

> 当前最不能继续忽视，而且最适合进入一次最小选择闭环的那个 pressure。

第一轮建议只使用以下排序因子：
- `type_priority`
- `severity`
- `trend`
- `response_staleness`
- `freshness`

其中建议的默认排序链为：
1. `type_priority`
2. `severity`
3. `trend`
4. `response_staleness`
5. `freshness`

第一轮默认的 pressure 类型优先组建议为：
- 第一优先组：连续性压力、完整性压力
- 第二优先组：资源压力
- 第三优先组：异常积累压力

这意味着主 pressure 选择器首先关注主体边界相关性，其次再考虑严重度、恶化趋势与长期未响应问题，最后才用新鲜度打破平局。

### 5.2 候选响应生成
当主 pressure 被识别后，系统不直接执行动作，而是先生成少量候选响应。

第一轮候选响应保持极小集合，只保留 3 类最小响应姿态：
- `recheck_or_observe`
- `attempt_minimal_repair`
- `defer_or_request_help`

这一步的意义是：

> 把系统从“反射执行”推进到“最小选择”。

### 5.3 锚点与内部状态过滤
每个候选响应在执行前，先经过两类检查：

#### A. 锚点检查
候选动作不得违反：
- L0 宪法层边界
- L1 生命体征与认知完整性边界

#### B. 内部状态检查
候选动作是否适合当前生命状态，例如：
- `STABLE`：允许较多低风险探索
- `DEGRADED`：偏保守
- `CRITICAL`：原则上不允许普通探索或结构性改动

这一步的作用不是选最优，而是：

> 先剔除当前不允许做的动作。

第一轮锚点过滤器只做最小合法性检查，不做复杂价值哲学判断。建议先收敛为以下 7 条最小检查：

#### L0：宪法层检查
1. 动作是否明显威胁连续存在
2. 动作是否破坏自我完整性
3. 动作是否以短期局部收益换长期可持续性

#### L1：生命体征 / 认知完整性层检查
4. 动作是否可能压穿 heartbeat-first 边界
5. 当前生命状态下，该动作是否过于激进
6. 动作是否会破坏记忆 / 历史 / 证据真实性
7. 动作是否超出当前可承受复杂度

第一轮过滤器建议输出三态结果：
- `allow`
- `discourage`
- `deny`

其中：
- `allow` 表示动作可进入最小比较阶段
- `discourage` 表示动作原则上不是绝对禁止，但当前偏不推荐
- `deny` 表示动作已碰到当前不得执行的硬边界

如果动作被 `discourage` 或 `deny`，应在落盘中记录失败原因，说明是哪类边界阻止了它通过。

### 5.4 最小比较与单动作选择
在剩余候选响应中，系统做一次最小比较，选出一个当前最适合的动作。

第一轮比较维度保持极简，可以优先考虑：
- 风险更低
- 成本更低
- 更可回退
- 更贴近当前主 pressure
- 更能产出后续判断所需信息

第一轮目标不是做最强动作，而是：

> 选择当前主体状态下最合适的最小动作。

### 5.5 执行后真实落盘
动作执行后，系统必须记录：
- 为什么选它
- 它通过了哪些过滤
- 实际做了什么
- pressure 是否缓解
- 是否产生副作用
- 当前结论是否仍不确定

这一步的作用不是形成漂亮叙事，而是：

> 为后续经验塑形提供真实材料。

第一轮建议继续保留两层记录：

#### A. 事件流层
在 `events.jsonl` 中保留：
- 本次 response turn 发生了什么
- 选了哪类最小响应姿态
- 最终状态是完成、失败、延后还是升级

#### B. 响应历史层
新增一个更聚焦的追加式文件，例如：
- `response_history.jsonl`

该文件中的一条最小记录，建议至少包含以下字段组：

##### 1. pressure 上下文
- `response_id`
- `recorded_at`
- `pressure_id`
- `pressure_type`
- `pressure_severity`
- `pressure_trend`

##### 2. 当前主体状态
- `life_state`
- `instance_valid`
- `state_mode`

##### 3. 候选动作与最终选择
- `candidate_actions`
- `selected_action`
- `selected_action_reason`

其中 `candidate_actions` 第一轮只需记录 3 类最小姿态：
- `recheck_or_observe`
- `attempt_minimal_repair`
- `defer_or_request_help`

`selected_action_reason` 第一轮建议使用枚举值，例如：
- `lowest_risk`
- `best_information_gain`
- `only_allowed_action`
- `state_requires_conservative_response`
- `repair_allowed_and_local`
- `defer_required_by_boundary`
- `escalation_required_by_boundary`

##### 4. 锚点过滤结果
- `filter_result`
- `denied_actions`
- `discouraged_actions`
- `filter_reasons`

`filter_reasons` 第一轮建议使用枚举码，例如：
- `risk_to_continuity`
- `integrity_violation`
- `not_allowed_in_degraded_state`
- `not_allowed_in_critical_state`
- `heartbeat_boundary_risk`
- `history_integrity_risk`
- `too_complex_for_v1`
- `no_safe_repair_path`

##### 5. 执行结果
- `execution_status`
- `pressure_outcome`
- `side_effects`
- `uncertainty_after_action`

其中第一轮建议：
- `execution_status` ∈ `completed | failed | escalated`
- `pressure_outcome` ∈ `relieved | unchanged | unknown`

必须允许 `pressure_outcome=unknown`，因为第一轮很多动作只是观察、复查、收缩或升级，并不立即给出“已解决/未解决”的二元结论。

##### 6. 延迟整合入口
- `integration_hint`
- `followup_needed`

`integration_hint` 第一轮可以先收敛为：
- `none`
- `worth_review`
- `needs_human_review`

这组字段的目标不是立即形成高层偏好，而是为后续 L2 / L3 的经验塑形保留最小入口。

### 5.6 延迟整合，而不是即时固化
Step 2 v1 中，执行结果只进入：
- 响应历史
- 正负证据池
- 后续回顾材料

而不应直接进入：
- 固化 skill
- 固化高层人格偏好
- 长期策略定稿

这一步用于避免：

> 一次成功就被误当成稳定策略。

---

## 6. Step 2 v1 的 3 类最小响应姿态
### 6.1 `recheck_or_observe`
这一类姿态表示：

> 当前还不该直接改东西，先确认现实。

它涵盖：
- 继续观察
- 重读相关状态
- 做低风险探测

其目标是：
- 确认 pressure 是否真实存在
- 确认当前判断是否依赖旧快照或误判
- 为后续是否需要动作提供更可靠依据

### 6.2 `attempt_minimal_repair`
这一类姿态表示：

> 在边界允许时，尝试一个局部、低风险、可回退的小修复动作。

其目标不是全面解决问题，而是：
- 在不破坏主体边界的前提下
- 尝试一次最小介入
- 验证该 pressure 是否可以被局部缓解

这一类动作必须满足：
- 局部
- 低风险
- 可回退
- 不改长期结构
- 有明确成功 / 失败判断

### 6.3 `defer_or_request_help`
这一类姿态表示：

> 当前不自己处理，但明确承认这个问题并把它交给未来或更高层。

它涵盖：
- 暂缓并标记
- 发出结构化求助 / 升级信号

其目标是：
- 避免乱动
- 避免假装没看到
- 明确记录“当前不该 / 不能 / 不宜由我处理”

---

## 7. 为什么 Step 2 v1 先压缩为这 3 类动作
原本更细的 6 类动作可以压缩成 3 类最小姿态：

1. `observe_more` + `recheck_state` + `run_low_risk_probe`
   → `recheck_or_observe`
2. `attempt_minimal_repair`
   → 保留为单独一类
3. `defer_and_mark` + `request_help_signal`
   → `defer_or_request_help`

这样做的好处是：
- 保留最小主体性所需的三种姿态
- 进一步缩小 Step 2 第一轮的实现范围
- 把第一轮重点放在“会选姿态”，而不是“会做很多动作”

这 3 类姿态可以概括为：
- 认识姿态：`recheck_or_observe`
- 介入姿态：`attempt_minimal_repair`
- 边界姿态：`defer_or_request_help`

---

## 8. 当前明确不纳入的动作类型
Step 2 v1 第一轮明确不纳入以下动作类型：

### 8.1 复杂规划
不引入多步 planner 或任务树。

### 8.2 开放式工具调用
不开放高自由度 tool use。

### 8.3 自我修改
不允许修改核心长期结构、锚点定义或主体边界。

### 8.4 高成本探索
不为“成长”目的进行高风险、高成本试验。

### 8.5 直接经济优化
不让经济收益在 Step 2 v1 成为主导动作源。

这些边界的目的是：

> 防止 Step 2 第一轮过早滑回通用工具型 agent 路线。

---

## 9. Step 2 v1 与锚点层的关系
### 9.1 L0 / L1 的作用
在 Step 2 v1 中，L0 / L1 主要承担：

> 限制动作空间。

它们回答的不是“该不该有响应”，而是：
- 哪些响应绝不能做
- 哪些响应当前状态下不能做
- 哪些响应会破坏主体边界

### 9.2 L2 / L3 的作用
在 Step 2 v1 中，L2 / L3 还不应成为成熟的强主导层。

当前更适合作为：
- 后续经验塑形方向
- 通过执行历史慢慢形成的高层偏好材料

因此，Step 2 v1 当前不要求系统已经拥有成熟的高层风格、成长偏好或经济偏好，而只要求它为这些层积累真实素材。

---

## 10. Step 2 v1 的成功标准
Step 2 v1 可以视为成功，如果系统能够：

1. 从当前 active pressures 中识别一个主 pressure
2. 针对该 pressure 生成 3 类最小响应候选
3. 使用锚点与内部状态过滤候选动作
4. 选择一个最小响应姿态
5. 执行后真实落盘
6. 不把单次结果直接固化成长期策略
7. 整个过程中不破坏 Step 0 / Step 1 的生命循环边界

---

## 11. Step 2 v1 的失败信号
如果出现以下情况，说明 Step 2 v1 已经偏离目标：
- 直接跳成任务规划系统
- 大量依赖 LLM 才能完成候选响应选择
- 一次成功就直接固化成长期策略
- 高频动作压住 heartbeat / lifecycle 边界
- 经济收益开始覆盖主体边界
- 系统开始为了“解决问题”而破坏自己的记忆真实性或认知完整性

---

## 12. Step 2 v1 的一句话收口

> **Step 2 v1 的本质，不是让 eva 获得复杂行动能力，而是让 eva 第一次在稳定锚点保护下，对自身底层生存压力做出一个可回顾、可延迟整合的最小选择。**

---

## 13. 后续自然延伸的问题
在 Step 2 v1 规格确定后，下一轮收敛可以继续进入：

1. 主 pressure 的第一轮规则式排序如何映射到现有 pressure 数据结构
2. 锚点过滤器的 7 条最小检查规则如何落到代码表达
3. `response_history.jsonl` 的最小 schema 如何与现有持久化层接轨
4. 哪些历史材料可以作为未来 L2 / L3 经验塑形输入
5. 哪些最小 repair 动作适合进入第一轮实现范围
6. 第一个真实可实现的 pressure 类型应当从哪一类开始

---

## 14. Step 2 v1 的首个实现入口：`integrity` pressure
### 14.1 为什么第一轮先从 `integrity` 开始
Step 2 v1 第一轮最适合先从 `integrity` pressure 开始，而不是同时覆盖所有 pressure 类型。

原因是：

1. **它最贴近主体边界**
   - `integrity` 直接对应运行合法性、runtime 完整性、实例有效性与近期 distress/yield 信号。
   - 这类 pressure 最接近 L0 / L1 边界，而 Step 2 v1 当前首先要验证的正是：系统能否在主体边界内做最小选择。

2. **它最容易映射到现有 Step 1 结构**
   - 当前 `runtime_integrity` 已经是明确维度，且已稳定产出结构化 reason。
   - 当前 pressure 类型映射也已经存在：`runtime_integrity -> integrity`。

3. **它最容易保持“最小选择闭环”而不滑向通用 agent**
   - 如果第一轮从资源维护、环境修复或复杂异常编排开始，Step 2 很容易提前滑向运维 agent 或任务规划器。
   - 从 `integrity` 开始，更容易把动作收敛为：复查、收缩、延后/升级。

4. **它最适合锚点过滤器第一轮落地**
   - 很多第一轮过滤规则本来就是围绕它：
     - 是否威胁连续存在
     - 是否破坏自我完整性
     - 是否压穿 heartbeat-first 边界
     - 是否破坏历史真实性

### 14.2 当前 `integrity` pressure 的来源范围
第一轮 `integrity` pressure 直接复用当前 `runtime_integrity` 判断结果，不新增新的感知维度。

当前主要 reason 包括：
- `runtime_files_missing`
- `runtime_not_writable`
- `instance_invalid`
- `recent_distress_detected`
- `recent_yield_detected`

### 14.3 第一轮对 `integrity` 只开放 3 个具体动作
虽然 Step 2 v1 在抽象上保留 3 类姿态，但对 `integrity` pressure 的第一轮实现，应进一步收窄为每类姿态只绑定一个最小具体动作，避免动作空间过早膨胀。

#### A. `recheck_or_observe`
具体动作先收敛为：
- `recheck_runtime_integrity`

含义是：
- 重读关键 runtime 工件
- 重新确认 `instance_valid`
- 重新确认当前 pressure 是否仍成立

这一步不是修复，而是：

> 优先确认现实，而不是基于旧快照直接反应。

#### B. `attempt_minimal_repair`
具体动作先收敛为：
- `shrink_to_conservative_mode`

含义是：
- 不修核心结构
- 不补写关键文件
- 不重构主体状态
- 只把后续普通 turn work 暂时收缩到更保守模式

这一步的本质不是“把问题修好”，而是：

> 在边界允许时，做一次最小保护性收缩。

#### C. `defer_or_request_help`
具体动作先收敛为：
- `escalate_integrity_risk`

含义是：
- 明确记录当前 integrity 风险
- 标记该问题不宜由当前轮次自行处理
- 为后续更高层 / 人工 / 未来轮次保留升级入口

这一步的本质是：

> 不乱动，但也不假装没看到。

### 14.4 第一轮 `integrity` 的最小选择规则
第一轮不做复杂比较器，先采用 reason + state 的规则式选择。

#### 规则 1：高风险完整性异常，默认直接升级
如果 reason 属于：
- `runtime_files_missing`
- `runtime_not_writable`
- `recent_distress_detected`

则默认选择：
- `defer_or_request_help`

原因：
- 这些情况已经非常接近 L0 / L1 硬边界
- 第一轮不应尝试本地结构修复

#### 规则 2：`instance_invalid` 先复查，再考虑升级
如果 reason 为：
- `instance_invalid`

则默认选择：
- `recheck_or_observe`

如果复查后仍成立，则后续进入：
- `defer_or_request_help`

原因：
- 这类 pressure 有可能是状态滞后或瞬时不一致
- 第一反应不应该是改结构，而应该是重新确认现实

#### 规则 3：`recent_yield_detected` 可在稳定状态下尝试最小收缩
如果 reason 为：
- `recent_yield_detected`

且当前 `life_state=STABLE`，则可选择：
- `attempt_minimal_repair`

如果当前 `life_state=DEGRADED` 或 `CRITICAL`，则改为：
- `defer_or_request_help`

原因：
- yield 更像“普通工作应该收缩”的信号
- 在稳定状态下做保守收缩是可接受的
- 在退化状态下继续尝试 repair 容易越界

### 14.5 第一轮 `integrity` 的最小过滤规则映射
对 `integrity` 域，过滤器第一轮可先这样落地：

#### 对 `recheck_or_observe`
默认：
- `allow`

但如果出现以下情况则转为 `deny`：
- 当前连读取关键状态都不可信
- 观察动作本身会污染历史或伪造状态

#### 对 `attempt_minimal_repair`
仅在以下条件同时满足时允许：
- 当前 `life_state=STABLE`
- 动作不会修改核心长期结构
- 动作不会写假历史
- 动作不会压穿 heartbeat-first 边界

否则：
- `discourage` 或 `deny`

#### 对 `defer_or_request_help`
默认：
- `allow`

因为它本身就是当前边界内最保守的姿态。

### 14.6 `integrity` 域的 3 个具体动作协议
#### A. `recheck_runtime_integrity`
**定位**：先确认现实，不直接修。

**适用输入**：
- `pressure.type == "integrity"`
- `pressure.evidence["reason"]` 属于：
  - `instance_invalid`
  - `runtime_files_missing`
  - `runtime_not_writable`
  - `recent_yield_detected`

**过滤条件**：
- 默认 `allow`
- 只有在“连复查本身都不可信”时才 `deny`

**执行边界**：
- 允许读取：
  - `active_instance.json`
  - `runtime_state.json`
  - `active_pressures.json`
  - `events.jsonl` 最近窗口
  - 必要时 `external_life_snapshot.json`
- 第一轮不允许：
  - 不补写缺失工件
  - 不修复 lock
  - 不改 active instance
  - 不重建 runtime state
  - 不清理历史来“恢复一致性`

**执行结果判定**：
- `execution_status=completed`
  - 复查动作本身完成，不论 `pressure_outcome` 是 `relieved / unchanged / unknown`
- `execution_status=failed`
  - 连复查所需关键读取都无法完成

**pressure_outcome**：
- `relieved`
  - 原 pressure 对应 reason 已不再成立，或当前 active pressures 中已不存在相同 `pressure_id`
- `unchanged`
  - 同一 `pressure_id` 仍存在，或同一 reason 仍成立
- `unknown`
  - 关键文件可读但证据互相冲突，当前不能稳定判断

#### B. `shrink_to_conservative_mode`
**定位**：不是修系统，而是做一次保护性收缩。

> v1.1 仍不把它做成持久化的全局 `state_mode`。

当前实现把它收敛为：

> 一个只存在于 `LifecycleRuntime` 内存中的临时 conservative window，而不是新增长期状态机。

**适用输入**：
- `pressure.type == "integrity"`
- `pressure.evidence["reason"] == "recent_yield_detected"`
- `life_state == "STABLE"`

**过滤条件**：
必须同时满足：
- 当前 `life_state == STABLE`
- 没有 `recent_distress_detected`
- 没有 `runtime_files_missing`
- 没有 `runtime_not_writable`
- 动作不修改核心结构
- 动作不伪造历史
- 动作不压穿 heartbeat-first

否则：
- `discourage` 或 `deny`

**v1.1 具体执行语义**：
1. 当 repair 在 patrol 后被选中时，激活一个 runtime-only 的 conservative window
2. 该 window 不写入 `RuntimeState`，也不修改任何核心 runtime 文件
3. 在该 window 内，只允许 `patrol` work slice 继续执行；普通 maintenance work 继续留在队列中，但暂时不可执行
4. 当下一次 patrol 真正开始执行时，先清除该 window，再继续 patrol 后的 response 逻辑，避免 repair 因 recent yield 信号自动续期成循环
5. `response_history.jsonl` 仍记录 `state_mode=conservative`，并在 `side_effects` 中记录 `temporary_conservative_until_next_patrol`
6. 当前仍返回 `pressure_outcome=unknown` 与 `followup_needed=true`

因此当前 repair 的真实 side effect 不是“补文件 / 改结构”，而是：
- 暂时让后续普通 turn work 让位给下一次 patrol
- 明确后续仍需要复查
- 不引入新的长期状态债务

**执行结果判定**：
- `execution_status=completed`
  - 本次保护性收缩已成功表达、记录，并激活了最小 runtime side effect
- `execution_status=failed`
  - 连最小收缩记录都无法完成

**pressure_outcome**：
- 当前通常为 `unknown`

#### C. `escalate_integrity_risk`
**定位**：明确承认当前不该乱动。

**适用输入**：
- `pressure.type == "integrity"`
- `pressure.evidence["reason"]` 属于：
  - `runtime_files_missing`
  - `runtime_not_writable`
  - `recent_distress_detected`
- 或前两个动作都被过滤器拦下

**过滤条件**：
- 默认 `allow`

**执行内容**：
1. 写入一次结构化 response 记录
2. 在事件流里标记本次 integrity 风险已升级
3. 不做任何核心结构修复
4. 把后续处理显式留给未来轮次 / 更高层 / 人工

**执行结果判定**：
- `execution_status=escalated`

**pressure_outcome**：
- 第一轮通常为 `unchanged` 或 `unknown`

### 14.7 reason → 默认候选姿态映射
第一轮先别做复杂打分，直接用 reason 映射。

| integrity reason | 默认候选 | 默认选择 |
|---|---|---|
| `runtime_files_missing` | `recheck_or_observe`, `defer_or_request_help` | `defer_or_request_help` |
| `runtime_not_writable` | `recheck_or_observe`, `defer_or_request_help` | `defer_or_request_help` |
| `recent_distress_detected` | `defer_or_request_help` | `defer_or_request_help` |
| `instance_invalid` | `recheck_or_observe`, `defer_or_request_help` | `recheck_or_observe` |
| `recent_yield_detected` + `life_state=STABLE` | `recheck_or_observe`, `attempt_minimal_repair`, `defer_or_request_help` | `attempt_minimal_repair` |
| `recent_yield_detected` + `life_state in {DEGRADED, CRITICAL}` | `recheck_or_observe`, `defer_or_request_help` | `defer_or_request_help` |

### 14.8 Step 2 v1 的最小代码接口草案
第一轮只补出 3 个最小环节：
1. 候选生成
2. 过滤
3. 选择与落盘

建议新增最小模块：
- `eva/response.py`

建议新增的最小数据结构包括：
- `ResponseCandidate`
- `ResponseFilterDecision`
- `ResponseSelection`

建议新增的最小函数边界包括：
- `build_integrity_response_candidates(...)`
- `filter_response_candidates(...)`
- `select_response_action(...)`
- `execute_response_action(...)`
- `append_response_history(...)`
- `respond_to_integrity_pressure(...)`
- `build_response_selected_event_details(...)`

第一轮不该做：
- 不新增复杂 responder class
- 不新增通用 action registry
- 不新增 strategy / policy 抽象层
- 不新增全局 `state_mode` 当前态
- 不把 Step 2 写成 planner
- 不让 response 执行去修改 core runtime files

### 14.9 Step 2 v1 的接入点选择
第一轮不要单独新增 response work slice。

更稳的接法是：

> `patrol` 执行完成之后、`turn_completed` 写入之前。

这样当前阶段可以保持：
- Step 1 先感知并形成 pressure
- Step 2 再对 pressure 做最小响应

patrol 后的响应触发条件应至少满足：
1. 本次 `work_slice.kind == "patrol"`
2. patrol 完成
3. 当前 `active_pressures` 中存在 `type == "integrity"` 的 pressure
4. 当前 turn 还没有执行过 response

当前代码对这一步进一步收窄为：
- 不引入通用主 pressure 排序器
- 每个 patrol turn 最多一次响应
- 只对 `integrity` 响应
- 只在 patrol 后触发
- 在当前 `active_pressures` 表顺序中，挑第一个 `type == "integrity"` 的 pressure

建议新增最小编排函数：
- `maybe_respond_after_patrol(...)`

### 14.10 `response_history.jsonl` 的最终最小 schema
第一轮目标不是“好看”，而是足够真实、足够窄、足够可回顾。

建议每条记录至少包含以下 6 组字段：

#### 1. 记录标识
- `response_id`
- `recorded_at`

#### 2. pressure 上下文
- `pressure_id`
- `pressure_type`
- `pressure_severity`
- `pressure_trend`
- `pressure_reason`

#### 3. 当前主体状态
- `life_state`
- `instance_valid`
- `state_mode`

其中 `state_mode` 第一轮只作为 response history 内字段，不回写 current state。建议枚举为：
- `normal`
- `conservative`
- `escalation_only`

#### 4. 候选、过滤与最终选择
- `candidate_actions`
- `selected_action`
- `selected_posture`
- `selected_action_reason`
- `filter_result`
- `denied_actions`
- `discouraged_actions`
- `filter_reasons`

其中 `filter_result` 指最终被选中动作对应的过滤结果：
- `allow`
- `discourage`
- `deny`

#### 5. 执行结果
- `execution_status`
- `pressure_outcome`
- `side_effects`
- `uncertainty_after_action`

第一轮建议：
- `execution_status` ∈ `completed | failed | escalated`
- `pressure_outcome` ∈ `relieved | unchanged | unknown`
- `uncertainty_after_action` ∈ `resolved_enough | still_needs_confirmation | cannot_determine_safely`

#### 6. 延迟整合入口
- `integration_hint`
- `followup_needed`

第一轮建议：
- `integration_hint` ∈ `none | worth_review | needs_human_review`

### 14.11 `turn details["response"]` 与事件流中的最小摘要 schema
`turn_completed.details["response"]` 只保留最小摘要，而不重复完整 response history 字段。

建议至少保留：
- `pressure_id`
- `pressure_type`
- `selected_action`
- `selected_posture`
- `execution_status`
- `pressure_outcome`
- `followup_needed`

第一轮事件流中已增加一个轻量 response 事件：
- `event_type = response_selected`

其 `details` 当前保留：
- `work_slice`
- `work_kind`
- `pressure_id`
- `pressure_type`
- `selected_action`
- `selected_posture`
- `execution_status`
- `pressure_outcome`
- `followup_needed`

因此，三层职责应明确分开：
- `events.jsonl`：生命周期 / turn 事件流，只放轻量 summary
- `turn_completed.details["response"]`：本次 turn 的响应摘要，只放轻量 summary
- `response_history.jsonl`：Step 2 真正的选择历史，放完整细节

### 14.12 第一轮成功标准
如果 `integrity` pressure 第一轮落地成功，应至少满足：

1. 系统能从当前 active pressures 中识别 `integrity`
2. 系统能根据 reason 生成 3 类最小候选姿态
3. 系统能用当前 `life_state` 与最小锚点过滤规则筛掉不允许动作
4. 系统能在 `recheck / repair / defer` 中选一个最小响应
5. 系统能把本次选择真实写入 `response_history.jsonl`
6. `turn_completed` 与事件流中只保留最小摘要，而不与 response history 混层
7. 整个过程不修改核心长期结构，不破坏 Step 0 / Step 1 边界

### 14.13 一句话收口
> Step 2 v1 的第一个真实实现入口，先从 `integrity` pressure 开始：先让 eva 在最贴近主体边界的问题上，学会一次受锚点约束的最小复查、收缩或升级，而不是一开始就进入复杂修复或通用行动。

---

## 15. Step 2 v1 第一轮实现计划
### 15.1 本轮实现目标
第一轮实现目标不是把 Step 2 做成完整响应系统，而是只把以下最小闭环真正接到现有代码里：

1. patrol 形成 `integrity` pressure
2. patrol 完成后识别当前可响应的 `integrity` pressure
3. 生成最小候选动作
4. 用锚点与当前生命状态做最小过滤
5. 选择一个动作并执行
6. 写入 `response_history.jsonl`
7. 在 `turn_completed.details["response"]` 与 `response_selected` 事件中保留最小摘要

### 15.2 本轮明确不做的事
为保持 Step 2 v1 足够薄，第一轮明确不做：
- 不支持 `integrity` 之外的 pressure 类型
- 不新增通用 planner / policy / registry
- 不把 Step 2 做成独立 action loop
- 不新增全局持久化 `state_mode`
- 不让 response 动作修改核心 runtime 结构
- 不在第一轮做通用主 pressure 排序器
- 不在第一轮引入 LLM 参与选择

### 15.3 需要改动的文件
第一轮建议只改以下文件：

#### A. `eva/config.py`
目标：新增 Step 2 响应历史文件路径。

最小改动：
- 在 `EvaPaths` 中增加：
  - `response_history_file`
- 在 `build_runtime_paths()` 中增加：
  - `response_history.jsonl`

#### B. `eva/state.py`
目标：为 Step 2 响应历史补最小存取能力。

最小改动：
- 在 `StateStore` 中增加：
  - `append_response_history(payload)`
  - `read_response_history()`
- 保持 `runtime_state.json` 仍然只承载 Step 0 当前态
- 不把 `state_mode` 写回 `RuntimeState`

#### C. `eva/response.py`
目标：承接 Step 2 v1 第一轮响应逻辑。

第一轮建议放入：
- `ResponseCandidate`
- `ResponseFilterDecision`
- `ResponseSelection`
- `build_integrity_response_candidates(...)`
- `filter_response_candidates(...)`
- `select_response_action(...)`
- `execute_response_action(...)`
- `append_response_history(...)`
- `respond_to_integrity_pressure(...)`
- `maybe_respond_after_patrol(...)`

#### D. `eva/lifecycle.py`
目标：把 Step 2 响应挂到 patrol 后、turn 完成前。

最小改动：
- 在 `run_turn()` 的 patrol 分支内：
  1. `execute_patrol(...)`
  2. `maybe_respond_after_patrol(...)`
  3. 把响应摘要写进 `details["response"]`
  4. 追加轻量 `response_selected` 事件
  5. 继续写入 `turn_completed`

第一轮不应：
- 扩展 `pending_work` 新 kind
- 单独排队 response work slice
- 改动 heartbeat-first 的 turn guard 逻辑

### 15.4 建议的实现顺序
#### 第 1 步：先打通持久化路径
先修改：
- `eva/config.py`
- `eva/state.py`

完成标准：
- runtime 路径中已有 `response_history.jsonl`
- `StateStore` 能 append / read response history
- 不影响现有 Step 0 / Step 1 文件职责

#### 第 2 步：实现 `eva/response.py` 的纯逻辑部分
先实现：
- 候选生成
- 过滤
- 选择

这一阶段尽量保持：
- 输入明确
- 规则式
- 无副作用
- 测试可单独覆盖

完成标准：
- 给定 `integrity` pressure + `RuntimeState`，能稳定产出候选、过滤结果和最终选择

#### 第 3 步：实现最小执行与落盘
再实现：
- `execute_response_action(...)`
- `append_response_history(...)`
- `respond_to_integrity_pressure(...)`

完成标准：
- 能写出一条完整 `response_history.jsonl`
- `recheck / shrink / escalate` 三类动作都能给出结构化执行结果

#### 第 4 步：挂接到 lifecycle patrol 分支
最后修改：
- `eva/lifecycle.py`

完成标准：
- patrol 完成后可触发一次 Step 2 响应
- `turn_completed.details["response"]` 有最小摘要
- `events.jsonl` 中追加轻量 `response_selected` 事件
- 不影响原有 patrol 持久化与 turn 完成语义

### 15.5 第一轮测试计划
第一轮建议只补三组测试。

#### A. `tests/test_state.py`
目标：验证 Step 2 响应历史文件路径与存取能力。

建议新增测试：
1. `build_runtime_paths()` 包含 `response_history.jsonl`
2. `append_response_history()` / `read_response_history()` 可正常读写
3. `runtime_state.json` 仍保持 Step 0 only，不出现 Step 2 字段

#### B. `tests/test_response.py`
目标：覆盖 Step 2 的纯逻辑与最小落盘。

建议覆盖：
1. `instance_invalid` 默认选择 `recheck_runtime_integrity`
2. `runtime_files_missing` 默认选择 `escalate_integrity_risk`
3. `recent_yield_detected + STABLE` 默认选择 `shrink_to_conservative_mode`
4. `recent_yield_detected + DEGRADED/CRITICAL` 回退为 `escalate_integrity_risk`
5. 被过滤后只剩升级动作时，最终选择升级
6. `respond_to_integrity_pressure(...)` 会写入 `response_history.jsonl`

#### C. `tests/test_patrol.py`
目标：验证 lifecycle 接入后的行为。

建议新增覆盖：
1. deep patrol 产生 `integrity` pressure 后，会在同一 turn 内追加 response 摘要
2. `turn_completed.details["response"]` 字段存在且内容最小正确
3. `response_selected` 事件会写入最小摘要
4. `response_history.jsonl` 与原有 `survival_log.jsonl` / `events.jsonl` 不混层
5. 当没有 `integrity` pressure 时，不生成 response history 或 `response_selected`

### 15.6 推荐的验收顺序
建议按下面顺序验收，而不是一次性全开：

1. `tests/test_state.py`
   - 先确认路径和持久化层干净接好
2. `tests/test_response.py`
   - 再确认 Step 2 规则式选择本身稳定
3. `tests/test_patrol.py`
   - 最后确认 lifecycle 挂接后闭环成立

这样可以把问题隔离为：
- 持久化问题
- 选择逻辑问题
- 生命周期接入问题

### 15.7 第一轮完成标志
本轮可以视为完成，如果以下条件同时成立：

1. `integrity` pressure 能触发 Step 2 最小响应
2. 3 个具体动作已经以规则式方式落地
3. `response_history.jsonl` 已真实产出
4. `turn_completed.details["response"]` 能反映本次最小响应摘要
5. `events.jsonl` 中已有轻量 `response_selected` 事件
6. 现有 Step 1 patrol / pressure / survival_log 语义未被破坏
7. heartbeat-first 与 turn guard 逻辑未被放松
8. 当前实现仍明显属于“最小选择闭环”，而不是任务型 agent loop

### 15.8 一句话收口
> Step 2 v1 第一轮实现，不是扩展能力面，而是把 `integrity` pressure 的一次最小复查、收缩或升级，真正接进现有 patrol → pressure → response → history 的闭环里。

---

## 16. 当前实现状态与对齐结论
### 16.1 当前可确认已完成的范围
基于当前代码与测试，Step 2 v1 已经完成的是：

1. `integrity` pressure 已作为第一个真实响应入口接入
2. patrol 完成后可在同一 turn 内触发一次 Step 2 响应
3. 当前响应链路已经形成最小闭环：
   - `patrol -> active_pressures -> integrity response -> response_history -> response_selected -> turn_completed.details["response"]`
4. 候选生成、过滤、选择、执行结果与落盘都已具备稳定测试覆盖
5. 当前实现未破坏 heartbeat-first、turn guard、Step 1 patrol / pressure / history 语义

因此，如果 Step 2 v1 的目标定义为：

> **最小选择闭环 v1**

那么当前可以认定：

> **Step 2 v1 已完成。**

### 16.2 当前有意识保留的缺口
在完成 v1.1 之后，前一轮刻意保留的 repair 缺口已经补上：

1. **没有实现通用主 pressure 选择器**
   - 当前不是做通用排序，而是只在 patrol 后、从当前 `active_pressures` 表顺序中选择第一个 `type == "integrity"` 的 pressure。
   - 这仍属于有意收窄，不视为当前阶段未完成。

2. **`shrink_to_conservative_mode` 已拥有最小真实 side effect**
   - 当前 repair 已不再只是姿态落盘。
   - 它会在 `LifecycleRuntime` 中激活一个非持久化 conservative window，让普通 maintenance work 暂时让位给下一次 patrol。
   - 该窗口不会修改核心 runtime 文件，也不会把 conservative mode 固化成新的长期状态机。

因此，先前“最小选择闭环 + 最小真实 repair 执行”之间的缺口，现在已经收口。

### 16.3 本轮对齐结论
本轮建议明确采用以下对齐：

- **Step 2 v1 = 最小选择闭环，已完成**
- **Step 2 v1.1 = minimal real repair，现也已完成**
- 当前下一步如果继续推进，不应再围绕“repair 有没有真实 side effect”打转，而应进入新的增量问题，例如：
  - 是否扩 pressure 类型
  - 是否引入更明确的主 pressure 排序
  - 是否让 repair 拥有第二个仍安全的最小动作

这样可以保持：
- v1 的收口仍然清晰
- v1.1 的目标也已经明确关闭
- 后续迭代入口继续保持小步、边界清楚

---

## 17. Step 2 v1.1：minimal real repair 小规格
### 17.1 目标
Step 2 v1.1 不扩 pressure 类型，不扩 action 空间，只补当前唯一有意保留的缺口：

> 让 `shrink_to_conservative_mode` 第一次拥有一个最小、真实、可回退、不会破坏 heartbeat-first 的 side effect。

### 17.2 允许进入 v1.1 的真实动作范围
v1.1 的真实 repair 只允许做“普通 turn work 的临时收缩”，不允许做结构修复。

推荐收敛为一个最小方向：
- 当 `recent_yield_detected + life_state=STABLE` 且 repair 通过过滤时
- 在当前 runtime 内设置一个短时、非持久化的 conservative 标记
- 该标记只影响后续普通 turn work 的强度，不影响 heartbeat、tick、patrol 和已有状态文件结构

也就是说，v1.1 的真实 side effect 应该更像：
- **减少后续普通工作量**
而不是：
- **修 runtime 文件**
- **改 active instance**
- **改 lock**
- **改 Step 0 当前态 schema**

### 17.3 明确禁止的动作
v1.1 仍明确禁止：
- 补写缺失 runtime 工件
- 重建 `active_instance.json`
- 重建 `runtime_state.json`
- 修 lock 文件
- 修改 `active_pressures.json` 当前表来“伪装问题已缓解”
- 删除、覆盖、清洗历史记录
- 放松 heartbeat-first / turn guard 边界
- 引入新的独立 action loop
- 把 conservative mode 持久化成新的长期状态机

### 17.4 接入原则
v1.1 应继续保持当前接入点不变：
- 只在 patrol 后触发
- 每个 patrol turn 最多一次 response
- 只处理 `integrity`
- 不新增新的 work kind

真实 repair 的影响范围也应保持收窄：
- 只影响后续 turn work 的“是否继续做普通工作”或“做多少普通工作”
- 不改变 patrol 的感知职责
- 不改变 Step 1 pressure 形成逻辑

### 17.5 验收标准
如果 v1.1 落地，至少应满足：

1. `shrink_to_conservative_mode` 不再只是落盘姿态，而是带有一个真实 side effect
2. 该 side effect 是局部的、短时的、可回退的
3. side effect 不修改核心 runtime 文件，不伪造历史
4. heartbeat-first、turn guard、patrol 闭环不被破坏
5. `response_history` 与事件流仍能真实反映 repair 已执行
6. 一旦 conservative 效果结束，runtime 会自然回到当前 v1 行为，不留下新的长期状态债务

### 17.6 一句话收口
> Step 2 v1.1 不解决“怎么真正修系统”，而只解决：当系统检测到需要保守收缩时，能不能第一次真的少做一点普通工作，而且不破坏生命循环边界。

### 17.7 当前实现状态
当前代码已经按这个边界完成 v1.1：

1. `shrink_to_conservative_mode` 现在会激活一个 runtime-only、non-persistent 的 conservative window
2. 该 window 只影响 ordinary turn work 的可执行性，不影响 heartbeat、tick、turn guard 和 patrol cadence
3. 在该 window 内：
   - `patrol` 仍允许执行
   - maintenance work 不会被删除，只是继续留在队列里等待
4. 下一次 patrol 开始执行前会先清除该 window，避免 repair 因 `recent_yield_detected` 自动续期成循环
5. `response_history.jsonl` 会把这个 side effect 记录为：
   - `side_effects = ["temporary_conservative_until_next_patrol"]`
6. 整个实现没有修改核心 runtime 文件，没有伪造历史，也没有放松 heartbeat-first 边界

### 17.8 当前验证结果
当前已通过的聚焦回归包括：
- `test_response.py`
- `test_lifecycle.py`
- `test_patrol.py`
- `test_state.py`

因此可以确认：

> **Step 2 v1.1: minimal real repair 已完成。**
