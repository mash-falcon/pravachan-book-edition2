#!/usr/bin/env python3
"""Try ONE model on ONE page and look at what actually comes back.

    python3 conversion/probe.py --list
    python3 conversion/probe.py --model nvidia/baidu/paddleocr-vl --day 01-01
    python3 conversion/probe.py --model X --day 01-01 --task marks
    python3 conversion/probe.py --model X --image some.png --prompt "Extract the text."

Use this before conversion/bakeoff.py. The bake-off gives you a score; this gives you
the raw text the model produced, so you can see *how* it is wrong. Nothing is written
to content/ — the raw response goes to content/drafts/probes/.

Standard library only; no `requests`, no SDK, nothing to pip install.

Environment:
    PRAVACHAN_BASE_URL   e.g. https://inference-api.nvidia.com/v1
    PRAVACHAN_API_KEY    your token
"""
import argparse, base64, collections, json, os, pathlib, re, sys, time
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "conversion" / "prompts"
PROBES = ROOT / "content" / "drafts" / "probes"
PAGES = ROOT / "source" / "pages"

BASE_URL = os.environ.get("PRAVACHAN_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("PRAVACHAN_API_KEY", "local")

# The forms this edition prints, and what a model "corrects" them to.
# Counting these in raw output detects modernisation without needing a gold file.
ORTHOGRAPHY = [
    ("नांव", "नाव"), ("कांहीं", "काही"), ("नाहीं", "नाही"), ("केलीं", "केली"),
    ("हें", "हे"), ("तें", "ते"), ("असें", "असे"), ("घ्यावें", "घ्यावे"),
    ("आहेत", "आहेत"), ("जसें", "जसे"), ("शेवटीं", "शेवटी"), ("मुळांत", "मुळात"),
]


def http(method: str, path: str, body: dict | None = None, timeout: int = 1800):
    url = BASE_URL.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:800]
        raise SystemExit(f"HTTP {e.code} from {url}\n{detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"cannot reach {url}: {e.reason}\n"
                         f"Check PRAVACHAN_BASE_URL (currently {BASE_URL}).")


def list_models() -> None:
    payload = http("GET", "/models", None, timeout=60)
    names = sorted(m.get("id", "?") for m in payload.get("data", []))
    print(f"{len(names)} model(s) at {BASE_URL}\n")
    for n in names:
        print(" ", n)


def words(text: str) -> "collections.Counter[str]":
    """Whole Devanagari words. Substring counting is wrong here: ते is inside होते
    and तेव्हां, हे is inside आहे — naive counting flags a faithful page as modernised."""
    return collections.Counter(re.findall(r"[\u0900-\u097F]+", text))


def orthography_report(text: str) -> None:
    """Does the output keep the book's spelling, or quietly modernise it?"""
    counts = words(text)
    rows, kept, lost = [], 0, 0
    for old, new in ORTHOGRAPHY:
        if old == new:
            continue
        a, b = counts[old], counts[new]
        if a or b:
            rows.append((old, a, new, b))
            kept += a
            lost += b
    print("\nORTHOGRAPHY")
    if not rows:
        print("  none of the tracked forms appear — too little text to judge")
        return
    print(f"  {'book form':<12}{'kept':>6}   {'modern form':<12}{'used':>6}")
    for old, a, new, b in rows:
        warn = "  <-- modernised" if b else ""
        print(f"  {old:<12}{a:>6}   {new:<12}{b:>6}{warn}")
    print(f"\n  kept {kept} book form(s), used {lost} modern form(s)")
    if lost:
        print("  VERDICT: this model rewrites the orthography. Usable only if every")
        print("           sentence is corrected by hand, which is most of the work.")
    elif kept:
        print("  VERDICT: orthography preserved in this sample. Score it properly next:")
        print("           python3 conversion/score.py 01-01")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list models the gateway offers")
    ap.add_argument("--model")
    ap.add_argument("--day", help="use source/pages/<day>.jpg")
    ap.add_argument("--image", help="use this image instead")
    ap.add_argument("--task", choices=["transcribe", "marks", "translate"], default="transcribe")
    ap.add_argument("--prompt", help="send this instead of the task prompt")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="Devanagari is token-hungry; 1024 truncates a full page (default 8192)")
    ap.add_argument("--temperature", type=float, default=0.0)
    a = ap.parse_args()

    if a.list:
        list_models()
        return
    if not a.model:
        raise SystemExit("--model is required (or use --list)")

    if a.image:
        image = pathlib.Path(a.image)
    elif a.day:
        image = next((PAGES / f"{a.day}{e}" for e in (".jpg", ".jpeg", ".png", ".JPG", ".PNG")
                      if (PAGES / f"{a.day}{e}").exists()), None)
        if image is None:
            raise SystemExit(f"no scan at source/pages/{a.day}.[jpg|png]")
    else:
        raise SystemExit("give --day or --image")

    prompt = a.prompt or (PROMPTS / f"{a.task}.md").read_text(encoding="utf-8")
    if a.task in ("marks", "translate") and not a.prompt and a.day:
        gold = ROOT / "content" / "days" / f"{a.day}.json"
        if gold.exists():
            d = json.loads(gold.read_text(encoding="utf-8"))
            listing = "\n".join(f'{s["n"]}. {s["mr"]}' for s in d["sentences"])
            prompt += "\n\nSENTENCES:\n" + listing
            print("(using the verified sentences for this day as context)")

    mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(image.read_bytes()).decode()
    body = {
        "model": a.model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "temperature": a.temperature,
        "max_tokens": a.max_tokens,
        "stream": False,
    }

    print(f"model  : {a.model}")
    print(f"image  : {image}  ({image.stat().st_size/1024:.0f} KB)")
    print(f"task   : {a.prompt and 'custom prompt' or a.task}   max_tokens {a.max_tokens}")
    print(f"url    : {BASE_URL}\n")

    t0 = time.time()
    payload = http("POST", "/chat/completions", body)
    secs = time.time() - t0

    choice = payload["choices"][0]
    text = choice["message"]["content"] or ""
    usage = payload.get("usage", {})
    finish = choice.get("finish_reason")

    print(f"{secs:.1f}s   finish_reason={finish}   "
          f"tokens in/out {usage.get('prompt_tokens','?')}/{usage.get('completion_tokens','?')}")
    if finish == "length":
        print("  TRUNCATED — the page did not fit. Re-run with a larger --max-tokens.")

    PROBES.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", a.model).strip("_")
    raw = PROBES / f"{a.day or image.stem}__{slug}__{a.task}.txt"
    raw.write_text(text, encoding="utf-8")

    print("\n" + "─" * 78)
    print(text[:3000] + ("\n… (truncated for display)" if len(text) > 3000 else ""))
    print("─" * 78)
    print(f"full response: {raw.relative_to(ROOT)}")

    stripped = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        parsed = json.loads(stripped[stripped.find("{"):] if "{" in stripped else stripped)
        keys = list(parsed)[:8]
        print(f"\nJSON: parsed ok — keys {keys}")
        if "sentences" in parsed:
            print(f"      {len(parsed['sentences'])} sentences returned")
    except Exception as e:
        print(f"\nJSON: did NOT parse ({type(e).__name__}). "
              f"Fine for a probe; assist.py tolerates fences and leading prose.")

    if a.task == "transcribe" or a.prompt:
        orthography_report(text)


if __name__ == "__main__":
    main()
