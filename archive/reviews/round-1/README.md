# Design Review Package — *Pravachane* Daily Reader

Three candidate designs for one page of a Marathi devotional daily-reading book,
prepared for independent evaluation.

## What to do

1. Read **BRIEF.md** — project context, audience, and what each design is.
2. Look at **screenshots/** (9 PNGs) and, if you can run a browser, open **prototypes/**.
3. Score against **RUBRIC.md** and return the JSON block it specifies.

**JUDGE_PROMPT.md** is a paste-ready prompt if you are handing this to an LLM.

## Contents

```
README.md            you are here
BRIEF.md             context, source material, what each design does
RUBRIC.md            criteria, weights, required output format
JUDGE_PROMPT.md      paste-ready instructions for an LLM reviewer
prototypes/          3 self-contained HTML files, no build step, no server
screenshots/         10 PNGs — enough to judge without running anything
content/             the source data, plus the original page scan
```

## Running the prototypes

Open any file in `prototypes/` directly in a browser — `file://` works, nothing to install.

They accept URL parameters so you can reproduce any state:

| File | Parameters |
|---|---|
| `design-a-reader.html` | `?mode=mr\|en\|both` `&hl=on\|only\|off` `&theme=day\|sepia\|night` |
| `design-b-deck.html` | `?theme=day\|night` `&card=N` `&marked=0\|1` `&tr=on\|off` `&reveal=1` |
| `design-c-margin.html` | `?theme=day\|night` `&marks=on\|off` `&lit=N` `&fax=1` |

Fonts load from Google Fonts; **offline they fall back to system serifs** and the
Devanagari will look noticeably worse than intended. Judge typography from the
screenshots, which were captured with fonts loaded.

## Disclosure

All three designs were produced by the same author (Claude, working with the
project owner) in a single session. They are prototypes of one page, not
production code. Known limitations are listed at the end of BRIEF.md — please
read them before penalising something already known.
