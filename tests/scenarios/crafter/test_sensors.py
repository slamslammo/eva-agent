from __future__ import annotations

import tempfile
import unittest

from eva.kernel import ActivePressureTable, ExternalLifeConfig, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l1_sensing import build_external_life_snapshot, collect_external_life_inputs, default_sensor_registry, get_default_dimension_specs
from eva.l2_drive.pressure_to_drive import build_active_pressure_table
from scenarios.crafter import activate_crafter_scenario
from runners.run_crafter import CrafterRuntimeSession


class CrafterSensorTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def _runtime_state(self) -> RuntimeState:
        return RuntimeState(instance_valid=True, heartbeat_ok=True, tick_ok=True, updated_at=utc_now())

    def _agent_observation(self) -> dict[str, object]:
        return {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "episode-1",
            "step": 3,
            "visible": {
                "local_view": {
                    "format": "semantic_grid",
                    "source": "semantic_local_crop",
                    "width": 9,
                    "height": 7,
                    "center": {"col": 4, "row": 3},
                    "cells": [["grass"] * 9 for _ in range(7)],
                    "nearby_objects": {"zombie": 1},
                    "nearby_materials": {"tree": 2, "water": 1, "table": 1},
                    "notes": [],
                },
                "life_panel": {
                    "available": True,
                    "values": {"health": 2, "food": 9, "water": 1, "energy": 4},
                },
                "inventory_panel": {
                    "available": True,
                    "items": {"wood": 1, "stone": 0, "wood_pickaxe": 1},
                },
                "facing": "left",
                "nearby_objects": ["zombie"],
            },
            "task_context": {"objective": "survive and unlock achievements"},
            "available_actions": ["noop"],
            "notes": [],
        }

    def test_default_sensor_registry_collects_crafter_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.ensure_runtime_dir()
            runtime_state = self._runtime_state()
            store.write_runtime_state(runtime_state)
            inputs = collect_external_life_inputs(
                store,
                runtime_state,
                ExternalLifeConfig(recent_event_window_sec=60.0),
                utc_now(),
                sensor_registry=default_sensor_registry(),
            )
            self.assertEqual(
                set(inputs.keys()),
                {
                    "avatar_metabolic",
                    "avatar_safety",
                    "avatar_recovery",
                    "inventory_acquisition",
                    "inventory_capability",
                    "local_view_state",
                },
            )

    def test_crafter_sensors_translate_agent_observation_from_shared_facts(self) -> None:
        registry = default_sensor_registry()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.ensure_runtime_dir()
            runtime_state = self._runtime_state()
            store.write_runtime_state(runtime_state)
            context_inputs = collect_external_life_inputs(
                store,
                runtime_state,
                ExternalLifeConfig(recent_event_window_sec=60.0),
                utc_now(),
                sensor_registry=registry,
            )
            self.assertEqual(context_inputs["avatar_safety"]["status"], "healthy")

            from eva.l1_sensing.sensor_registry import SensingContext

            context = SensingContext(
                store=store,
                runtime_state=runtime_state,
                config=ExternalLifeConfig(recent_event_window_sec=60.0),
                now=utc_now(),
                shared_facts={"agent_observation": self._agent_observation()},
            )
            outputs = registry.collect_all(context)
            by_dimension = {output.dimension: output.payload for output in outputs}
            self.assertEqual(by_dimension["avatar_safety"]["status"], "critical")
            self.assertEqual(by_dimension["avatar_safety"]["reason"], "health_critical")
            self.assertEqual(by_dimension["avatar_metabolic"]["status"], "critical")
            self.assertEqual(by_dimension["avatar_recovery"]["status"], "degraded")
            self.assertEqual(by_dimension["inventory_capability"]["available_tools"], ["wood_pickaxe"])
            self.assertIn("stone", by_dimension["inventory_acquisition"]["scarce_resources"])
            self.assertEqual(by_dimension["local_view_state"]["threat_counts"], {"zombie": 1})
            self.assertEqual(by_dimension["local_view_state"]["utility_counts"], {"table": 1})
    def test_crafter_dimension_specs_drive_judgment_and_pressure_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.ensure_runtime_dir()
            runtime_state = self._runtime_state()
            store.write_runtime_state(runtime_state)
            now = utc_now()
            registry = default_sensor_registry()
            from eva.l1_sensing.sensor_registry import SensingContext

            context = SensingContext(
                store=store,
                runtime_state=runtime_state,
                config=ExternalLifeConfig(recent_event_window_sec=60.0),
                now=now,
                shared_facts={"agent_observation": self._agent_observation()},
            )
            inputs = {output.dimension: output.payload for output in registry.collect_all(context)}
            self.assertEqual(
                [spec.name for spec in get_default_dimension_specs()],
                [
                    "avatar_safety",
                    "avatar_metabolic",
                    "avatar_recovery",
                    "inventory_capability",
                    "inventory_acquisition",
                    "local_view_state",
                ],
            )
            snapshot = build_external_life_snapshot(
                "deep",
                inputs,
                ExternalLifeConfig(recent_event_window_sec=60.0),
                now,
            )
            self.assertEqual(snapshot.primary_gap, {"type": "avatar_safety", "reason": "health_critical"})
            table, opened, resolved = build_active_pressure_table(snapshot, ActivePressureTable(captured_at=now))
            self.assertEqual(len(table.pressures), 5)
            self.assertTrue(all(pressure.type == "integrity" for pressure in table.pressures))
            self.assertEqual(len(opened), 5)
            self.assertEqual(resolved, [])
    def test_runtime_session_exposes_latest_agent_observation_as_shared_fact(self) -> None:
        class StubWrapper:
            def __init__(self) -> None:
                self.closed = False
                self.last_reset = {
                    "schema_version": "symbolic_observation_v0",
                    "visible": {
                        "life_panel": {"values": {"health": 4, "food": 8, "water": 8, "energy": 8}},
                        "inventory_panel": {"items": {}},
                        "nearby_objects": [],
                        "local_view": {"nearby_objects": {}},
                    },
                    "task_context": {"unlocked_achievements_visible": []},
                }

            def reset(self, *, seed=None):
                del seed
                return dict(self.last_reset)

            def step(self, action_name: str):
                del action_name
                raise AssertionError("step should not be called")

            def close(self) -> None:
                self.closed = True

        session = CrafterRuntimeSession(wrapper=StubWrapper(), latest_agent_observation={"visible": {"life_panel": {"values": {"health": 4, "food": 8, "water": 8, "energy": 8}}, "inventory_panel": {"items": {}}, "nearby_objects": [], "local_view": {"nearby_objects": {}}}, "task_context": {"unlocked_achievements_visible": []}})
        self.assertIn("agent_observation", session.build_shared_facts())
        self.assertEqual(session.build_shared_facts()["agent_observation"]["visible"]["life_panel"]["values"]["health"], 4)


if __name__ == "__main__":
    unittest.main()
