"""Crafter plugin extractor 单元测试。"""

from __future__ import annotations

import unittest

from observation_tools.plugins.crafter.extractor import extract_crafter_view


def _make_deliberation_with_dims(dims_evidence: dict) -> dict:
    """构造一个含 status signal 的 deliberation_audit 条目。

    ``dims_evidence`` 形如::
        {"avatar_safety": {"status": "healthy", "evidence": {"health": 9, ...}}, ...}
    """

    dimensions = {
        name: {
            "status": data.get("status"),
            "evidence": data.get("evidence") or {},
        }
        for name, data in dims_evidence.items()
    }
    return {
        "recorded_at": "2026-05-19T17:47:30Z",
        "deliberation_input": {
            "signal_batch": {
                "signals": [
                    {
                        "source": "shallow",
                        "class": "status",
                        "payload": {"dimensions": dimensions},
                    }
                ]
            }
        },
    }


class ExtractCrafterViewTests(unittest.TestCase):
    def test_returns_none_when_both_inputs_missing(self) -> None:
        self.assertIsNone(extract_crafter_view(None, None))

    def test_returns_none_when_inputs_present_but_no_signals(self) -> None:
        empty_deliberation = {"deliberation_input": {"signal_batch": {"signals": []}}}
        # 没有 dims 且 response 是 None —— 应返回 None
        self.assertIsNone(extract_crafter_view(empty_deliberation, None))

    def test_extracts_vitals_from_avatar_safety(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "avatar_safety": {
                "status": "healthy",
                "evidence": {
                    "health": 9.0,
                    "food": 6.0,
                    "water": 5.0,
                    "energy": 9.0,
                    "threat_count": 0,
                    "episode_id": "ep-123",
                },
            },
        })
        view = extract_crafter_view(deliberation, None)
        self.assertIsNotNone(view)
        vitals = view["vitals"]
        self.assertEqual(vitals["health"], 9.0)
        self.assertEqual(vitals["food"], 6.0)
        self.assertEqual(vitals["water"], 5.0)
        self.assertEqual(vitals["energy"], 9.0)
        self.assertEqual(vitals["threat_count"], 0)
        self.assertEqual(vitals["status_safety"], "healthy")
        self.assertEqual(vitals["episode_id"], "ep-123")

    def test_extracts_inventory_with_items_and_tools(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "inventory_capability": {
                "status": "degraded",
                "evidence": {
                    "items": {"wood": 2, "stone": 1, "wood_pickaxe": 1},
                    "tools": {"wood_pickaxe": 1, "stone_pickaxe": 0},
                    "available_tools": ["wood_pickaxe"],
                },
            },
            "inventory_acquisition": {
                "status": "critical",
                "evidence": {
                    "key_resources": ["wood", "stone"],
                    "scarce_resources": ["coal", "iron"],
                },
            },
        })
        view = extract_crafter_view(deliberation, None)
        inv = view["inventory"]
        self.assertEqual(inv["items"]["wood"], 2)
        self.assertEqual(inv["tools"]["wood_pickaxe"], 1)
        self.assertEqual(inv["available_tools"], ["wood_pickaxe"])
        self.assertEqual(inv["scarce_resources"], ["coal", "iron"])
        self.assertEqual(inv["status_capability"], "degraded")
        self.assertEqual(inv["status_acquisition"], "critical")

    def test_extracts_local_view(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "local_view_threat": {
                "status": "healthy",
                "evidence": {"threat_total": 0},
            },
            "local_view_resource": {
                "status": "healthy",
                "evidence": {
                    "resource_total": 5,
                    "scarce_resources": ["coal"],
                },
            },
            "local_view_utility": {
                "status": "degraded",
                "evidence": {
                    "utility_total": 1,
                    "available_tools": ["table"],
                    "capability_gap": ["wood_pickaxe"],
                },
            },
        })
        view = extract_crafter_view(deliberation, None)
        lv = view["local_view"]
        self.assertEqual(lv["threat_total"], 0)
        self.assertEqual(lv["resource_total"], 5)
        self.assertEqual(lv["utility_total"], 1)
        self.assertEqual(lv["available_tools"], ["table"])
        self.assertEqual(lv["capability_gap"], ["wood_pickaxe"])

    def test_extracts_rate_context(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "avatar_safety": {
                "status": "healthy",
                "evidence": {
                    "health": 9.0,
                    "rate_context": {
                        "available": True,
                        "elapsed_sec": 1.3,
                        "health_direction": "decreasing",
                        "health_change_per_sec": -0.5,
                        "threat_count_direction": "stable",
                        "direction": "decreasing",
                        "magnitude": 0.3,
                        "acceleration": "stable",
                    },
                },
            },
        })
        view = extract_crafter_view(deliberation, None)
        rc = view["rate_context"]
        self.assertTrue(rc["available"])
        self.assertAlmostEqual(rc["elapsed_sec"], 1.3)
        self.assertEqual(rc["health_direction"], "decreasing")

    def test_extracts_deltas_from_response(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "avatar_safety": {"status": "healthy", "evidence": {"health": 9.0}},
        })
        response = {
            "achievement_delta": 1.0,
            "life_delta": {"health": -0.5, "food": 0.0},
            "inventory_delta": {"wood": 1},
            "visible_threat_count": 0,
        }
        view = extract_crafter_view(deliberation, response)
        d = view["deltas"]
        self.assertEqual(d["achievement_delta"], 1.0)
        self.assertEqual(d["life_delta"], {"health": -0.5, "food": 0.0})
        self.assertEqual(d["inventory_delta"], {"wood": 1})
        self.assertEqual(d["visible_threat_count"], 0)

    def test_status_summary_lists_all_dimensions(self) -> None:
        deliberation = _make_deliberation_with_dims({
            "avatar_safety": {"status": "healthy", "evidence": {"health": 9.0}},
            "inventory_capability": {"status": "degraded", "evidence": {}},
            "local_view_threat": {"status": "critical", "evidence": {}},
        })
        view = extract_crafter_view(deliberation, None)
        statuses = view["statuses"]
        self.assertEqual(statuses["avatar_safety"], "healthy")
        self.assertEqual(statuses["inventory_capability"], "degraded")
        self.assertEqual(statuses["local_view_threat"], "critical")

    def test_only_response_without_deliberation_still_works(self) -> None:
        view = extract_crafter_view(
            None,
            {"achievement_delta": 1.0, "life_delta": {"health": 1.0}, "inventory_delta": {}, "visible_threat_count": 0},
        )
        self.assertIsNotNone(view)
        self.assertEqual(view["deltas"]["achievement_delta"], 1.0)
        # 没有 deliberation 时不应有 vitals / inventory / local_view
        self.assertNotIn("vitals", view)
        self.assertNotIn("inventory", view)
        self.assertNotIn("local_view", view)

    def test_ignores_non_status_signals(self) -> None:
        # 只有 pressure / threat 类 signal —— extractor 不应误取 evidence
        deliberation = {
            "deliberation_input": {
                "signal_batch": {
                    "signals": [
                        {
                            "source": "shallow",
                            "class": "pressure",
                            "payload": {
                                "dimensions": {
                                    "avatar_safety": {
                                        "status": "healthy",
                                        "evidence": {"health": 9.0},
                                    }
                                }
                            },
                        }
                    ]
                }
            }
        }
        view = extract_crafter_view(deliberation, None)
        # 没有 status signal -> 没有 vitals -> 返回 None
        self.assertIsNone(view)


class PluginHookIntegrationTests(unittest.TestCase):
    """验证 ChainView.to_dict() 经过 plugin 注入后含 crafter 字段。"""

    def test_chain_view_to_dict_injects_crafter_field(self) -> None:
        from observation_tools.core.chain_builder import ChainView

        deliberation = _make_deliberation_with_dims({
            "avatar_safety": {"status": "healthy", "evidence": {"health": 9.0}},
        })
        chain = ChainView(
            turn_idx=0,
            recorded_at="2026-05-19T17:00:00Z",
            deliberation=deliberation,
            response={"selected_action": "move_left", "life_state": "STABLE"},
        )
        data = chain.to_dict()
        self.assertIn("crafter", data)
        self.assertEqual(data["crafter"]["vitals"]["health"], 9.0)

    def test_chain_view_to_dict_omits_crafter_when_no_dims(self) -> None:
        from observation_tools.core.chain_builder import ChainView

        # 既没有 deliberation 也没有 response 的有效场景数据
        chain = ChainView(turn_idx=0, recorded_at="2026-05-19T17:00:00Z")
        data = chain.to_dict()
        self.assertNotIn("crafter", data)


if __name__ == "__main__":
    unittest.main()
