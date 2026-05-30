"""Framework-agnostic Crafter wrapper for H-0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .observation import build_symbolic_observation
from ..actions import ActionAdapter


class CrafterLoadError(RuntimeError):
    """Raised when the local Crafter environment cannot be created."""


# Crafter facing == the last movement direction (a blocked move still turns the
# agent), so the wrapper tracks it from the issued action rather than env internals.
_MOVE_TO_FACING = {
    "move_left": "left",
    "move_right": "right",
    "move_up": "up",
    "move_down": "down",
}


@dataclass(frozen=True)
class StepResult:
    raw_observation: Any
    reward: float
    done: bool
    raw_info: dict[str, Any]
    agent_observation: dict[str, Any]


class CrafterEnvWrapper:
    """Minimal H-0 wrapper around a locally installed Crafter environment."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._seed = seed
        self._env = self._create_env(seed=seed)
        self._adapter = ActionAdapter()
        self._episode_id = uuid4().hex
        self._step = 0
        self._facing = "down"  # Crafter spawns facing down; updated on each move
        self._last_raw_observation: Any | None = None
        self._last_info: dict[str, Any] = {}

        action_report = self._adapter.validate_env_action_space(getattr(self._env, "action_space", None))
        if not bool(action_report.get("matches_expected")):
            raise CrafterLoadError(
                f"Crafter action space mismatch: {action_report}"
            )

    @property
    def action_adapter(self) -> ActionAdapter:
        return self._adapter

    def reset(self, *, seed: int | None = None) -> dict[str, Any]:
        if seed is not None:
            self._seed = seed
        self._episode_id = uuid4().hex
        self._step = 0
        self._facing = "down"
        raw_observation, info = self._reset_env(seed=self._seed)
        self._last_raw_observation = raw_observation
        self._last_info = dict(info)
        return build_symbolic_observation(
            episode_id=self._episode_id,
            step=self._step,
            raw_observation=raw_observation,
            raw_info=info,
            facing=self._facing,
        )

    def step(self, action_name: str) -> StepResult:
        action_id = self._adapter.name_to_id(action_name)
        raw_observation, reward, done, info = self._step_env(action_id)
        self._step += 1
        if action_name in _MOVE_TO_FACING:
            self._facing = _MOVE_TO_FACING[action_name]
        self._last_raw_observation = raw_observation
        self._last_info = dict(info)
        agent_observation = build_symbolic_observation(
            episode_id=self._episode_id,
            step=self._step,
            raw_observation=raw_observation,
            raw_info=info,
            facing=self._facing,
        )
        return StepResult(
            raw_observation=raw_observation,
            reward=reward,
            done=done,
            raw_info=dict(info),
            agent_observation=agent_observation,
        )

    def close(self) -> None:
        close = getattr(self._env, "close", None)
        if callable(close):
            close()

    @staticmethod
    def _create_env(*, seed: int | None) -> Any:
        try:
            import crafter
        except Exception as exc:  # pragma: no cover - depends on local env
            raise CrafterLoadError("Crafter is not installed in the current Python environment") from exc

        env_cls = getattr(crafter, "Env", None)
        if env_cls is None:
            raise CrafterLoadError("Installed crafter package does not expose crafter.Env")
        try:
            if seed is None:
                return env_cls()
            return env_cls(seed=seed)
        except Exception as exc:  # pragma: no cover - depends on local env
            raise CrafterLoadError(f"crafter.Env(seed={seed!r}) failed") from exc

    def _reset_env(self, *, seed: int | None) -> tuple[Any, dict[str, Any]]:
        try:
            if seed is not None:
                result = self._env.reset(seed=seed)
            else:
                result = self._env.reset()
        except TypeError:
            if seed is not None and hasattr(self._env, "seed"):
                self._env.seed(seed)
            result = self._env.reset()
        if isinstance(result, tuple) and len(result) == 2:
            observation, info = result
            return observation, dict(info or {})
        # Old gym API: reset() returns a bare observation with no info dict.
        # Crafter's player and world are already initialised at this point, so
        # we can reconstruct the same info fields that step() would produce,
        # giving the agent a non-blind first observation.
        player = getattr(self._env, "_player", None)
        birth_inv = dict(getattr(player, "inventory", None) or {})
        sem_view = getattr(self._env, "_sem_view", None)
        birth_info: dict[str, Any] = {}
        if birth_inv:
            birth_info["inventory"] = birth_inv
        if player is not None and sem_view is not None:
            try:
                birth_info["semantic"] = sem_view()
                birth_info["player_pos"] = player.pos
            except Exception:
                pass
        return result, birth_info

    def _step_env(self, action_id: int) -> tuple[Any, float, bool, dict[str, Any]]:
        result = self._env.step(action_id)
        if isinstance(result, tuple) and len(result) == 5:
            observation, reward, terminated, truncated, info = result
            return observation, float(reward or 0.0), bool(terminated or truncated), dict(info or {})
        if isinstance(result, tuple) and len(result) == 4:
            observation, reward, done, info = result
            return observation, float(reward or 0.0), bool(done), dict(info or {})
        raise RuntimeError(f"Unexpected env.step result shape: {type(result)!r} {result!r}")


__all__ = ["CrafterEnvWrapper", "CrafterLoadError", "StepResult"]
