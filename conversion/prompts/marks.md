You are reading a scanned page of a printed book that a previous reader marked by
hand. Your only job is to report WHICH printed text carries a hand-drawn underline.

Context: the numbered sentences of this page are given below. Underlines were drawn
in pen or pencil beneath the printed line. They are not part of the printing.

RULES:

1. Report a sentence as underlined only if you can actually see a hand-drawn line
   beneath its words. Do not infer from meaning or importance.
2. Some underlines run across two or more consecutive sentences. Report each
   sentence separately; grouping happens later.
3. Partial underlines count — if most of a sentence is underlined, report it.
4. If you are unsure about a sentence, put it in "uncertain" rather than "underlined".
   A false positive silently rewrites what the reader marked; being unsure is safer.

Return ONLY valid JSON, no prose:

{
  "underlined": [3, 4, 5],
  "uncertain": [9],
  "note": "anything about image quality that limited you"
}
