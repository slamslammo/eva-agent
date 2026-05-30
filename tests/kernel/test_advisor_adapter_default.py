"""framework-scenario-timing slice 4 — advisor adapter default decoupling.

Observation 2: with ``working_memory_backend="llm_assisted"`` and the previous
default ``working_memory_adapter_mode="inert"``, ``_resolve_working_memory_adapter``
fell through to ``ClientBackedWorkingMemoryAdapter(client_mode=<config>)``. When the
client mode is ``live`` (the canonical dlPFC run), that shell issues a *separate*
per-turn advisory LLM call on top of the dlPFC candidate producer — an implicit,
costly coupling the operator had to suppress by hand (``--working-memory-adapter-mode
heuristic``).

This slice flips the default ``adapter_mode`` to ``heuristic`` so the advisory adapter
is local-only by default (``HeuristicWorkingMemoryAdapter``, no model call). Operators
who want the client-backed advisory shell opt in explicitly with ``adapter_mode=inert``.
The dlPFC producer is gated only on ``backend==llm_assisted`` + ``client_mode==live``
(no ``adapter_mode`` check), so this flip does not affect it.
"""

from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from eva.kernel.config import build_runtime_config
from eva.kernel.main import _resolve_working_memory_adapter, parse_args
from eva.l3_deliberation.memory.working_memory_adapter import (
    ADAPTER_MODE_HEURISTIC,
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
)


def _parse_minimal():
    argv = ["prog", "--runtime-dir", "/tmp/eva-adapter-default-test"]
    with mock.patch("sys.argv", argv):
        return parse_args()


class AdapterModeDefaultTests(unittest.TestCase):
    def test_build_runtime_config_default_adapter_mode_is_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir)
            self.assertEqual(config.working_memory_adapter_mode, ADAPTER_MODE_HEURISTIC)

    def test_argparse_default_adapter_mode_is_heuristic(self) -> None:
        args = _parse_minimal()
        self.assertEqual(args.working_memory_adapter_mode, ADAPTER_MODE_HEURISTIC)


class AdapterResolutionTests(unittest.TestCase):
    def test_llm_assisted_default_resolves_to_local_heuristic_not_client_backed(self) -> None:
        # THE observation-2 guard: llm_assisted + default adapter_mode must NOT
        # silently build a ClientBackedWorkingMemoryAdapter (which would issue a
        # live advisory call under client_mode=live).
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir, working_memory_backend="llm_assisted")
            adapter = _resolve_working_memory_adapter(config, explicit_adapter=None)
            self.assertIsInstance(adapter, HeuristicWorkingMemoryAdapter)
            self.assertNotIsInstance(adapter, ClientBackedWorkingMemoryAdapter)

    def test_explicit_inert_still_opts_into_client_backed_shell(self) -> None:
        # The client-backed advisory shell remains reachable via explicit opt-in.
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(
                temp_dir,
                working_memory_backend="llm_assisted",
                working_memory_adapter_mode="inert",
            )
            adapter = _resolve_working_memory_adapter(config, explicit_adapter=None)
            self.assertIsInstance(adapter, ClientBackedWorkingMemoryAdapter)

    def test_local_rule_based_backend_unaffected_by_adapter_mode_flip(self) -> None:
        # The default backend (local_rule_based) resolves to no adapter regardless
        # of adapter_mode, so the flip is scoped to llm_assisted / auto backends.
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir)  # backend defaults to local_rule_based
            adapter = _resolve_working_memory_adapter(config, explicit_adapter=None)
            self.assertIsNone(adapter)

    def test_auto_backend_default_resolves_to_local_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = build_runtime_config(temp_dir, working_memory_backend="auto")
            adapter = _resolve_working_memory_adapter(config, explicit_adapter=None)
            self.assertIsInstance(adapter, HeuristicWorkingMemoryAdapter)
            self.assertNotIsInstance(adapter, NullWorkingMemoryAdapter)


if __name__ == "__main__":
    unittest.main()
