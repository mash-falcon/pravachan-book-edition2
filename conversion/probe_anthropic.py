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

FALLBACK_PROMPT = """You are transcribing one page of a printed Marathi devotional book.

Transcribe EXACTLY what is printed. This book uses OLDER MARATHI ORTHOGRAPHY —
preserve it letter for letter. Do not "correct" नांव to नाव, कांहीं to काही,
नाहीं to नाही, तें to ते, or हें to हे. If a spelling looks wrong to you, it is
probably correct for this edition. Do not normalise anusvara or vowel length.

Split the BODY into sentences, numbered from 1. Mark illegible words as [?].

The page title and the date are NOT sentences. Put them in their own fields and do
not repeat them in the sentence list. The footnote is not a sentence either.

Return ONLY valid JSON:
{"title_mr": "...", "date_label_mr": "e.g. २ जानेवारी",
 "sentences": [{"n": 1, "mr": "..."}], "footnote": {"marker": "२", "mr": "..."}}
"""

MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}


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
    ap.add_argument("--model", default="claude-sonnet-5",
                    help="claude-sonnet-5 (default), claude-opus-5, claude-haiku-4-5-20251001")
    ap.add_argument("--image", help="path to the page image")
    ap.add_argument("--day", help="use source/pages/<day>.jpg from this repo")
    ap.add_argument("--prompt", help="send this instead of the transcription prompt")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="Devanagari is token-hungry; 1024 truncates a full page")
    ap.add_argument("--temperature", type=float, default=None,
                    help="omitted unless given; not every model accepts it")
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

    prompt, prompt_src = a.prompt, "custom (--prompt)"
    if prompt is None:
        pf = HERE / "prompts" / "transcribe.md"
        if pf.exists():
            prompt, prompt_src = pf.read_text(encoding="utf-8"), str(pf)
        else:
            prompt, prompt_src = FALLBACK_PROMPT, "built-in fallback (no prompts/ beside this file)"

    b64 = base64.standard_b64encode(image.read_bytes()).decode()
    client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY

    print(f"model  : {a.model}")
    print(f"image  : {image}  ({image.stat().st_size/1024:.0f} KB, {media_type})")
    print(f"prompt : {prompt_src}")
    print(f"limit  : max_tokens {a.max_tokens}\n")

    kwargs = {
        "model": a.model,
        "max_tokens": a.max_tokens,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image", "source": {"type": "base64",
                                         "media_type": media_type, "data": b64}},
        ]}],
    }
    if a.temperature is not None:
        kwargs["temperature"] = a.temperature

    t0 = time.time()
    try:
        try:
            msg = client.messages.create(**kwargs)
        except TypeError as e:
            # Not every SDK version and model accepts temperature. Losing it costs
            # a little determinism; failing the whole run costs the run.
            if "temperature" not in str(e):
                raise
            print("  note: this SDK/model rejects `temperature` — retrying without it")
            kwargs.pop("temperature", None)
            msg = client.messages.create(**kwargs)
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

    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", a.model).strip("_")
    name = f"{a.day or image.stem}__{slug}__anthropic.txt"
    if (HERE / "prompts").exists():                  # running inside the repo
        dest = ROOT / "content" / "drafts" / "probes" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
    else:                                            # standalone: write beside you
        dest = pathlib.Path.cwd() / name
    dest.write_text(text, encoding="utf-8")

    print("\n" + "-" * 78)
    print(text[:3000] + ("\n… (truncated for display)" if len(text) > 3000 else ""))
    print("-" * 78)
    print(f"full response: {dest}")

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
