# Round 1.E — L3 Reasoning Proposal Path — Startup Instruction for Claude Code

**Recipient**: Claude Code (code line, `claude/recursing-hertz-7c4029`)
**Issued by**: Architect (current session)
**Status**: startup — fill the L3 reasoning "virtual position". Make the model an **anchor-bounded candidate/profile proposer**; the peer-circuit keeps selection authority and the mediator keeps release authority. The model drives *what is considered*, never *what is released*.

**Companion documents (read before starting)**:
- `.claude/plans/federated-snacking-engelbart.md` — Round 1 master plan. Slot this round as the post-rev2 substantive priority; renumber if the plan owner prefers (the round letter is not load-bearing).
- `docs/architecture-implementation-blueprint-v0.6.md` §7.4 (reasoning core: "forms candidates, not actions; outputs a ranked candidate set"), §7.5–7.6 (peer-circuit / mediator authority), §4 (anchors pre-generative), §15.4 (evolution guardrails).
- `maintainer/development/round-1a-progress.md` — the motivating finding: action surface is widened but L3 picked `stabilize_first` in 198/198 audits; selection is rule/positional (`crafter_minimal_selection`); the model only adds a ≤0.12 post-hoc bias.
- `maintainer/development/rev2-existence-semantics-alignment.md` — current paradigm baseline (existence semantics scenario-declared; do not disturb).
- Code seams to read in full before changing:
  - `eva/l3_deliberation/runtime.py` — `run_deliberation` (the orchestration entry).
  - `eva/l3_deliberation/reasoning/value_judgment.py` — current `_llm_advisory_bonus_for_candidate_profile` (the ≤0.12 ceiling).
  - `eva/l3_deliberation/reasoning/working_memory.py` — advisory assembly + the `llm_assisted` adapter path.
  - `eva/l3_deliberation/reasoning/candidate_generation.py` — `build_candidates` (admitted schemas → candidates).
  - `eva/l3_deliberation/peer_circuit/mediator.py`, `peer_circuit/selection.py` — selection + release authority.
  - `eva/l3_deliberation/contracts.py` — `DeliberationInput`, `Candidate`, `ReleaseDecision`, audit record.

---

## 1. What this work is and is not

**The problem.** Round 1.A widened the Crafter action surface (17 actions across 3 profiles) and exploration/idle-spin fixes made the agent *act* via rules. But the L3 reasoning position the blueprint §7.4 specifies — "reasoning core forms candidates and outputs a ranked candidate set" — is effectively empty: candidate generation just converts anchor-admitted schemas; the model's only influence is a ≤0.12 post-assessment bonus in `value_judgment`. The agent is **rule-driven, not reasoning-driven**. Rules suffice for simple reactive behavior; multi-step synthesis / trade-off / novel situations need bounded strong reasoning.

**What Round 1.E is**:
- Introduce a **proposal stage** between anchor admission and candidate assessment: a `Proposer` produces, *within the anchor-admitted domain only*, a ranked set of candidate/profile hints (with predicted outcome, rationale, confidence, provenance `source="reasoning"`).
- Two proposer implementations behind one protocol: a **HeuristicProposer** (deterministic; default; `local_rule_based`-compatible) and an **LLM-backed proposer** (reuses the existing working-memory model-client path; schema-bound JSON; bounded with timeout + fallback).
- Normalize proposals into the **existing** candidate vocabulary (the 3 profiles + Round 1.A concrete actions); **discard out-of-domain / malformed proposals** (logged).
- Feed normalized candidates into the **unchanged** `assess_candidates → peer-circuit selection → mediator release` path.
- Record proposals + rejections + the `proposal_id → selected candidate` linkage in `deliberation_audit` so the model's contribution is measurable.
- Net effect: the model's influence rises from "≤0.12 nudge on already-generated candidates" to "shapes which candidates are considered" — **still** bounded by anchor admission, peer-circuit selection, mediator release, and default inhibition.

**What Round 1.E is NOT**:
- Not letting the model release actions, bypass the mediator, or bypass anchor admission.
- Not adding new candidate profiles. `eva/l3_deliberation/reasoning/conflict_detection.py` 3-profile whitelist stays untouched. (Profile-vocabulary widening is a separate, later option.)
- Not adding new action vocabulary. Round 1.A's action set stays.
- Not writing drive state, not changing anchor/mediator/persistence/audit structure, not touching existence semantics.
- Not the LLM-reasoning long-run evaluation — that is a **separate later validation round** (see §8). This round delivers the mechanism + structural tests only.

---

## 2. Exit criterion

Round 1.E is complete when **all** hold:

**Behavioral / functional**
- A `Proposer` seam exists with both `HeuristicProposer` and an LLM-backed proposer.
- Under `llm_assisted`, the model produces structured proposals that **demonstrably change the considered candidate set** relative to `local_rule_based` — verifiable in `deliberation_audit.jsonl`.
- Out-of-domain or malformed proposals are **rejected and logged** (covered by a test).
- A `proposal_id → selected candidate` linkage is recorded in audit (reasoning-contribution signal).

**Invariant (must prove by test)**
- A model proposal that anchor would not admit, or that names an action/profile outside the admitted domain, **does not execute** (rejected at normalization).
- The mediator remains the sole release authority and the peer-circuit the sole selection authority — proven by a test where a high-confidence proposal is still gated/withheld by the mediator.
- Default inhibition preserved: no proposal path triggers a side effect directly.

**Engineering**
- `local_rule_based` behavior-preserving: with the model off, traces are equivalent to a pre-1.E baseline (the proposer degrades to heuristic/inert).
- Full regression green. Tests asserting the old ≤0.12 advisory surface may need assertion-data updates (not logic changes).
- `git diff --name-only` shows **no** changes to `eva/l3_deliberation/peer_circuit/mediator.py` release-authority logic, `eva/anchor/`, `eva/l2_drive/` ownership, or append-only schema beyond additive proposal records.
- Linux unaffected (Linux uses the same L3 path; verify Linux suite + smoke unchanged).

**Documentation**
- `docs/implementation-tracking.md` (+ `-zh`) L3 reasoning row updated from `skeleton` toward `partial`/`production` per what actually lands; `blueprint-to-tracking-map.md` (+ `-zh`) corresponding row updated.
- `scenarios/crafter/SPEC.md` updated if the Crafter deliberation surface changes observably.
- `maintainer/development/round-1e-progress.md` written and closed; `current-intake.md` closeout updated.

---

## 3. The seam (where the proposer slots in)

Current flow (read to confirm):
```
run_deliberation
  → build_action_domain            (anchor admission — UNCHANGED)
  → build_candidates(admitted)     (schemas → candidates)
  → assess_candidates              (drive-weighted; model ≤0.12 bonus here today)
  → decide_release (peer-circuit)  (selection authority)
  → tool_edge                      (mediator-gated release)
```

Target flow:
```
run_deliberation
  → build_action_domain            (UNCHANGED — the domain bound)
  → proposer(working_memory_context, admitted_domain)
        → ranked ReasoningProposal(s), constrained to admitted profiles + actions
  → normalize proposals → candidates (existing vocabulary); DROP out-of-domain (audit)
  → assess_candidates              (UNCHANGED downstream)
  → decide_release (peer-circuit)  (UNCHANGED)
  → tool_edge (mediator-gated)     (UNCHANGED)
```

Key design points:
- The proposer reads `working_memory_context` (sensing + drive broadcast + episodic/semantic/procedural/inherited hints) and the **admitted domain**; it may only rank/propose within that domain.
- The existing `value_judgment` model-advisory may be subsumed by the proposer or kept as a secondary signal — but the ≤0.12 ceiling is no longer the model's only lever. Decide and document which.
- `local_rule_based` ⇒ proposer is the deterministic `HeuristicProposer` (or inert) ⇒ behavior-preserving.

---

## 4. Implementation slices (each a separate commit; G1 before E-1; G2 after E-7)

- **E-1 — failing tests** pinning: (a) under `llm_assisted` the considered candidate set differs from `local_rule_based`; (b) an out-of-domain proposal is rejected + logged; (c) a high-confidence proposal is still gated by the mediator (authority holds); (d) default inhibition holds (no direct side effect).
- **E-2 — `ReasoningProposal` contract** (minimal fields: `proposal_id`, `candidate_profile`, `action_hint`, `predicted_outcome` (vector, optional), `rationale`, `confidence`, `provenance source="reasoning"`). Add to `contracts.py` or `reasoning/`.
- **E-3 — `Proposer` protocol + two impls**: `HeuristicProposer` (deterministic, default) and `ModelBackedProposer` (reuse the working-memory model-client; **schema-bound JSON**, bounded timeout, fallback to heuristic on error/timeout). `local_rule_based` → heuristic/inert.
- **E-4 — normalization + rejection + audit**: map proposals to existing candidates; reject anything outside the admitted profiles/actions or malformed; log rejections with reason into `deliberation_audit`.
- **E-5 — wire into `run_deliberation`** between admission and assessment; keep peer-circuit/mediator untouched; prove `local_rule_based` behavior-preserving.
- **E-6 — reasoning-contribution audit**: record `proposal_id → selected candidate` linkage.
- **E-7 — integration test (Crafter)**: under `llm_assisted` the considered set differs from `local_rule_based`; all §6 invariants hold end-to-end.
- **E-8 — docs sync + closeout** (per §2 Documentation).

---

## 5. Tests

**Freeze (must pass without logic change)**: `tests/kernel/`, `tests/l1_sensing/`, `tests/l2_drive/`, `tests/anchor/`, `tests/l3_deliberation/peer_circuit/`, `tests/l3_deliberation/tool_edge/`, `tests/scenarios/linux_runtime/`, `tests/scenarios/test_existence_semantics.py`, `tests/integration/test_individual_identity.py`, `tests/stability_metrics/`, `tests/inheritance_distillation/`.

**May need assertion-data updates (allowed)**: `tests/l3_deliberation/reasoning/test_value.py`, `tests/l3_deliberation/reasoning/test_working_memory.py` — if the advisory→proposal shift changes their surface. Assertion-data only, not logic structure; if a test can't pass with assertion-data updates, pause and review (scope creep signal).

**New**: a `tests/l3_deliberation/reasoning/test_reasoning_proposal.py` (E-1 set) + integration coverage in `tests/integration/test_crafter_runtime.py`.

---

## 6. Red-lines / invariants (stop conditions)

1. **Anchor pre-generative restriction holds** — proposals live only inside the admitted domain; `conflict_detection.py` 3-profile whitelist untouched.
2. **Mediator is the sole release authority; peer-circuit the sole selection authority** — the proposer only supplies candidates; it never selects or releases.
3. **Default inhibition** — no proposal path triggers a side effect directly.
4. **Model output is operational content** — it may propose candidates/rankings; it may never write drive state, anchor structure, mediator authority, audit semantics, persistence-target definitions, or existence semantics.
5. **`local_rule_based` behavior-preserving** — model off ⇒ current behavior.
6. **Append-only additive only** — audit gains proposal/rejection records; no schema breaks, no new mandatory fields on existing records.
7. **Linux bit-exact** equivalent (same L3 path; verify).
8. **Bounded model use** — schema-bound JSON, timeout, fallback to heuristic; a model failure must never crash deliberation or release an unvalidated action.

---

## 7. Architect gates

- **G1 — pre-implementation intake**: before E-1, write a change intake into `current-intake.md` (layer = `eva/l3_deliberation/reasoning/` + `contracts.py`; canonical owners touched; profile vocabulary unchanged; tests to freeze per §5; docs to sync per §2). Present to architect. Approval required before E-1.
- **G2 — post-E-7 review**: present (a) a `deliberation_audit` excerpt showing model proposals changing the considered set vs `local_rule_based`; (b) the invalid-proposal rejection trace; (c) the authority-holds + default-inhibition test results; (d) `git diff` showing no release-authority / anchor / drive-ownership / schema widening; (e) Linux equivalence. Architect approves before the validation round.

---

## 8. Validation positioning (do NOT do in this round)

This round delivers the **mechanism + structural tests**, not the LLM-reasoning evaluation. After G2, a separate validation round compares `local_rule_based` vs `heuristic_proposer` vs `llm_proposer` on: survival length, achievements, no-op rate, invalid-proposal rejection rate, reasoning-contribution ratio, token-per-useful-progress.

The currently-planned Phase 3 long-run should run as **`local_rule_based`** (structural validation of the now-playing rule-driven agent); the LLM-reasoning long-run waits until Round 1.E lands. Running a live-model long-run before this round measures the rule system and burns tokens for ≤0.12 influence.

---

## 9. Recommended starting flow

1. Read the companion documents and the §1 seam code in full.
2. Write the G1 intake into `current-intake.md`; request G1 approval.
3. After G1, proceed E-1 → E-8, one commit per slice; full regression after each.
4. After E-7, request G2.

---

## 10. Out-of-round housekeeping (not part of Round 1.E; flagged for the human/architect)

These are tracked separately and must **not** be bundled into Round 1.E:
- `#3` closeout edit (Crafter `identity_continuity` string tighten) is applied in the worktree but uncommitted — commit it with the rev2 closeout.
- Convergence: the rev2 docs are committed on `main`; bring them onto the code line (merge `main` → `claude/recursing-hertz-7c4029`, resolving the `scenarios/crafter/SPEC.md` overlap in favor of the rev2 rewrite) when convenient. Round 1.E does not depend on it (it touches L3 reasoning, not existence semantics).
- `CLAUDE.md` (code line) still references deleted intake docs (`development-standards.md`, `module-organization-contract.md`, `codebase-realignment-plan.md`, `change-intake-template.md`); update those references to the actual Round-based process.
- Stage H followup #3 (placeholder Crafter outcome confidence) — relevant once reasoning unlocks action variety; schedule after this round.
