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

## Why there is no OCR step

The book is set in older Marathi orthography. General-purpose OCR normalises those
spellings without saying so, and a silent alteration to a devotional text is worse
than no automation at all. If OCR is added later it should write to a **separate
draft field** for a human to accept, never straight into `mr`.

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
