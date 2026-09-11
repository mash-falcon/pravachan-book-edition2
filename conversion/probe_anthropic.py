#!/usr/bin/env python3
"""Standalone probe against the Anthropic API. One model, one page, raw output.

    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

    python3 conversion/probe_anthropic.py --image page.jpg
    python3 conversion/probe_anthropic.py --day 01-01 --model claude-opus-5
    python3 conversion/probe_anthropic.py --image page.jpg --prompt "Extract the text."

Self-contained: it imports nothing from this repo, so you can copy this one file
somewhere else and it still works. If you run it inside the repo it will find
conversion/prompts/transcribe.md and source/pages/<day>.jpg for you.

This is the sibling of conversion/probe.py. That one speaks the OpenAI-compatible
/v1/chat/completions shape (the NVIDIA gateway, Ollama, vLLM). This one speaks the
Anthropic Messages API, which formats images differently:

    OpenAI-compatible : {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    Anthropic         : {"type": "image", "source": {"type": "base64", "media_type": ..., "data": ...}}

Claude models via your NVIDIA gateway (aws/anthropic/..., azure/anthropic/...) go
through the OpenAI-compatible shape instead — use probe.py for those.
"""
import argparse, base64, collections, json, os, pathlib, re, sys, time

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# The forms this edition prints, and what a model "corrects" them to.
ORTHOGRAPHY = [
    ("नांव", "नाव"), ("कांहीं", "काही"), ("नाहीं", "नाही"), ("केलीं", "केली"),
    ("हें", "हे"), ("तें", "ते"), ("असें", "असे"), ("घ्यावें", "घ्यावे"),
    ("जसें", "जसे"), ("शेवटीं", "शेवटी"), ("मुळांत", "मुळात"),
]

FALLBACK_PROMPT = """You are transcribing one page of a printed Marathi devotional book.

Transcribe EXACTLY what is printed. This book uses OLDER MARATHI ORTHOGRAPHY —
preserve it letter for letter. Do not "correct" नांव to नाव, कांहीं to काही,
नाहीं to नाही, तें to ते, or हें to हे. If a spelling looks wrong to you, it is
probably correct for this edition. Do not normalise anusvara or vowel length.

Split into sentences, numbered from 1. Mark illegible words as [?].

Return ONLY valid JSON:
{"title_mr": "...", "sentences": [{"n": 1, "mr": "..."}], "footnote": {"mr": "..."}}
"""

MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}


def orthography_report(text: str) -> None:
    """Whole-word counting. Substrings get this wrong: ते is inside होते and
    तेव्हां, हे is inside आहे — naive matching flags a faithful page as modernised."""
    counts = collections.Counter(re.findall(r"[ऀ-ॿ]+", text))
    rows = [(old, counts[old], new, counts[new]) for old, new in ORTHOGRAPHY
            if counts[old] or counts[new]]
    print("\nORTHOGRAPHY")
    if not rows:
        print("  none of the tracked forms appear — too little Devanagari to judge")
        return
    kept = sum(r[1] for r in rows)
    lost = sum(r[3] for r in rows)
    print(f"  {'book form':<12}{'kept':>6}   {'modern form':<12}{'used':>6}")
    for old, a, new, b in rows:
        print(f"  {old:<12}{a:>6}   {new:<12}{b:>6}{'  <-- modernised' if b else ''}")
    print(f"\n  kept {kept} book form(s), used {lost} modern form(s)")
    if lost:
        print("  VERDICT: this model rewrites the orthography. Usable only if every")
        print("           sentence is corrected by hand — most of the work it was to save.")
    else:
        print("  VERDICT: orthography preserved in this sample.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="claude-sonnet-5",
                    help="claude-sonnet-5 (default), claude-opus-5, claude-haiku-4-5-20251001")
    ap.add_argument("--image", help="path to the page image")
    ap.add_argument("--day", help="use source/pages/<day>.jpg from this repo")
    ap.add_argument("--prompt", help="send this instead of the transcription prompt")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="Devanagari is token-hungry; 1024 truncates a full page")
    ap.add_argument("--temperature", type=float, default=0.0)
    a = ap.parse_args()

    if a.image:
        image = pathlib.Path(a.image)
    elif a.day:
        image = next((p for e in MEDIA
                      for p in [ROOT / "source" / "pages" / f"{a.day}{e}"] if p.exists()), None)
        if image is None:
            sys.exit(f"no scan at source/pages/{a.day}.[jpg|png]")
    else:
        sys.exit("give --image or --day")
    if not image.exists():
        sys.exit(f"{image} not found")

    media_type = MEDIA.get(image.suffix.lower())
    if media_type is None:
        sys.exit(f"unsupported image type {image.suffix} (jpg, png, gif, webp)")

    prompt = a.prompt
    if prompt is None:
        p = HERE / "prompts" / "transcribe.md"
        prompt = p.read_text(encoding="utf-8") if p.exists() else FALLBACK_PROMPT

    b64 = base64.standard_b64encode(image.read_bytes()).decode()
    client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY

    print(f"model  : {a.model}")
    print(f"image  : {image}  ({image.stat().st_size/1024:.0f} KB, {media_type})")
    print(f"prompt : {'custom' if a.prompt else 'conversion/prompts/transcribe.md'}")
    print(f"limit  : max_tokens {a.max_tokens}\n")

    t0 = time.time()
    try:
        msg = client.messages.create(
            model=a.model,
            max_tokens=a.max_tokens,
            temperature=a.temperature,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {"type": "base64",
                                             "media_type": media_type, "data": b64}},
            ]}],
        )
    except anthropic.APIStatusError as e:
        sys.exit(f"HTTP {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        sys.exit(f"could not reach the API: {e}")
    secs = time.time() - t0

    # Join every text block rather than taking content[0]: a response can begin with
    # a non-text block, and taking the first one silently drops the rest.
    text = "".join(b.text for b in msg.content if b.type == "text")

    print(f"{secs:.1f}s   stop_reason={msg.stop_reason}   "
          f"tokens in/out {msg.usage.input_tokens}/{msg.usage.output_tokens}")
    if msg.stop_reason == "max_tokens":
        print("  TRUNCATED — the page did not fit. Re-run with a larger --max-tokens.")

    out = ROOT / "content" / "drafts" / "probes"
    if out.parent.exists():
        out.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", a.model).strip("_")
        dest = out / f"{a.day or image.stem}__{slug}__anthropic.txt"
        dest.write_text(text, encoding="utf-8")
    else:
        dest = None

    print("\n" + "-" * 78)
    print(text[:3000] + ("\n… (truncated for display)" if len(text) > 3000 else ""))
    print("-" * 78)
    if dest:
        print(f"full response: {dest.relative_to(ROOT)}")

    body = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        parsed = json.loads(body[body.find("{"):] if "{" in body else body)
        print(f"\nJSON: parsed ok — keys {list(parsed)[:8]}")
        if isinstance(parsed.get("sentences"), list):
            print(f"      {len(parsed['sentences'])} sentences returned")
    except Exception as e:
        print(f"\nJSON: did not parse ({type(e).__name__}) — fine for a probe")

    orthography_report(text)


if __name__ == "__main__":
    main()
