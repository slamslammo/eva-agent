# Round 1.7 — LLM Client 通用化 — 进展记录

**状态**：已完成（1.7-a 到 1.7-e 全部落地，已 batch commit）
**Directive**：`maintainer/development/round-1.7-llm-client-generalization-startup-instruction.md`
**Smoke 验证产物**：`validation-runs/phase1.7-live-smoke/`
**Commit**：`e8b916e`

---

## 摘要

Round 1.7 将 model-client 架构从两条并行的厂家专用实现（Anthropic + DeepSeek）收敛为**单一的 vendor-neutral OpenAI Chat Completions 客户端**，通过 `EVA_LLM_*` 环境变量配置。

**代码净变化**：负值（约 -150 LOC），即使新增了 retry + fallback 纪律也是净删除。

**功能层面**：框架不再存在任何 per-vendor 代码路径。任何能讲 OpenAI Chat Completions 的端点（DeepSeek / OpenAI / Moonshot / Qwen / Ollama / vLLM / OpenRouter / ...）都能通过环境变量配置，**零代码改动**。

---

## 子切片落地情况

### 1.7-a — 新增 `OpenAICompatibleWorkingMemoryModelClient` + env loader（纯增量）

- 新增 dataclass：`OpenAICompatibleWorkingMemoryModelClientConfig`
- 新增类：`OpenAICompatibleWorkingMemoryModelClient`
- 新增 helper：`_load_live_config_from_env`（fail-fast 校验 env），加上 5 个辅助函数（URL resolver / payload builder / response extractor / transport / HTTP error label）
- 新增 mode 常量：`MODEL_CLIENT_MODE_LIVE = "live"`
- 新增 4 个 env 常量：`EVA_LLM_API_BASE_URL` / `EVA_LLM_API_KEY` / `EVA_LLM_MODEL` / `EVA_LLM_EXTRA_PARAMS_JSON`
- 新增 factory `live` 分支 + CLI 增加 `live` 选项（旧 Anthropic / DeepSeek 在过渡期保留）
- 新增 15 个测试在 `tests/l3_deliberation/memory/test_openai_compatible_client.py`
- Sanity 验证：live mode + 真实 DeepSeek 调用返回合法 advisory

### 1.7-b — 增加 retry + fallback wrapper

- 修改 `OpenAICompatibleWorkingMemoryModelClient.build_working_memory_advisory`：在 5xx 和 `openai_compatible_transport_unavailable` 错误上指数退避重试（1s / 2s / 4s）
- 修改构造函数：未传 fallback 时自动构建 `HeuristicWorkingMemoryModelClient`，provider 标签为 `"openai-compatible-fallback"`，便于审计辨识
- 修改 `_load_live_config_from_env`：seed `max_retries=3`、`retry_backoff_base_sec=1.0`
- 新增 helper：`_is_retryable_openai_compatible_error`、`_attach_fallback_reason`
- 新增 12 个测试（retry classifier 4 个 + retry/fallback 端到端 8 个）
- Fallback 原因会追加到 `reasoning_trace`，让审计日志能区分"按设计走 heuristic"和"因 LLM 失败 fallback 到 heuristic"

### 1.7-c — 删除 vendor clients + 简化 CLI

**删除**：
- `AnthropicWorkingMemoryModelClient` 及其全部 helper（`_post_anthropic_messages`、`_anthropic_request_payload`、`_anthropic_text_response`、`_anthropic_http_error_label`、`_resolve_anthropic_messages_url`）
- `DeepSeekWorkingMemoryModelClient` 及其全部 helper
- 10 个 vendor 常量（`DEFAULT_ANTHROPIC_MODEL` / `ANTHROPIC_API_KEY_ENV` 等）
- 2 个 mode 字符串：`MODEL_CLIENT_MODE_ANTHROPIC` / `MODEL_CLIENT_MODE_DEEPSEEK`
- `AnthropicTransport` 类型别名

**简化**：
- CLI mode 选项收敛为 `inert | heuristic | live`（默认从 `anthropic` 改为 `inert`）
- `WorkingMemoryModelClientConfig` 默认值改为 `provider="heuristic"` / `model="bounded-local-placeholder"`
- `HeuristicWorkingMemoryModelClient` 不再需要"Anthropic 默认模型名 rebrand"的兼容逻辑
- `working_memory_adapter.py` 中 `client_mode` 默认值改为 `MODEL_CLIENT_MODE_LIVE`
- `_extract_advisory_payload` 错误标签 `"anthropic_response_not_json"` 改为 `"openai_compatible_response_not_json"`
- `_adapter_client_metadata` 同时识别 `request_timeout_sec` 与 `timeout_sec`；为 live client 合成 `provider="openai-compatible"` 标签
- `_provider_and_model_from_source`、`_default_advisory_source_for_adapter` 改用新的 `client_backed_live_openai_compatible` source 标签
- `eva/kernel/config.py` 中 `working_memory_model_client_mode` 默认值由 `"anthropic"` 改为 `"inert"`

**测试整理**：
- 删除 13 个 vendor 专用测试（`AnthropicWorkingMemoryModelClient` / `DeepSeekWorkingMemoryModelClient` / `*ApiBaseUrlResolutionTests`）
- 删除一个 legacy 集成测试 `test_runtime_defaults_to_anthropic_client_shell_and_falls_back_locally_when_unavailable`（已被 `test_openai_compatible_client.py` 的 unit 级 retry/fallback 覆盖取代）
- 更新 `test_runtime_config_carries_working_memory_backend` 的断言以匹配新默认值
- 更新 legacy 测试中对 `provider="anthropic"` 的断言为 `provider="openai-compatible"`

### 1.7-d — Env 文件重命名 + 文档

- 重命名：`.local-archive/anthropic.env` → `.local-archive/llm.env`
- 内容替换：以 DeepSeek v4-flash + `thinking.disabled` 作为激活配置，DeepSeek-chat（legacy）、thinking mode、OpenAI、Moonshot、本地 Ollama 作为注释备用配置
- 文件权限 `chmod 600` 保留
- 新增 `docs/architecture-overview.md` §9 "LLM advisory configuration"，含 env 变量表 + 参考配置 + 容错说明 + Anthropic-not-supported 说明
- 同步 `docs/architecture-overview-zh.md` §9（中文版）

### 1.7-e — Smoke 验证 + Closeout

Smoke 命令（产物在 `validation-runs/phase1.7-live-smoke/`）：

```bash
source .local-archive/llm.env
python -m runners.run_crafter \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --max-runtime-sec 300 \
  ... \
  --working-memory-backend llm_assisted \
  --working-memory-model-client-mode live \
  --working-memory-model-client-timeout-sec 15.0
```

Smoke 结果：

| 指标 | 数值 |
|---|---|
| 运行时长 | 300 秒（5 分钟，通过 max_runtime_sec 干净退出） |
| Ticks / Turns | 210 / 213 |
| LLM advisory 调用次数 | 211 |
| 成功（`advisory_attached`） | 211（100%） |
| 错误次数 | 0 |
| Fallback 到 heuristic 次数 | 0 |
| 审计中的模型名 | `deepseek-v4-flash` |
| `deepseek_response_empty_content` 错误 | 0 |
| Reasoning content 泄漏 | 无（干净 JSON） |
| 最终状态 | STABLE，instance_valid=True |
| `exit_reason` | `max_runtime_sec` |

**关于本次 smoke 中 provider 标签的说明**：审计中所有 211 条记录的 `provider="unknown"`。原因是 `working_memory.py` 中 `_adapter_client_metadata` 的修复是在 smoke 已启动**之后**才落地的。功能层面完全正确——smoke 验证了 live client 端到端 transport 正常、`thinking.disabled` 产出干净 JSON、heuristic fallback 在 211 次调用中从未被触发。修复后续运行中标签会显示为 `"openai-compatible"`。

---

## 改动文件清单

| 文件 | 改动 |
|---|---|
| `eva/l3_deliberation/memory/working_memory_model_client.py` | -250 LOC vendor 代码，+180 LOC live client + retry/fallback；净 -70 LOC |
| `eva/l3_deliberation/memory/__init__.py` | 清理 exports |
| `eva/l3_deliberation/__init__.py` | 清理 exports |
| `eva/l3_deliberation/memory/working_memory_adapter.py` | 默认 `client_mode` 改为 live |
| `eva/l3_deliberation/reasoning/working_memory.py` | 审计 metadata + advisory source 标签适配 live client |
| `eva/kernel/main.py` | CLI 简化；live mode 默认审计标签 |
| `eva/kernel/config.py` | 默认 `working_memory_model_client_mode = "inert"` |
| `tests/l3_deliberation/memory/test_openai_compatible_client.py` | **新增**，27 个测试 |
| `tests/l3_deliberation/memory/test_working_memory_model_client.py` | 收敛为 2 个存留测试（heuristic + factory） |
| `tests/l3_deliberation/reasoning/test_working_memory.py` | 一个测试更新为新标签 |
| `tests/integration/test_main_runtime.py` | 一个更新、一个删除 |
| `.local-archive/anthropic.env` | 重命名为 `llm.env`，内容替换 |
| `docs/architecture-overview.md` | +§9 LLM advisory configuration |
| `docs/architecture-overview-zh.md` | 中文镜像 |
| `docs/implementation-tracking.md` | 行更新 + 新增 follow-up 条目 |
| `docs/implementation-tracking-zh.md` | 中文镜像 |
| `maintainer/development/round-1.7-llm-client-generalization-startup-instruction.md` | Directive（gitignored，本地） |
| `maintainer/development/round-1.7-progress.md` | 本文件 |
| `maintainer/development/current-intake.md` | Closeout |

---

## 回归 baseline

| 阶段 | 测试总数 | 通过 | 失败 | 备注 |
|---|---|---|---|---|
| 1.7-a 之前 | 403 | 402 | 1（pre-existing） | baseline |
| 1.7-a | 418 | 417 | 1（pre-existing） | +15 个 live-client 测试 |
| 1.7-b | 430 | 429 | 1（pre-existing） | +12 个 retry/fallback 测试 |
| 1.7-c | 415 | 414 | 1（pre-existing） | -15 个 vendor 专用测试（Anthropic + DeepSeek + URL resolvers + 1 集成测试） |
| 1.7-d | 415 | 414 | 1（pre-existing） | 仅文档 |
| 1.7-e | 415 | 414 | 1（pre-existing） | 测试更新 + 审计修复 |

唯一的失败是 `tests.l2_drive.test_drive.test_update_drive_state_accumulates_over_multiple_patrols` — 在 `main` 上也存在，与 Round 1.7 无关。

---

## 接下来

- **Phase 2** — `validation_viewer/` HTML viewer（design 草稿在 `maintainer/development/round-2-validation-viewer-design.md`；启动前需要讨论 7 个开放设计问题 Q1-Q7）
- **Phase 3** — 6h Crafter 长跑（用户驱动；基础设施已齐备）
- **D-6** — Phase 3 数据产出后的 post-run report

---

## Anthropic 恢复推迟到未来

如果将来某个切片需要 Anthropic 模型，候选方案（当前不决定）：

1. **Anthropic 官方 OpenAI-compatible beta endpoint** — 当作普通 `EVA_LLM_*` 配置使用，无需框架改动（特性子集会缩减，但对 advisory 用途完全够）
2. **第三方中转层**（OpenRouter / Helicone / Portkey）暴露 OpenAI Chat Completions 接口对接 Claude 模型 — 同样无需框架改动
3. **恢复 Anthropic Messages API 原生协议** — 需要重新引入 per-vendor 代码路径；仅在选项 1 和 2 都无法满足某个具体阻塞需求时才考虑

未来需要时的默认选择：选项 1 或 2。
