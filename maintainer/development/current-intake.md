# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Round 1.B-4 — Signal Classification De-coupling — COMPLETE

### Status
- **implementation complete**
- 397 / 397 tests pass for this slice (1 pre-existing failure on `main` unrelated to 1.B-4)
- Crafter exploration drive verified working post-fix (smoke: max=1.0 mean=0.40 nonzero=55%)
- 6h long-run now meaningful (previously would have captured buggy framework behavior)
- progress: `maintainer/development/round-1b-4-progress.md`

### What's next
- Phase 2: HTML viewer (validation_viewer/) for monitoring 6h run
- Phase 3: actual 6h Crafter long-run (real LLM or local)
- D-6: post-run report + parameter tuning recommendations
