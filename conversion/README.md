# Conversion — a page image becomes a day file

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

## Doing one day

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
`http://localhost:11434/v1`), `PRAVACHAN_MODEL`, `PRAVACHAN_API_KEY`.
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
the model used the book's form (नांव, कांहीं, नाहीं, तें, हें) versus the modern one.

That check is the fastest useful signal you can get from one call. On the 1 January
text it reports 28 book forms and 0 modern forms for a faithful transcription, and
the exact inverse for a modernised one.

Note it counts **whole words**, not substrings — ते is inside होते and तेव्हां, हे is
inside आहे, so substring counting flags a perfectly faithful page as modernised.

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
