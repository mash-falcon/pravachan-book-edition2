# Underline detection: what the first real test showed

2 January, three vision models through the NVIDIA gateway, scored against marks a
human (me) had read off the scan.

| model | marked |
|---|---|
| `aws/anthropic/bedrock-claude-opus-4-8` | 2, 5, 7, 13, 14 · unsure about 6 |
| `azure/openai/gpt-5.6-sol` | 13, 14 · unsure about 2, 5, 7, 8 |
| `nvidia/nvidia/nemotron-3.5-super-vl-preview` | all 14 |

## The record was wrong, not the models

All three marked sentence 13, which the record omitted, and the tooling duly called
it **INVENTED** — because it treated the human record as ground truth.

Sentence 13 *is* underlined. Its rule runs across a row break: the end of one
typographic row and the start of the next both carry a line, and sentence 14's own
underline begins mid-row at म्हणून. Reading the row-2 rule as sentence 14's, the
first pass missed 13 entirely.

Three independent models caught what one careful human reading missed. The record
has been corrected to 2, 5, 7, 13, 14.

**Consequence for the tooling:** an extra mark is now reported as `extra`, not
`INVENTED`, and when *every* model agrees on something the record omits, the run says
so and tells you to check the scan there. A stored mark is a record, not truth.

## The models, individually

- **claude-opus-4-8** got all five and flagged 6 as uncertain. The only model whose
  confident answer was usable as-is.
- **gpt-5.6-sol** was right but under-confident: it put 2, 5, 7 in `uncertain`
  rather than `underlined`. Its uncertainty list was more accurate than its answer —
  worth reading both fields rather than only the confident one.
- **nemotron-3.5-super-vl-preview** marked every sentence on the page. That is not
  detection, and it is now excluded automatically: a model marking 70% or more of a
  page is dropped from the consensus rather than dragging every line into dispute.

## What this says about consensus

Unanimity was [13, 14] — both correct. With the degenerate answer excluded, the
disputed set is [2, 5, 7]: three lines to check by eye instead of fourteen.

But the earlier warning stands and is now demonstrated in both directions:
agreement is not correctness, and **disagreement with the record is not error**.
Consensus is a way of deciding where to look. It is not a way of deciding what is true.

## Practical recommendation

Underline detection is usable as a **proposal**, never as a record. Run two models
that disagree usefully — claude-opus-4-8 and gpt-5.6-sol — take the union of their
`underlined` and `uncertain` as the review queue, and confirm every mark against the
scan before it enters `content/`. `confirmed_by_human` stays false until someone has.
