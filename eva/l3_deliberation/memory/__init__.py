"""Memory-side subpackage for stubs, habit skills, and advisory adapters."""

from .skill_library import derive_habit_skills
from .stub import build_memory_stub
from .working_memory_adapter import (
    ADAPTER_MODE_HEURISTIC,
    ADAPTER_MODE_INERT,
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
    build_builtin_working_memory_adapter,
)
from .working_memory_model_client import (
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_HEURISTIC,
    MODEL_CLIENT_MODE_INERT,
    NullWorkingMemoryModelClient,
    WorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    WorkingMemoryModelClientResponse,
    build_builtin_working_memory_model_client,
)

__all__ = [
    "derive_habit_skills",
    "build_memory_stub",
    "ADAPTER_MODE_INERT",
    "ADAPTER_MODE_HEURISTIC",
    "WorkingMemoryAdapter",
    "WorkingMemoryAdapterRequest",
    "WorkingMemoryAdapterResponse",
    "NullWorkingMemoryAdapter",
    "HeuristicWorkingMemoryAdapter",
    "ClientBackedWorkingMemoryAdapter",
    "build_builtin_working_memory_adapter",
    "WorkingMemoryModelClient",
    "WorkingMemoryModelClientConfig",
    "WorkingMemoryModelClientRequest",
    "WorkingMemoryModelClientResponse",
    "NullWorkingMemoryModelClient",
    "HeuristicWorkingMemoryModelClient",
    "MODEL_CLIENT_MODE_INERT",
    "MODEL_CLIENT_MODE_HEURISTIC",
    "build_builtin_working_memory_model_client",
]
