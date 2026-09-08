# Paste-ready prompt

Copy everything below the line into the reviewing model, and attach the package
(or its files) alongside it.

---

You are an experienced product and typography reviewer. I need an independent,
critical evaluation of three candidate designs for a digital edition of a Marathi
devotional book. I did not design these and I am not attached to any of them —
tell me plainly which is best and which should be dropped.

**Read in this order:**

1. `BRIEF.md` — context, audience, what each design does, and known limitations.
2. `screenshots/` — nine images, three per design, covering both light and dark
   themes and the key interaction states. See `screenshots/MANIFEST.md` for what
   each one shows.
3. `RUBRIC.md` — the criteria, weights, and the exact output format I need back.
4. `prototypes/` — the three HTML files, if you can run or read code. Optional.
5. `content/2026-01-01.json` — the shared data model all three read from.

**Then:**

- Score all three designs on all seven criteria.
- Return the JSON block specified in `RUBRIC.md`, followed by no more than
  400 words of commentary.

**Ground rules:**

- The text is sacred to its readers. Weigh tone heavily.
- The Marathi is the primary text; English is secondary support.
- The hand-drawn underlines are a previous reader's marginalia, not the author's
  emphasis — judge how well each design conveys that.
- The archaic Marathi spellings are intentional. Do not flag them.
- Skip anything listed under "Known limitations" in `BRIEF.md`.
- Be specific and be willing to be negative. A flattering review is useless to me.
- If you think the brief's own weights are wrong, say so and show what the ranking
  would be under your weights as well.
