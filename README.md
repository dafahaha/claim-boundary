# claim-boundary

**Gate a research draft's wording against what you actually measured.** A JSON
manifest records seeds, comparison arms, envs and whether a difference was
observed; the scanner flags line by line the claims that cross that boundary:
superiority without a comparison arm, "stable across seeds" below n=3, universal
extrapolation, seed-count mismatch, and a null result packaged as a win.

Pure Python standard library, offline, bilingual EN/ZH phrase list.

> **Scope note up front:** the phrase list covers known overclaim patterns, not
> every creative rewording; it is a deterministic backstop, not a semantic
> reviewer. Every finding needs human review — lexicon tools produce false
> positives.

## Why this exists

AI writing assistants and researchers upgrade wording faster than they upgrade
evidence: "outperforms", "generalizes to all", "stable across seeds" appear even
when only one arm, one seed, or no observed difference exists. claim-boundary is
a deterministic pre-submission gate, not a style rewriter.

## Install

No build, no dependencies.

- Claude Code (from GitHub, personal marketplace):

  ```bash
  claude plugin marketplace add dafahaha/claim-boundary
  claude plugin install claim-boundary@dafahaha-skills
  ```

  In a session: `/plugin marketplace add dafahaha/claim-boundary`, then
  `/plugin install claim-boundary@dafahaha-skills`.
- Claude Code (local development): `claude --plugin-dir ./claim-boundary`.
- Portable skill (Codex/Cursor/Gemini CLI/Roo Code): copy
  `skills/claim-boundary/` into the client's skills directory.

## Usage

```bash
python skills/claim-boundary/scripts/claim_boundary.py draft.md \
  --manifest scope.json [--json] [--output report.md]
```

Manifest (`assets/example-manifest.json`):

```json
{
  "seeds": 3,
  "envs": ["CartPole-v1"],
  "arms": ["method", "baseline"],
  "no_difference": false
}
```

### Exit codes

| code | meaning |
|---|---|
| 0 | clean |
| 2 | warnings (low-n superiority, undeclared env, manifest inconsistency) |
| 3 | failures (overclaim, extrapolation, mismatch, null-as-win) |
| 1 | usage / IO / malformed manifest |

## Related work

- [q1-reviewer-mcp](https://pypi.org/project/q1-reviewer-mcp/) is an LLM-driven
  Q1 Reviewer#2 simulator (red-flag matrix, overclaiming, n<3 replicates,
  absolute language); it depends on a host LLM, is biomedical-oriented, and does
  not read a machine-readable manifest. [OVER_CLAIM_GUARD](https://bahayonghang.github.io/academic-writing-skills/skills/typst-paper/resources/references/OVER_CLAIM_GUARD.html)
  is a static wording-replacement table with no manifest cross-check and no exit
  code. This tool complements them: deterministic, offline, bilingual, it
  reconciles draft wording against a JSON manifest field by field and exits with
  a code CI can gate on.
- Pairs with [seedlot](https://github.com/dafahaha/seedlot): seedlot checks the
  numbers (n, mean, CI, overlap), claim-boundary checks the wording against the
  declared measured scope — an "honest reporting" two-step.

## Tests

```bash
python -m pytest tests/ -q
```

38 tests, stdlib only; manual predicate-mutation spot checks (inverting the R1
arm gate turns the superiority tests red; recorded in CHANGELOG).

## Limits (honest)

- Lexicon-based: known phrases only, not every creative overclaim; expect false
  positives and read each finding before acting on it.
- Trusts the manifest; it cannot verify the runs happened.
- Not a statistical test, not a semantic reviewer, and not a copyeditor; every
  finding requires human judgment.

## License

MIT, © 2026 Daizhi Liao (dafahaha).
