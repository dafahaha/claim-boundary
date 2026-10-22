---
name: claim-boundary
description: Check a research draft's claims against a JSON manifest of what was actually measured (seeds, arms, envs, null result). Use when the user is writing a results section, paper paragraph, README benchmark claim, or ablation summary and wants to catch unsupported superiority wording, "stable across seeds" below n=3, universal extrapolation ("all environments/generalizes to every task"), seed-count mismatch, or a null result packaged as a win. Deterministic regex rules, line-level findings, offline.
license: MIT
compatibility: Python 3.10+, stdlib only; offline; Windows/macOS/Linux; needs a draft Markdown file and a JSON scope manifest.
---

# claim-boundary — wording vs measured scope

## When to activate

- The user drafted results text and wants a pre-submission honesty pass.
- The user asks "can I say this beats the baseline / generalizes / is stable?".
- There is (or can be) a short JSON manifest of what was actually run.

Do not use this to fact-check experiments, run statistics, or rewrite prose; it
compares wording to the manifest and reports line-level findings. The phrase list
is a known-pattern backstop, not an exhaustive semantic reviewer; every finding
needs human review because lexicon matching can false-positive.

## Steps

1. Build the manifest from what was actually run (see `assets/example-manifest.json`):

```json
{
  "seeds": 3,
  "envs": ["CartPole-v1"],
  "arms": ["method", "baseline"],
  "no_difference": false
}
```

2. Run:

```bash
python skills/claim-boundary/scripts/claim_boundary.py draft.md \
  --manifest scope.json [--json] [--output report.md]
```

3. Triage findings:
   - **FAIL (exit 3):** superiority with no comparison arm; robustness below n=3;
     universal extrapolation; seed-count mismatch; improvement wording on a null result.
   - **WARN (exit 2):** superiority at n<3; env token not declared; null wording
     inconsistent with the manifest.
4. Fix wording or, better, fix the missing measurement before publishing.

## Rules (deterministic, bilingual EN/ZH)

| rule | triggers | severity |
|---|---|---|
| superiority-no-arm | outperforms/beats/SOTA with <2 arms declared | FAIL |
| superiority-low-n | superiority wording at seeds<3 | WARN |
| robustness-below-n3 | "stable/robust/multiple seeds" with seeds<3 | FAIL |
| universal-scope | "all environments/generalizes to any task/通用普适" | FAIL |
| seed-count-mismatch | draft seed count != manifest | FAIL |
| no-difference-claimed | improvement wording while no_difference=true | FAIL |
| null-wording-vs-manifest | draft says "no difference" but manifest.no_difference=false | WARN |
| env-not-declared | versioned env token (e.g. Hopper-v3) absent from manifest | WARN |

Fenced code blocks and inline code are skipped so identifiers do not false-positive.

## Boundaries

- Lexicon-based: it catches known phrases, not every creative overclaim; expect
  false positives and read each finding before acting.
- It trusts the manifest; it cannot verify the runs happened.
- Not a substitute for reviewer judgment or a real statistical test.
- LLM semantic reviewers (e.g. q1-reviewer-mcp) and static tables
  (OVER_CLAIM_GUARD) cover different ground; this tool reconciles wording against
  a JSON manifest offline. Pair with seedlot, which checks the numbers (n, mean,
  CI) while this checks the wording — an honest-reporting two-step.
