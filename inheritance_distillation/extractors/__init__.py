"""Extractor entrypoints for inherited-prior distillation."""

from .pattern_extractor import extract_pattern_priors
from .risk_extractor import extract_risk_priors
from .skill_template_extractor import extract_skill_template_priors
from .threshold_extractor import extract_threshold_priors

__all__ = [
    "extract_pattern_priors",
    "extract_risk_priors",
    "extract_skill_template_priors",
    "extract_threshold_priors",
]
