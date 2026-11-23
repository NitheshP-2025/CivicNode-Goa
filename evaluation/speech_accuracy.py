"""Measure speech-to-text accuracy per language (WER, CER) and field-capture accuracy.

1) Print a recording script, have teammates/volunteers record each sentence:
       python -m civicnode_ai2.evaluation.speech_accuracy --write-script data/speech_eval/script.jsonl
   Save recordings next to it and add an "audio" path to each line (see manifest format below).

2) Score:
       python -m civicnode_ai2.evaluation.speech_accuracy --manifest data/speech_eval/manifest.jsonl \
           --backend whisper --out data/speech_eval/report.json

Manifest = JSON lines: {"audio": "rec/mr_01.wav", "reference": "...", "language": "mr",
                        "expected_fields": {...}}   (expected_fields is optional)
Or score transcripts you already have by giving "hypothesis" instead of "audio".

WER/CER use code points after Unicode NFC and punctuation removal. Report your numbers
honestly in the pitch: they are only as good as the recordings you made.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..voice.extract import extract_fields
from ..voice.stt import get_transcriber


def normalise_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "").lower().replace("‌", "").replace("‍", "")
    s = re.sub(r"[^\wऀ-ॿ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def edit_distance(a: Sequence, b: Sequence) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def word_errors(reference: str, hypothesis: str):
    r, h = normalise_text(reference).split(), normalise_text(hypothesis).split()
    return edit_distance(r, h), len(r)


def char_errors(reference: str, hypothesis: str):
    r, h = normalise_text(reference), normalise_text(hypothesis)
    return edit_distance(r, h), len(r)


def wer(reference: str, hypothesis: str) -> float:
    e, n = word_errors(reference, hypothesis)
    return e / n if n else (0.0 if not normalise_text(hypothesis) else 1.0)


def cer(reference: str, hypothesis: str) -> float:
    e, n = char_errors(reference, hypothesis)
    return e / n if n else (0.0 if not normalise_text(hypothesis) else 1.0)


def _same(a: str, b: str) -> bool:
    return normalise_text(a) == normalise_text(b)


def evaluate(entries: List[dict], transcriber=None, base_dir: Path = Path(".")) -> dict:
    per_lang = defaultdict(lambda: {"n": 0, "word_err": 0, "word_n": 0, "char_err": 0, "char_n": 0,
                                    "wer_list": [], "cer_list": [], "field_hits": 0, "field_total": 0,
                                    "failed": 0})
    rows = []
    for e in entries:
        lang = e["language"]
        hyp, error = e.get("hypothesis"), None
        if hyp is None:
            try:
                t = transcriber or get_transcriber()
                hyp = t.transcribe(base_dir / e["audio"], lang).text
            except Exception as exc:  # keep scoring the rest
                hyp, error = "", str(exc)
        s = per_lang[lang]
        s["n"] += 1
        if error:
            s["failed"] += 1
        we, wn = word_errors(e["reference"], hyp)
        ce, cn = char_errors(e["reference"], hyp)
        s["word_err"] += we; s["word_n"] += wn; s["char_err"] += ce; s["char_n"] += cn
        s["wer_list"].append(wer(e["reference"], hyp)); s["cer_list"].append(cer(e["reference"], hyp))
        row = {"language": lang, "reference": e["reference"], "hypothesis": hyp,
               "wer": round(wer(e["reference"], hyp), 3), "cer": round(cer(e["reference"], hyp), 3)}
        if error:
            row["error"] = error
        if e.get("expected_fields"):
            got = extract_fields(hyp, lang, allow_bare=None)
            hits = sum(1 for k, v in e["expected_fields"].items() if k in got and _same(got[k], v))
            s["field_hits"] += hits
            s["field_total"] += len(e["expected_fields"])
            row["fields_correct"] = f"{hits}/{len(e['expected_fields'])}"
        rows.append(row)

    summary = {}
    for lang, s in per_lang.items():
        summary[lang] = {
            "utterances": s["n"], "failed_to_transcribe": s["failed"],
            "corpus_wer": round(s["word_err"] / s["word_n"], 3) if s["word_n"] else None,
            "corpus_cer": round(s["char_err"] / s["char_n"], 3) if s["char_n"] else None,
            "mean_wer": round(sum(s["wer_list"]) / len(s["wer_list"]), 3),
            "mean_cer": round(sum(s["cer_list"]) / len(s["cer_list"]), 3),
            "field_accuracy": round(s["field_hits"] / s["field_total"], 3) if s["field_total"] else None,
        }
    return {"summary": summary, "rows": rows}


# ---------------------------------------------------------------------------
# recording script
# ---------------------------------------------------------------------------
_PEOPLE = [("Ramesh Naik", "रमेश नाईक"), ("Anita Desai", "अनिता देसाई"), ("Suresh Gawas", "सुरेश गावस"),
           ("Savita Velip", "सविता वेळीप"), ("Prakash Parab", "प्रकाश परब"), ("Meena Sawant", "मीना सावंत")]
_VILLAGES = [("Valpoi", "वाळपई"), ("Sankhali", "सांखळी"), ("Honda", "होंडा"),
             ("Pissurlem", "पिसुर्ले"), ("Poriem", "पोरीम"), ("Nagargao", "नागरगाव")]
_SURVEYS = ["45/2", "112/1", "8/4", "230/3", "67", "19/7"]
_DATES = [(22, 7, 2021), (23, 7, 2021), (21, 7, 2021), (24, 7, 2021), (22, 7, 2021), (20, 7, 2021)]
_MONTH_EN = "July"
_MONTH_MR, _MONTH_KOK = "जुलै", "जुलय"


def recording_script(per_language: int = 6) -> List[dict]:
    """Sentences to read aloud; each carries the fields a perfect transcript would yield."""
    out = []
    for lang in ("en", "mr", "kok"):
        for k in range(min(per_language, len(_PEOPLE))):
            en_name, dev_name = _PEOPLE[k]
            en_vil, dev_vil = _VILLAGES[k]
            survey, (d, m, y) = _SURVEYS[k], _DATES[k]
            iso = f"{y:04d}-{m:02d}-{d:02d}"
            if lang == "en":
                text = f"My name is {en_name}, survey number {survey}, village {en_vil}, flood date {d} {_MONTH_EN} {y}."
                name, vil = en_name, en_vil
            elif lang == "mr":
                text = f"माझे नाव {dev_name} आहे, सर्वे क्रमांक {survey}, गाव {dev_vil}, पुराची तारीख {d} {_MONTH_MR} {y}."
                name, vil = dev_name, dev_vil
            else:
                text = f"म्हजें नांव {dev_name} आसा, सर्वे क्रमांक {survey}, गांव {dev_vil}, पुराची तारीख {d} {_MONTH_KOK} {y}."
                name, vil = dev_name, dev_vil
            out.append({"id": f"{lang}_{k + 1:02d}", "language": lang, "audio": f"rec/{lang}_{k + 1:02d}.wav",
                        "reference": text,
                        "expected_fields": {"name": name, "survey_no": survey, "village": vil, "incident_date": iso}})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Speech accuracy (WER/CER) tool")
    ap.add_argument("--manifest", help="JSONL manifest to score")
    ap.add_argument("--backend", default=None, help="auto | whisper | mock (default from CIVICNODE_STT)")
    ap.add_argument("--out", help="write the JSON report here")
    ap.add_argument("--write-script", help="write a recording script (JSONL) and exit")
    a = ap.parse_args(argv)

    if a.write_script:
        p = Path(a.write_script)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recording_script()) + "\n", encoding="utf-8")
        print(f"wrote {p} - record each 'reference' sentence to its 'audio' path, then run with --manifest")
        return
    if not a.manifest:
        ap.error("give --manifest or --write-script")
    mp = Path(a.manifest)
    entries = [json.loads(l) for l in mp.read_text(encoding="utf-8").splitlines() if l.strip()]
    report = evaluate(entries, get_transcriber(a.backend), mp.parent)
    for lang, s in report["summary"].items():
        print(f"{lang:4} n={s['utterances']:3} corpus WER={s['corpus_wer']} CER={s['corpus_cer']} "
              f"field accuracy={s['field_accuracy']} failed={s['failed_to_transcribe']}")
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report written to {a.out}")


if __name__ == "__main__":
    main()
