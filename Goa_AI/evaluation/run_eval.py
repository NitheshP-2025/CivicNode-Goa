from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import load_thresholds
from ..documents.extract import extract_document
from ..documents.validate import values_agree
from ..recommend.engine import recommend
from ..schemas import ClaimBundle

FIELDS = ["owner", "survey", "area_ha", "village", "taluka"]
RESULTS = Path(__file__).parent / "results"
DOC_TYPES = {".png", ".jpg", ".jpeg", ".pdf"}


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}% ({a}/{b})" if b else "n/a"


def eval_extraction(samples: Path, expected_dir: Path) -> str:
    min_conf = load_thresholds()["extraction"]["min_field_confidence"]
    stats = {f: dict(n=0, ok=0, acc=0, acc_ok=0) for f in FIELDS}
    gate_n = gate_ok = 0
    for exp_path in sorted(expected_dir.glob("*.json")):
        exp = json.loads(exp_path.read_text(encoding="utf-8"))
        doc = next((p for p in samples.glob(exp_path.stem + ".*") if p.suffix.lower() in DOC_TYPES), None)
        if doc is None:
            print(f"skip {exp_path.name}: no matching document")
            continue
        result = extract_document(doc.read_bytes(), doc.name, exp_path.stem)
        if "quality_ok" in exp:
            gate_n += 1
            gate_ok += int(result.quality.ok == exp["quality_ok"])
        got = {f.name: f for f in result.fields}
        for name, truth in (exp.get("fields") or {}).items():
            if name not in stats:
                continue
            f = got.get(name)
            correct = bool(f and values_agree(name, f.value, truth))
            accepted = bool(f and f.value is not None and f.confidence >= min_conf)
            s = stats[name]
            s["n"] += 1
            s["ok"] += int(correct)
            s["acc"] += int(accepted)
            s["acc_ok"] += int(accepted and correct)

    lines = ["# Extraction accuracy", "",
             f"Confidence threshold for 'accepted': {min_conf}", "",
             "| Field | Correct (all) | Accepted (confident) | Correct among accepted |",
             "|---|---|---|---|"]
    for name, s in stats.items():
        lines.append(f"| {name} | {_pct(s['ok'], s['n'])} | {_pct(s['acc'], s['n'])} | {_pct(s['acc_ok'], s['acc'])} |")
    lines += ["", f"Quality gate (good/bad document caught correctly): {_pct(gate_ok, gate_n)}"]
    return "\n".join(lines)


def eval_lanes(cases_path: Path) -> str:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    ok = 0
    confusion: dict = {}
    rows = []
    for c in cases:
        lane = recommend(ClaimBundle.model_validate(c["bundle"])).lane
        exp = c["expected_lane"]
        ok += int(lane == exp)
        confusion[(exp, lane)] = confusion.get((exp, lane), 0) + 1
        rows.append(f"| {c.get('name', '?')} | {exp} | {lane} | {'ok' if lane == exp else 'WRONG'} |")
    lines = ["# Lane correctness", "", f"Matches expected lane: {_pct(ok, len(cases))}", "",
             "| Case | Expected | Got | Result |", "|---|---|---|---|", *rows, "",
             "Confusion (expected -> got): " + ", ".join(f"{e}->{g}: {n}" for (e, g), n in sorted(confusion.items()))]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extraction")
    e.add_argument("--samples", type=Path, required=True)
    e.add_argument("--expected", type=Path, required=True)
    l = sub.add_parser("lanes")
    l.add_argument("--cases", type=Path, required=True)
    args = ap.parse_args()

    report = eval_extraction(args.samples, args.expected) if args.cmd == "extraction" else eval_lanes(args.cases)
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{args.cmd}_results.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
