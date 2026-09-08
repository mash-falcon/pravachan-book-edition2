# Prompt 1 — blind scoring

Run this **first, in a fresh session**, and do not attach the `prior/` folder.
It exists so D is scored on its own merits rather than graded against a checklist.

Copy everything below the line.

---

You are an experienced product and typography reviewer. I need an independent, critical
evaluation of four candidate designs for a digital edition of a Marathi devotional book.
Tell me plainly which is best and which should be dropped.

Read in this order:

1. `BRIEF.md` — context, audience, what each design does, and known limitations.
2. `content/original-page-scan.JPG` — the original printed page, with a previous reader's
   hand underlines. This is the thing being adapted.
3. `screenshots/` — see `screenshots/MANIFEST.md` for what each image shows.
4. `RUBRIC.md` — the criteria, weights, and the exact output format I need back.
5. `prototypes/` — the four HTML files, if you can run or read code. Optional.
6. `content/2026-01-01.json` — the shared data model all four read from.

Then:

- Score **all four** designs (A, B, C, D) on all seven criteria in `RUBRIC.md`.
- Return the JSON block specified there — extended to four designs — followed by no more
  than 400 words of commentary.

Ground rules:

- The text is sacred to its readers. Weigh tone heavily.
- The Marathi is the primary text; English is secondary support.
- The underlines are a previous reader's marginalia, not the author's emphasis. Judge how
  well each design conveys that distinction.
- The archaic Marathi spellings are intentional. Do not flag them.
- Skip anything listed under "Known limitations" in `BRIEF.md`.
- Be specific and be willing to be negative. A flattering review is useless to me.
- If you think the rubric's weights are wrong, say so, and show what the ranking would be
  under your weights as well.

Two questions I want answered explicitly in your commentary:

- **D keeps a japa counter** as a 108-bead mala, arguing that counting repetitions is a
  traditional instrument rather than a gamification pattern. Does that reading hold, or is
  it rationalising an engagement mechanic?
- **D puts editorial commentary in the margin**, beside the author's text, distinguished
  by typography and an explicit header. Is that separation sufficient, or does proximity
  still confer authority the commentary has not earned?
