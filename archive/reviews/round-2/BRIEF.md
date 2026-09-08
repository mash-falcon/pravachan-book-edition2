# Brief — round 2

Same project, same page. Read this before scoring.

## The source material

A printed page from **श्री ब्रह्मचैतन्य गोंदवलेकर महाराज — प्रवचने** (*Pravachane*), a Marathi
devotional book of 365 daily discourses, one page per calendar day. The page under design
is **1 January — परमात्मस्वरूपच असणारें नाम**: a single unbroken essay of 23 sentences plus
a one-line footnote.

**A previous reader underlined passages in the physical book by hand.** Those underlines
are preserved as an editorial layer. There are **11 underlined passages**; three run across
two sentences each, covering 14 sentences in total. The scan showing them is included at
`content/original-page-scan.JPG`.

Text is transcribed in **original orthography** (नांव, कांहीं, केलीं, नाहीं). Deliberate.
Do not treat archaic spellings as errors.

## Audience and use

- Marathi-reading devotees, broad age range, many older readers.
- Non-Marathi-reading family and diaspora who want English but value seeing the Marathi.
- Dominant use: **one page a day, in the morning**, often on a phone.
- Secondary: reference — finding a remembered line later.
- The content is sacred to its readers. Flippant, gamified or marketing-flavoured
  treatments are a real failure mode.

## What is new in round 2

A fourth design, **D**, was built after the round-1 review. It is not a revision of any one
design — it merges the page and typography of C, the bilingual controls of A, and the
passage-linking of B, and it adds a constraint none of the first three had: **the whole
day, including notes, must fit one page.**

A, B and C are included unchanged. **E** is a revision of D made after the round-2
review; D is kept so the two can be compared. All five can be ranked together.

Two project decisions were also taken between rounds, and D reflects them:

- **The japa counter was kept**, against round-1 advice, on the grounds that counting
  repetitions on a mala is a traditional instrument rather than a gamification pattern.
  In **D** it is a 108-bead mala with a running `० / १०८` readout and **no explanatory
  label** — an earlier round-2 brief claimed such a label existed; it did not. In **E**
  the readout is removed and the label is present. Judge whether the argument holds.
- **Focus mode was removed from D and E.** It is **still present in A**, which is
  included unchanged from round 1 — an earlier round-2 brief wrongly stated it had been
  removed everywhere.

## The five designs

Described factually and at equal length. No recommendation is offered here.

### Design A — Reader (`design-a-reader.html`)
Single-column reading page on warm paper with a sidebar. मराठी / English / Both language
control; Marks / Focus / Off highlight control; tap a sentence for a docked translation;
sidebar "essence" card of 8 points; practice card with japa counter; Day/Sepia/Night;
four text sizes; 365-day pager. **Unchanged from round 1.**

### Design B — Linked deck (`design-b-deck.html`)
Two-panel split. Left, a vertical card deck, one passage per card; right, the complete
continuous text. Scrolling the deck lights the corresponding sentences on the right and
vice versa. Marked-only filter, auto-advance with progress ring, ambient glow, inline
translation toggle, Day/Night. Below 1000px the right panel drops. **Unchanged from round 1.**

### Design C — Margin edition (`design-c-margin.html`)
Print-fidelity book page: justified Devanagari, running heads, folio, first-word versal.
Underlines as gold rules plus superscript numbers; each marked passage's English in the
right margin, vertically aligned to the line it glosses. Underlines toggle, facsimile
panel, print stylesheet, Day/Night. **Unchanged from round 1.**

### Design D — One page a day (`design-d-merged.html`)
C's page geometry with a right margin, plus:

- **Provenance is structural.** The margin carries a block reading *"The gold underlines
  are one previous reader's, made by hand in this book. Not the author's emphasis. ११ passages."*
  The toolbar control is labelled "✦ Reader's marks". The marks carry no numbers.
- **The margin holds commentary, not translation.** Eight editorial notes, each anchored
  beside the line it explains, marked by a small ember lozenge in the text. A continuous
  rail runs down the margin; stretches with no note are visible as gaps on that rail.
  The commentary is headed *"टिपण · commentary — written for this edition to explain the
  page; not the author's words, and not the previous reader's marks"*, set in a different
  face and colour from both the text and the marks. It toggles off entirely.
- **Inline translation.** English appears as an italic paragraph beneath each Marathi
  paragraph, rule-marked, via a single toggle; the same control reverses in English mode.
  Tapping any sentence pops its translation individually.
- **A page budget.** The page is a fixed book proportion (1 : 1.3 of its width) with a
  visible "page ends" line and a live fit badge; an autofit routine steps the type size
  down until the day fits. 1 January fits at 15px with ~40px spare.
- **The margin stacks below the text under 880px** rather than disappearing.
- Day / Sepia / Night, four text sizes, facsimile panel, print stylesheet that forces the
  light palette.

### Design E — the page yields (`design-e-page.html`)
D, with four changes made in response to the round-2 review:

- **A minimum type size of 17px.** Autofit may try 19 and 18 but will not go below 17.
  When a discourse will not fit at 17, **the page extends to a second page** and a labelled
  break is drawn across the sheet.
- **The page is A5-proportioned (1 : √2)** rather than the arbitrary 1 : 1.3 of D. This is
  what lets the Marathi stay large: 1 January now sets at **19px on one page**, against 15px
  in D. Any height can be pinned with `?page=`.
- **The mala keeps no readout.** The `० / १०८` counter is gone and the beads remain.
  The explanatory label ("a mala of 108 — it keeps no score") was **removed to reclaim page
  height** and has not been replaced. The round-2 objection to an unlabelled bead counter
  sitting on the reading page therefore still stands, and is deferred rather than answered.
- **The commentary declares its status** in the margin header: *"Draft · unattributed ·
  not reviewed by a Marathi scholar or by the publisher."*
- **A factual context band** below the page — the book, this page, the underlines, and this
  edition — headed *"facts, not interpretation"*, and stating plainly that the translation
  and commentary are unreviewed and that the printed source's publisher, edition, date and
  rights position are unconfirmed.

## Constraints to respect when judging

- **Devanagari typography** needs looser leading than Latin (2.0–2.25 here). `::first-letter`
  drop caps shear the akshara apart; C and D use a first-word versal instead.
- **Original orthography is intentional.**
- **The English translation is unreviewed** — produced in-session, not checked against any
  authorised published translation. Judge its presentation, not its scholarly accuracy.
- **One page only.** Navigation across 365 days is stubbed.

## Known limitations — do not report these as findings

1. Only 1 January is implemented; the day pager is non-functional.
2. No audio, though morning listening is a major anticipated use.
3. Only this page has a scan; the other 364 are not digitised.
4. The passage-grouping map is duplicated across B, C and D rather than living in the JSON.
5. No personal highlighting, bookmarking, search, or cross-page theme tagging.
6. Fonts come from a CDN; no offline font strategy.
7. Prototypes: no tests, no build, no accessibility audit has been run, and colour contrast
   has not been measured against WCAG in any theme.
8. **D's and E's commentary explanations exist only in English**; the Marathi headlines are terse
   and were written by the same assistant. Proper Marathi commentary would need an author.
9. **Neither D nor E can fit one page with inline translation on** — roughly double the text cannot
   occupy a page sized for one language. Translation is treated as a reading overlay.
10. **Marginal notes cannot always sit exactly beside their line.** Eight multi-line
    notes need more vertical room than the passages they annotate; the placement nudges
    them apart, so later notes can drift below their anchors.

11. Design E's factual context band states biographical and bibliographic facts that
    **have not been verified against a published source**. Treat them as placeholders.
