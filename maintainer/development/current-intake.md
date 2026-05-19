# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Round 1.7 — LLM Client Generalization — COMPLETE

### Status
- **all sub-slices landed**: 1.7-a (additive) → 1.7-b (retry+fallback) → 1.7-c (delete vendor) → 1.7-d (env + docs) → 1.7-e (smoke + closeout)
- 414 / 415 tests pass (1 pre-existing l2_drive failure on `main`, unrelated)
- 27 new tests in `tests/l3_deliberation/memory/test_openai_compatible_client.py`
- 5min Crafter smoke (live mode + DeepSeek v4-flash + thinking.disabled): **211 calls / 100% success / 0 errors / 0 fallbacks**
- progress: `maintainer/development/round-1.7-progress.md`

### What's next
- Phase 2: `validation_viewer/` HTML viewer — design drafted in `maintainer/development/round-2-validation-viewer-design.md`; design discussion still pending before implementation
- Phase 3: 6h Crafter long-run (user-driven; infrastructure ready)
- D-6: post-run report after Phase 3 produces durable data
