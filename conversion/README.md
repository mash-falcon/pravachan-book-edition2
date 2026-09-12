# Conversion — a page image becomes a day file

## The whole thing in one command

```bash
python3 conversion/pipeline.py \
    --image ~/Downloads/Edn2_Jan02.JPG --id 01-02 \
    --out-full renders/jan02.html --out-summary renders/jan02-summary.html
```

Every stage writes a named artifact you can read and edit, because the model's
output needs correcting and the corrections must survive:

| artifact | what it is |
|---|---|
| `work/<id>/1-transcript.mr.txt` | raw Marathi, plain text, one sentence per line |
| `work/<id>/1-transcript.json` | the same, structured |
| `work/<id>/2-english.txt` | the translation, aligned by sentence number |
| `work/<id>/2-english.json` | the same, structured |
| `work/<id>/3-marks.json` | which sentences the previous reader underlined |
| `work/<id>/4-day.json` | everything merged — the file the readers read |
| `work/<id>/5-summary.json` | the summary essay and the day's practice |

Every artifact records **who made it and when**, and a skipped stage prints that:

```
[transcribe] skipped — 1-transcript.json already exists
          made by anthropic:claude-sonnet-5 at 2026-09-11T14:02:18+05:30
```

If a run skips every stage it says **NO MODEL WAS CALLED** rather than letting a
rendered page imply one was. An artifact from another source reports
`origin UNRECORDED`.

Re-running skips any stage whose artifact already exists, so fixing
`1-transcript.mr.txt` by hand and re-running costs nothing:

```bash
python3 conversion/pipeline.py --image X.jpg --id 01-02 --only marks     # redo one stage
python3 conversion/pipeline.py --image X.jpg --id 01-02 --from merge     # no model calls
python3 conversion/pipeline.py --image X.jpg --id 01-02 --force          # redo everything
```

### OCR models are different

`nvidia/baidu/paddleocr-vl` is an OCR engine, not an instruction-following model. Ask
it for JSON with sentence numbers and a paragraph map and it will either ignore you
or guess. So the pipeline treats it differently — automatically, when the model name
contains `ocr`, or with `--ocr`:

- it sends `prompts/transcribe_ocr.md`, which asks only for the text;
- the raw response is kept at `work/<id>/0-ocr-raw.txt`;
- **the splitting happens in `conversion/structure.py`**, in code, where it is testable.

Round-tripped against the verified 2 January page — title, date and footnote
recovered, and 13 of 13 body sentences byte-identical. The one difference is a real
editorial call: our sentence 1 holds two questions, and the splitter separates them
at the `?`. No text is lost either way.

Two things OCR mode cannot give you:

- **Paragraph breaks.** They are not in the text stream. `paras` comes back as one
  block covering every sentence; split it by reading the scan.
- **Underlines.** An OCR model reads printed glyphs, not pencil. The marks stage is
  skipped unless you pass `--marks-model` naming a vision-language model.

```bash
python3 conversion/pipeline.py --image scan.jpg --id 01-02 \
    --base-url https://inference-api.nvidia.com/v1 \
    --model nvidia/baidu/paddleocr-vl \
    --marks-model gcp/google/gemini-3.8-flash \
    --text-model nvidia/moonshotai/kimi-k3 \
    --out-full renders/jan02-ocr.html
```

That splits the work three ways: OCR transcribes, a vision-language model reads the
pencil, a large text model translates and drafts the summary.

### Which models actually work

Before spending a page on a model, find out whether it answers at all and whether it
can see an image:

```bash
export PRAVACHAN_BASE_URL=https://inference-api.nvidia.com/v1
export PRAVACHAN_API_KEY="$NVIDIA_API_KEY"      # or paste the token

python3 conversion/ping.py --models conversion/models.example.txt --image
```

A bare `--image` sends a 1×1 pixel, which separates text-only models from
vision-capable ones for almost nothing. The summary at the end lists which are
usable for the transcribe and marks stages.

Two results are worth reading carefully rather than at face value:

- **`empty 'choices'` with a usage block.** A reasoning model spends its budget
  thinking and returns no text if the budget runs out. `ping.py` detects that shape
  and retries with 4096 tokens before calling the model unusable. If you see it as a
  final verdict, raise `--max-tokens`.
- **"text only" on a model whose name says vision.** That is usually the gateway
  rejecting the image encoding for that route, not the model lacking vision. Read
  the HTTP error printed beneath it before ruling the model out.

`ping.py` prints the gateway's own error text. A hand-written snippet that indexes
`response.json()["choices"]` without checking the status fails as
`KeyError: 'choices'`, which says nothing — most often the cause is an unexpanded
`"Bearer $API_KEY"` in a Python string, and `ping.py` detects that specific case and
says so.

### Several models at once

Different stages want different models, and `--recipe` names the set:

```bash
python3 conversion/pipeline.py --image scan.jpg --id 01-02 \
    --recipe conversion/recipes/nvidia-split.json --out-full renders/jan02.html
```

`conversion/recipes/nvidia-split.json` sends OCR to `paddleocr-vl`, underline
detection to a vision-language model, and translation plus summary to a large text
model. Explicit flags still override the recipe.

### Using disagreement to target review

`conversion/consensus.py` runs several models over the same page and reports where
they differ. The point is not a better answer by vote — it is knowing **where to
look**. Reading all 365 pages against the scan will not happen; reading the handful
of lines where independent models disagree will.

```bash
python3 conversion/consensus.py --image scan.jpg --id 01-02 --stage transcribe \
    --models nvidia/baidu/paddleocr-vl,azure/openai/gpt-5.6-sol,aws/anthropic/bedrock-claude-opus-4-8
python3 conversion/consensus.py --image scan.jpg --id 01-02 --stage marks --models ...
```

The marks stage needs a sentence list. It uses `work/<id>/1-transcript.json` if one
exists, and otherwise falls back to `content/days/<id>.json` — which is better, since
those sentences are verified. When that file also records underlines, each model is
scored against them:

```
recorded marks    : [2, 5, 7, 14]
    model-A: found 4/4
    model-B: found 4/4, INVENTED [8]
    model-C: found 3/4, missed [5]
```

An invented mark is called out separately from a missed one on purpose: a miss loses
information, an invention attributes something to the previous reader that they
never wrote.

Exercised against the verified 2 January page with three simulated models — one
faithful, one making the `ठेवाचें`/`ठेवावें` slip Claude actually made, one
modernising `नांव` to `नाव`:

```
unanimous   : 12/14
need a human: [2, 9]
  [9]  A,C: म्हणून नामाचें साधन चालू ठेवावें.
       B  : म्हणून नामाचें साधन चालू ठेवाचें.
```

Two sentences to check instead of fourteen, and both real errors surfaced. On marks
it reports what every model agreed on and what only some marked:

```
all models agree : [2, 5, 7, 14]
disputed         : [9]   marked by [C], not by [A, B]
```

Nothing here writes to `content/`. Consensus never picks a winner on a contested
item — it records every variant and leaves the decision to a person with the scan.

**Agreement is not correctness.** It means the models failed the same way or not at
all — three models sharing a training bias toward modern spelling will agree
confidently and be wrong together. Disagreement is the reliable signal; agreement
only narrows where to spend attention.

### Which endpoint

`--base-url` decides the API shape. Anything containing `anthropic.com` speaks the
Messages API and reads `ANTHROPIC_API_KEY`; everything else speaks OpenAI-compatible
`/v1/chat/completions` and reads `PRAVACHAN_API_KEY`. No SDK either way.

```bash
--base-url https://api.anthropic.com/v1      --model claude-sonnet-5
--base-url https://inference-api.nvidia.com/v1 --model nvidia/baidu/paddleocr-vl
--base-url http://localhost:11434/v1         --model qwen2.5vl:7b
```

The run prints which provider it picked, so a misconfigured URL shows up on line one
rather than as a confusing HTTP error.

### It is a repository tool

`pipeline.py` needs `conversion/assist.py` beside it, and `templates/` and
`tools/build.py` above it to render. **Run it from inside a clone**, not from a copy
dropped in another directory — it says so if you try. For a single self-contained
call, `conversion/probe_anthropic.py` is the file to copy around.

Two safety defaults worth knowing:

- The merged day is **not** copied into `content/days/` unless you pass `--promote`.
- `render` never overwrites an existing `content/days/<id>.json`. If you have already
  corrected a day by hand, re-running the pipeline will not silently undo it.

### The summary, and what fences it in

The summary stage drafts the short edition from the underlined passages. A model is
allowed to write it, but inside a hard boundary:

- `prompts/summary.md` says the underlined passages carry the argument and the
  model's own sentences only connect them, and that **every claim must be cited**
  as `{{n}}` pointing at an underlined sentence.
- `validate.py` **refuses the file** if any citation points at a sentence that is not
  underlined. Not a warning — a build-blocking error.

That check is what keeps the short page an abridgement of the previous reader's
marks rather than an essay the model felt like writing. Verified: adding a citation
to an unmarked sentence fails validation with exit code 1.

It still needs reading. The guard proves *where* a claim came from, not that the
Marathi is idiomatic or the argument fair.

## Doing it stage by stage

```
source/pages/01-01.jpg          the scan
        │
        │  python3 conversion/new_day.py 01-01      scaffold the JSON
        ▼
content/days/01-01.json         transcription, translation, marks, commentary
        │
        │  python3 conversion/validate.py           checks before anything renders
        │  python3 tools/build.py                   injects data into the templates
        ▼
apps/full-page/01-01.html       the reader
apps/short-page/01-01.html
```

### Or by hand, without any model

1. `python3 conversion/new_day.py 01-02`
2. Transcribe the Marathi **sentence by sentence**, in the book's **original
   orthography** — नांव, कांहीं, केलीं, नाहीं. Do not modernise. A spelling
   toggle can be added later as a transform; a silent change now is unrecoverable.
3. Set `highlight: 1` on any sentence the previous reader underlined. Where an
   underline runs across two or more consecutive sentences, give them all the same
   `group` number so they read as one passage.
4. Fill `paras` with the paragraph breaks as `[first, last]` sentence pairs.
   Together they must tile every sentence exactly once.
5. Translate. Leave `en` empty rather than guessing; the validator warns, and the
   apps degrade rather than lie.
6. `python3 conversion/validate.py 01-02`, then `python3 tools/build.py 01-02`.

## Using a local model

The tooling here has **no model dependency** — `assist.py` speaks the
OpenAI-compatible `/v1/chat/completions` API using only the standard library, so it
works with Ollama, llama.cpp's server, LM Studio or vLLM. No SDK, no pip install.

```bash
# 1. calibrate on a day you already trust
cp <your scan of 1 Jan> source/pages/01-01.jpg
python3 conversion/assist.py 01-01 --model qwen2.5vl:7b
python3 conversion/score.py  01-01          # measures the model against verified content

# 2. only if the score is acceptable, run a new day
cp <your scan of 2 Jan> source/pages/01-02.jpg
python3 conversion/assist.py 01-02 --model qwen2.5vl:7b
python3 conversion/accept.py 01-02                          # read it against the scan
python3 conversion/accept.py 01-02 --promote --by "Name"    # then promote
python3 conversion/validate.py 01-02 && python3 tools/build.py 01-02
```

Configuration is by flag or environment: `PRAVACHAN_BASE_URL` (default
`http://localhost:11434/v1`), `PRAVACHAN_MODEL`, and `PRAVACHAN_API_KEY` — which is
simply the token you would send as `Authorization: Bearer <token>`. If
`NVIDIA_API_KEY` or `OPENAI_API_KEY` is already exported, it is used automatically
and you need not set a project-specific name at all.
Use `--text-model` to translate with a different, larger model than the vision one.

Against a hosted gateway rather than a local server, set both:

```bash
export PRAVACHAN_BASE_URL=https://<your-gateway>/v1
export PRAVACHAN_API_KEY=<token>
```

## Trying one model first

Before the bake-off, look at what a single model actually returns:

```bash
cp .env.example .env && $EDITOR .env && source .env

python3 conversion/probe.py --list                                   # what the gateway offers
python3 conversion/probe.py --model nvidia/baidu/paddleocr-vl --day 01-01
python3 conversion/probe.py --model <a vision model> --day 01-01 --task marks
python3 conversion/probe.py --model X --image any.png --prompt "Extract the text."
```

`probe.py` prints the raw response, latency, token counts and `finish_reason`, saves
the full text to `content/drafts/probes/`, and then runs an **orthography check that
needs no verified day file**: it counts whole Devanagari words and reports how often
the model used the book's form versus the modern one.

Two things that check gets right, both learned the hard way:

**It counts whole words, not substrings.** ते sits inside होते and तेव्हां, हे inside
आहे. Substring counting reported a perfectly faithful page as modernised.

**Only unambiguous pairs decide the verdict.** नाहीं→नाही and कांहीं→काही are real
evidence: the modern spelling has no other reading. But तें→ते proves nothing, because
**ते is also the ordinary word for "they"** — a page about ants finding sugar will
contain ते legitimately. Six of the eleven pairs are like this. They are printed under
"ambiguous" and excluded from the verdict, so a clean transcription is not condemned
by a pronoun.

### Against the Anthropic API directly

`probe.py` speaks the OpenAI-compatible shape. The Anthropic Messages API formats
images differently, so there is a separate standalone script for it:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 conversion/probe_anthropic.py --day 01-01 --model claude-sonnet-5
```

It imports nothing from this repo — copy the single file anywhere and it still runs,
falling back to a built-in transcription prompt if `prompts/transcribe.md` is absent.

Note the two request shapes differ:

| | image block |
|---|---|
| OpenAI-compatible | `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,…"}}` |
| Anthropic | `{"type": "image", "source": {"type": "base64", "media_type": …, "data": …}}` |

Claude models reached **through the NVIDIA gateway** (`aws/anthropic/…`,
`azure/anthropic/…`) use the OpenAI-compatible shape — use `probe.py` for those.
This script is only for `api.anthropic.com`.

It is also the one place in this repo that needs a pip install. Everything else is
standard library.

### max_tokens

A full page of Devanagari does not fit in 1024 tokens. The default here is **8192**,
and both `probe.py` and `assist.py` warn when `finish_reason` comes back as `length`.
If a model returns half a page, that is usually the cause, not the model.

## Comparing models

Which model to use is an empirical question, not one to settle from model names.

```bash
python3 conversion/bakeoff.py 01-01 --models conversion/models.example.txt
```

Runs each model over the same page and prints one table. It refuses to run on a day
that has no verified file in `content/days/`, because there would be nothing to score
against. Drafts go to `content/drafts/bakeoff/` and cannot reach the readers.

**Rank on the MODERN column, not on char accuracy.** A model that rewrites नांव as
नाव will show 99% character accuracy and be unusable. A model with a lower character
score but zero modernisation is the better one, because its errors are visible.

Two things the table will not tell you, and you must check by eye:

- whether the translation is any good — it is scored only for coverage;
- whether the underlines are right. Confirm every mark against the scan even at
  100% F1. A mark the model invents attributes something to the previous reader
  that they never marked.

Drafts land in `content/drafts/` and **never** in `content/days/`. Only
`accept.py --promote` moves them, and it requires a name.

## Read the score, not the accuracy

`score.py` compares a draft to a verified day file. The number that matters is not
character accuracy — it is **silent modernisation**: the model writing नाव where the
book prints नांव. A simulated draft that modernised the spelling of 15 of 23
sentences still scored **99.1% mean character accuracy**. Character accuracy will
tell you the model is excellent while it quietly rewrites the text.

`score.py` detects this directly: if two sentences differ only by anusvara, or only
by anusvara and vowel length, it is reported as MODERNISED rather than as a small
error. Any non-zero count there means the transcription needs correcting by hand.

It also reports underline detection as precision/recall, and calls out **invented**
marks separately from missed ones — a false positive attributes something to the
previous reader that they did not mark, which is worse than missing one.

## Why there is no automatic OCR path

The book is set in older Marathi orthography. General-purpose OCR normalises those
spellings without saying so — and a language model does it more confidently, because
its training says Marathi looks like the modern form. A silent alteration to a
devotional text is worse than no automation. That is why model output goes to a
draft field for a human to accept, never straight into `mr`.

Underline detection deserves the same suspicion. These are hand-drawn lines under
printed Devanagari, sometimes spanning two sentences, sometimes stopping mid-clause.
A model will answer confidently and be roughly right, and "roughly right" here means
silently changing what a previous reader marked. Confirm every mark against the scan.

## What the validator enforces

Errors block a build; warnings do not.

- sentence numbers run 1..N with no gaps, and every `mr` contains Devanagari
- `paras` tile the sentences exactly once, in order
- a `group` is a consecutive run, and all of its members are underlined
- commentary anchors point at sentences that exist
- **every `{{n}}` citation in a summary points at a sentence that is actually
  underlined** — this is what keeps the short page honest about being built from
  the inherited marks
- warns when a translation, page image, named author, or Marathi review is missing
