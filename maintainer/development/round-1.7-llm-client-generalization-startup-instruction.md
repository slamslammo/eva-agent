# Round 1.7 — LLM Client 通用化（仅 OpenAI Chat Completions）— 启动指令

**接收方**：Claude Code（下一会话）
**发起方**：架构师（当前会话）
**状态**：实施前准备完毕。设计已得到用户批准，可以开始。

**配套文档**：
- `.claude/plans/federated-snacking-engelbart.md` — 主计划，先读这个
- `maintainer/development/round-1b-4-progress.md` — Round 1.B-4 closeout（前置背景）
- DeepSeek thinking-mode 文档：https://api-docs.deepseek.com/guides/thinking_mode
- DeepSeek pricing 文档：https://api-docs.deepseek.com/quick_start/pricing
- OpenAI Chat Completions 参考：https://platform.openai.com/docs/api-reference/chat
- 当前 model-client 模块：`eva/l3_deliberation/memory/working_memory_model_client.py`

---

## 1. 相对原 directive 的修正

原 Phase 1.7 directive（`round-1.7-provider-registry-refactor-startup-instruction.md`，已被本文件替换）提出 `OpenAICompatibleProvider` dataclass + 内置 provider registry，同时把 Anthropic 保留为独立 client 类。

经架构师 / 用户讨论后采纳两个改进：

1. **本轮放弃 Anthropic 支持**。Anthropic 是唯一需要协议适配的主流厂家（Messages API vs Chat Completions、`x-api-key` vs `Bearer`、`content[].text` blocks vs `choices[0].message.content`）。本轮不支持它之后，**剩余的所有 provider 都天然兼容 OpenAI Chat Completions**，框架代码保持统一，零 per-vendor 分支。如果未来需要恢复 Anthropic，那是一次独立、隔离的决策（原生协议 vs OpenAI-compatible beta vs 中转），届时再做，不是现在的技术债承诺。

2. **同时也放弃 provider registry**。去掉 Anthropic 之后，剩余 provider（DeepSeek / OpenAI / Moonshot / Qwen / Ollama / vLLM / Together / OpenRouter / ...）都讲相同的协议、相同的 auth header（`Authorization: Bearer ...`）、相同的路径（`/v1/chat/completions`）。每家厂家的差异**只剩 `base_url` 和 `model`**——两者本来就是 env 变量。Registry 数据结构在这种情况下不承载任何信息，就变成"为假想未来的预留"——这正是 EVA 项目约定明确反对的过度抽象。

净效果：本轮**删除多于新增**。约 -150 ~ -200 LOC 减少（Anthropic client + DeepSeek client + mode-to-provider 映射），约 +80 LOC 新增（一个通用 client + env 校验 + retry/fallback 包装）。

---

## 2. 本轮存在的意义

Round 1.B-4 和 Phase 1.6 完成后，model-client 模块持有两条并行的厂家实现（Anthropic + DeepSeek）。每条都重复 5-6 个 helper（transport / payload builder / response parser / error labeler / URL resolver）。新增任何 provider 都需要在 3 个文件做 ~10 处改动。

但**~95% 的现代 LLM API 已经是 OpenAI Chat Completions 兼容的**（DeepSeek / OpenAI / Moonshot / Zhipu / 阿里 DashScope / Qwen / Together / Fireworks / Groq / OpenRouter / 本地 Ollama / vLLM / LM Studio）。OpenAI Chat Completions 已经是事实标准。

**正确的抽象是"由 env 配置的一个 OpenAI Chat Completions endpoint"，而不是"一个有名字和配置的 provider"。**

本轮顺带处理的事项：
- DeepSeek 的 `deepseek-chat` / `deepseek-reasoner` 模型名即将被弃用。按 DeepSeek 官方文档，应显式使用 `deepseek-v4-flash`（或 `-pro`）+ `{"thinking": {"type": "disabled" | "enabled"}}` 参数控制思考模式。
- 当前我们 pin 在 `deepseek-chat`，能跑但在弃用清单里。
- 新 client 的 `EVA_LLM_EXTRA_PARAMS_JSON` env 变量正好可以承载 `thinking.disabled` 参数（以及未来任何 vendor-private body 字段），且框架层无需了解这些字段的含义。

---

## 3. 本轮做什么、不做什么

**做**：
- 引入 `OpenAICompatibleWorkingMemoryModelClient` —— 唯一的 live client 类
- 由 4 个 env 变量驱动，**无 dataclass / 无 registry / 无 per-vendor 代码**
- 删除 `AnthropicWorkingMemoryModelClient`（及全部 helper / 常量）
- 删除 `DeepSeekWorkingMemoryModelClient`（及全部 helper / 常量）
- 把 CLI `--working-memory-model-client-mode` flag 简化为三个结构性值：`inert` | `heuristic` | `live`
- 加入最小的 retry + fallback 纪律：
  - 5xx / timeout / connection error 上指数退避重试 N 次
  - 耗尽（或 4xx）时 fallback 到 `HeuristicWorkingMemoryModelClient`（让长跑不会因为 API 抖动而崩溃）
- 将 `.local-archive/anthropic.env` 重命名为 `.local-archive/llm.env`；文件不再持 `ANTHROPIC_API_KEY`，仅持 `EVA_LLM_*` 变量
- 在 README 提供 DeepSeek / OpenAI / Moonshot / Ollama 的 env 套装（Anthropic 明确标注本轮不支持）

**不做**：
- 不为旧 mode 名（`anthropic` / `deepseek`）保留 backward-compat alias。EVA 是研究项目，没有外部用户契约
- 不引入任何 vendor 专用的 Python 代码路径
- 不改变 scenario 看到的内容 —— model integration 仍是框架层
- 不改 heuristic / null client（仅重构 live client）
- 不改 working_memory adapter 如何消费 model client（`WorkingMemoryModelClient` ABC 不变）
- 不增加 multi-provider failover / load balancing / cost tracking
- 不引入 LiteLLM 或任何第三方 LLM SDK 依赖

---

## 4. 架构目标

### 一个 client 类

```python
@dataclass(frozen=True)
class OpenAICompatibleWorkingMemoryModelClientConfig:
    """单个 OpenAI-compatible endpoint 的解析后配置。"""

    base_url: str                          # 如 "https://api.deepseek.com/v1"
    api_key: str                           # bearer token
    model: str                             # 如 "deepseek-v4-flash"
    extra_params: dict[str, Any]           # 合并入 request body；不透明
    timeout_sec: float                     # 单次尝试 timeout
    max_retries: int                       # 0 即禁用 retry
    retry_backoff_base_sec: float          # 指数退避基数（如 1.0）


class OpenAICompatibleWorkingMemoryModelClient(WorkingMemoryModelClient):
    """唯一的 live working-memory advisory client。

    不知道任何厂家名。讲 OpenAI Chat Completions，在 transient 失败时
    fallback 到 heuristic。
    """

    def __init__(
        self,
        config: OpenAICompatibleWorkingMemoryModelClientConfig,
        *,
        fallback: WorkingMemoryModelClient | None = None,
        transport: Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]] | None = None,
    ) -> None: ...

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None: ...
```

未提供 fallback 时，默认为 `HeuristicWorkingMemoryModelClient(None)`。

### Env 变量契约

| 变量 | live 模式必需？ | 作用 |
|---|---|---|
| `EVA_LLM_API_BASE_URL` | 是 | 含 `/v1` 段的 base URL。`/chat/completions` 由 client 内部追加 |
| `EVA_LLM_API_KEY` | 是 | Bearer token |
| `EVA_LLM_MODEL` | 是 | 请求体中的 model 字段 |
| `EVA_LLM_EXTRA_PARAMS_JSON` | 否 | JSON object，合并入请求体（vendor-private 字段） |

如果 live 模式下缺失任何必需变量，在 startup 时抛出 `RuntimeError`。**不允许**静默 fallback 到 heuristic（那会掩盖长跑场景下的配置错误）。

如果 `EVA_LLM_EXTRA_PARAMS_JSON` 设了但不是合法 JSON、或是 JSON 但不是 object，同样在 startup 时抛 `RuntimeError`。

### Factory

```python
def build_builtin_working_memory_model_client(
    mode: str,
    config: WorkingMemoryModelClientConfig | None = None,
) -> WorkingMemoryModelClient:
    normalized = str(mode or MODEL_CLIENT_MODE_INERT)
    if normalized == MODEL_CLIENT_MODE_INERT:
        return NullWorkingMemoryModelClient()
    if normalized == MODEL_CLIENT_MODE_HEURISTIC:
        return HeuristicWorkingMemoryModelClient(config)
    if normalized == MODEL_CLIENT_MODE_LIVE:
        return OpenAICompatibleWorkingMemoryModelClient(
            _load_live_config_from_env(config),
        )
    raise ValueError(f"unknown_working_memory_model_client_mode:{normalized}")
```

`_load_live_config_from_env` 是 env 读取与校验的唯一入口。

### CLI flag

```
--working-memory-model-client-mode {inert,heuristic,live}
```

旧的厂家命名值（`anthropic`、`deepseek`）移除。`eva/kernel/main.py` 的 help text 同步更新。

### 删除内容

模块 `eva/l3_deliberation/memory/working_memory_model_client.py`：
- `AnthropicWorkingMemoryModelClient` 及全部 helper
  （`_post_anthropic_messages`、`_anthropic_request_payload`、
  `_anthropic_text_response`、`_anthropic_http_error_label`、
  `_resolve_anthropic_messages_url`）
- `DeepSeekWorkingMemoryModelClient` 及全部 helper
  （`_post_deepseek_chat`、`_deepseek_request_payload`、
  `_deepseek_text_response`、`_deepseek_http_error_label`、
  `_resolve_deepseek_chat_url`）
- 常量：`DEFAULT_ANTHROPIC_MODEL`、`ANTHROPIC_API_KEY_ENV`、
  `ANTHROPIC_API_BASE_URL_ENV`、`DEFAULT_ANTHROPIC_BASE_URL`、
  `ANTHROPIC_MESSAGES_API_PATH`、`DEFAULT_DEEPSEEK_MODEL`、
  `DEEPSEEK_API_KEY_ENV`、`DEEPSEEK_API_BASE_URL_ENV`、
  `DEFAULT_DEEPSEEK_API_BASE_URL`、`DEEPSEEK_CHAT_COMPLETIONS_API_PATH`
- Mode 字符串：`MODEL_CLIENT_MODE_ANTHROPIC`、`MODEL_CLIENT_MODE_DEEPSEEK`
- `eva/l3_deliberation/memory/__init__.py` 和 `eva/l3_deliberation/__init__.py` 中的对应 re-export

### 新增内容

模块 `eva/l3_deliberation/memory/working_memory_model_client.py`：
- `OpenAICompatibleWorkingMemoryModelClientConfig` dataclass
- `OpenAICompatibleWorkingMemoryModelClient` 类
- `MODEL_CLIENT_MODE_LIVE = "live"` 常量
- `EVA_LLM_API_BASE_URL_ENV = "EVA_LLM_API_BASE_URL"`、
  `EVA_LLM_API_KEY_ENV = "EVA_LLM_API_KEY"`、
  `EVA_LLM_MODEL_ENV = "EVA_LLM_MODEL"`、
  `EVA_LLM_EXTRA_PARAMS_JSON_ENV = "EVA_LLM_EXTRA_PARAMS_JSON"`
- `_load_live_config_from_env(config: WorkingMemoryModelClientConfig | None)` helper
- 最小 HTTP transport 函数（stdlib `urllib.request`，无新依赖）+ retry 包装

### 不动的部分

- `WorkingMemoryModelClient` ABC、`WorkingMemoryModelClientRequest`、`WorkingMemoryModelClientResponse`、`WorkingMemoryModelClientConfig`
- `HeuristicWorkingMemoryModelClient`、`NullWorkingMemoryModelClient`
- `WorkingMemoryAdapter` 及其消费方
- `build_working_memory_context_from_store` 及相关 working-memory 机制
- 所有 scenario 代码（`scenarios/` 下任何文件）
- Drive / mediator / anchor / sensor 各层

---

## 5. 实施切片

每个子切片一个 commit（或最后批量一个 commit）。

### 1.7-a — 新增 `OpenAICompatibleWorkingMemoryModelClient` + env loader

新增 client、config dataclass、env loader。**暂不删除**旧 vendor client。Factory 有新 `live` 分支，旧 vendor mode 也仍能用。

本切片是**纯增量** —— 回归必须保持绿，现有 DeepSeek / Anthropic 使用在过渡期内继续工作。

新增测试（`tests/l3_deliberation/memory/test_openai_compatible_client.py`）：
- 设置 `EVA_LLM_EXTRA_PARAMS_JSON` 时 request body 含 extra params
- 未设置 env 时 request body 不含 extra params
- 正确解析 `choices[0].message.content`
- 缺 API key env 抛 `RuntimeError`（消息含 `EVA_LLM_API_KEY`）
- 缺 base URL env 抛 `RuntimeError`
- 缺 model env 抛 `RuntimeError`
- 非合法 JSON 的 `EVA_LLM_EXTRA_PARAMS_JSON` 抛 `RuntimeError`
- 是 JSON 但非 object 的 `EVA_LLM_EXTRA_PARAMS_JSON` 抛 `RuntimeError`
- URL 正确拼接 `base_url + "/chat/completions"`

### 1.7-b — 增加 retry + fallback 包装

为 5xx / timeout / connection error 增加透明 retry（指数退避），耗尽（或 4xx，因为 4xx 是不值得重试的配置错误）时 fallback 到 `HeuristicWorkingMemoryModelClient`。

新增测试：
- 503 重试一次后第二次成功
- 持续 503 重试耗尽后 fallback 到 heuristic，响应含 `metadata.fallback_reason`
- 4xx 不重试，直接 fallback
- 第一次 200：不 retry、不 fallback
- max_retries=0 禁用 retry（单次尝试 → 任何错误都 fallback）

### 1.7-c — 删除 vendor client + 简化 CLI

`live` mode 已经 end-to-end 跑通带 retry 后，删除：
- `AnthropicWorkingMemoryModelClient` + helper + 常量
- `DeepSeekWorkingMemoryModelClient` + helper + 常量
- `MODEL_CLIENT_MODE_ANTHROPIC`、`MODEL_CLIENT_MODE_DEEPSEEK`
- `__init__.py` 中的对应 re-export
- CLI mode choices 缩减为 `inert | heuristic | live`

更新现有测试：
- `AnthropicWorkingMemoryModelClientTests` —— **整体删除**（这条协议路径已消失）
- `DeepSeekWorkingMemoryModelClientTests` —— **整体删除**（被 `test_openai_compatible_client.py` 替代）
- 检查 factory 中针对 vendor mode 名的测试 —— 更新为断言 vendor mode 现在抛 `ValueError`

更新 `eva/kernel/main.py`：
- `--working-memory-model-client-mode` choices：`inert | heuristic | live`
- 同步更新 help text

### 1.7-d — Env 文件重命名 + README env 套装

重命名 `.local-archive/anthropic.env` → `.local-archive/llm.env`。剥除 Anthropic key。内容变为：

```bash
# DeepSeek v4-flash, 非思考模式（advisory 推荐）
export EVA_LLM_API_BASE_URL=https://api.deepseek.com/v1
export EVA_LLM_API_KEY=sk-de63a8f28dde44ea9844b2097de83e9a
export EVA_LLM_MODEL=deepseek-v4-flash
export EVA_LLM_EXTRA_PARAMS_JSON='{"thinking":{"type":"disabled"}}'
```

在 `docs/scenarios-SPEC.md` 或 `docs/architecture-overview.md`（择一更合适的）新增一节，标题为 "LLM advisory configuration"，提供以下 env 套装的复制粘贴模板：

- DeepSeek v4-flash 非思考模式（推荐）
- DeepSeek v4-flash 思考模式
- DeepSeek-chat legacy alias（过渡，即将弃用）
- OpenAI（gpt-4o-mini）
- Moonshot（kimi-k2）
- 本地 Ollama（qwen2.5:7b）
- Anthropic：**标注为本轮不支持**，链回到本 directive 说明

### 1.7-e — Smoke 验证 + closeout

5 min Crafter smoke（live mode + DeepSeek v4-flash 非思考）：

```bash
source .local-archive/llm.env
python -m runners.run_crafter \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --max-runtime-sec 300 \
  --heartbeat-interval 1.0 \
  --recovering-window 0.05 \
  --idle-sleep-sec 0.01 \
  --turn-guard-window 0.01 \
  --shallow-patrol-interval 0.5 \
  --deep-patrol-interval 2.0 \
  --full-report-interval 5.0 \
  --working-memory-backend llm_assisted \
  --working-memory-model-client-mode live \
  --working-memory-model-client-timeout-sec 15.0
```

验证：
- 100+ 次 LLM advisory 调用
- ~100% 成功率（对齐 Phase 1.6 的 158/158 baseline）
- 审计日志显示 `model="deepseek-v4-flash"`
- 无 `deepseek_response_empty_content` 错误
- 响应中无 `reasoning_content` 字段
- 绝大多数（理想是 100%）调用响应中无 `metadata.fallback_reason`

Closeout：
- `maintainer/development/round-1.7-progress.md` —— 新文件，记录切片工作 + smoke 结果 + LOC 净变化
- `maintainer/development/current-intake.md` —— closeout
- `docs/implementation-tracking.md` —— 替换 vendor 命名的行为通用 client 行
- `docs/implementation-tracking-zh.md` —— 镜像
- 更新 `.claude/plans/federated-snacking-engelbart.md` —— 标记 Phase 1.7 完成，指针前移到 Phase 2

---

## 6. 改动文件

### 主要
- `eva/l3_deliberation/memory/working_memory_model_client.py`
  - 删除 Anthropic + DeepSeek helper / 类 / 常量 / mode 字符串
  - 新增 `OpenAICompatibleWorkingMemoryModelClient` 类 + config dataclass
  - 新增 env loader + retry 包装
  - 更新 factory

### Re-exports / imports
- `eva/l3_deliberation/memory/__init__.py` —— 移除删除的符号，加入新符号
- `eva/l3_deliberation/__init__.py` —— 移除删除的符号，加入新符号
- `eva/kernel/main.py` —— 更新 CLI mode choices + help text

### Env / 配置文件
- 重命名 `.local-archive/anthropic.env` → `.local-archive/llm.env`

### 测试
- `tests/l3_deliberation/memory/test_working_memory_model_client.py` —— 删除 vendor 专用测试类
- `tests/l3_deliberation/memory/test_openai_compatible_client.py`（新）
- 任何引用旧 mode 名的 CLI / runner 测试需要更新

### 文档
- `docs/implementation-tracking.md` —— vendor 行替换为通用行
- `docs/implementation-tracking-zh.md` —— 镜像
- `docs/architecture-overview.md`（或 scenarios-SPEC）—— 新增 "LLM advisory configuration" 节及 env 套装
- `maintainer/development/round-1.7-progress.md` —— 新 closeout 文件
- `maintainer/development/current-intake.md` —— intake / closeout 条目

### 不改动
- Heuristic / Null client
- Working memory adapter
- Scenario 代码（任何 `scenarios/` 下的文件）
- `eva/l1_sensing/`、`eva/l2_drive/`、`eva/anchor/`、`eva/kernel/` 下任何内容（`main.py` 除外，需调 CLI flag）

---

## 7. 边界 / 不变量

- Linux 等价性：跨切片行为 bit-equivalent（Linux scenario 有独立的确定性路径；LLM advisory 默认不参与）
- Crafter 等价性：live-mode-DeepSeek-v4-flash 必须产出与 Phase 1.6 的 DeepSeek-chat 在 shape 上等价的 advisory（仅 thinking mode 字段为显式）
- 不引入任何第三方依赖。仅 stdlib `urllib.request` + `json` + `time`
- 不改 scenario 契约
- 所有现有测试通过（删除的 vendor 专用测试除外）
- 维持 403 / 404 baseline 测试数量（1 个 pre-existing 失败）
- Anchor / mediator / drive 层不动

---

## 8. 架构师 gate

- **G1**（实施前）：intake 写入 `current-intake.md`，架构师在 1.7-a 开始前确认 scope
- **G2**（1.7-c 后）：factory 仅含三个 mode；vendor 类已删除；除有意删除的测试外回归绿
- **G3**（1.7-e 后）：smoke 验证 live-mode-DeepSeek 产出与 Phase 1.6 相同的 advisory_attached 成功率；closeout 文档已写；主计划已更新

---

## 9. 工作量预估

- 新通用 client + config dataclass + env loader：约 80 LOC
- Retry + fallback 包装：约 40 LOC
- Anthropic + DeepSeek 删除：约 -250 LOC
- 测试：约 150 LOC（新增）− 约 100 LOC（删除 vendor 测试）
- Env 文件 + README：少量
- Progress / intake 文档：标准

净 LOC：**负值**（即使引入了 retry + fallback 纪律，仍然删多于加）。

挂钟时间：约 2-3 小时实施 + 约 30 分钟 smoke + closeout 文档。

---

## 10. 为什么现在做

- 锁定 v4-flash 显式 model 名 + thinking.disabled，避免 `deepseek-chat` alias 弃用后出问题（时间表未知但官方已宣布）
- 降低未来接入任何便宜 OpenAI-compatible provider（Moonshot / Qwen / OpenRouter / 本地 Ollama）的成本——变成"改 env，不改代码"
- 移除框架中唯一的协议专用分支（Anthropic），把 LLM integration 拉到最大架构纯净度，然后再让 Phase 3 长跑产出 durable 数据
- Phase 2 viewer 不依赖本轮 —— 但本轮结构简化幅度小到不值得推迟，且让 Phase 2 的 "LLM advisory log" 面板更简单（只需展示一个 vendor 概念）
- 如果将来 Anthropic 需要恢复，那是一次刻意的切片（Phase 1.8 或更晚）按其当时的依据做决定 —— 不是永久技术债

---

## 11. 推迟到未来的开放问题

如果未来某切片需要 Anthropic，候选方案（当前不决定）：
1. Anthropic 官方 OpenAI-compatible beta endpoint —— 当作普通 `EVA_LLM_*` 配置使用，无需框架改动。特性子集会缩减（无 prompt cache、无 tool use 细节等），对 advisory 用途完全够。
2. 第三方中转层（cccai.cfd、OpenRouter、Helicone、Portkey 等）暴露 OpenAI Chat Completions 接口对接 Claude 模型 —— 当作普通 `EVA_LLM_*` 配置使用，无需框架改动。
3. 恢复 Anthropic Messages API 原生协议 —— 需要重新引入 per-vendor 代码路径；仅在选项 1 和 2 都无法满足某个具体特性要求时才考虑。

默认：需要时选 1 或 2。除非出现具体阻塞需求，否则选项 3 明确不在考虑范围内。
