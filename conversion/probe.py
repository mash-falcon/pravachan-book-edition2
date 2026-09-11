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

# Book form -> modern form.
# STRONG pairs: the modern spelling has no other reading, so seeing it is real
# evidence the model normalised the text.
STRONG = [
    ("नांव", "नाव"), ("कांहीं", "काही"), ("नाहीं", "नाही"),
    ("शेवटीं", "शेवटी"), ("मुळांत", "मुळात"), ("पाहिजें", "पाहिजे"),
]
# AMBIGUOUS pairs: the "modern" form is also an ordinary Marathi word, so a count
# here proves nothing. ते is "they", हे is "these", केली is the feminine past —
# all legitimate. Reported for information, never counted toward the verdict.
AMBIGUOUS = [
    ("तें", "ते"), ("हें", "हे"), ("असें", "असे"),
    ("केलीं", "केली"), ("घ्यावें", "घ्यावे"), ("जसें", "जसे"),
]
ORTHOGRAPHY = STRONG + AMBIGUOUS


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
    """Whole-word counting, and only STRONG pairs decide the verdict.

    Substring matching gets this wrong (ते sits inside होते), and so does treating
    every pair as diagnostic: ते is also the plural pronoun "they", so one of them
    on a page is ordinary Marathi, not evidence of anything."""
    counts = collections.Counter(re.findall(r"[ऀ-ॿ]+", text))

    def rows(pairs):
        return [(o, counts[o], n, counts[n]) for o, n in pairs if counts[o] or counts[n]]

    strong, ambig = rows(STRONG), rows(AMBIGUOUS)
    print("\nORTHOGRAPHY")
    if not strong and not ambig:
        print("  none of the tracked forms appear — too little Devanagari to judge")
        return

    def show(title, rs):
        if not rs:
            return
        print(f"  {title}")
        print(f"    {'book form':<12}{'kept':>6}   {'modern form':<12}{'used':>6}")
        for o, a, n, b in rs:
            print(f"    {o:<12}{a:>6}   {n:<12}{b:>6}{'   <-- modernised' if b else ''}")

    show("diagnostic", strong)
    show("ambiguous (the modern form is also a normal word — not counted)", ambig)

    kept = sum(r[1] for r in strong)
    lost = sum(r[3] for r in strong)
    amb_modern = sum(r[3] for r in ambig)
    print(f"\n  diagnostic: kept {kept} book form(s), used {lost} modern form(s)")
    if lost:
        print("  VERDICT: this model rewrites the orthography. Usable only if every")
        print("           sentence is corrected by hand — most of the work it was to save.")
    elif kept:
        print("  VERDICT: orthography preserved on the forms that can prove it.")
        if amb_modern:
            print(f"           ({amb_modern} ambiguous form(s) present; check a few by eye,")
            print("            but ते/हे/केली are ordinary words and usually mean nothing.)")
    else:
        print("  VERDICT: no diagnostic form appeared — this page cannot judge the model.")

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
