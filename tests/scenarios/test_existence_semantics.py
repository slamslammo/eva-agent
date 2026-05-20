"""v0.6 rev2 — 存在语义声明契约测试（修复 B）。

验证：每个场景都声明了 ExistenceSemantics；框架 reader 返回当前激活场景的声明；
RuntimeScenarioBundle 把 existence_semantics 作为必填字段（强制场景声明生死规则）。
"""

from __future__ import annotations

import unittest

from eva.scenario_bundle import (
    ExistenceSemantics,
    RuntimeScenarioBundle,
    get_active_existence_semantics,
)
from scenarios.crafter import CRAFTER_SCENARIO_BUNDLE, activate_crafter_scenario
from scenarios.linux_runtime import (
    LINUX_RUNTIME_SCENARIO_BUNDLE,
    activate_linux_runtime_scenario,
)


class ExistenceSemanticsDeclarationTests(unittest.TestCase):
    def test_crafter_declares_single_episode_terminal_death(self) -> None:
        es = CRAFTER_SCENARIO_BUNDLE.existence_semantics
        self.assertIsInstance(es, ExistenceSemantics)
        # Crafter 单局世界：HP=0 真死、无 in-life 可恢复中断、reset=新个体、step 时钟
        self.assertEqual(es.recoverable_interruption, ())
        self.assertEqual(es.reset_semantics, "new_individual")
        self.assertEqual(es.clock_source, "step")
        self.assertIn("HP=0", es.terminal_failure)

    def test_linux_declares_recoverable_restart_same_individual(self) -> None:
        es = LINUX_RUNTIME_SCENARIO_BUNDLE.existence_semantics
        self.assertIsInstance(es, ExistenceSemantics)
        # Linux 重进程连续性：重启可恢复、同一个体恢复、挂钟时钟
        self.assertIn("process restart", es.recoverable_interruption)
        self.assertEqual(es.reset_semantics, "same_individual_recovery")
        self.assertEqual(es.clock_source, "wall_clock")

    def test_reader_returns_active_scenario_declaration(self) -> None:
        activate_crafter_scenario()
        self.assertEqual(get_active_existence_semantics().clock_source, "step")
        activate_linux_runtime_scenario()
        self.assertEqual(get_active_existence_semantics().clock_source, "wall_clock")

    def test_existence_semantics_is_required_field(self) -> None:
        # RuntimeScenarioBundle 必须带 existence_semantics —— 缺失即构造失败，
        # 强制每个场景声明生死规则（rev2）。
        with self.assertRaises(TypeError):
            RuntimeScenarioBundle(  # type: ignore[call-arg]
                name="incomplete",
                drive_preset=None,
                sensors=None,
                actions=None,
                anchors=None,
                outcome_observers=None,
                prior_skills=None,
            )


if __name__ == "__main__":
    unittest.main()
