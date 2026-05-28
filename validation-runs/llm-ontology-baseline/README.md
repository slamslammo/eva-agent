# llm-ontology-run-100-turn-baseline — interface-audit run artifacts

Date: 2026-05-29
Owner: B-claude-2
Branch: `llm-ontology-run-100-turn-baseline`
Plan: `plans/llm-eva-ontology-interface-plan.md` §7 + §8
Source commits:
- `09d6390` — PR-Γ (main HEAD before run)
- `ee49769` — PR-Β' (transcript schema v1.1)
- `289f314` — PR-Β (CRAFTER ontology + producer 6-section injection)
- `75b92b1` — PR-Α (transcript sink + token refs)

## Run configuration

| Setting | Value |
|---|---|
| EVA_LLM_TRANSCRIPT | raw |
| EVA_LLM_API_BASE_URL | https://api.deepseek.com |
| EVA_LLM_MODEL | deepseek-v4-pro |
| EVA_LLM_EXTRA_PARAMS_JSON | `{"thinking":{"type":"enabled"},"reasoning_effort":"high","stream":false,"max_tokens":1024}` |
| --max-turns | 100 |
| --shallow-patrol-interval | 5 |
| --working-memory-adapter-mode | heuristic |
| --working-memory-backend | llm_assisted |
| --working-memory-model-client-mode | live |
| --seed | 1 |
| heartbeat / lease / guard / recovering | 30 / 120 / 1.0 / 0.5 |

Run id: `eva-20260528183617-db1f7d` (started 2026-05-28T18:36:17Z; ended ~19:17:27Z; ~41 min)

## Artifact summary

| File / dir | Count | Notes |
|---|---:|---|
| `llm_transcripts/dlPFC/turn-*.json` | 98 | one per LLM dlPFC call |
| `llm_transcripts/OFC_classical/turn-*.json` | 98 | one per assess_candidates pass |
| `deliberation_audit.jsonl` | 98 | one per deliberation turn |
| `cognitive_trace.jsonl` | 1581 | EVA_TRACE=1 events |
| `response_history.jsonl` | 3 | turns that produced an executed response |
| `llm_advisory_audit.jsonl` | 98 | all `advisory_source=builtin_heuristic_adapter` (no extra LLM) |

## Interface-audit checks (plan §7 acceptance — DATA INTEGRITY only)

| Check | Status |
|---|---|
| dlPFC transcript schema v1.1 | ✅ all 98 |
| OFC_classical transcript schema v1.1 | ✅ all 98 |
| 6 ontology section headers present in dlPFC system prompts | ✅ (verified turn-0, expected stable per hash check) |
| prompt_sections_present reflects 8 sections | ✅ all 8 True |
| 3 ontology hashes (PR-Β') stable across turns (no mid-run drift) | ✅ all 98 dlPFC: `ontology_hash=sha256:62080f49b3237b66` / `world_facts_hash=sha256:e611c400e958ee61` / `action_effect_schema_hash=sha256:3165852cb81a784c` (unique-count=1 each) |
| ScoreDecomposition present in OFC parsed_response.assessments[*] | ✅ (verified turn-0; OFC always parses ok) |
| mediator ReleaseToken 3-ref end-to-end (anchor / dlPFC / OFC) | ✅ deliberation_audit shows release_token with refs |
| Both transcript tracks coexist | ✅ 98 + 98 matched pairs |

## dlPFC LLM response status finding (NOT an interface failure — config observation for A)

| parse_status | count | meaning |
|---|---:|---|
| `transport_error` | 91 | chat_fn raised; 86× `RuntimeError: openai_compatible_response_empty_content` + 5× `TimeoutError` |
| `parse_error` | 3 | LLM returned non-JSON text |
| `ok` | 4 | LLM returned valid JSON with candidates |

**Root cause hypothesis**: `max_tokens=1024` (sourced from PR-5 EXTRA_PARAMS) was sized for the legacy 2-section system prompt (~1KB). Post-PR-Β the system prompt grew to ~12,849 chars (8 sections incl. role contract + drive ontology + action ontology + 102-cell effect schema + world facts). With `thinking=enabled / reasoning_effort=high`, the model spends the 1024-token budget on `reasoning_content` and emits empty `content`.

**Evidence**: first 4-5 turns succeeded (early turns have shorter `state_packet` / fewer messages), then the pattern flips to consistent empty-content from turn ~5 onward.

**Impact on interface-audit purpose (per plan §7 ❌ list)**: this is precisely the kind of data B is **NOT supposed to judge** behaviorally — it tells us nothing about Crafter quality / EVA stability / LLM decision quality / OFC scoring. It DOES tell us:
- ✅ prompts were assembled correctly (all 98 captured with full 6 sections)
- ✅ R3 swallow path worked end-to-end (production never crashed)
- ✅ transport-error code path produces well-formed transcripts (`errors` array populated)

**Suggestion for A**: increase `max_tokens` to 4096+ when re-running for behavioral analysis (NOT this PR — leave that decision to A per plan §8 analysis path "①/②/③").

## §8 analysis checklist coverage status (B side)

| §8 item | B side reportable | Notes |
|---|---|---|
| ① data completeness — 8 prompt sections | ✅ verifiable | A reads dlPFC transcript |
| ② ontology clarity — drive/salience/action/effect texts | ✅ verifiable | A reads CRAFTER_SCENARIO_ONTOLOGY texts |
| ③ dlPFC reasoning feasibility from transcript alone | ⚠️ partial | only 4 LLM responses with content; A can read the 4 ok cases + prompts to judge feasibility |
| ④ OFC ↔ dlPFC alignment | ⚠️ degraded | OFC ran on stub raw-action candidates (post-empty-content); A can still inspect ScoreDecomposition arithmetic |
| ⑤ mediator release ↔ OFC top-score | ✅ verifiable | deliberation_audit has both |
| ⑥ cross-turn reason diversity | ⚠️ limited sample | only 4 reasons available |

## Red lines verified (plan §9)

- ✅ R1 OFC scoring untouched (run used existing assess_candidates math)
- ✅ R2 anchor / dlPFC reasoning unchanged
- ✅ R3 transcript write/transport errors swallowed; run completed normally (exit code 0)
- ✅ R4 ran with EVA_LLM_TRANSCRIPT=raw — off path unaffected (FileBasedSink only created when env=raw)
- ✅ R5 Linux untouched (run is Crafter scenario)
- ✅ R6 dlPFC prompt contains role/drive/salience/action/effect/world_facts — no OFC formula leaked
- ✅ R7 ontology text used is PR-Β / §5.4 草稿 (A-authored, hash stable)
- ✅ R8 this report does NOT evaluate decision quality

## What this run unlocks

Plan §8 A-side analysis can proceed on the captured prompts + OFC assessments, with the caveat noted above on §8 items ③④⑥.
