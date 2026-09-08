#!/usr/bin/env python3
"""Run several models over the same page and put the results side by side.

    python3 conversion/bakeoff.py 01-01 --models models.txt
    python3 conversion/bakeoff.py 01-01 --models a/b/c,d/e/f --task transcribe

Only useful on a day that already has a verified file in content/days/ — you cannot
score a model against content you have not checked. 01-01 is the worked example.

Drafts go to content/drafts/bakeoff/<day>__<model>.json so nothing collides, and
nothing here can reach content/days/.

Model names are passed through untouched. Which of them can see an image, and which
are text-only, is something this finds out empirically rather than assuming.
"""
import argparse, json, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "content" / "drafts" / "bakeoff"


def slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model).strip("_")


def load_models(spec: str) -> list[str]:
    p = pathlib.Path(spec)
    if p.exists():
        return [ln.strip() for ln in p.read_text().splitlines()
                if ln.strip() and not ln.startswith("#")]
    return [m.strip() for m in spec.split(",") if m.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day")
    ap.add_argument("--models", required=True,
                    help="comma-separated list, or a path to a file with one per line")
    ap.add_argument("--task", choices=["transcribe", "marks", "translate", "all"],
                    default="transcribe")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--text-model", default=None,
                    help="use this model for translation instead of each vision model")
    a = ap.parse_args()

    gold = ROOT / "content" / "days" / f"{a.day}.json"
    if not gold.exists():
        raise SystemExit(f"{gold.relative_to(ROOT)} does not exist — bake off against a "
                         f"day you have already verified, not one you have not.")
    OUT.mkdir(parents=True, exist_ok=True)
    models = load_models(a.models)
    print(f"{len(models)} model(s), day {a.day}, task {a.task}\n")

    rows = []
    for model in models:
        draft = OUT / f"{a.day}__{slug(model)}.json"
        cmd = [sys.executable, str(ROOT / "conversion" / "assist.py"), a.day,
               "--task", a.task, "--model", model, "--out", str(draft)]
        if a.base_url:
            cmd += ["--base-url", a.base_url]
        if a.text_model:
            cmd += ["--text-model", a.text_model]
        print(f"── {model}")
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        secs = time.time() - t0
        if r.returncode != 0:
            first = (r.stderr or r.stdout).strip().splitlines()
            rows.append({"model": model, "error": first[-1][:70] if first else "failed",
                         "seconds": secs})
            print(f"   FAILED: {rows[-1]['error']}\n")
            continue
        s = subprocess.run([sys.executable, str(ROOT / "conversion" / "score.py"),
                            a.day, f"--draft={draft}", "--json"],
                           capture_output=True, text=True)
        if s.returncode != 0:
            rows.append({"model": model, "error": "scoring failed", "seconds": secs})
            print("   scoring failed\n")
            continue
        m = json.loads(s.stdout)
        m.update(model=model, seconds=secs)
        rows.append(m)
        print(f"   {secs:.0f}s  exact {m['exact']}/{m['sentences_gold']}  "
              f"modernised {m['modernised']}  marks F1 {m['mark_f1']:.0%}\n")

    print("\n" + "=" * 96)
    print(f"{'model':<44} {'sent':>6} {'exact':>6} {'MODERN':>7} {'char':>6} "
          f"{'markF1':>7} {'inv':>4} {'sec':>5}")
    print("-" * 96)
    for r in rows:
        if "error" in r:
            print(f"{r['model'][:44]:<44} {'—':>6} {'—':>6} {'—':>7} {'—':>6} "
                  f"{'—':>7} {'—':>4} {r['seconds']:>5.0f}   {r['error']}")
            continue
        print(f"{r['model'][:44]:<44} {r['sentences_draft']:>6} "
              f"{r['exact']:>6} {r['modernised']:>7} {r['char_accuracy']:>5.0%} "
              f"{r['mark_f1']:>6.0%} {len(r['marks_invented']):>4} {r['seconds']:>5.0f}")
    print("=" * 96)
    print("MODERN = sentences that differ from the book only by anusvara or vowel length.")
    print("         Any number above zero means the model is rewriting the orthography,")
    print("         and char accuracy will still look excellent. Rank on this column.")
    print("inv    = underlines the model invented — text it marked that the reader did not.")

    ok = [r for r in rows if "error" not in r and r["modernised"] == 0
          and r["sentences_draft"] == r["sentences_gold"]]
    print()
    if ok:
        best = max(ok, key=lambda r: (r["exact"], r["mark_f1"]))
        print(f"Cleanest transcription: {best['model']} "
              f"({best['exact']}/{best['sentences_gold']} exact, marks F1 {best['mark_f1']:.0%})")
        print("Still read it against the scan before promoting anything.")
    else:
        print("No model transcribed this page without modernising it or losing sentences.")
        print("Either tighten conversion/prompts/transcribe.md and re-run, or accept that")
        print("transcription stays a human job and use the models only for translation.")

    (OUT / f"{a.day}__results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nfull results: {(OUT / f'{a.day}__results.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
