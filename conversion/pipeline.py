#!/usr/bin/env python3
"""One page in, rendered readers out, with every intermediate kept on disk.

    python3 conversion/pipeline.py --image ~/Downloads/Edn2_Jan02.JPG --id 01-02 \
        --out-full renders/jan02.html --out-summary renders/jan02-summary.html

Stages run in order and each writes a named artifact. Nothing is held in memory
between them, so you can stop after any stage, edit the artifact by hand, and
carry on — which is the point, because the model's output needs correcting.

    work/<id>/1-transcript.mr.txt      raw Marathi, plain text, one sentence per line
    work/<id>/1-transcript.json        the same, structured
    work/<id>/2-english.txt            the translation, plain text, aligned by number
    work/<id>/2-english.json           the same, structured
    work/<id>/3-marks.json             which sentences the previous reader underlined
    work/<id>/4-day.json               everything merged — the file the readers use
    work/<id>/5-summary.json           the summary essay and the day's practice

Re-running skips any stage whose artifact already exists. Use --force to redo a
stage, or --from/--only to control which run.

    --only marks            just redo underline detection
    --from merge            merge, summary, render — no model calls at all
    --force                 ignore existing artifacts

Models: --model is the vision model (transcribe, marks), --text-model the one used
for translation and summary. Both default to the PRAVACHAN_* environment.

Endpoint: --base-url decides which API shape is used. Anything containing
anthropic.com speaks the Messages API and reads ANTHROPIC_API_KEY; everything else
speaks OpenAI-compatible /v1/chat/completions and reads PRAVACHAN_API_KEY.

    --base-url https://api.anthropic.com/v1 --model claude-sonnet-5
    --base-url https://inference-api.nvidia.com/v1 --model nvidia/baidu/paddleocr-vl
    --base-url http://localhost:11434/v1 --model qwen2.5vl:7b
"""
import argparse, datetime, json, os, pathlib, re, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    from assist import call, as_json, provider_for, DEFAULT_URL, DEFAULT_MODEL
except ModuleNotFoundError:
    sys.exit(
        "pipeline.py is a repository tool, not a standalone script.\n"
        "It needs conversion/assist.py beside it, and templates/ and tools/build.py\n"
        "above it to render anything.\n\n"
        "Run it from inside a clone:\n"
        "    git clone https://github.com/mash-falcon/pravachan-book-edition2.git\n"
        "    cd pravachan-book-edition2\n"
        "    python3 conversion/pipeline.py --image ~/Downloads/Edn2_Jan02.JPG --id 01-02 \\\n"
        "        --out-full renders/jan02.html\n\n"
        "For a single self-contained call, use conversion/probe_anthropic.py instead.")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "conversion" / "prompts"
STAGES = ["transcribe", "translate", "marks", "merge", "summary", "render"]


def art(work: pathlib.Path, name: str) -> pathlib.Path:
    return work / name


def rel(p: pathlib.Path) -> str:
    """Path for display. --work can be relative or outside the repo, and
    Path.relative_to raises rather than falling back."""
    p = pathlib.Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


NEEDS = {"1-transcript.json": "transcribe", "2-english.json": "translate",
         "3-marks.json": "marks", "4-day.json": "merge"}


def load(p: pathlib.Path):
    if not p.exists():
        stage = NEEDS.get(p.name, "an earlier stage")
        sys.exit(f"{rel(p)} is missing.\n"
                 f"It is produced by the `{stage}` stage — run that first, or drop the\n"
                 f"--from/--only flag so the earlier stages run too.")
    return json.loads(p.read_text(encoding="utf-8"))


def save(p: pathlib.Path, obj, cfg=None, how=None) -> None:
    """Every artifact records how it was made. Without this, a skipped stage can
    quietly hand you someone else's output as if it were your model's."""
    if isinstance(obj, dict):
        obj = {**obj, "_meta": {
            "made_by": how or (f"{provider_for(cfg['base_url'])}:{cfg['model']}" if cfg else "unknown"),
            "base_url": cfg["base_url"] if cfg else None,
            "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        }}
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    wrote {rel(p)}")


def describe(p: pathlib.Path) -> str:
    try:
        m = json.loads(p.read_text(encoding="utf-8")).get("_meta")
    except Exception:
        m = None
    if not m:
        return "origin UNRECORDED — this file was not made by this pipeline"
    return f"made by {m.get('made_by')} at {m.get('at')}"


# ---------------------------------------------------------------- stages

def stage_transcribe(cfg, work):
    """OCR models and instruction-following models need different handling.

    An OCR model returns a page of text; asking it for JSON, sentence numbers and a
    paragraph map is asking for a job it was not built for, and it will guess. In OCR
    mode we ask only for the text and split it deterministically in structure.py."""
    out_j, out_t = art(work, "1-transcript.json"), art(work, "1-transcript.mr.txt")
    if cfg["ocr"]:
        raw = call(cfg["base_url"], cfg["model"],
                   (PROMPTS / "transcribe_ocr.md").read_text(encoding="utf-8"),
                   cfg["image"], 0.0, cfg["max_tokens"])
        art(work, "0-ocr-raw.txt").write_text(raw, encoding="utf-8")
        print(f"    wrote {rel(art(work,'0-ocr-raw.txt'))}  ({len(raw)} chars)")
        from structure import structure
        r = structure(raw)
        print(f"    structured into {len(r['sentences'])} sentences in code, not by prompt")
        print("    paragraph breaks are NOT recoverable from OCR — set paras by hand")
    else:
        r = as_json(call(cfg["base_url"], cfg["model"],
                         (PROMPTS / "transcribe.md").read_text(encoding="utf-8"),
                         cfg["image"], 0.0, cfg["max_tokens"]), "transcribe")
    save(out_j, r, cfg)
    lines = [f'{s["n"]}. {s["mr"]}' for s in r.get("sentences", [])]
    header = [f'# {r.get("title_mr","")}', f'# {r.get("date_label_mr","")}', ""]
    footer = ["", f'[footnote {r.get("footnote",{}).get("marker","")}] '
                  f'{r.get("footnote",{}).get("mr","")}']
    out_t.write_text("\n".join(header + lines + footer), encoding="utf-8")
    print(f"    wrote {rel(out_t)}  ({len(lines)} sentences)")


def stage_translate(cfg, work):
    tr = load(art(work, "1-transcript.json"))
    listing = "\n".join(f'{s["n"]}. {s["mr"]}' for s in tr["sentences"])
    prompt = (PROMPTS / "translate.md").read_text(encoding="utf-8") + "\n\nSENTENCES:\n" + listing
    r = as_json(call(cfg["base_url"], cfg["text_model"], prompt, None, 0.0,
                     cfg["max_tokens"]), "translate")
    save(art(work, "2-english.json"), r, cfg)
    art(work, "2-english.txt").write_text(
        "\n".join(f'{s["n"]}. {s["en"]}' for s in r.get("sentences", [])), encoding="utf-8")
    print(f"    wrote {rel(art(work,'2-english.txt'))}")


def stage_marks(cfg, work):
    if cfg["ocr"] and cfg["marks_model"] == cfg["model"]:
        print("    SKIPPED — an OCR model reads printed glyphs, not hand-drawn pencil.")
        print("    Pass --marks-model <a vision-language model> to detect underlines,")
        print("    or read them off the scan yourself.")
        return
    tr = load(art(work, "1-transcript.json"))
    listing = "\n".join(f'{s["n"]}. {s["mr"]}' for s in tr["sentences"])
    prompt = (PROMPTS / "marks.md").read_text(encoding="utf-8") + "\n\nSENTENCES:\n" + listing
    r = as_json(call(cfg["base_url"], cfg["marks_model"], prompt, cfg["image"], 0.0,
                     cfg["max_tokens"]), "marks")
    r.setdefault("uncertain", [])
    r["detected_by"] = f"MODEL:{cfg['marks_model']}"
    r["confirmed_by_human"] = False
    save(art(work, "3-marks.json"), r, cfg)
    print(f"    {len(r.get('underlined',[]))} underlined, {len(r['uncertain'])} uncertain")
    print("    CONFIRM THESE AGAINST THE SCAN. An invented mark attributes something")
    print("    to the previous reader that they never wrote.")


def stage_merge(cfg, work):
    """Not a model stage — assembles the artifacts into the file the readers read."""
    tr = load(art(work, "1-transcript.json"))
    en = {s["n"]: s["en"] for s in load(art(work, "2-english.json")).get("sentences", [])} \
        if art(work, "2-english.json").exists() else {}
    mk = load(art(work, "3-marks.json")) if art(work, "3-marks.json").exists() else {}
    under = set(mk.get("underlined", []))
    ns = [s["n"] for s in tr["sentences"]]
    day = {
        "id": cfg["id"],
        "date": {"day": int(cfg["id"][3:]), "month": int(cfg["id"][:2]),
                 "label_mr": tr.get("date_label_mr", ""), "label_en": ""},
        "title_mr": tr.get("title_mr", ""), "title_en": "",
        "source": {"page_image": cfg["image_rel"], "orthography": "original",
                   "transcribed_by": f"MODEL:{cfg['model']}" + (" via structure.py" if cfg["ocr"] else ""),
                   "transcription_reviewed_by": None,
                   "translation_by": f"MODEL:{cfg['text_model']}" if en else None,
                   "translation_reviewed": False},
        "marks": {"kind": "inherited",
                  "by": "an unidentified previous reader of this copy",
                  "count_passages": len(under),
                  "detected_by": mk.get("detected_by"),
                  "confirmed_by_human": False,
                  "uncertain": mk.get("uncertain", []),
                  "note": mk.get("note", "")},
        "paras": tr.get("paras") or [[min(ns), max(ns)]],
        "sentences": [{"n": s["n"], "mr": s["mr"], "en": en.get(s["n"], ""),
                       "highlight": 1 if s["n"] in under else 0} for s in tr["sentences"]],
        "footnote": {"marker": tr.get("footnote", {}).get("marker", ""),
                     "mr": tr.get("footnote", {}).get("mr", ""), "en": ""},
        "commentary": [],
        "commentary_status": {"state": "none", "author": None,
                              "reviewed_by_marathi_editor": False,
                              "reviewed_by_publisher": False},
    }
    save(art(work, "4-day.json"), day, cfg, how="merged from artifacts")
    dest = ROOT / "content" / "days" / f"{cfg['id']}.json"
    if cfg["promote"]:
        shutil.copyfile(art(work, "4-day.json"), dest)
        print(f"    copied to {rel(dest)}  (--promote)")
    else:
        print(f"    NOT copied to content/days/ — pass --promote once you have read it")


def stage_summary(cfg, work):
    """Drafts the short edition from the underlined passages.

    A model may draft this, but it is fenced in: the prompt allows citations only to
    underlined sentences, and conversion/validate.py rejects the file if any {{n}}
    points at an unmarked one. That is what keeps the short page an abridgement of
    the reader's marks rather than an essay the model felt like writing."""
    day = load(art(work, "4-day.json"))
    marked = [s for s in day["sentences"] if s["highlight"]]
    if not marked:
        print("    no underlined passages — nothing to summarise, skipping")
        return
    full = "\n".join(f'{s["n"]}. {s["mr"]}' for s in day["sentences"])
    nums = ", ".join(str(s["n"]) for s in marked)
    prompt = ((PROMPTS / "summary.md").read_text(encoding="utf-8")
              + f"\n\nTITLE: {day['title_mr']}\n\nDISCOURSE:\n{full}"
              + f"\n\nUNDERLINED SENTENCES: {nums}\n")
    r = as_json(call(cfg["base_url"], cfg["text_model"], prompt, None, 0.0,
                     cfg["max_tokens"]), "summary")

    allowed = {s["n"] for s in marked}
    bad = set()
    for blk in r.get("essay", []):
        for lang in ("mr", "en"):
            bad |= {int(n) for n in re.findall(r"\{\{(\d+)\}\}", blk.get(lang, ""))} - allowed
    r.update(id=cfg["id"], status={
        "state": "draft", "author": None,
        "reviewed_by_marathi_editor": False, "reviewed_by_publisher": False,
        "note": f"Drafted by {cfg['text_model']} from the underlined passages. "
                "Marathi connective prose needs a native editor."})
    save(art(work, "5-summary.json"), r, cfg)
    print(f"    {len(r.get('essay', []))} blocks, "
          f"{len(r.get('practice_actions', []))} practice action(s)")
    if bad:
        print(f"    REJECTED CITATIONS {sorted(bad)} — these sentences are not underlined.")
        print("    Fix them by hand; validate.py will refuse the file until you do.")

def stage_render(cfg, work):
    src = art(work, "4-day.json")
    if not src.exists():
        sys.exit("no 4-day.json — run the earlier stages first")
    dest = ROOT / "content" / "days" / f"{cfg['id']}.json"
    if not dest.exists():
        shutil.copyfile(src, dest)
        print(f"    staged {rel(dest)} for rendering")
    s = art(work, "5-summary.json")
    if s.exists():
        blocks = load(s).get("essay", [])
        if any(b.get("mr", "").strip() not in ("", "…") for b in blocks):
            (ROOT / "summary" / "days").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(s, ROOT / "summary" / "days" / f"{cfg['id']}.json")
            print(f"    staged summary for {cfg['id']}")
        else:
            print("    summary has no written blocks — short page will be skipped")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), cfg["id"]], check=True)
    for built, out in ((ROOT / "apps" / "full-page" / f"{cfg['id']}.html", cfg["out_full"]),
                       (ROOT / "apps" / "short-page" / f"{cfg['id']}.html", cfg["out_summary"])):
        if out and built.exists():
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, out)
            print(f"    rendered {out}")
        elif out:
            print(f"    {out} not written — {built.name} was not built")


RUNNERS = {"transcribe": stage_transcribe, "translate": stage_translate,
           "marks": stage_marks, "merge": stage_merge, "summary": stage_summary,
           "render": stage_render}
ARTIFACT = {"transcribe": "1-transcript.json", "translate": "2-english.json",
            "marks": "3-marks.json", "merge": "4-day.json",
            "summary": "5-summary.json", "render": None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--id", required=True, help="MM-DD, e.g. 01-02")
    ap.add_argument("--out-full", default=None, help="where to write the full-page reader")
    ap.add_argument("--out-summary", default=None, help="where to write the summary reader")
    ap.add_argument("--work", default=None, help="artifact directory (default work/<id>/)")
    ap.add_argument("--base-url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="vision model")
    ap.add_argument("--text-model", default=None)
    ap.add_argument("--marks-model", default=None,
                    help="model for underline detection (OCR models cannot do this)")
    ap.add_argument("--ocr", action="store_true",
                    help="treat --model as an OCR engine: ask for text, structure in code. "
                         "Enabled automatically when the model name contains 'ocr'.")
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--only", choices=STAGES)
    ap.add_argument("--from", dest="start", choices=STAGES)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--promote", action="store_true",
                    help="copy the merged day into content/days/ (do this after reading it)")
    a = ap.parse_args()

    image = pathlib.Path(a.image).expanduser().resolve()
    if not image.exists():
        sys.exit(f"{image} not found")
    work = (pathlib.Path(a.work) if a.work else ROOT / "work" / a.id).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)

    ocr = a.ocr or "ocr" in a.model.lower()
    cfg = {"id": a.id, "image": image, "base_url": a.base_url, "model": a.model,
           "text_model": a.text_model or a.model,
           "marks_model": a.marks_model or a.model, "ocr": ocr,
           "max_tokens": a.max_tokens,
           "promote": a.promote, "out_full": a.out_full, "out_summary": a.out_summary,
           "image_rel": f"source/pages/{a.id}{image.suffix.lower()}"}

    # keep the scan where the readers expect it
    staged = ROOT / "source" / "pages" / f"{a.id}{image.suffix.lower()}"
    if not staged.exists():
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image, staged)
        print(f"staged scan at {rel(staged)}")

    if a.only:
        todo = [a.only]
    else:
        start = STAGES.index(a.start) if a.start else 0
        todo = STAGES[start:]

    skipped = []
    print(f"\n{a.id}   {image.name}")
    print(f"{provider_for(a.base_url)} · {a.base_url} · {a.model}"
          + ("   [OCR mode]" if ocr else ""))
    if ocr and not a.marks_model:
        print("no --marks-model: underline detection will be skipped")
    print()
    for stage in todo:
        name = ARTIFACT[stage]
        existing = art(work, name) if name else None
        if existing and existing.exists() and not a.force:
            print(f"[{stage}] skipped — {existing.name} already exists")
            print(f"          {describe(existing)}")
            skipped.append(stage)
            continue
        print(f"[{stage}]")
        RUNNERS[stage](cfg, work)

    if len(skipped) >= len([t for t in todo if ARTIFACT[t]]):
        print("\nNO MODEL WAS CALLED — every stage reused an existing artifact.")
        print(f"To actually run {a.model}:  --force   (or --work <fresh dir>)")
    print(f"\nartifacts in {rel(work)}/")
    for f in sorted(work.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
