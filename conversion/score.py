#!/usr/bin/env python3
"""Score a model draft against a verified day file.

    python3 conversion/score.py 01-01

Compares content/drafts/<id>.json to content/days/<id>.json and reports how well the
model did. Run this on a day you have already verified by hand — 01-01 is the worked
example — before trusting the model on a day you have not.

The metric that matters most is not character accuracy. It is SILENT MODERNISATION:
the model writing नाव where the book prints नांव. That reads perfectly, passes every
other check, and quietly alters the text. It is reported separately.
"""
import difflib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ANUSVARA = "ंँ"          # ं ঁ  — the marks older orthography keeps
LONG_SHORT = str.maketrans("ीूैौ", "िुेो")   # vowel-length flattening


def strip_anusvara(s: str) -> str:
    return "".join(c for c in s if c not in ANUSVARA)


def flatten_vowels(s: str) -> str:
    return s.translate(LONG_SHORT)


def classify(gold: str, draft: str) -> str:
    if gold == draft:
        return "exact"
    if strip_anusvara(gold) == strip_anusvara(draft):
        return "MODERNISED (anusvara dropped or added)"
    if flatten_vowels(strip_anusvara(gold)) == flatten_vowels(strip_anusvara(draft)):
        return "MODERNISED (anusvara + vowel length)"
    return "different"


def char_accuracy(gold: str, draft: str) -> float:
    return difflib.SequenceMatcher(None, gold, draft).ratio()


def measure(gold: dict, draft: dict) -> dict:
    """The numbers, without the prose. Used by score.py and by bakeoff.py."""
    g = {s["n"]: s for s in gold["sentences"]}
    d = {s["n"]: s for s in draft.get("sentences", [])}
    shared = sorted(set(g) & set(d))
    exact = modern = different = 0
    for n in shared:
        v = classify(g[n]["mr"], d[n]["mr"])
        if v == "exact":
            exact += 1
        elif v.startswith("MODERNISED"):
            modern += 1
        else:
            different += 1
    gh = {n for n, s in g.items() if s["highlight"]}
    dh = {n for n, s in d.items() if s.get("highlight")}
    tp, fp, fn = len(gh & dh), len(dh - gh), len(gh - dh)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "sentences_gold": len(g), "sentences_draft": len(d),
        "exact": exact, "modernised": modern, "different": different,
        "char_accuracy": (sum(char_accuracy(g[n]["mr"], d[n]["mr"]) for n in shared) / len(shared))
                          if shared else 0.0,
        "mark_precision": prec, "mark_recall": rec,
        "mark_f1": (2 * prec * rec / (prec + rec)) if prec + rec else 0.0,
        "marks_invented": sorted(dh - gh), "marks_missed": sorted(gh - dh),
        "translated": sum(1 for n in shared if d[n].get("en")),
        "usable": modern == 0 and len(g) == len(d),
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        raise SystemExit(__doc__)
    day_id = args[0]
    draft_flag = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--draft=")), None)
    gold_p = ROOT / "content" / "days" / f"{day_id}.json"
    draft_p = pathlib.Path(draft_flag) if draft_flag else ROOT / "content" / "drafts" / f"{day_id}.json"
    for p in (gold_p, draft_p):
        if not p.exists():
            raise SystemExit(f"missing {p.relative_to(ROOT)}")
    gold = json.loads(gold_p.read_text(encoding="utf-8"))
    draft = json.loads(draft_p.read_text(encoding="utf-8"))

    if "--json" in sys.argv:
        print(json.dumps(measure(gold, draft), ensure_ascii=False))
        return

    g = {s["n"]: s for s in gold["sentences"]}
    d = {s["n"]: s for s in draft.get("sentences", [])}
    prov = draft.get("_provenance", {})

    print(f"day {day_id}")
    print(f"vision model : {prov.get('vision_model','?')}")
    print(f"text model   : {prov.get('text_model','?')}")
    print(f"sentences    : gold {len(g)}, draft {len(d)}"
          + ("" if len(g) == len(d) else "   <-- COUNT MISMATCH, everything below is approximate"))

    shared = sorted(set(g) & set(d))
    exact = modern = different = 0
    worst = []
    for n in shared:
        verdict = classify(g[n]["mr"], d[n]["mr"])
        acc = char_accuracy(g[n]["mr"], d[n]["mr"])
        if verdict == "exact":
            exact += 1
        elif verdict.startswith("MODERNISED"):
            modern += 1
            worst.append((0.0, n, verdict, g[n]["mr"], d[n]["mr"]))   # sort these first
        else:
            different += 1
            worst.append((acc, n, verdict, g[n]["mr"], d[n]["mr"]))

    if shared:
        mean = sum(char_accuracy(g[n]["mr"], d[n]["mr"]) for n in shared) / len(shared)
        print(f"\nTRANSCRIPTION over {len(shared)} shared sentences")
        print(f"  exact match        : {exact}/{len(shared)}")
        print(f"  silently modernised: {flag(modern)}")
        print(f"  otherwise different: {different}/{len(shared)}")
        print(f"  mean char accuracy : {mean:.1%}")

    if worst:
        print("\n  worst sentences:")
        for acc, n, verdict, gm, dm in sorted(worst)[:6]:
            print(f"    [{n}] {verdict}")
            print(f"        book : {gm}")
            print(f"        model: {dm}")

    gh = {n for n, s in g.items() if s["highlight"]}
    dh = {n for n, s in d.items() if s.get("highlight")}
    if dh or gh:
        tp, fp, fn = len(gh & dh), len(dh - gh), len(gh - dh)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        print(f"\nUNDERLINE DETECTION")
        print(f"  book marked  : {sorted(gh)}")
        print(f"  model marked : {sorted(dh)}")
        print(f"  precision {prec:.0%}  recall {rec:.0%}  F1 {f1:.0%}")
        if fp:
            print(f"  INVENTED marks on {sorted(dh - gh)} — these would misattribute the reader")
        if fn:
            print(f"  missed marks on {sorted(gh - dh)}")
        if draft.get("_marks_uncertain"):
            print(f"  model was unsure about {draft['_marks_uncertain']}")

    tr = [n for n in shared if d[n].get("en")]
    if tr:
        print(f"\nTRANSLATION")
        print(f"  {len(tr)}/{len(shared)} sentences translated (quality needs a human; not scored)")

    print("\nVERDICT")
    if modern:
        print("  NOT USABLE AS-IS for transcription — the model is normalising the")
        print("  orthography. Every modernised sentence must be corrected by hand,")
        print("  which is most of the work the model was supposed to save.")
    elif exact == len(shared) and len(g) == len(d):
        print("  Transcription is clean on this page. Still read it against the scan.")
    else:
        print("  Transcription needs correction. See the worst sentences above.")
    print("  Underline detection must be confirmed against the scan regardless of score.")


def flag(n: int) -> str:
    return f"{n}   <-- the number that matters" if n else "0"


if __name__ == "__main__":
    main()
