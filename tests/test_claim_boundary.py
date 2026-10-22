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
