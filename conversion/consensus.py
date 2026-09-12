#!/usr/bin/env python3
"""Run several models over the same page and use their agreement to target review.

    python3 conversion/consensus.py --image scan.jpg --id 01-02 --stage marks \
        --models gcp/google/gemini-3.8-flash,aws/anthropic/bedrock-claude-opus-4-8,xai/xai/grok-4.6

The point is not a better answer by vote. It is knowing WHERE TO LOOK. Over 365
pages, reading every sentence against the scan is not going to happen; reading the
few where independent models disagree is. Agreement is a cheap proxy for "probably
fine", disagreement is a reliable proxy for "a person must decide".

Consensus never silently picks a winner on a contested item. Disagreements are
written out with every variant under `needs_review`, for a person to settle against
the scan. Nothing here writes to content/ — resolving them is a separate, deliberate
edit to the transcript or the marks file.

Stages:
    transcribe   compares the Marathi sentence by sentence
    marks        compares which sentences each model says are underlined

Output: work/<id>/consensus-<stage>.json, plus each model's raw result beside it.
"""
import argparse, collections, difflib, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from assist import call, as_json, provider_for, DEFAULT_URL
    from structure import structure
except ModuleNotFoundError:
    sys.exit("run this from inside a clone — it needs conversion/assist.py beside it")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "conversion" / "prompts"


def slug(m: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", m).strip("_")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- transcribe

def run_transcribe(model, cfg):
    is_ocr = "ocr" in model.lower()
    prompt = (PROMPTS / ("transcribe_ocr.md" if is_ocr else "transcribe.md")).read_text(encoding="utf-8")
    raw = call(cfg["base_url"], model, prompt, cfg["image"], 0.0, cfg["max_tokens"])
    r = structure(raw) if is_ocr else as_json(raw, "transcribe")
    return {"sentences": [norm(s["mr"]) for s in r.get("sentences", [])],
            "title": norm(r.get("title_mr", "")), "raw": r}


def consensus_transcribe(results):
    """Align on the model that returned the median sentence count, then compare."""
    models = list(results)
    counts = {m: len(results[m]["sentences"]) for m in models}
    ref = sorted(models, key=lambda m: abs(counts[m] - sorted(counts.values())[len(models) // 2]))[0]
    ref_s = results[ref]["sentences"]

    rows, agreed = [], 0
    for i, base in enumerate(ref_s):
        variants = {}
        for m in models:
            ss = results[m]["sentences"]
            if i < len(ss) and difflib.SequenceMatcher(None, base, ss[i]).ratio() > 0.55:
                cand = ss[i]
            else:  # counts drifted — find this sentence wherever it landed
                best = max(ss, key=lambda x: difflib.SequenceMatcher(None, base, x).ratio(),
                           default="")
                cand = best if difflib.SequenceMatcher(None, base, best).ratio() > 0.55 else ""
            variants.setdefault(cand, []).append(m)
        unanimous = len(variants) == 1 and "" not in variants
        agreed += unanimous
        rows.append({
            "n": i + 1,
            "agreed": unanimous,
            "text": base if unanimous else None,
            "variants": None if unanimous else
                        [{"models": v, "mr": k or "(no matching sentence returned)"}
                         for k, v in sorted(variants.items(), key=lambda kv: -len(kv[1]))],
        })
    return {
        "reference_model": ref,
        "sentence_counts": counts,
        "count_agreement": len(set(counts.values())) == 1,
        "unanimous": agreed, "total": len(ref_s),
        "sentences": rows,
        "needs_review": [r["n"] for r in rows if not r["agreed"]],
    }


# ---------------------------------------------------------------- marks

def run_marks(model, cfg, sentences):
    listing = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
    prompt = (PROMPTS / "marks.md").read_text(encoding="utf-8") + "\n\nSENTENCES:\n" + listing
    r = as_json(call(cfg["base_url"], model, prompt, cfg["image"], 0.0, cfg["max_tokens"]), "marks")
    return {"underlined": sorted(set(r.get("underlined", []))),
            "uncertain": sorted(set(r.get("uncertain", [])))}


def consensus_marks(results, n_sentences):
    models = list(results)
    votes = collections.Counter()
    for m in models:
        votes.update(results[m]["underlined"])
    every, some = [], []
    for n in range(1, n_sentences + 1):
        if votes[n] == len(models):
            every.append(n)
        elif votes[n]:
            some.append(n)
    return {
        "per_model": {m: results[m]["underlined"] for m in models},
        "all_models_agree": every,
        "disputed": [{"n": n, "marked_by": [m for m in models if n in results[m]["underlined"]],
                      "not_marked_by": [m for m in models if n not in results[m]["underlined"]]}
                     for n in some],
        "needs_review": some,
        "note": "A disputed mark must be settled against the scan. An invented one "
                "attributes something to the previous reader that they never wrote.",
    }


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--stage", choices=["transcribe", "marks"], default="transcribe")
    ap.add_argument("--models", required=True, help="comma-separated, or a file of names")
    ap.add_argument("--base-url", default=DEFAULT_URL)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--work", default=None)
    a = ap.parse_args()

    image = pathlib.Path(a.image).expanduser().resolve()
    mp = pathlib.Path(a.models)
    models = ([ln.strip() for ln in mp.read_text().splitlines()
               if ln.strip() and not ln.startswith("#")] if mp.exists()
              else [m.strip() for m in a.models.split(",") if m.strip()])
    if len(models) < 2:
        sys.exit("consensus needs at least two models")

    work = (pathlib.Path(a.work) if a.work else ROOT / "work" / a.id).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    cfg = {"base_url": a.base_url, "image": image, "max_tokens": a.max_tokens}

    print(f"\n{a.id}  {image.name}  ·  {a.stage}  ·  {len(models)} models")
    print(f"{provider_for(a.base_url)} · {a.base_url}\n")

    sentences = None
    if a.stage == "marks":
        tr = work / "1-transcript.json"
        if not tr.exists():
            sys.exit(f"{tr.name} is missing — marks compares against a transcript. "
                     f"Run the transcribe stage first.")
        sentences = [s["mr"] for s in json.loads(tr.read_text(encoding="utf-8"))["sentences"]]

    results = {}
    for m in models:
        print(f"── {m}")
        try:
            r = run_transcribe(m, cfg) if a.stage == "transcribe" else run_marks(m, cfg, sentences)
        except SystemExit as e:
            print(f"   FAILED: {e}\n")
            continue
        results[m] = r
        (work / f"{a.stage}__{slug(m)}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print("   " + (f"{len(r['sentences'])} sentences" if a.stage == "transcribe"
                       else f"underlined {r['underlined']}  uncertain {r['uncertain']}") + "\n")

    if len(results) < 2:
        sys.exit("fewer than two models succeeded — nothing to compare")

    out = (consensus_transcribe(results) if a.stage == "transcribe"
           else consensus_marks(results, len(sentences)))
    out["_models"] = list(results)
    dest = work / f"consensus-{a.stage}.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    if a.stage == "transcribe":
        print(f"sentence counts   : {out['sentence_counts']}")
        if not out["count_agreement"]:
            print("                    models disagree on how many sentences the page has")
        print(f"unanimous         : {out['unanimous']}/{out['total']}")
        print(f"need a human      : {out['needs_review'] or 'none'}")
        for r in out["sentences"]:
            if r["agreed"]:
                continue
            print(f"\n  [{r['n']}]")
            for v in r["variants"]:
                print(f"    {','.join(v['models'])}:")
                print(f"      {v['mr'][:110]}")
    else:
        print(f"all models agree  : {out['all_models_agree']}")
        print(f"disputed          : {out['needs_review'] or 'none'}")
        for d in out["disputed"]:
            print(f"    [{d['n']}] marked by {d['marked_by']} — not by {d['not_marked_by']}")
    print("=" * 72)
    print(f"\nwrote {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")
    print("Agreement is not correctness — it means the models failed the same way or")
    print("not at all. Disagreement is the reliable signal: those lines need the scan.")


if __name__ == "__main__":
    main()
