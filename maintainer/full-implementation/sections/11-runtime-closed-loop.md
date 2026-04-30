# 11. 运行闭环

## 11.1 sensing -> signal -> drive

到这一章，完整实现不再按层分别展开，而是要把前面已经建立起来的结构重新接成一条持续运行链。EVA-agent 的关键不只是“有这些层”，而是这些层能否形成一个不会轻易断裂的闭环。

闭环的第一段是：**sensing -> signal -> drive**。

它从基础设施层提供的 heartbeat cadence 与 runtime posture 开始。主体在合法实例与持续节律之中，通过 L1 感知当前内部与外部生命相关状态，把原始输入整理成标准化的 signals，并在深度解释之前先完成 routing。随后，L2 读取这些 signals，不把它们直接翻译成动作，而是把它们吸收到 continuous drive state 中。

这一步非常关键，因为它决定了系统不会从“外部事件发生”直接跳到“马上去做某事”。真正发生的是：
- 先有感知；
- 再有正式 signal surface；
- 再由 signals 改变主体所处的内部 drive environment。

也就是说，外部与内部输入先塑形主体环境，而不是直接下达命令。这正是 EVA-agent 与 task-command 结构的第一个根本分叉。

## 11.2 drive -> candidate shaping

闭环的第二段是：**drive -> candidate shaping**。

一旦 L2 形成了当前 drive environment，L3 就不再是在真空中进行 deliberation。它读取的是：
- 当前 `drive_broadcast`；
- 当前 `runtime_gate_context`；
- 当前 signal context；
- 当前 memory retrieval；
- 当前 Anchor 已经收缩后的 candidate domain。

在这些输入之上，Reasoning Core 形成 candidate suggestions、做 value judgment、暴露 conflict。这里最重要的是：candidate 不是从“任务目标”直接长出来的，而是在 drive context、runtime posture 与 Anchor 共同塑形的环境里生成的。

这意味着，系统不会先决定“外部任务是什么”，再围绕任务做全局规划；而是先处在一个主体环境里，再在这个环境中看见某些候选、忽略某些候选、压低某些候选、强调另一些候选。也正因为如此，deliberation 在 EVA-agent 里不是 command planning，而是 environment-shaped candidate formation。

## 11.3 mediator -> release -> execution

闭环的第三段是：**mediator -> release -> execution**。

前一段结束时，系统拥有的是候选，而不是行为。Reasoning Core 可以给出预测、解释和价值比较，但候选仍处于 default inhibition 之下。接下来，Peer Circuit / Mediator 负责决定：
- 当前是否允许释放；
- 当前多个候选中哪个被释放；
- 当前 runtime gate、Anchor、tool edge 是否共同允许越界。

只有当显式 release process 完成时，candidate 才会进入 Tool Edge，并通过 executors 真正触碰外部世界。

因此，这一段闭环同时保证了两件事：
- reasoning 不等于 release；
- execution 不是系统中某个隐式 helper 顺手做掉的事，而是唯一合法出口上的正式行为。

这条路径一旦成立，系统就不再是“想到了就做”，而是“形成候选之后，仍需经过正式释放边界”。这也是 default inhibition 在时间维度上的真正落点。

## 11.4 outcome -> memory / RPE / habit

闭环的第四段是：**outcome -> memory / RPE / habit**。

行为一旦真正越过 Tool Edge，闭环并没有结束。相反，这才是学习回流开始的位置。系统需要正式记录：
- 实际发生了什么；
- 这与原本的 expected 有何差异；
- 这次偏差是否影响 drive、边界感、未来候选倾向；
- 这次经历是否值得更强地编码进 episodic memory；
- 某条重复成功路径是否开始具备 crystallize 成 habit / skill 的条件。

也就是说，outcome 不是执行后的尾声，而是 memory encoding、RPE 形成与 habit 演化的上游输入。只有这一段存在，系统才不只是“做过很多事”，而是真的被自己的经历重新塑形。

这条回流还有一个关键限制：learning 只能以 bounded 的方式回到未来结构中。它可以形成更强或更弱的倾向、形成更快或更慢的检索、逐渐压缩 deliberative cost，但它不能扩成新的 release authority，也不能绕过 kernel、Anchor 与 mediator。

从写权限上说，bounded learning 至少应满足：
- 可以影响 BG pathway 倾向、episodic salience 与 habit crystallization 条件；
- 可以影响 future reasoning 的 retrieval bias 与 candidate preference；
- 不能直接改写 runtime continuity boundary；
- 不能直接改写 Anchor structural envelope；
- 不能直接授予新的 side effect release 权。

因此，EVA-agent 的学习闭环不是“越学越自由”，而是“越学越被已有边界内的经验结构化”。

## 11.5 整个系统如何形成持续运行闭环

把前面四段重新接在一起，完整运行闭环可以写成：

```text
heartbeat / runtime posture
-> sensing
-> signal routing
-> drive update
-> candidate shaping
-> peer-circuit selection
-> mediated release
-> tool-edge execution
-> outcome evaluation
-> memory / RPE / habit
-> next-cycle context
```

这条链之所以重要，不只是因为它完整，而是因为它让前面所有章节里的关键主张同时落到同一条运行线上：

- **continuous existence** 通过 heartbeat-first、instance validity 与 runtime posture 成为闭环的前提；
- **drive as internal context** 通过 signals 吸收到 L2，而不是直接变成命令；
- **Anchor as pre-generative restriction** 作用在 candidate shaping 之前，而不是执行之后；
- **reasoning ≠ release** 通过 mediator 显式分离；
- **audit 与 memory 分层** 通过 release / outcome / memory 的不同数据轨保持成立；
- **RPE / habit** 通过 outcome 回流重新塑形未来行为，而不是作为外部奖励接口附加在系统外面。

因此，EVA-agent 的“持续运行”不是单纯让一个进程一直活着，而是让这条从感知到学习的结构链持续闭合。主体之所以存在，不只是因为它还没崩溃，而是因为它能在边界之内不断经历、不断更新、不断积累，并把这些积累重新带入下一次存在姿态。

下一章将从运行链回到验证面，说明这样一套闭环结构应如何被测试，以及哪些验证分别对应哪些工程不变量。
