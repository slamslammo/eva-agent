"""framework-scenario-timing slice 1 — ``RuntimeScenarioBundle.suggested_timing``.

场景可声明建议的外部生命节律（external-life timing）。框架在 CLI 未显式指定时回退
到这个声明（回退接线在 slice 2）。slice 1 只固定 ``RuntimeScenarioBundle`` 上的字段契约：

- 新增 ``suggested_timing`` 字段，类型 ``ExternalLifeConfig | None``，默认 ``None``（向后兼容）；
- 不影响既有必填字段（``existence_semantics`` 仍必填，缺失即构造失败）。

复用 ``eva.kernel.config.ExternalLifeConfig`` 作为 timing 数据结构，不新建类型。
"""

from __future__ import annotations

import dataclasses
import unittest

from eva.kernel.config import ExternalLifeConfig
from eva.scenario_bundle import RuntimeScenarioBundle


def _make_bundle(**overrides: object) -> RuntimeScenarioBundle:
    """Construct a bundle with placeholder required fields.

    ``RuntimeScenarioBundle`` 是 frozen dataclass，运行时不对字段做类型校验（仅存储），
    所以这里用 ``None`` 占位全部必填字段，专注验证 ``suggested_timing`` 字段契约。
    """

    base: dict[str, object] = dict(
        name="timing-probe",
        drive_preset=None,
        sensors=None,
        actions=None,
        anchors=None,
        outcome_observers=None,
        prior_skills=None,
        existence_semantics=None,
    )
    base.update(overrides)
    return RuntimeScenarioBundle(**base)  # type: ignore[arg-type]


class SuggestedTimingFieldTests(unittest.TestCase):
    def test_defaults_to_none_when_omitted(self) -> None:
        # 向后兼容：现有所有 bundle 构造点都不传 suggested_timing，必须默认 None。
        bundle = _make_bundle()
        self.assertIsNone(bundle.suggested_timing)

    def test_stores_explicit_external_life_config(self) -> None:
        timing = ExternalLifeConfig(
            shallow_patrol_interval_sec=2.0,
            deep_patrol_interval_sec=4.0,
            full_report_interval_sec=8.0,
            recent_event_window_sec=4.0,
        )
        bundle = _make_bundle(suggested_timing=timing)
        self.assertIs(bundle.suggested_timing, timing)
        self.assertEqual(bundle.suggested_timing.shallow_patrol_interval_sec, 2.0)

    def test_field_is_part_of_dataclass_with_none_default(self) -> None:
        fields = {f.name: f for f in dataclasses.fields(RuntimeScenarioBundle)}
        self.assertIn("suggested_timing", fields)
        self.assertIsNone(fields["suggested_timing"].default)

    def test_suggested_timing_is_declared_after_required_fields(self) -> None:
        # 红线：带默认的新字段必须排在必填字段之后，否则破坏
        # test_existence_semantics 的"缺字段即 TypeError"契约。
        names = [f.name for f in dataclasses.fields(RuntimeScenarioBundle)]
        self.assertGreater(
            names.index("suggested_timing"),
            names.index("existence_semantics"),
        )

    def test_bundle_remains_frozen(self) -> None:
        bundle = _make_bundle()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            bundle.suggested_timing = ExternalLifeConfig()  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
