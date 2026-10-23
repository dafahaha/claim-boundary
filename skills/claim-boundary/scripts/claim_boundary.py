#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claim-boundary — gate a research draft's wording against a declared measured scope.

Given a JSON manifest of what was actually measured (seeds, envs, arms, whether
a difference was observed) and a draft Markdown file, flag line by line:

  * superiority wording with no comparison arm declared;
  * seed/robustness claims below n=3;
  * a claimed seed count that disagrees with the manifest;
  * universal extrapolation ("all environments", "generalizes to every task");
  * improvement wording when the manifest records no observed difference.

Pure standard library. Offline. It checks wording vs the manifest; it does not
fact-check the experiments themselves and does not rewrite prose.

Exit codes:
    0  clean
    2  warnings
    3  failures
    1  usage / IO / malformed manifest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Finding:
    line: int
    severity: str          # "FAIL" | "WARN"
    rule: str
    message: str
    suggestion: str


# --------------------------------------------------------------------------- #
# Rule patterns (bilingual EN/ZH; deterministic regex, no LLM)
# --------------------------------------------------------------------------- #

SUPERIORITY = re.compile(
    r"(\bsignificantly outperform\w*|\boutperform\w*|\bbeats?\b|\bsuperior to\b|"
    r"\bstate[- ]of[- ]the[- ]art\b|\bSOTA\b|"
    r"显著优于|全面超越|明显胜过|超越基线)",
    re.IGNORECASE,
)
SEED_ROBUST = re.compile(
    r"(stable across seeds|robust across seeds|multiple seeds|several seeds|averaged over seeds|"
    r"多种子|种子间稳定|鲁棒)",
    re.IGNORECASE,
)
UNIVERSAL = re.compile(
    r"(all environments|every environment|any task|generalizes? to (all|every|any)|universally|"
    r"across all tasks|all tasks|所有环境|任意任务|泛化到所有|通用普适)",
    re.IGNORECASE,
)
SEED_COUNT_EN = re.compile(r"(\d+)\s*seeds?", re.IGNORECASE)
SEED_COUNT_ZH = re.compile(r"(\d+)\s*个?种子")
NO_DIFF_WORDS = re.compile(r"(no (observed )?difference|no improvement|failed to improve|未观察到差异|无提升)", re.IGNORECASE)
# Gym-style env token with a version suffix, e.g. CartPole-v1, Humanoid-v2.
ENV_TOKEN = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*-v\d+)\b")
FENCE = re.compile(r"^\s*```")
INLINE_CODE = re.compile(r"`[^`]*`")
# Negation within a short window before a flagged keyword (a word-based gate
# cannot parse grammar, but "does not outperform" / "not all environments" must
# not be flagged as a positive claim).
NEGATION_RE = re.compile(
    r"(?:\b(?:do|does|did|will|would|can|could|should|is|are|was|were)?\s*not\b|"
    r"\bno\b|\bnever\b|\bwithout\b|n't\b|并不|并非|没有|不能|不会|不应|不可|无法|没有)",
    re.IGNORECASE,
)
# A qualification just after a universal phrase that narrows it to a list.
QUALIFY_RE = re.compile(
    r"(listed|shown|in table|in the (?:table|manifest|appendix)|above|measured|evaluated)",
    re.IGNORECASE,
)
# Fields allowed in the manifest; anything else is a typo and must not be
# silently ignored (e.g. "seed" instead of "seeds").
MANIFEST_KEYS = {"seeds", "envs", "arms", "no_difference"}


def _is_negated(line: str, start: int) -> bool:
    return bool(NEGATION_RE.search(line[max(0, start - 40):start]))


def _is_qualified(line: str, end: int) -> bool:
    return bool(QUALIFY_RE.search(line[end:end + 40]))


def strip_code(text: str) -> tuple[list[str], bool]:
    """Return (cleaned_lines, unclosed_fence). Fenced blocks and inline code are
    blanked while line numbers are preserved. `unclosed_fence` is True when the
    scan ended inside a ``` block (a dangling opener); the caller warns rather
    than silently dropping the trailing lines."""
    cleaned: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            cleaned.append("")
            continue
        if in_fence:
            cleaned.append("")
        else:
            cleaned.append(INLINE_CODE.sub("", line))
    return cleaned, in_fence


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    # Reject unknown fields up front so a typo (e.g. "seed" for "seeds") is not
    # silently ignored and then filled with a default.
    unknown = sorted(set(data) - MANIFEST_KEYS)
    if unknown:
        raise ValueError(
            f"unknown manifest field(s) {unknown}; expected one of {sorted(MANIFEST_KEYS)}"
        )
    data.setdefault("seeds", 0)
    data.setdefault("envs", [])
    data.setdefault("arms", [])
    data.setdefault("no_difference", False)
    # bool is a subclass of int; reject it explicitly so `"seeds": true` is
    # not silently read as seeds=1.
    if not isinstance(data["seeds"], int) or isinstance(data["seeds"], bool) or data["seeds"] < 0:
        raise ValueError("manifest.seeds must be a non-negative integer")
    if not isinstance(data["arms"], list) or not all(isinstance(a, str) for a in data["arms"]):
        raise ValueError("manifest.arms must be a list of arm-name strings")
    if not isinstance(data["envs"], list) or not all(isinstance(e, str) for e in data["envs"]):
        raise ValueError("manifest.envs must be a list of strings")
    # no_difference must be a real boolean; the string "false" is truthy and a
    # numeric 0 would be neither False nor True, so validate explicitly.
    if not isinstance(data["no_difference"], bool):
        raise ValueError("manifest.no_difference must be a boolean")
    return data


def scan_line(line: str, lineno: int, manifest: dict) -> list[Finding]:
    out: list[Finding] = []
    seeds = manifest["seeds"]
    arms = manifest["arms"]

    # R1: superiority wording (a negated phrase such as "does not outperform"
    # is not a superiority claim).
    sup = SUPERIORITY.search(line)
    if sup and not _is_negated(line, sup.start()):
        if len(arms) < 2:
            out.append(Finding(
                lineno, "FAIL", "superiority-no-arm",
                "superiority wording appears but the manifest declares fewer than two arms to compare",
                "either add the baseline arm to the manifest or soften to 'on this setup'",
            ))
        elif seeds < 3:
            out.append(Finding(
                lineno, "WARN", "superiority-low-n",
                f"superiority wording rests on n={seeds} seed(s); reviewers usually require >=3",
                "report the seed-level distribution and CI instead of a comparative adjective",
            ))

    # R2: seed/robustness claim below n=3
    if SEED_ROBUST.search(line) and seeds < 3:
        out.append(Finding(
            lineno, "FAIL", "robustness-below-n3",
            f"robustness/stable wording but manifest seeds={seeds} (<3)",
            "run more seeds or remove 'stable/robust/multiple seeds' wording",
        ))

    # R3: universal extrapolation; a negated ("not all environments") or
    # narrowed ("all environments listed in Table 1") phrase is not extrapolation.
    uni = UNIVERSAL.search(line)
    if uni and not _is_negated(line, uni.start()) and not _is_qualified(line, uni.end()):
        out.append(Finding(
            lineno, "FAIL", "universal-scope",
            "universal extrapolation ('all/every/any/generalizes to') beyond measured scope",
            "name the exact env/scale measured; state what was NOT tested",
        ))

    # R4: claimed seed count disagrees with manifest. A line may mention several
    # numbers (a quick look over the full run); the claim matches the manifest
    # when ANY mentioned seed count equals it.
    mentioned = [int(m.group(1)) for m in SEED_COUNT_EN.finditer(line)]
    mentioned += [int(m.group(1)) for m in SEED_COUNT_ZH.finditer(line)]
    if seeds > 0 and mentioned and seeds not in mentioned:
        out.append(Finding(
            lineno, "FAIL", "seed-count-mismatch",
            f"draft mentions {mentioned} seed(s) but manifest declares {seeds}",
            "align the number with the actual runs; do not round up",
        ))

    # R5: improvement wording while manifest records no difference. A negated
    # phrase is consistent with the null result, so it is not flagged.
    if manifest["no_difference"] and sup is not None and not _is_negated(line, sup.start()):
        out.append(Finding(
            lineno, "FAIL", "no-difference-claimed",
            "manifest records no observed difference, yet improvement wording appears",
            "report the null result honestly; do not package it as a win",
        ))

    # R6: draft itself admits no difference but pairs it with superiority elsewhere
    if NO_DIFF_WORDS.search(line) and manifest["no_difference"] is False:
        out.append(Finding(
            lineno, "WARN", "null-wording-vs-manifest",
            "draft mentions no difference but manifest.no_difference is false; check consistency",
            "set no_difference=true if that is what the data show",
        ))

    # R7: a versioned env token not declared in manifest.envs
    declared = {e.lower() for e in manifest["envs"]}
    for tok in ENV_TOKEN.findall(line):
        if tok.lower() not in declared:
            out.append(Finding(
                lineno, "WARN", "env-not-declared",
                f"env token {tok!r} appears but is not listed in manifest.envs {manifest['envs']}",
                "add it to the manifest if measured, or remove the name if not",
            ))
    return out


def scan_text(text: str, manifest: dict) -> list[Finding]:
    findings: list[Finding] = []
    cleaned, unclosed = strip_code(text)
    for lineno, line in enumerate(cleaned, start=1):
        findings.extend(scan_line(line, lineno, manifest))
    if unclosed:
        last = len(cleaned)
        findings.append(Finding(
            last, "WARN", "unclosed-fence",
            "fenced block opened but never closed; lines after the last ``` were skipped",
            "close the ``` fence so all prose is checked",
        ))
    return findings


def format_report(findings: list[Finding], draft: str, manifest_path: str) -> str:
    lines = ["# claim-boundary report", ""]
    lines.append(f"- draft: {draft}")
    lines.append(f"- manifest: {manifest_path}")
    fails = [f for f in findings if f.severity == "FAIL"]
    warns = [f for f in findings if f.severity == "WARN"]
    lines.append(f"- FAIL: {len(fails)}  WARN: {len(warns)}")
    lines.append("")
    if not findings:
        lines.append("No boundary violations found.")
    for f in findings:
        lines.append(f"- [{f.severity}] L{f.line} ({f.rule}): {f.message}")
        lines.append(f"    -> {f.suggestion}")
    return "\n".join(lines) + "\n"


class _Parser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors exit 1 (argparse default is 2, which
    collides with the WARN exit code). --help still exits 0."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    ap = _Parser(description="Gate draft wording against a measured-scope manifest (stdlib).")
    ap.add_argument("draft", help="Markdown draft file")
    ap.add_argument("--manifest", required=True, help="JSON measured-scope manifest")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)

    try:
        manifest = load_manifest(Path(args.manifest))
        text = Path(args.draft).read_text(encoding="utf-8-sig")
        findings = scan_text(text, manifest)
        if args.json:
            rendered = json.dumps(
                {"findings": [asdict(f) for f in findings]}, indent=2, ensure_ascii=False
            )
        else:
            rendered = format_report(findings, args.draft, args.manifest)
        # Output writing stays inside the try so a bad path is a clean exit 1.
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
    except (ValueError, OSError) as exc:
        print(f"claim-boundary: error: {exc}", file=sys.stderr)
        return 1

    if any(f.severity == "FAIL" for f in findings):
        return 3
    if findings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
