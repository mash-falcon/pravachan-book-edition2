# Rubric

Score each design **1–5** on every criterion. Weights sum to 100.

`1` = actively harmful · `2` = weak · `3` = adequate · `4` = strong · `5` = exceptional

---

### 1. Reverence and tone — weight 20

Does the design treat a sacred text with appropriate gravity? Would a devotee feel
the book was honoured or cheapened? Watch for: gamification, marketing gloss,
decorative flourish that upstages the text, or novelty that will not age.

### 2. Reading the Marathi — weight 20

Quality of the primary reading experience *in Marathi*: type size and leading,
line length, justification, contrast, how the eye moves through a long unbroken
discourse. Is the original text the centre of gravity, or has it become supporting
material for an interface?

### 3. Handling of the underlines — weight 15

The underlines are inherited marginalia, not the author's emphasis. Is that
distinction legible? Does the treatment let a reader (a) read the page unmarked,
(b) see the marks in context, and (c) read only the marked passages — without ever
implying the marks are the whole page?

### 4. Bilingual presentation — weight 15

How well Marathi and English coexist. Is the English available without displacing
the Marathi? Can a mixed-fluency household use the same artifact? Is switching
cheap and reversible?

### 5. Daily-habit fit — weight 10

Fitness for the dominant use: one page, each morning, often on a phone. Consider
time-to-first-word, whether it suits a 6 a.m. attention span, and whether it would
survive 365 consecutive days without fatigue.

### 6. Findability and reference — weight 10

The secondary use: locating a half-remembered line later, moving around within the
page, returning to a specific passage. Sequential-only designs should be judged
honestly here.

### 7. Craft and durability — weight 10

Execution quality: visual hierarchy, spacing, colour discipline in both themes,
responsive behaviour, restraint. Would this scale to 365 pages of varying length
without breaking?

---

## Required output

Return **exactly this JSON**, then at most 400 words of prose commentary.

```json
{
  "scores": {
    "A": {"reverence":0,"marathi_reading":0,"underlines":0,"bilingual":0,"daily_habit":0,"findability":0,"craft":0,"weighted_total":0.0},
    "B": {"reverence":0,"marathi_reading":0,"underlines":0,"bilingual":0,"daily_habit":0,"findability":0,"craft":0,"weighted_total":0.0},
    "C": {"reverence":0,"marathi_reading":0,"underlines":0,"bilingual":0,"daily_habit":0,"findability":0,"craft":0,"weighted_total":0.0},
    "D": {"reverence":0,"marathi_reading":0,"underlines":0,"bilingual":0,"daily_habit":0,"findability":0,"craft":0,"weighted_total":0.0}
  },
  "ranking": ["", "", "", ""],
  "recommended_primary": "",
  "recommended_combination": "",
  "strongest_single_idea": {"design":"","idea":"","why":""},
  "must_fix": [
    {"design":"","issue":"","severity":"high|medium|low","suggested_fix":""}
  ],
  "kill": {"design":"","reason":""},
  "format_recommendation": {"choice":"ebook|pwa|native app|print+digital","why":""},
  "confidence": "high|medium|low",
  "what_would_raise_confidence": ""
}
```

Field notes:

- `weighted_total` — sum of (score × weight) ÷ 100, to one decimal.
- `recommended_combination` — these are not required to be mutually exclusive.
  If two should ship together, say which and in what roles.
- `strongest_single_idea` — the one mechanic worth carrying forward regardless of
  which design wins.
- `kill` — name the design you would drop, and why. If you would keep all three,
  set `design` to `"none"` and justify that too.
- `confidence` — be honest; the package contains screenshots and code but no user
  research and no live Marathi readers.

## Please do

- Weigh **screenshots over code**. Judge what a reader sees.
- Argue against the brief where you disagree with it. The weights above are the
  project owner's current opinion, not a fact.
- Name specific elements (colours, spacing, a particular control) rather than
  giving general impressions.

## Please don't

- Don't report anything in the "Known limitations" list in BRIEF.md.
- Don't assess the accuracy of the English translation or the Marathi transcription.
- Don't recommend adding features that would require abandoning the shared JSON
  data model without saying so explicitly.

## A note on criterion 3 for round 2

Design D introduces a third voice on the page: the author's text, the previous reader's
underlines, and editorial commentary in the margin. Criterion 3 should be read as covering
the legibility of **all three** distinctions in D, not only the underlines.
