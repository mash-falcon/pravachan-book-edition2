# प्रवचने — a digital edition

A daily-reading edition of **श्री ब्रह्मचैतन्य गोंदवलेकर महाराज — प्रवचने**: one discourse
for each day of the year, set from scans of a printed Marathi edition, in its
**original orthography**.

One physical copy of the book carries a previous reader's hand underlines. Those
marks are preserved as their own layer — labelled as that reader's, never as the
author's emphasis, and never as editorial apparatus.

> **Read [RIGHTS.md](RIGHTS.md) first.** This repository is public, the rights
> position for the printed source is unconfirmed, and the translation and
> commentary are unreviewed drafts. Page scans are deliberately not committed yet.

## What is here

```
content/days/01-01.json      the discourse: sentences, marks, paragraphs, commentary
summary/days/01-01.json      the summary essay and the day's practice
source/pages/                page scans, one per day  (empty — see RIGHTS.md)

conversion/                  scan → day file: scaffold, rules, validator
tools/build.py               day file → reader pages
templates/                   the two readers, before data is injected

apps/full-page/              READER 1 — the whole discourse, one page a day
apps/short-page/             READER 2 — the summary, and the marked passages

archive/                     earlier designs and the two independent reviews
docs/                        plain-text transcript
```

## The two readers

**`apps/full-page/`** — the complete discourse as a book page. Marathi first, with
inline English on a toggle; the previous reader's underlines with a provenance note;
editorial commentary anchored in the margin and switchable off; a facsimile panel;
and a page budget. The page is A5-proportioned and the **type never drops below
17px** — a long day extends onto a second page rather than shrinking the Marathi.

**`apps/short-page/`** — the same day in two shorter forms. `index.html` is the
summary: the underlined passages written as one continuous argument, every claim
carrying a tappable marker back to its source sentence. `01-01-passages.html` is the
marked passages alone, with a practice section in which every item is a quotation.

Both open straight from the filesystem — no server, no build step needed to read.

## Working on it

```bash
python3 conversion/new_day.py 01-02      # scaffold a day, then transcribe by hand
python3 conversion/validate.py           # check everything before it renders
python3 tools/build.py                   # inject content into the readers
```

`validate.py` exits non-zero on error, so it can gate a build. Among other things it
enforces that **every citation in a summary points at a sentence that is actually
underlined** — which is what stops the short page from quietly becoming an editorial
abridgement.

There is deliberately **no OCR step**. See [conversion/README.md](conversion/README.md).

## Three voices, kept separate

| | Whose | How it appears |
|---|---|---|
| The discourse | गोंदवलेकर महाराज | The page itself |
| The underlines | one previous reader | Gold rules, with a standing provenance note |
| Translation, commentary, summary | this project, **unreviewed** | Different type, own rule colour, explicit draft status |

That separation is the single most important thing in this repository. Two
independent design reviews both found that blurring it was the most serious risk in
the work; every surface here is built to keep it visible.

## Status

1 January is complete and is the worked example for everything else. The largest
open item is not code: **the Marathi authored text needs a Marathi editor.** See
[RIGHTS.md](RIGHTS.md) for the full list.
