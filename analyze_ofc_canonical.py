#!/usr/bin/env python3
"""PR-O3 canonical-run analyzer — OFC dlpfc-rank behavior from a runtime dir.

Reads ``<runtime_dir>/deliberation_audit.jsonl`` and reports the PR-O2/O3
acceptance signals, contrasted with the T3 baseline (62% flat-tie withholds that
lost the dlPFC order):

  - LLM-candidate coverage (dlPFC producer actually drove the run)
  - dlpfc_term active rate (PR-O2 rank wired into the score)
  - **dlPFC rank respect rate** = rank0 (dlPFC top pick) released / multi-candidate
    deliberations — the core fix (T3 lost this to a candidate_id alphabetical tiebreak)
  - withhold rate (default inhibition; should be far below T3's 62%)
  - release-action distribution + per-deliberation score/term trace

Pure-offline (no LLM). Usage:
    python analyze_ofc_canonical.py <runtime_dir> [--trace]
"""

from __future__ import annotations

import collections
import json
import sys


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "n/a"


def analyze(runtime_dir: str, trace: bool = False) -> None:
    path = f"{runtime_dir.rstrip('/')}/deliberation_audit.jsonl"
    rows = [json.loads(line) for line in open(path)]
    n = len(rows)

    llm_cov = sum(
        1 for d in rows
        if any(c.get("parameter_domain", {}).get("dlpfc_proposal_ref") for c in d["candidates"])
    )
    dlpfc_active = sum(
        1 for d in rows
        if any((a.get("score_decomposition") or {}).get("dlpfc_term", 0) > 0 for a in d["assessments"])
    )

    released = [d for d in rows if d["release_decision"].get("selected_action")]
    withhold = n - len(released)
    actions: collections.Counter = collections.Counter()
    multi = rank0 = 0
    for d in rows:
        sel = d["release_decision"].get("selected_action")
        cands = d["candidates"]
        if sel:
            actions[sel] += 1
            if len(cands) > 1:  # tiebreak only matters with >1 candidate
                multi += 1
                if cands[0].get("action") == sel:  # cands[0] == dlPFC rank0
                    rank0 += 1

    print(f"# PR-O3 canonical analysis — {runtime_dir}\n")
    print(f"- deliberations: **{n}**")
    print(f"- LLM-candidate coverage: {llm_cov}/{n} ({_pct(llm_cov, n)}) — dlPFC producer drove the run")
    print(f"- dlpfc_term active: {dlpfc_active}/{n} ({_pct(dlpfc_active, n)}) — PR-O2 rank wired into score")
    print(f"- release: {len(released)} | withhold: {withhold} ({_pct(withhold, n)}) — vs T3 baseline ~62% withhold")
    print(f"- **dlPFC rank respected (rank0 released): {rank0}/{multi} ({_pct(rank0, multi)})** — vs T3 62% flat-tie lost order")
    print(f"- release-action distribution: {dict(actions)}")

    if trace:
        print("\n## per-deliberation trace\n")
        for i, d in enumerate(rows):
            cands = d["candidates"]
            sel = d["release_decision"].get("selected_action") or "WITHHOLD"
            terms = [round((a.get("score_decomposition") or {}).get("dlpfc_term", 0), 3) for a in d["assessments"]]
            scores = [round(a.get("score", 0), 3) for a in d["assessments"]]
            acts = [c.get("action") for c in cands]
            print(f"- delib{i}: acts={acts} scores={scores} dlpfc_terms={terms} -> {sel}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    analyze(args[0] if args else ".", trace="--trace" in sys.argv)
