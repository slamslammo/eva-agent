# Stage G Side Observations

本文档记录 **Stage G** 执行过程中发现、但不属于当前 slice 直接范围的旁支观察。

使用规则：
- 只记录非 blocker 的后续清理项、命名不一致、可延后改进项
- 不在当前 slice 中顺手扩大 scope
- 若观察升级为真正 blocker，再转写到 `stage-g-blockers.md`

## 2026-05-11 — G-0 residual clearance

- `eva/l3_deliberation/peer_circuit/habit_track.py` 仍保留 `observe_first / stabilize_first / escalate_first` 的本地字符串常量。
- 当前它们是 reasoning-side bounded shaping vocabulary，而不是 import-time scenario export；因此不阻断 G-0 的两项 residual closeout。
- 但若后续要把 framework grep-clean 进一步从“no import-time scenario leakage”收紧到“no concrete scenario vocabulary literal in framework owners”，这一处需要在后续 slice 中再判断是否收束。
