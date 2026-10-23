# Changelog — claim-boundary

v1.2.0 — 2026-10-23

## Round-5 independent technical review (fresh reviewer, cold reading)
- P1-1 (fixed): argparse usage errors (missing positional/--manifest, invalid
  type) exited 2, colliding with the WARN exit code; a custom parser now exits 1
  for usage errors (--help still exits 0).
- P2-1 (fixed): broadened the CLI catch to OSError (PermissionError, etc.).
- P2-2 (fixed): `no_difference` is now validated as a real boolean (the string
  "false" is truthy and would otherwise be treated as a null result).
- P2-3 (fixed): `--output` write is inside the try (clean exit 1 on bad path).
- P2-4 (fixed): `arms` elements must be strings (e.g. `[null, null]` no longer
  counts as a two-arm comparison).
- New tests: no_difference bool, arms elements, usage exit 1. Suite: 35 -> 38.

v1.0.0 — 2026-10-22

## v1 (baseline)
- JSON manifest (seeds/envs/arms/no_difference); R1 superiority-no-arm, R2
  robustness-below-n3, R3 universal-scope, R4 seed-count-mismatch, R5
  no-difference-claimed, R6 null-wording inconsistency; Markdown + `--json`;
  exit codes; 21 tests green.

## v2 (declared-env cross-check) — quality issue: drafts name an env that was
never in the manifest with no signal.
- R7 flags a versioned env token (`Name-vN`) absent from `manifest.envs` (WARN,
  case-insensitive); new tests cover declared match and undeclared token.

## v3 (code-awareness) — quality issue: code identifiers like `outperforms()`
inside fences/backticks false-positived as claims.
- `strip_code()` blanks fenced blocks and inline code while preserving line
  numbers; new tests for fenced block and inline code.

## v4 (manifest validation)
- Malformed/non-object manifest, negative seeds, non-list arms exit 1 with clear
  messages; defaults applied; tests cover each validation branch.

## v5 (spec compliance + manual mutation spot check)
- Frontmatter limited to spec fields; manifest example shipped in `assets/`;
  README states lexicon limits honestly.
- Manual predicate-mutation spot check: inverted R1 arm gate (`<2` -> `>=2`) ->
  superiority tests red; reverted, full suite green (25). No automated
  mutation-testing framework is configured.

## Round-1 independent review fixes (v1.1.0)
- P1-1: `beats?` now uses `\bbeats?\b` so heartbeat/offbeat prose no longer
  false-positives as superiority-no-arm; a real "beats the baseline" still FAILs.
- P2-1: R4 seed count collects ALL numbers on a line (any equal to the manifest
  passes; only all-different FAILs) and adds the Chinese `(\d+)个?种子` pattern.
- P2-2: an unclosed ``` fence at EOF emits an `unclosed-fence` WARN instead of
  silently swallowing trailing prose.
- P2-3: `manifest.envs` non-list raises a clean ValueError -> exit 1 instead of a
  TypeError traceback.
- P3-1: draft and manifest read as utf-8-sig so a BOM does not corrupt the first
  token.
- Product: phrase-list non-exhaustive scope note moved to the README front; added
  Related work (q1-reviewer-mcp, OVER_CLAIM_GUARD); every finding flagged for
  human review / false-positive expectation; cross-named with seedlot as the
  honest-reporting pair; manual spot-check wording replaces "mutation-checked".
- New tests: heartbeat/offbeat benign, standalone beats, any-number seed match,
  all-different mismatch, Chinese match/mismatch, unclosed fence WARN, bad envs,
  BOM manifest. Suite: 25 -> 35.
