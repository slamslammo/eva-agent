"""v0.6 rev2 — individual 身份层（收敛点②）契约测试。

验证框架的 substrate ↔ individual 分层：
- instance_id / generation = substrate（承载一条生命的进程/"躯壳"）
- individual_id = 被承载的"自我"，其延续规则由场景
  ``existence_semantics.reset_semantics`` 决定：
  - ``same_individual_recovery``（Linux）：同 runtime_dir 重启 → 复用同一
    individual_id，substrate provenance 链增长（"换躯壳、灵魂延续"）。
  - ``new_individual``（Crafter）：每次都是新个体 → 每次 mint 新 individual_id。
- 无场景激活（裸 kernel）：generic 个体，绝不复用未声明恢复规则的 id。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import LifecycleConfig, LoopControl, StateStore, build_runtime_config
from eva.kernel.main import _resolve_individual_id, run_runtime
from eva.kernel.state import utc_now
from scenarios.crafter import activate_crafter_scenario
from scenarios.linux_runtime import activate_linux_runtime_scenario


class IndividualIdentityResolutionTests(unittest.TestCase):
    def test_crafter_new_individual_mints_fresh_id_each_run(self) -> None:
        activate_crafter_scenario()
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir)
            config.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
            first_id, first_born = _resolve_individual_id(
                config, instance_id="eva-A", generation=1, now=utc_now()
            )
            second_id, second_born = _resolve_individual_id(
                config, instance_id="eva-B", generation=2, now=utc_now()
            )
            self.assertTrue(first_id.startswith("individual-crafter-"))
            self.assertTrue(first_born)
            self.assertTrue(second_born)
            # 单局世界：每次 run 都是新个体，绝不复用上一个体的 id。
            self.assertNotEqual(first_id, second_id)
            record = json.loads((config.paths.runtime_dir / "individual.json").read_text(encoding="utf-8"))
            self.assertEqual(record["reset_semantics"], "new_individual")
            self.assertEqual(record["individual_id"], second_id)
            self.assertEqual(len(record["substrate_instances"]), 1)

    def test_linux_same_individual_recovery_reuses_id_and_grows_provenance(self) -> None:
        activate_linux_runtime_scenario()
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir)
            config.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
            first_id, first_born = _resolve_individual_id(
                config, instance_id="eva-A", generation=1, now=utc_now()
            )
            second_id, second_born = _resolve_individual_id(
                config, instance_id="eva-B", generation=2, now=utc_now()
            )
            self.assertTrue(first_id.startswith("individual-linux_runtime-"))
            self.assertTrue(first_born)
            # 同一个体在新 substrate 上恢复："灵魂延续、躯壳更换"。
            self.assertFalse(second_born)
            self.assertEqual(first_id, second_id)
            record = json.loads((config.paths.runtime_dir / "individual.json").read_text(encoding="utf-8"))
            self.assertEqual(record["reset_semantics"], "same_individual_recovery")
            self.assertEqual(record["individual_id"], first_id)
            chain = record["substrate_instances"]
            self.assertEqual([s["instance_id"] for s in chain], ["eva-A", "eva-B"])
            self.assertEqual([s["generation"] for s in chain], [1, 2])

    def test_no_scenario_falls_back_to_generic_fresh_individual(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir)
            config.paths.runtime_dir.mkdir(parents=True, exist_ok=True)
            with patch(
                "eva.kernel.main.get_active_runtime_scenario",
                side_effect=RuntimeError("no scenario activated"),
            ):
                first_id, _ = _resolve_individual_id(
                    config, instance_id="eva-A", generation=1, now=utc_now()
                )
                second_id, _ = _resolve_individual_id(
                    config, instance_id="eva-B", generation=2, now=utc_now()
                )
            self.assertTrue(first_id.startswith("individual-generic-"))
            # 未声明恢复规则的裸 kernel：每次都是新个体，绝不静默复用。
            self.assertNotEqual(first_id, second_id)


class IndividualIdentityRuntimeWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def _bounded_config(self, temp_dir: str):
        return build_runtime_config(
            temp_dir,
            lifecycle=LifecycleConfig(
                heartbeat_interval_sec=0.05, lease_duration_sec=0.2, recovering_window_sec=0.05
            ),
            control=LoopControl(max_ticks=2, max_runtime_sec=1.0, idle_sleep_sec=0.01),
        )

    def test_run_summary_carries_individual_id_distinct_from_substrate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._bounded_config(temp_dir)
            summary = run_runtime(config)
            self.assertTrue(summary.individual_id.startswith("individual-linux_runtime-"))
            store = StateStore(config.paths)
            active = store.read_active_instance()
            self.assertIsNotNone(active)
            assert active is not None
            # individual（自我）不是 substrate（躯壳）。
            self.assertNotEqual(summary.individual_id, active.instance_id)
            startup = [e for e in store.read_events() if e["event_type"] == "startup"][0]
            self.assertEqual(startup["details"]["individual_id"], summary.individual_id)
            self.assertTrue(startup["details"]["individual_newly_born"])
            self.assertTrue((config.paths.runtime_dir / "individual.json").exists())

    def test_sequential_runs_resume_same_individual_on_new_substrate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = run_runtime(self._bounded_config(temp_dir))
            second = run_runtime(self._bounded_config(temp_dir))
            # 同 runtime_dir 重启：灵魂延续（individual_id 不变）。
            self.assertEqual(first.individual_id, second.individual_id)
            paths = build_runtime_config(temp_dir).paths
            record = json.loads((paths.runtime_dir / "individual.json").read_text(encoding="utf-8"))
            # 躯壳更换：substrate provenance 链增长。
            self.assertGreaterEqual(len(record["substrate_instances"]), 2)
            startups = [e for e in StateStore(paths).read_events() if e["event_type"] == "startup"]
            self.assertFalse(startups[-1]["details"]["individual_newly_born"])


if __name__ == "__main__":
    unittest.main()
