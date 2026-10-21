"""Check and record the results of /turng-flow:review-task.

  review_record.py <manifest.json> <result.json> [<result.json> ...]

Checks that every quote in the results appears verbatim in the review input, merges the results of
all parts, appends the period to .turng-flow/reports/review-history.tsv and the counts to
.turng-flow/reports/metrics.tsv, and writes the merged results next to the manifest.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SECTIONS = ["rule_violations", "outside_approach", "corrections", "subagents_and_steps",
            "rule_files_without_approval", "decision_logs_in_work_mode"]
QUOTE_FIELDS = ["quote", "owner_quote", "agent_quote"]
CATEGORIES = ["analyze-solve", "review-own-work", "self-critique", "context-intent", "verify-reality", "scope",
              "owner-agent-split", "owner-pace", "clear-communication", "usable-handoff", "traceability",
              "root-cause", "context", "status", "risk", "other"]


def append_tsv(path: Path, header: list[str], row: list) -> None:
    if not path.exists():
        path.write_text("\t".join(header) + "\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\t".join(str(v) for v in row) + "\n")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corpus = "\n".join(Path(p).read_text(encoding="utf-8") for p in manifest["parts"])
    merged = {s: [] for s in SECTIONS}
    rejected = []
    for result_path in sys.argv[2:]:
        result = json.loads(Path(result_path).read_text(encoding="utf-8"))
        for section in SECTIONS:
            for item in result.get(section) or []:
                bad = [f for f in QUOTE_FIELDS if item.get(f) and item[f] not in corpus]
                if section == "corrections" and item.get("category") not in CATEGORIES:
                    bad.append(f"category {item.get('category')!r}")
                if bad:
                    rejected.append({"section": section, "item": item, "problems": bad})
                else:
                    merged[section].append(item)
    merged["rejected"] = rejected
    out = manifest_path.with_name(manifest_path.stem.replace("review-input", "review-result") + ".json")
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")

    reports = manifest_path.parent
    counts = Counter(c["category"] for c in merged["corrections"])
    append_tsv(reports / "review-history.tsv", ["since", "until", "result"],
               [manifest["since"] or "", manifest["until"], out.name])
    append_tsv(reports / "metrics.tsv", ["since", "until", "owner_messages", "corrections", "rate", *CATEGORIES],
               [manifest["since"] or "", manifest["until"], manifest["owner_messages"], len(merged["corrections"]),
                f"{len(merged['corrections']) / manifest['owner_messages']:.3f}" if manifest["owner_messages"] else "",
                *[counts.get(c, 0) for c in CATEGORIES]])
    for section in SECTIONS:
        print(f"{section}: {len(merged[section])}")
    print(f"rejected (quote not found or bad category): {len(rejected)}")
    print(f"result: {out}")


if __name__ == "__main__":
    main()
