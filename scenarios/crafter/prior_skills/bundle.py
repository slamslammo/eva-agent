"""Canonical Crafter startup prior bundle for Stage I I-2."""

from __future__ import annotations

from dataclasses import dataclass

from eva.skills import PriorSkillRecord, PriorSkillRegistry, SkillProvenance

CRAFTER_STARTUP_PRIOR_PREFIX = "crafter_startup_prior"


@dataclass(frozen=True)
class CrafterPriorDefinition:
    prior_id: str
    candidate_profile: str
    preferred_action: str | None
    provenance_detail: str
    confidence: float
    mutable: bool
    source_paths: tuple[str, ...]
    applies_to_top_drives: tuple[str, ...] = ()
    applies_to_pressure_reasons: tuple[str, ...] = ()
    applies_to_life_states: tuple[str, ...] = ("STABLE",)
    related_dimension_names: tuple[str, ...] = ()
    related_persistence_levels: tuple[int, ...] = ()
    related_anchor_profiles: tuple[str, ...] = ()

    def runtime_record(self, *, top_drive: str, life_state: str, pressure_reason: str, situation_key: str) -> PriorSkillRecord:
        return PriorSkillRecord(
            recorded_at="scenario_definition",
            situation_key=situation_key,
            candidate_profile=self.candidate_profile,
            preferred_action=self.preferred_action,
            provenance=SkillProvenance(
                source="scenario",
                provenance_detail=self.provenance_detail,
                confidence=self.confidence,
                scope={
                    "scenario": "crafter",
                    "top_drive": top_drive,
                    "life_state": life_state,
                    "pressure_reason": pressure_reason,
                    "source_paths": list(self.source_paths),
                    "applies_to_top_drives": list(self.applies_to_top_drives),
                    "applies_to_pressure_reasons": list(self.applies_to_pressure_reasons),
                    "applies_to_life_states": list(self.applies_to_life_states),
                    "related_dimension_names": list(self.related_dimension_names),
                    "related_persistence_levels": list(self.related_persistence_levels),
                    "related_anchor_profiles": list(self.related_anchor_profiles),
                },
                mutable=self.mutable,
            ),
        )

    def startup_record(self) -> PriorSkillRecord:
        return PriorSkillRecord(
            recorded_at="scenario_definition",
            situation_key=f"{CRAFTER_STARTUP_PRIOR_PREFIX}|{self.prior_id}",
            candidate_profile=self.candidate_profile,
            preferred_action=self.preferred_action,
            provenance=SkillProvenance(
                source="scenario",
                provenance_detail=self.provenance_detail,
                confidence=self.confidence,
                scope={
                    "scenario": "crafter",
                    "source_paths": list(self.source_paths),
                    "applies_to_top_drives": list(self.applies_to_top_drives),
                    "applies_to_pressure_reasons": list(self.applies_to_pressure_reasons),
                    "applies_to_life_states": list(self.applies_to_life_states),
                    "related_dimension_names": list(self.related_dimension_names),
                    "related_persistence_levels": list(self.related_persistence_levels),
                    "related_anchor_profiles": list(self.related_anchor_profiles),
                },
                mutable=self.mutable,
            ),
        )


CRAFTER_STARTUP_PRIOR_DEFINITIONS = (
    CrafterPriorDefinition(
        prior_id="safety_escalate_do",
        candidate_profile="escalate_first",
        preferred_action="do",
        provenance_detail="crafter_safety_escalation_prior",
        confidence=0.9,
        mutable=False,
        source_paths=(
            "scenarios/crafter/anchors/policy.py",
            "scenarios/crafter/prior_skills/compatibility.py",
        ),
        applies_to_top_drives=("safety",),
        applies_to_pressure_reasons=("health_critical", "threat_visible"),
        related_dimension_names=("avatar_safety", "local_view_threat"),
        related_persistence_levels=(1, 2),
        related_anchor_profiles=("escalate_first",),
    ),
    CrafterPriorDefinition(
        prior_id="safety_stabilize_sleep",
        candidate_profile="stabilize_first",
        preferred_action="sleep",
        provenance_detail="crafter_safety_stabilization_floor_prior",
        confidence=0.75,
        mutable=False,
        source_paths=(
            "scenarios/crafter/anchors/policy.py",
            "scenarios/crafter/prior_skills/compatibility.py",
        ),
        applies_to_top_drives=("safety",),
        applies_to_pressure_reasons=("health_critical", "threat_visible"),
        related_dimension_names=("avatar_safety", "local_view_threat"),
        related_persistence_levels=(1, 2),
        related_anchor_profiles=("stabilize_first",),
    ),
    CrafterPriorDefinition(
        prior_id="metabolic_stabilize_do",
        candidate_profile="stabilize_first",
        preferred_action="do",
        provenance_detail="crafter_metabolic_stabilization_prior",
        confidence=0.85,
        mutable=False,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/dimensions/__init__.py",
        ),
        applies_to_top_drives=("metabolic",),
        applies_to_pressure_reasons=("water_critical", "food_critical"),
        related_dimension_names=("avatar_metabolic",),
        related_persistence_levels=(4,),
        related_anchor_profiles=("stabilize_first",),
    ),
    CrafterPriorDefinition(
        prior_id="metabolic_observe_noop",
        candidate_profile="observe_first",
        preferred_action="noop",
        provenance_detail="crafter_metabolic_recognition_prior",
        confidence=0.6,
        mutable=True,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/actions/compatibility.py",
        ),
        applies_to_top_drives=("metabolic",),
        applies_to_pressure_reasons=("water_critical", "food_critical"),
        related_dimension_names=("avatar_metabolic",),
        related_anchor_profiles=("observe_first",),
    ),
    CrafterPriorDefinition(
        prior_id="recovery_stabilize_sleep",
        candidate_profile="stabilize_first",
        preferred_action="sleep",
        provenance_detail="crafter_recovery_rest_prior",
        confidence=0.85,
        mutable=False,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/dimensions/__init__.py",
        ),
        applies_to_top_drives=("recovery",),
        applies_to_pressure_reasons=("energy_critical",),
        related_dimension_names=("avatar_recovery",),
        related_anchor_profiles=("stabilize_first",),
    ),
    CrafterPriorDefinition(
        prior_id="recovery_observe_noop",
        candidate_profile="observe_first",
        preferred_action="noop",
        provenance_detail="crafter_recovery_recognition_prior",
        confidence=0.6,
        mutable=True,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/actions/compatibility.py",
        ),
        applies_to_top_drives=("recovery",),
        applies_to_pressure_reasons=("energy_critical",),
        related_dimension_names=("avatar_recovery",),
        related_anchor_profiles=("observe_first",),
    ),
    CrafterPriorDefinition(
        prior_id="acquisition_observe_noop",
        candidate_profile="observe_first",
        preferred_action="noop",
        provenance_detail="crafter_acquisition_resource_chain_prior",
        confidence=0.8,
        mutable=False,
        source_paths=(
            "scenarios/crafter/drive_preset.py",
            "scenarios/crafter/prior_skills/compatibility.py",
        ),
        applies_to_top_drives=("acquisition",),
        related_dimension_names=("inventory_acquisition", "local_view_resource"),
        related_persistence_levels=(4,),
        related_anchor_profiles=("observe_first",),
    ),
    CrafterPriorDefinition(
        prior_id="acquisition_stabilize_sleep",
        candidate_profile="stabilize_first",
        preferred_action="sleep",
        provenance_detail="crafter_acquisition_survival_floor_prior",
        confidence=0.5,
        mutable=False,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/anchors/policy.py",
        ),
        applies_to_top_drives=("acquisition",),
        related_dimension_names=("inventory_acquisition", "local_view_resource"),
        related_anchor_profiles=("stabilize_first",),
    ),
    CrafterPriorDefinition(
        prior_id="capability_observe_noop",
        candidate_profile="observe_first",
        preferred_action="noop",
        provenance_detail="crafter_capability_resource_chain_prior",
        confidence=0.8,
        mutable=False,
        source_paths=(
            "scenarios/crafter/drive_preset.py",
            "scenarios/crafter/prior_skills/compatibility.py",
        ),
        applies_to_top_drives=("capability",),
        related_dimension_names=("inventory_capability", "local_view_utility"),
        related_persistence_levels=(3,),
        related_anchor_profiles=("observe_first",),
    ),
    CrafterPriorDefinition(
        prior_id="capability_stabilize_sleep",
        candidate_profile="stabilize_first",
        preferred_action="sleep",
        provenance_detail="crafter_capability_survival_floor_prior",
        confidence=0.5,
        mutable=False,
        source_paths=(
            "scenarios/crafter/prior_skills/compatibility.py",
            "scenarios/crafter/anchors/policy.py",
        ),
        applies_to_top_drives=("capability",),
        related_dimension_names=("inventory_capability", "local_view_utility"),
        related_anchor_profiles=("stabilize_first",),
    ),
    CrafterPriorDefinition(
        prior_id="default_observe_noop",
        candidate_profile="observe_first",
        preferred_action="noop",
        provenance_detail="crafter_action_surface_baseline_prior",
        confidence=0.7,
        mutable=True,
        source_paths=(
            "scenarios/crafter/actions/compatibility.py",
            "scenarios/crafter/prior_skills/compatibility.py",
        ),
        related_anchor_profiles=("observe_first",),
    ),
)


def prior_definitions_for_context(*, top_drive: str, pressure_reason: str) -> tuple[CrafterPriorDefinition, ...]:
    if pressure_reason in {"health_critical", "threat_visible"} or top_drive == "safety":
        return CRAFTER_STARTUP_PRIOR_DEFINITIONS[0:2]
    if pressure_reason == "energy_critical" or top_drive == "recovery":
        return CRAFTER_STARTUP_PRIOR_DEFINITIONS[4:6]
    if pressure_reason in {"water_critical", "food_critical"} or top_drive == "metabolic":
        return CRAFTER_STARTUP_PRIOR_DEFINITIONS[2:4]
    if top_drive == "acquisition":
        return CRAFTER_STARTUP_PRIOR_DEFINITIONS[6:8]
    if top_drive == "capability":
        return CRAFTER_STARTUP_PRIOR_DEFINITIONS[8:10]
    return (CRAFTER_STARTUP_PRIOR_DEFINITIONS[10],)


def build_crafter_prior_skill_registry(*, top_drive: str, life_state: str, pressure_reason: str, situation_key: str | None = None) -> PriorSkillRegistry:
    resolved_situation_key = situation_key or f"{top_drive}|{life_state}|{pressure_reason}"
    return PriorSkillRegistry(
        [
            definition.runtime_record(
                top_drive=top_drive,
                life_state=life_state,
                pressure_reason=pressure_reason,
                situation_key=resolved_situation_key,
            )
            for definition in prior_definitions_for_context(
                top_drive=top_drive,
                pressure_reason=pressure_reason,
            )
        ]
    )


def build_crafter_startup_prior_registry() -> PriorSkillRegistry:
    return PriorSkillRegistry([definition.startup_record() for definition in CRAFTER_STARTUP_PRIOR_DEFINITIONS])


__all__ = [
    "CRAFTER_STARTUP_PRIOR_DEFINITIONS",
    "CRAFTER_STARTUP_PRIOR_PREFIX",
    "CrafterPriorDefinition",
    "build_crafter_prior_skill_registry",
    "build_crafter_startup_prior_registry",
    "prior_definitions_for_context",
]
