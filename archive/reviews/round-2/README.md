# Design Review Package — round 2

Four candidate designs for a Marathi devotional daily-reading book. Round 1 reviewed
A, B and C. **Design D is new** — a merge built in response to that review.

## How to run this

Two prompts, deliberately kept apart:

| | Prompt | Attach | Why |
|---|---|---|---|
| **1** | `JUDGE_PROMPT_1_score.md` | everything **except** `prior/` | Scores all four designs fresh. Withholding the old verdict stops it anchoring the new numbers. |
| **2** | `JUDGE_PROMPT_2_audit.md` | everything **including** `prior/` | Audits whether D actually resolved round 1's five findings. |

Run them in **separate sessions**. If you only run one, run Prompt 1 — a comparable score
is worth more than a self-graded checklist.

## Contents

```
README.md              you are here
BRIEF.md               context, all four designs, known limitations
RUBRIC.md              7 weighted criteria + required JSON output (unchanged from round 1)
JUDGE_PROMPT_1_score.md
JUDGE_PROMPT_2_audit.md
prototypes/            4 self-contained HTML files + the page scan they load
screenshots/           17 PNGs + MANIFEST.md
content/               the shared JSON, a markdown transcript, and the original scan
prior/                 round-1 scores and findings — withhold for Prompt 1
```

## Running the prototypes

Open any file in `prototypes/` in a browser — `file://` works, nothing to install.
URL parameters reproduce any state:

| File | Parameters |
|---|---|
| `design-a-reader.html` | `?mode=mr\|en\|both` `&hl=on\|only\|off` `&theme=day\|sepia\|night` |
| `design-b-deck.html` | `?theme=day\|night` `&card=N` `&marked=0\|1` `&tr=on\|off` |
| `design-c-margin.html` | `?theme=day\|night` `&marks=on\|off` `&lit=N` `&fax=1` |
| `design-d-merged.html` | `?theme=day\|sepia\|night` `&lang=mr\|en` `&tr=on` `&marks=off` `&comm=off` `&fax=1` `&autofit=1` `&page=NNN` |

Fonts load from Google Fonts; offline they fall back to system serifs and the Devanagari
looks materially worse. Judge typography from the screenshots, captured with fonts loaded.

## Disclosure

All four designs were produced by the same author (Claude, working with the project owner).
D was built specifically to address round 1's findings, so treat its self-description in
`BRIEF.md` with the scepticism that deserves — the screenshots and code are the evidence,
not the description.

The project owner's own preferences shaped D as much as the review did: the inline
translation treatment, the margin holding commentary rather than an index, and the
one-page-per-day constraint were all their calls.
