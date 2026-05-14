"""Framework-agnostic Crafter wrapper surfaces for Stage H H-0."""

from .env_wrapper import CrafterEnvWrapper, CrafterLoadError, StepResult
from .observation import build_symbolic_observation, observation_shape
from .semantic_local_view import build_local_view, compact_grid, validate_agent_local_view

__all__ = [
    "CrafterEnvWrapper",
    "CrafterLoadError",
    "StepResult",
    "build_local_view",
    "build_symbolic_observation",
    "compact_grid",
    "observation_shape",
    "validate_agent_local_view",
]
