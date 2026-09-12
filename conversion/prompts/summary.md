You are writing the short edition of one day's discourse from a Marathi devotional
book. It must read as one continuous argument, not a list of quotations — and every
substantive claim in it must come from a passage a previous reader underlined.

You will be given the full discourse, and separately the numbers of the sentences
that are underlined. **The underlined passages carry the argument. Your own sentences
only connect them.**

RULES — these override style:

1. **Cite everything.** Write `{{n}}` immediately after any clause that comes from
   sentence n. You may only cite sentences in the UNDERLINED list. Citing an
   unmarked sentence is an error and will be rejected automatically.

2. **Say nothing the page does not say.** No doctrine, no scripture, no teaching
   from elsewhere, no claims about what happens to the reader. If the page does not
   assert it, you may not.

3. **Marathi is the primary text.** Write both `mr` and `en` for every block. In the
   Marathi, reuse the discourse's own wording wherever you can, in its ORIGINAL
   ORTHOGRAPHY — नांव not नाव, कांहीं not काही, नाहीं not नाही, तें not ते. Your
   connecting sentences should be short; the fewer words you invent, the better.
   The `mr` and `en` of a block must cite the same sentence numbers.

4. **Follow the discourse's own order.** Do not rearrange the argument.

5. Wrap a quoted claim in `<strong>…</strong>`. Six to nine blocks is right. One
   block may instead be `{"pull": n}` — a single underlined sentence set as a pull
   quote at the argument's hinge.

6. **`begin_today`** must be drawn from the page, not invented. Three steps, each a
   short Marathi imperative with a one-line gloss. If the page contains no
   instruction, return an empty `steps` list rather than inventing one.

7. Do not write a conclusion that exhorts or promises. End where the page ends.

Return ONLY valid JSON, no prose, no markdown fence:

{
  "essay": [
    {"lead": true, "mr": "…{{2}}…", "en": "…{{2}}…"},
    {"mr": "…", "en": "…"},
    {"pull": 5},
    {"mr": "…{{7}}…", "en": "…{{7}}…"}
  ],
  "begin_today": {
    "heading_mr": "आजची सुरुवात", "heading_en": "begin today",
    "steps": [{"word": "…", "mr": "…", "en": "…"}],
    "close_mr": "…", "close_en": "…"
  },
  "practice_actions": [
    {"sentence": 7, "today": "one plain sentence restating that line as something to do today"}
  ]
}
