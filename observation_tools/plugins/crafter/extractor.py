"""从 EVA Crafter 运行时 trace 提取场景特定数据。

源字段（与 ``scenarios/crafter`` 的 ``SensorPolicyBundle`` 输出对齐）：

- ``deliberation.deliberation_input.signal_batch.signals[i].payload.dimensions``：
    - ``avatar_safety.evidence.{health, food, water, energy, threat_count}``
    - ``avatar_metabolic.evidence``
    - ``avatar_recovery.evidence``
    - ``inventory_capability.evidence.{items, tools, available_tools}``
    - ``inventory_acquisition.evidence.{key_resources, scarce_resources}``
    - ``local_view_threat.evidence.threat_total``
    - ``local_view_resource.evidence.{resource_total, scarce_resources}``
    - ``local_view_utility.evidence.{utility_total, available_tools, capability_gap}``

- ``response.{life_delta, inventory_delta, achievement_delta, visible_threat_count}``

容错策略：任一来源缺失就降级为 None / 空 dict；不抛错，让前端按字段降级显示。
"""

from __future__ import annotations

from typing import Any


def extract_crafter_view(
    deliberation: dict[str, Any] | None,
    response: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """从单 turn 的链路数据提取 Crafter view dict。

    返回结构（每个子 dict 都是 Optional，由前端按字段降级）::

        {
          "vitals":      {"health":9,"food":6,"water":5,"energy":9,
                          "threat_count":0,"status":"healthy"},
          "inventory":   {"items":{wood:0,stone:0,...},
                          "tools":{wood_pickaxe:0,...},
                          "available_tools":[]},
          "local_view":  {"threat_total":0,"resource_total":5,
                          "scarce_resources":[...],"utility_total":0,
                          "available_tools":[],"capability_gap":...},
          "deltas":      {"achievement_delta":0.0,"life_delta":{...},
                          "inventory_delta":{...},"visible_threat_count":0},
          "rate_context":{"health_direction":"stable",
                          "threat_count_direction":"stable",...},
        }

    如果 deliberation 和 response 都缺，返回 None（前端不渲染本 section）。
    """

    if not deliberation and not response:
        return None

    view: dict[str, Any] = {}

    dims = _extract_dimensions(deliberation)
    if dims:
        view["vitals"] = _build_vitals(dims)
        view["inventory"] = _build_inventory(dims)
        view["local_view"] = _build_local_view(dims)
        view["rate_context"] = _build_rate_context(dims)
        view["statuses"] = _build_status_summary(dims)

    if response:
        view["deltas"] = {
            "achievement_delta": response.get("achievement_delta"),
            "life_delta": response.get("life_delta"),
            "inventory_delta": response.get("inventory_delta"),
            "visible_threat_count": response.get("visible_threat_count"),
        }

    return view or None


# --------------------------------------------------------------------------
# 内部
# --------------------------------------------------------------------------


def _extract_dimensions(deliberation: dict[str, Any] | None) -> dict[str, dict]:
    """从 signal_batch 中合并所有 status 类 signal 的 dimensions 字段。

    Crafter 的 sensor 把多个维度（avatar_safety / inventory_capability /
    local_view_* 等）放在同一个 status signal 的 payload.dimensions 里。
    取所有 status signal 的 dimensions 合并（后出现的覆盖先出现的）。
    """

    if not deliberation:
        return {}
    signal_batch = (deliberation.get("deliberation_input") or {}).get("signal_batch") or {}
    signals = signal_batch.get("signals") or []
    merged: dict[str, dict] = {}
    for sig in signals:
        if (sig.get("class") or "") != "status":
            continue
        dims = (sig.get("payload") or {}).get("dimensions") or {}
        for dim_name, dim_data in dims.items():
            evidence = (dim_data or {}).get("evidence") or {}
            merged[dim_name] = {
                "status": (dim_data or {}).get("status"),
                "evidence": evidence,
            }
    return merged


def _build_vitals(dims: dict[str, dict]) -> dict[str, Any]:
    """从 avatar_safety + avatar_metabolic + avatar_recovery 合并生命体征。"""

    safety = (dims.get("avatar_safety") or {}).get("evidence") or {}
    return {
        "health": safety.get("health"),
        "food": safety.get("food"),
        "water": safety.get("water"),
        "energy": safety.get("energy"),
        "threat_count": safety.get("threat_count"),
        "episode_id": safety.get("episode_id"),
        "status_safety": (dims.get("avatar_safety") or {}).get("status"),
        "status_metabolic": (dims.get("avatar_metabolic") or {}).get("status"),
        "status_recovery": (dims.get("avatar_recovery") or {}).get("status"),
    }


def _build_inventory(dims: dict[str, dict]) -> dict[str, Any]:
    cap = (dims.get("inventory_capability") or {}).get("evidence") or {}
    acq = (dims.get("inventory_acquisition") or {}).get("evidence") or {}
    items = cap.get("items") or {}
    # tools 是 items 的子集，但单独维护方便前端区分显示
    tools = cap.get("tools") or {}
    return {
        "items": items,
        "tools": tools,
        "available_tools": cap.get("available_tools") or [],
        "key_resources": acq.get("key_resources") or [],
        "scarce_resources": acq.get("scarce_resources") or [],
        "status_capability": (dims.get("inventory_capability") or {}).get("status"),
        "status_acquisition": (dims.get("inventory_acquisition") or {}).get("status"),
    }


def _build_local_view(dims: dict[str, dict]) -> dict[str, Any]:
    threat = (dims.get("local_view_threat") or {}).get("evidence") or {}
    resource = (dims.get("local_view_resource") or {}).get("evidence") or {}
    utility = (dims.get("local_view_utility") or {}).get("evidence") or {}
    return {
        "threat_total": threat.get("threat_total"),
        "threat_status": (dims.get("local_view_threat") or {}).get("status"),
        "resource_total": resource.get("resource_total"),
        "scarce_resources": resource.get("scarce_resources") or [],
        "resource_status": (dims.get("local_view_resource") or {}).get("status"),
        "utility_total": utility.get("utility_total"),
        "available_tools": utility.get("available_tools") or [],
        "capability_gap": utility.get("capability_gap"),
        "utility_status": (dims.get("local_view_utility") or {}).get("status"),
    }


def _build_rate_context(dims: dict[str, dict]) -> dict[str, Any]:
    """从 avatar_safety.evidence.rate_context 提取关键变化率信号。"""

    safety = (dims.get("avatar_safety") or {}).get("evidence") or {}
    rc = safety.get("rate_context") or {}
    if not rc.get("available"):
        return {"available": False}
    return {
        "available": True,
        "elapsed_sec": rc.get("elapsed_sec"),
        "health_direction": rc.get("health_direction"),
        "health_change_per_sec": rc.get("health_change_per_sec"),
        "threat_count_direction": rc.get("threat_count_direction"),
        "threat_count_change_per_sec": rc.get("threat_count_change_per_sec"),
        "direction": rc.get("direction"),
        "magnitude": rc.get("magnitude"),
        "acceleration": rc.get("acceleration"),
    }


def _build_status_summary(dims: dict[str, dict]) -> dict[str, str]:
    """快速一览：每个 dimension 的 status，便于前端徽章呈现。"""

    return {name: (data.get("status") or "unknown") for name, data in dims.items()}
