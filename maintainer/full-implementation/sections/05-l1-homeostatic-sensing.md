# 5. L1：Homeostatic Sensing

## 5.1 L1 的职责边界

如果说基础设施层让主体拥有了一具能持续运行的“身体”，那么 L1 就是主体第一次正式知道：**自己正处在什么状态。**

它的职责可以压成一句话：**在任何更深层解释发生之前，先检测与可存活区间的偏离，并把信号按紧急程度路由出去。**

它由四个结构性元素组成：

![L1 position](../../../docs/assets/architecture/l1_position_in_eva.svg)


## 5.2 Sensor Registry — 可扩展的感知底座

L1 不是“预先写死几项指标”，而是先建立一个正式的 sensor registry。因为具体要感知什么天然依赖部署环境；真正需要稳定下来的，是**传感器如何注册、如何被采样、如何统一输出**。

感知的内容是部署相关的：跑在云主机上要感知磁盘和进程；跑在 Raspberry Pi 上要感知温度和电量；跑在容器里要感知 OOM 和重启次数。设计期定下的是**注册接口的形状**——任何符合这个形状的 sensor 都能挂上来。

挂上来的 sensor 输出经过注册器之后**形状统一**：不管底层是读 `/proc/loadavg` 还是 ping 一个外部 endpoint，对 L1 上层来说都是同一种 `Signal` 对象。这是为什么后面的信号总线只需要一种处理逻辑。

以跑在云主机为例：

![L1 sensor registry](../../../docs/assets/architecture/l1_sensor_registry.svg)


## 5.3 State + Rate — L1 最关键的概念

每一个有意义的指标都应该被**两个视角**同时观察：

- **State（当前态）**：此刻这个指标是多少。"剩余 10 GB"、"心跳年龄 0.2 秒"、"过去 30 分钟出现 2 次错误"。
- **Rate（变化率）**：单位时间的变化方向和速度。"每小时减少 2 GB"、"心跳年龄正在以 1 秒/秒 的速度增长"、"错误率 5 分钟翻一倍"。

只有 state 的系统是**被动反应式**——必须等到指标越过阈值才知道有事。同时有 state 和 rate 的系统是**预测式**的——可以在指标越过阈值之前算出大概什么时候会越过，提前进入应对姿态。这才是 EVA 理论里"metabolism"（代谢感知）的工程含义。

下面这张图展示同一个信号 `disk_free` 在两种视角下能告诉 agent 多少东西：

![L1 state vs rate](../../../docs/assets/architecture/l1_state_vs_rate.svg)

## 5.4 Signal Publication Contract — 统一输入面先于下游消费

L1 不只是把信号"发出去"，还必须先把它们收敛成一个稳定的发布合同。否则，后面 L2、L3 与 reflex path 看到的就不是同一种输入面，而只是各自直接读取底层来源的临时拼接。

这个 contract 至少应稳定三件事：

- **统一 shape**：每个 signal 都至少带有 source、class、severity、observed_at、payload 这类基础字段；
- **统一 owner**：raw sensing 归 sensor owner，signal classification 与 publication 归 L1 owner；
- **统一消费语义**：下游读取的是已经标准化的 signal surface，而不是各自回头直连 sensor。

这条 contract 的意义，不在于字段名长什么样，而在于后续层面对 L1 的依赖必须是**正式输入面依赖**，而不是对底层采样细节的隐式耦合。

## 5.5 Signal Bus — 分类先于解读

L1 的第三个结构性元素是把所有 sensor 产生的信号收集到一根**总线**上，由总线**优先级分类**之后再决定送往哪里。

关键工程点是：**分类必须发生在解读之前**。

因为解读需要时间。如果一条 threat 信号要等"先弄清楚发生了什么"再决定怎么处理，那等到搞清楚的时候响应窗口已经关掉了。生物大脑里 thalamus 就是这个角色——把进来的信号先粗分成"快路给 amygdala"、"慢路给 cortex"，然后两边并行处理。EVA 的 signal bus 是同样的逻辑。

分类规则本身**很便宜**：只看信号的 type 和 severity 这两个字段，不深入 payload。三个类别的语义是：

- **threat**：偏离已经明显，需要立刻反应。例如 `lock_lost`、`runtime_files_missing`、`distress_injected`。这条路径下游接到 L2 的反射弧。
- **status**：状况发生了变化但不紧急，需要在合适时机处理。例如 `disk_degraded`、`anomaly_count_rising`、`patrol_completed`。这条路径下游接到 L2 的 drive 更新和 L3 的 deliberation。
- **background**：常态心跳，没有偏离。例如 `tick_completed`、`heartbeat_refreshed`、`patrol_no_change`。下游用作环境氛围采样和可观测性数据，不触发任何主动处理。

![L1 signal bus](../../../docs/assets/architecture/l1_signal_bus_classification.svg)

## 5.6 Fast / Slow Path Split — 信号分类后真正分道扬镳

紧急程度分类的**结构性意义**在这里才显现：threat 信号走的是与 status/background 信号完全不同的下游路径，而且这两条路径**在架构上并行**——快路不需要等慢路，慢路也不会去争快路的执行权。这是直接借鉴生物大脑的 thalamo-amygdala（快路）vs thalamo-cortex（慢路）双路结构。

两条路的差异不只是速度，更是**经过的层数**：

- **快路**：threat → L2 反射弧 → 执行。**完全不经过 L3**。约一个 tick 内完成。这就是为什么它不能产生复杂的"考虑"——产生不出来，因为 L3 不在路径上。
- **慢路**：status/background → L2 drive 更新 → L3 deliberation → mediator → 执行。每一步都消化一会儿。可能跨越多个 tick。

![L1 fast/slow split](../../../docs/assets/architecture/l1_fast_slow_path_split.svg)

## 5.7 L1 与 kernel / L2 的关系

L1 的位置既不能下沉到 kernel，也不能上抬去代替 L2。

- **与 kernel**：kernel 提供 heartbeat cadence、instance gate 与最低 runtime posture；L1 在这个运行边界里完成 sensing，而不拥有 cadence 主权。
- **与 L2**：L1 发布标准化 signal，L2 读取 signal 并把它们吸收到 drive update、decay、recovery 中；L1 不直接拥有 drive 主状态。

因此，L1 真正负责的是把"发生了什么"整理成正式输入面；至于这些输入如何改变内部环境，则由 L2 owner 继续承接。

## 5.8 这一层真正决定了什么

L1 是后续所有反应能力和 deliberation 的唯一入口：
- 没有 registry，上层接口会随部署漂移；
- 没有 rate，系统只能事后反应；
- 没有 signal bus，所有输入会被同等对待；
-没有快慢分流，threat 会和 ordinary work 共用一条慢路径。

因此，L1 的角色不是“多做一点预处理”，而是让主体第一次以正式结构知道：**现在发生了什么，而且这些变化该走哪条处理路径。** 

下一章进入 L2：Drive Layer。
