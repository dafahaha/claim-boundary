# -*- coding: utf-8 -*-
"""claim-boundary tests (pytest, stdlib only, no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "skills" / "claim-boundary" / "scripts" / "claim_boundary.py"
sys.path.insert(0, str(SCRIPT.parent))

import claim_boundary as cb  # noqa: E402


def _manifest(tmp: Path, **over) -> Path:
    base = {"seeds": 3, "envs": ["CartPole-v1"], "arms": ["method", "baseline"], "no_difference": False}
    base.update(over)
    p = tmp / "scope.json"
    p.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
    return p


def _draft(tmp: Path, text: str) -> Path:
    p = tmp / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# manifest
# --------------------------------------------------------------------------- #

def test_load_manifest_defaults(tmp_path: Path):
    p = _manifest(tmp_path, seeds=5, arms=[])
    m = cb.load_manifest(p)
    assert m["seeds"] == 5 and m["envs"] == ["CartPole-v1"] and m["no_difference"] is False


def test_manifest_bad_seeds_raises(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"seeds": -2}), encoding="utf-8")
    with pytest.raises(ValueError, match="seeds"):
        cb.load_manifest(p)


def test_manifest_bool_seeds_rejected(tmp_path: Path):
    # bool is an int subclass; `"seeds": true` must not silently become seeds=1.
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"seeds": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="seeds"):
        cb.load_manifest(p)


def test_manifest_bad_arms_raises(tmp_path: Path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"arms": "method"}), encoding="utf-8")
    with pytest.raises(ValueError, match="arms"):
        cb.load_manifest(p)


# --------------------------------------------------------------------------- #
# rules
# --------------------------------------------------------------------------- #

def test_superiority_no_arm_is_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_line("Our method outperforms the baseline.", 2, m)
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_superiority_two_arms_low_n_warns(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=2))
    findings = cb.scan_line("Our method outperforms the baseline.", 2, m)
    assert any(f.rule == "superiority-low-n" and f.severity == "WARN" for f in findings)


def test_superiority_two_arms_n3_clean(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_line("Our method outperforms the baseline on this setup.", 2, m)
    assert findings == []


def test_robustness_below_n3_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=1))
    findings = cb.scan_line("The result is stable across seeds.", 4, m)
    assert any(f.rule == "robustness-below-n3" for f in findings)


def test_universal_scope_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_line("This generalizes to all environments.", 4, m)
    assert any(f.rule == "universal-scope" for f in findings)


def test_chinese_universal_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_line("该方法泛化到所有任务，通用普适。", 4, m)
    assert any(f.rule == "universal-scope" for f in findings)


def test_seed_count_mismatch_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=3))
    findings = cb.scan_line("Trained over 5 seeds.", 3, m)
    assert any(f.rule == "seed-count-mismatch" for f in findings)


def test_seed_count_match_clean(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=3))
    assert cb.scan_line("Trained over 3 seeds.", 3, m) == []


def test_no_difference_plus_superiority_fail(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, no_difference=True))
    findings = cb.scan_line("Our method significantly outperforms.", 2, m)
    assert any(f.rule == "no-difference-claimed" for f in findings)


def test_null_wording_without_manifest_flag_warns(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, no_difference=False))
    findings = cb.scan_line("We observed no difference versus baseline.", 2, m)
    assert any(f.rule == "null-wording-vs-manifest" and f.severity == "WARN" for f in findings)


def test_scan_text_reports_line_numbers(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("intro line\nOutperforms everyone.\n", m)
    assert findings and findings[0].line == 2


def test_env_token_not_declared_warns(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_line("We also ran on Hopper-v3.", 5, m)
    assert any(f.rule == "env-not-declared" for f in findings)


def test_declared_env_case_insensitive_clean(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, envs=["cartpole-v1"]))
    assert cb.scan_line("Tested on CartPole-v1.", 5, m) == []


def test_fenced_block_skipped(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    text = "Intro.\n```\nThis outperforms everything and generalizes to all.\n```\nDone.\n"
    assert cb.scan_text(text, m) == []


def test_inline_code_skipped(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("Call the `outperforms()` helper here.", m)
    assert findings == []


def test_negated_superiority_not_flagged(tmp_path: Path):
    # "does not outperform" is not a superiority claim.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("Our method does not significantly outperform the baseline.", m)
    assert findings == []


def test_negated_universal_not_flagged(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_text("We do not claim to cover all environments.", m)
    assert findings == []


def test_qualified_universal_not_flagged(tmp_path: Path):
    # "all environments listed in Table 1" is narrowed, not extrapolated.
    m = cb.load_manifest(_manifest(tmp_path))
    findings = cb.scan_text("All environments listed in Table 1 use the same wrapper.", m)
    assert findings == []


def test_comma_bounds_negation_previous_clause(tmp_path: Path):
    # P1: a negation before a half-width comma must not suppress a claim in the
    # next clause ("we do not rely on X, yet our model outperforms Y").
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text(
        "We do not rely on pre-training, yet our model outperforms the baseline.", m
    )
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_without_phrase_then_comma_claim_is_flagged(tmp_path: Path):
    # P1: "Without extra data, our method outperforms Y" — the comma separates
    # the prepositional phrase from the positive main clause.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("Without extra data, our method outperforms the baseline.", m)
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_fails_to_is_negation(tmp_path: Path):
    # "fails to outperform" is a negated claim, not a superiority statement.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    assert cb.scan_text("Our model fails to outperform the baseline.", m) == []


def test_tilde_fenced_block_skipped(tmp_path: Path):
    # CommonMark ~~~ fences must be stripped the same way as ``` fences.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    text = "Intro.\n~~~\nThis outperforms everything and generalizes to all.\n~~~\nDone.\n"
    assert cb.scan_text(text, m) == []


def test_non_performance_understanding_not_flagged(tmp_path: Path):
    # R5: qualitative "gained a better understanding" is not a performance win.
    m = cb.load_manifest(_manifest(tmp_path, no_difference=True))
    findings = cb.scan_text("We gained a better understanding of the failure modes.", m)
    assert findings == []


def test_unknown_manifest_field_raises(tmp_path: Path):
    # A typo "seed" must not be silently ignored.
    p = tmp_path / "scope.json"
    p.write_text(json.dumps({"seed": 3, "envs": [], "arms": ["a", "b"], "no_difference": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown manifest field"):
        cb.load_manifest(p)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def test_cli_clean_exit_zero(tmp_path: Path, capsys):
    mp = _manifest(tmp_path)
    dp = _draft(tmp_path, "We trained 3 seeds on CartPole-v1 and report the distribution.")
    code = cb.main([str(dp), "--manifest", str(mp)])
    assert code == 0
    assert "No boundary violations" in capsys.readouterr().out


def test_cli_fail_exit_three(tmp_path: Path):
    mp = _manifest(tmp_path, arms=[])
    dp = _draft(tmp_path, "We outperform everyone, generalizing to all environments.")
    assert cb.main([str(dp), "--manifest", str(mp)]) == 3


def test_cli_warn_exit_two(tmp_path: Path):
    mp = _manifest(tmp_path, no_difference=False)
    dp = _draft(tmp_path, "We observed no difference versus baseline.")
    assert cb.main([str(dp), "--manifest", str(mp)]) == 2


def test_cli_malformed_manifest_exit_one(tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text("{not json", encoding="utf-8")
    dp = _draft(tmp_path, "hello")
    assert cb.main([str(dp), "--manifest", str(bad)]) == 1


def test_cli_missing_draft_exit_one(tmp_path: Path):
    mp = _manifest(tmp_path)
    assert cb.main([str(tmp_path / "nope.md"), "--manifest", str(mp)]) == 1


def test_cli_json_output(tmp_path: Path, capsys):
    mp = _manifest(tmp_path, arms=[])
    dp = _draft(tmp_path, "Outperforms everyone.")
    code = cb.main([str(dp), "--manifest", str(mp), "--json"])
    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"][0]["rule"] == "superiority-no-arm"


def test_cli_output_file(tmp_path: Path):
    mp = _manifest(tmp_path, arms=[])
    dp = _draft(tmp_path, "Outperforms everyone.")
    out = tmp_path / "report.md"
    code = cb.main([str(dp), "--manifest", str(mp), "--output", str(out)])
    assert code == 3
    assert "claim-boundary report" in out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Round-1 review fixes
# --------------------------------------------------------------------------- #

def test_heartbeat_offbeat_benign_no_false_positive(tmp_path: Path):
    # P1-1: \bbeats?\b must not fire inside heartbeat/offbeat prose (arms=[]).
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text(
        "The agent learns a steady heartbeat rhythm over time.\n"
        "The controller fell offbeat but recovered after retraining.\n",
        m,
    )
    assert not any(f.rule == "superiority-no-arm" for f in findings)


def test_standalone_beats_baseline_still_fails(tmp_path: Path):
    # P1-1: a real comparative "beats the baseline" with no arm must still fire.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_line("This baseline beats the previous tuning on this setup.", 3, m)
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_seed_count_any_mentioned_number_matches(tmp_path: Path):
    # P2-1: a line listing several numbers passes when the manifest count appears.
    m = cb.load_manifest(_manifest(tmp_path, seeds=5))
    assert cb.scan_line("We ran 3 seeds for a quick look over 5 seeds total.", 3, m) == []


def test_seed_count_all_mentioned_numbers_mismatch_fails(tmp_path: Path):
    # P2-1: fail only when NO mentioned count equals the manifest.
    m = cb.load_manifest(_manifest(tmp_path, seeds=5))
    findings = cb.scan_line("We compared 3 seeds and 4 seeds in this snippet.", 3, m)
    assert any(f.rule == "seed-count-mismatch" for f in findings)


def test_seed_count_chinese_phrase_matches(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=5))
    assert cb.scan_line("我们完整跑了 5 个种子。", 3, m) == []


def test_seed_count_chinese_mismatch_fails(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=5))
    findings = cb.scan_line("只跑了 3 个种子。", 3, m)
    assert any(f.rule == "seed-count-mismatch" for f in findings)


def test_unclosed_fence_warns_instead_of_silently_skipping(tmp_path: Path):
    # P2-2: a dangling ``` must WARN, not drop trailing prose silently.
    m = cb.load_manifest(_manifest(tmp_path))
    text = "Intro.\n```\nOutperforms everything and generalizes to all.\n"
    findings = cb.scan_text(text, m)
    assert any(f.rule == "unclosed-fence" and f.severity == "WARN" for f in findings)


def test_manifest_bad_envs_raises(tmp_path: Path):
    # P2-3: envs must be a list of strings, not a TypeError traceback.
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"envs": "CartPole-v1"}), encoding="utf-8")
    with pytest.raises(ValueError, match="envs"):
        cb.load_manifest(bad)


def test_manifest_bom_does_not_break_first_env(tmp_path: Path):
    # P3-1: utf-8-sig strips a BOM so the first env token matches.
    p = tmp_path / "m.json"
    payload = '{"seeds":3,"envs":["CartPole-v1"],"arms":["a","b"]}'
    p.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    m = cb.load_manifest(p)
    assert cb.scan_line("Tested on CartPole-v1.", 5, m) == []


# ---- R5 review: no_difference bool, arms elements, usage exit 1 ----

def test_manifest_no_difference_must_be_bool(tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"seeds": 3, "no_difference": "false"}), encoding="utf-8")
    with pytest.raises(ValueError, match="no_difference"):
        cb.load_manifest(bad)


def test_manifest_arms_must_be_strings(tmp_path: Path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"seeds": 3, "arms": [None, None]}), encoding="utf-8")
    with pytest.raises(ValueError, match="arms"):
        cb.load_manifest(bad)


def test_usage_error_exits_one():
    with pytest.raises(SystemExit) as e:
        cb.main([])
    assert e.value.code == 1
    with pytest.raises(SystemExit) as e:
        cb.main(["x"])  # missing required --manifest
    assert e.value.code == 1


# ---- R8 review fixes ----

def test_negated_robustness_not_flagged(tmp_path: Path):
    # P1-1: "did not observe stable ... across seeds" is not a robustness claim.
    m = cb.load_manifest(_manifest(tmp_path, seeds=1))
    findings = cb.scan_line("We did not observe stable performance across seeds.", 4, m)
    assert not any(f.rule == "robustness-below-n3" for f in findings)


def test_no_difference_generic_improvement_fails(tmp_path: Path):
    # P1-2: "we improved by 5%" with no_difference=true must FAIL.
    m = cb.load_manifest(_manifest(tmp_path, no_difference=True))
    findings = cb.scan_line("We improved the score by 5% over baseline.", 4, m)
    assert any(f.rule == "no-difference-claimed" and f.severity == "FAIL" for f in findings)


def test_no_difference_chinese_improvement_fails(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, no_difference=True))
    findings = cb.scan_line("我们提升了 5%。", 4, m)
    assert any(f.rule == "no-difference-claimed" for f in findings)


def test_duplicate_arms_count_as_one(tmp_path: Path):
    # P2-6: ["baseline","baseline"] is fewer than two distinct arms.
    m = cb.load_manifest(_manifest(tmp_path, arms=["baseline", "baseline"]))
    findings = cb.scan_line("Our method outperforms the baseline.", 2, m)
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_chinese_negation_superiority_not_flagged(tmp_path: Path):
    # P2-1: "并未显著优于" is not a superiority claim.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("我们的方法并未显著优于基线。", m)
    assert not any(f.rule == "superiority-no-arm" for f in findings)


def test_negated_seed_count_not_used(tmp_path: Path):
    # P2-3: "did not use 5 seeds" must not be treated as a claimed 5.
    m = cb.load_manifest(_manifest(tmp_path, seeds=3))
    findings = cb.scan_line("We did not use 5 seeds here.", 3, m)
    assert not any(f.rule == "seed-count-mismatch" for f in findings)


def test_cross_clause_negation_does_not_suppress(tmp_path: Path):
    # P2-2: a negation in the previous sentence must not suppress a claim.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("We did not test X. Our method outperforms the baseline.", m)
    assert any(f.rule == "superiority-no-arm" for f in findings)


def test_odd_inline_backtick_truncated(tmp_path: Path):
    # P2-4: an unpaired inline-code opener truncates the rest of the line.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_text("Use the `outperforms helper which outperforms everything.", m)
    assert not any(f.rule == "superiority-no-arm" for f in findings)


def test_missing_file_exits_one(tmp_path: Path):
    # P2-7: missing draft yields a clean exit 1, not a traceback.
    mp = _manifest(tmp_path)
    assert cb.main([str(tmp_path / "nope.md"), "--manifest", str(mp)]) == 1


def test_negated_first_match_does_not_suppress_later_claim(tmp_path: Path):
    # R9 P1: a negated first superiority phrase must not suppress a later
    # non-negated claim on the same line.
    m = cb.load_manifest(_manifest(tmp_path, arms=[]))
    findings = cb.scan_line(
        "We do not outperform A; our method outperforms B.", 1, m
    )
    assert any(f.rule == "superiority-no-arm" and f.severity == "FAIL" for f in findings)


def test_negated_first_robustness_keeps_later(tmp_path: Path):
    m = cb.load_manifest(_manifest(tmp_path, seeds=1))
    findings = cb.scan_line(
        "Not stable across seeds, but we used several seeds here.", 1, m
    )
    assert any(f.rule == "robustness-below-n3" for f in findings)


def test_universal_any_environment_variant(tmp_path: Path):
    # R9 P2-1: "works in any environment" / "any setting" is extrapolation.
    m = cb.load_manifest(_manifest(tmp_path))
    assert any(f.rule == "universal-scope" for f in cb.scan_line(
        "Our agent works in any environment.", 1, m))
    assert any(f.rule == "universal-scope" for f in cb.scan_line(
        "It is robust across all settings.", 1, m))


def test_negated_env_token_not_declared(tmp_path: Path):
    # R9 P2-4: "did not test CartPole-v1" is not an undeclared-env WARN.
    m = cb.load_manifest(_manifest(tmp_path, envs=[]))
    findings = cb.scan_line("We did not test CartPole-v1 here.", 1, m)
    assert not any(f.rule == "env-not-declared" for f in findings)


def test_blank_arm_and_env_strings_rejected(tmp_path: Path):
    # R10 P2-5: ["", "baseline"] must not count as two arms.
    with pytest.raises(ValueError):
        cb.load_manifest(_manifest(tmp_path, arms=["", "baseline"]))
    with pytest.raises(ValueError):
        cb.load_manifest(_manifest(tmp_path, envs=["   "]))


def test_low_n_warn_independent_of_no_arm(tmp_path: Path):
    # R10 P2-1: no-arm FAIL and low-n WARN are both reported.
    m = cb.load_manifest(_manifest(tmp_path, arms=[], seeds=1))
    findings = cb.scan_line("Our method outperforms the baseline.", 2, m)
    rules = {f.rule for f in findings}
    assert "superiority-no-arm" in rules
    assert "superiority-low-n" in rules


def test_seed_count_undeclared_warn(tmp_path: Path):
    # R10 P2-2: a draft seed count when manifest seeds=0 is a WARN, not ignored.
    m = cb.load_manifest(_manifest(tmp_path, seeds=0))
    findings = cb.scan_line("We ran 5 seeds.", 1, m)
    assert any(f.rule == "seed-count-undeclared" for f in findings)


def test_arms_envs_whitespace_normalized(tmp_path: Path):
    # R11 P2: " baseline " and "baseline" are one arm; " CartPole-v1 " matches.
    m = cb.load_manifest(_manifest(
        tmp_path, arms=[" Method ", " baseline "], envs=[" CartPole-v1 "]))
    assert len({a.lower() for a in m["arms"]}) == 2
    findings = cb.scan_line("We tested on CartPole-v1.", 1, m)
    assert not any(f.rule == "env-not-declared" for f in findings)
