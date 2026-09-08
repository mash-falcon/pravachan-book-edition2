#!/usr/bin/env python3
"""Draft a day file from a page scan using a local LLM.

    python3 conversion/assist.py 01-02
    python3 conversion/assist.py 01-02 --task transcribe
    python3 conversion/assist.py 01-02 --model qwen2.5vl:7b --base-url http://localhost:11434/v1

Speaks the OpenAI-compatible /v1/chat/completions API, so it works with Ollama,
llama.cpp's server, LM Studio, vLLM, or anything else exposing that shape. Uses only
the standard library — no SDK, no pip install.

Output goes to content/drafts/<id>.json and NEVER to content/days/. A human promotes
a draft with conversion/accept.py after reading it against the scan. Nothing a model
produces reaches the readers unreviewed.

Environment:
    PRAVACHAN_BASE_URL   default http://localhost:11434/v1
    PRAVACHAN_MODEL      default qwen2.5vl:7b
    PRAVACHAN_API_KEY    default "local" (most local servers ignore it)
"""
import argparse, base64, json, os, pathlib, re, sys, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "conversion" / "prompts"
DRAFTS = ROOT / "content" / "drafts"
PAGES = ROOT / "source" / "pages"

DEFAULT_URL = os.environ.get("PRAVACHAN_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = os.environ.get("PRAVACHAN_MODEL", "qwen2.5vl:7b")
API_KEY = os.environ.get("PRAVACHAN_API_KEY", "local")


def find_image(day_id: str) -> pathlib.Path:
    for ext in (".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"):
        p = PAGES / f"{day_id}{ext}"
        if p.exists():
            return p
    raise SystemExit(f"no scan found at source/pages/{day_id}.[jpg|png]")


def call(base_url: str, model: str, prompt: str, image: pathlib.Path | None,
         temperature: float) -> str:
    content = [{"type": "text", "text": prompt}]
    if image is not None:
        mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(image.read_bytes()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"}})
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            payload = json.loads(r.read())
    except urllib.error.URLError as e:
        raise SystemExit(f"cannot reach {base_url}: {e}\n"
                         f"Is the local server running? Try: curl {base_url}/models")
    return payload["choices"][0]["message"]["content"]


def as_json(text: str, task: str):
    """Small models like to wrap JSON in prose or a fence. Dig it out rather than fail."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start > 0:
        text = text[start:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        bad = DRAFTS / f"_failed-{task}.txt"
        bad.write_text(text, encoding="utf-8")
        raise SystemExit(f"{task}: model did not return valid JSON ({e}).\n"
                         f"Raw output saved to {bad.relative_to(ROOT)}")


def run(day_id: str, tasks: list[str], base_url: str, model: str,
        text_model: str, temperature: float) -> None:
    DRAFTS.mkdir(exist_ok=True)
    out_path = DRAFTS / f"{day_id}.json"
    draft = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {
        "id": day_id, "_draft": True,
        "_provenance": {"base_url": base_url, "vision_model": model,
                        "text_model": text_model, "temperature": temperature,
                        "accepted": False},
        "source": {"page_image": f"source/pages/{day_id}.jpg",
                   "orthography": "original", "transcribed_by": f"MODEL:{model}",
                   "translation_by": None, "translation_reviewed": False},
    }
    image = find_image(day_id)
    draft["source"]["page_image"] = str(image.relative_to(ROOT))

    if "transcribe" in tasks:
        print(f"  transcribing with {model} …")
        r = as_json(call(base_url, model, (PROMPTS / "transcribe.md").read_text(encoding="utf-8"),
                         image, temperature), "transcribe")
        draft["title_mr"] = r.get("title_mr", "")
        draft["date"] = {"label_mr": r.get("date_label_mr", ""), "label_en": ""}
        draft["sentences"] = [{"n": s["n"], "mr": s["mr"], "en": "", "highlight": 0}
                              for s in r.get("sentences", [])]
        draft["paras"] = r.get("paras", [])
        draft["footnote"] = {"marker": r.get("footnote", {}).get("marker", ""),
                             "mr": r.get("footnote", {}).get("mr", ""), "en": ""}
        draft["_illegible"] = r.get("illegible_count", 0)
        print(f"    {len(draft['sentences'])} sentences, {draft['_illegible']} illegible")

    if "marks" in tasks:
        if not draft.get("sentences"):
            raise SystemExit("run --task transcribe first: marks needs the sentence list")
        listing = "\n".join(f'{s["n"]}. {s["mr"]}' for s in draft["sentences"])
        prompt = (PROMPTS / "marks.md").read_text(encoding="utf-8") + "\n\nSENTENCES:\n" + listing
        print(f"  reading underlines with {model} …")
        r = as_json(call(base_url, model, prompt, image, temperature), "marks")
        under = set(r.get("underlined", []))
        for s in draft["sentences"]:
            s["highlight"] = 1 if s["n"] in under else 0
        draft["_marks_uncertain"] = r.get("uncertain", [])
        draft["_marks_note"] = r.get("note", "")
        draft["marks"] = {"kind": "inherited",
                          "by": "an unidentified previous reader of this copy",
                          "count_passages": len(under), "detected_by": f"MODEL:{model}",
                          "confirmed_by_human": False}
        print(f"    {len(under)} underlined, {len(draft['_marks_uncertain'])} uncertain")

    if "translate" in tasks:
        if not draft.get("sentences"):
            raise SystemExit("run --task transcribe first: translate needs the sentences")
        listing = "\n".join(f'{s["n"]}. {s["mr"]}' for s in draft["sentences"])
        prompt = (PROMPTS / "translate.md").read_text(encoding="utf-8") + "\n\nSENTENCES:\n" + listing
        print(f"  translating with {text_model} …")
        r = as_json(call(base_url, text_model, prompt, None, temperature), "translate")
        en = {s["n"]: s["en"] for s in r.get("sentences", [])}
        for s in draft["sentences"]:
            s["en"] = en.get(s["n"], "")
        draft["source"]["translation_by"] = f"MODEL:{text_model}"
        print(f"    {sum(1 for s in draft['sentences'] if s['en'])} translated")

    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out_path.relative_to(ROOT)}")
    print("This is a DRAFT. Nothing reaches the readers until you run:")
    print(f"  python3 conversion/score.py  {day_id}      # if you have a gold file to compare")
    print(f"  python3 conversion/accept.py {day_id}      # review against the scan, then promote")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day")
    ap.add_argument("--task", choices=["transcribe", "marks", "translate", "all"],
                    default="all")
    ap.add_argument("--base-url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL, help="vision model")
    ap.add_argument("--text-model", default=None,
                    help="model for translation (defaults to --model)")
    ap.add_argument("--temperature", type=float, default=0.0)
    a = ap.parse_args()
    tasks = ["transcribe", "marks", "translate"] if a.task == "all" else [a.task]
    print(f"day {a.day} · {a.base_url}")
    run(a.day, tasks, a.base_url, a.model, a.text_model or a.model, a.temperature)


if __name__ == "__main__":
    main()
