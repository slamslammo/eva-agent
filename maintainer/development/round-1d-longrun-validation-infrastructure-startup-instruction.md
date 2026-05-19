# Round 1.D — Long-Run Validation Infrastructure (W1 redefined) — Startup Instruction

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.D — infrastructure for W1 long-run validation; the actual 6h+ runs are user-driven, this slice lands the supporting infrastructure

**Companion documents**:
- `.claude/plans/federated-snacking-engelbart.md` — Round 1 plan
- `maintainer/development/round-1b-2-progress.md` — Round 1.B-2 surfaced parameter-tuning items that Round 1.D's runs will produce data for
- `eva/kernel/main.py:54-141` — `run_runtime` (the canonical loop being extended)
- `stability_metrics/metrics.py` — `calculate_stability_profile` / `write_stability_profile` (existing, reused)
- `docs/architecture-implementation-blueprint-v0.6.md` §13.2 — long-run invariant validation is a v0.6 obligation

---

## 1. What this work is and is not

**Infrastructure for long-run validation**:
- **D-1**: graceful interrupt in `run_runtime`. KeyboardInterrupt still writes the shutdown event. Adds `exit_reason` to `RunSummary`.
- **D-2**: optional `periodic_hook` parameter on `run_runtime`. The hook is called every `hook_interval_sec` (default disabled). Hook returns `(should_stop, reason)`.
- **D-3**: new `runners/longrun_validation.py` providing `build_longrun_validation_hook(snapshot_dir, tripwire)` factory that returns a hook performing both snapshot-writing and tripwire-checking.

**What Round 1.D is NOT**:
- Not running the actual 24h+ validation (user-driven, after infrastructure lands)
- Not changing scenario behavior, drive layer, anchor surface, or release authority
- Not changing the canonical stability_metrics calculation
- Not adding new persistence schemas (snapshots use the existing `stability_profile.json` schema, written to a `snapshots/` subdir)
- Not modifying `runners/run_crafter.py` directly — the hook is opt-in and the runner can wire it up when invoked for validation

---

## 2. Exit criterion

### Behavioral
- KeyboardInterrupt during `run_runtime` writes a shutdown event with `exit_reason="keyboard_interrupt"` to events.jsonl
- Normal max-* exits write shutdown with `exit_reason` matching the bound that fired
- Periodic hook fires at most every `hook_interval_sec` seconds (no busy-loop)
- Periodic hook returning `(True, reason)` causes the loop to break and exit with `exit_reason=hook-reason`
- `LongrunValidationHook` writes a numbered snapshot file (e.g. `snapshots/profile-00001.json`) every interval
- Tripwire criteria configurable; default thresholds match blueprint §13.2 invariant set
- Linux + Crafter behavior bit-equivalent when no periodic_hook is supplied (the default)

### Engineering
- Full regression passes (target: 371 + ~8 new tests = ~379)
- `git diff main -- 'scenarios/' 'eva/l2_drive/' 'eva/anchor/' 'eva/l1_sensing/' 'eva/l3_deliberation/'` shows zero modifications
- `git diff main -- 'eva/kernel/main.py'` shows additive changes only (signature accepts optional new params; default behavior unchanged)

### Documentation
- `maintainer/development/round-1d-progress.md` written
- `maintainer/development/current-intake.md` updated
- `docs/implementation-tracking.md` adds row for "Long-run validation infrastructure" (blueprint §13.2 obligation now has supporting infrastructure)
- `docs/implementation-tracking-zh.md` mirror

---

## 3. Scope target state

### Files to modify
- `eva/kernel/main.py` — add `exit_reason` to `RunSummary`; refactor loop with try/except KeyboardInterrupt; add `periodic_hook` + `hook_interval_sec` params

### Files to add
- `runners/longrun_validation.py` — hook factory + tripwire dataclass
- `tests/kernel/test_runtime_graceful_interrupt.py` — D-1 + D-2 tests
- `tests/runners/test_longrun_validation_hook.py` — D-3 tests

### Files NOT to modify
- `scenarios/`, `eva/l2_drive/`, `eva/anchor/`, `eva/l1_sensing/`, `eva/l3_deliberation/`, `eva/scenario_bundle.py`, `stability_metrics/`
- `runners/run_crafter.py` / `runners/run_linux.py` — the hook is opt-in, runner integration can be done at validation time without code change

---

## 4. Implementation slices

### 1.D-1: Graceful interrupt + exit_reason
- Add `exit_reason: str` to `RunSummary`
- Wrap loop with try/except KeyboardInterrupt
- Always write shutdown event (with exit_reason in details)
- Default exit_reason values: `"normal"`, `"max_ticks"`, `"max_turns"`, `"max_runtime_sec"`, `"keyboard_interrupt"`, `"periodic_hook_stop"`

### 1.D-2: Periodic hook param on run_runtime
- New params: `periodic_hook: Callable[..., tuple[bool, str | None]] | None = None`, `hook_interval_sec: float = 1800.0`
- Hook is called when `monotonic() - last_hook_at >= hook_interval_sec`
- Hook signature: `hook(runtime_dir, elapsed_since_start, ticks, turns) -> (should_stop, reason)`
- Hook errors are caught and logged but do not crash the loop (defensive — a buggy hook should not kill a long-run)

### 1.D-3: Longrun validation hook factory
- `runners/longrun_validation.py`:
  - `LongrunTripwire` dataclass: thresholds for stability metrics
  - `build_longrun_validation_hook(snapshot_dir: Path, tripwire: LongrunTripwire | None = None)` → returns a hook function
  - The hook (when called):
    1. Computes the current stability profile via `stability_metrics.calculate_stability_profile`
    2. Writes it to `snapshot_dir / f"profile-{seq:05d}.json"` with monotonically increasing seq
    3. Checks tripwire thresholds
    4. Returns `(True, "tripwire:{metric_name}")` if a threshold is violated; else `(False, None)`

### 1.D-4: Dry-run smoke verification (optional in this slice)
- Run `python -m runners.run_crafter --max-runtime-sec 60` with the hook configured (interval 20s) and verify snapshots produced
- Can be done manually after slice lands; not a separate code commit

---

## 5. Boundary / invariants

- All framework runtime invariants preserved (heartbeat-first, instance legitimacy, mediator default inhibition, anchor pre-generative restriction, release token boundary, append-only artifact discipline)
- Drive read-only broadcast unchanged
- No new persistence files outside the optional `snapshots/` directory
- The new params on `run_runtime` are keyword-only with safe defaults — no caller break
- Hook errors are isolated (try/except inside the hook call site)
- Linux scenario behavior bit-equivalent when no periodic_hook supplied

---

## 6. Architect gates

- **G1-1D** (pre-implementation): intake written
- **G2-1D** (post-D-1+D-2): regression green; verify graceful interrupt write path works
- **G3-1D** (post-D-3 + closeout): full regression; verify hook factory + snapshot output

---

## 7. Surfaced for actual long-run execution (out of architect scope)

The actual 6h / 24h+ long-run validation is user-driven (machine time, not architect time):
- Architect lands D-1/D-2/D-3 infrastructure (this slice)
- User runs: `python -m runners.run_crafter --max-runtime-sec 21600 --working-memory-backend local_rule_based ...` with the hook wired in
- Validation report assembly happens post-run

After the long-run produces data, follow-up items expected:
- Crafter exploration drive parameter tuning (from Round 1.B-2 progress doc)
- Cold-start rebuild perf check for semantic indexing (from Round 1.C-1 progress doc)
- Working-memory parameter-object adoption migration check (from Round 1.C-2 progress doc)
