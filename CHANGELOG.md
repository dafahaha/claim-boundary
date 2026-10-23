# Changelog — claim-boundary

v1.6.1 — 2026-10-23

## Round-11 independent clean review (fresh reviewer, cold reading)
- P2-1 (fixed): manifest arms/envs are normalized (stripped) after validation,
  so the validation口径 and the later comparison口径 match. `" baseline "` and
  `"baseline"` are one arm (no false suppression of the no-arm gate), and
  `" CartPole-v1 "` matches a declared CartPole-v1 token (no false
  env-not-declared).
- Suite: 59 pytest (1 added).

v1.6.0 — 2026-10-23
- P2-1 (fixed): the no-arm FAIL and low-n WARN are checked independently.
- P2-2 (fixed): a draft seed count when the manifest omits seeds is a WARN.
- P2-5 (fixed): blank/whitespace arm or env strings are rejected.
- Suite: 58 pytest.

v1.5.0 — 2026-10-23

## Round-9 independent clean review (fresh reviewer, cold reading)
- P1-1 (fixed): the superiority, robustness, and universal rules now iterate
  every match. A negated first phrase ("we do not outperform A") no longer
  suppresses a later non-negated claim on the same line ("...; our method
  outperforms B").
- P2-1 (fixed): universal wording covers "any environment", "any/all
  settings", "all domains", "works in any".
- P2-4 (fixed): a negated env token ("did not test CartPole-v1") is not an
  undeclared-env warning.
- Kept as intentional (P2-5): a line mentioning several seed counts passes
  when any non-negated count equals the manifest; requiring exact set
  equality would false-positive on lines comparing different experiments.
- Suite: 55 tests (4 added).

v1.4.0 — 2026-10-23

## Round-8 independent clean review (fresh reviewer, cold reading)
- P1-1 (fixed): the robustness rule now applies the same negation check as the
  others, so "we did not observe stable performance across seeds" is not a
  robustness FAIL.
- P1-2 (fixed): the no-difference rule now covers generic improvement wording
  (improve/improved/gain/better/boost and 提升/改进/进步/提高/改善), not only
  superiority words.
- P2-1 (fixed): Chinese negation expanded (并未/未曾/毫不/绝非).
- P2-2 (fixed): negation/qualification windows are clause-bounded and shorter,
  so a negation in a previous sentence cannot suppress a claim in the next.
- P2-3 (fixed): seed-count matching ignores negated mentions ("did not use 5
  seeds").
- P2-4 (fixed): an unpaired inline-code opener truncates the rest of the line.
- P2-6 (fixed): arms are deduplicated case-insensitively, so
  ["baseline","baseline"] counts as fewer than two arms.
- P2-7 (fixed): null-wording applies negation; an unexpected error still
  yields a clean exit 1 rather than a traceback.
- Suite: 51 tests (9 added).

v1.3.0 — 2026-10-23

## Round-7 independent clean review (fresh reviewer, cold reading)
- Negated superiority/universal phrases ("does not outperform", "not all
  environments") and narrowed universal phrases ("all environments listed in
  Table 1") are no longer flagged.
- Unknown manifest fields are now rejected (a typo such as "seed" was silently
  ignored and then filled with a default).
- Suite: 42 tests (4 added).

v1.2.1 — 2026-10-23

## Round-6 independent clean review (fresh reviewer, cold reading)
- No changes: a fresh reviewer found 0 P0/P1/P2 and confirmed the bool-as-int
  guard, strict-boolean no_difference, code-block stripping, exit-code ordering
  and fail-closed handling. Suite stays at 38.

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
