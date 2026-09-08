# Brief

## The source material

A printed page from **श्री ब्रह्मचैतन्य गोंदवलेकर महाराज — प्रवचने** (*Pravachane*),
a Marathi devotional book of 365 daily discourses. One page per calendar day.

The page under design is **1 January — परमात्मस्वरूपच असणारें नाम**
("The Name That Is Itself the Supreme Reality"). It is a single unbroken essay of
23 sentences plus a one-line footnote.

**A previous reader underlined passages in the physical book by hand.** Those
underlines are preserved in the data as an editorial layer and are central to all
three designs — they represent "what matters most on this page." There are
**11 underlined passages**; three of them run across two sentences each, so the
underlines cover 14 sentences in total.

**The original scan is included** — `content/original-page-scan.JPG`, also loaded by
Design C's facsimile panel. Compare the typeset pages against it freely; the hand
underlines are visible in it.

The text is transcribed in its **original orthography** (older Marathi spellings:
नांव, कांहीं, केलीं, नाहीं). This is deliberate and must be preserved. A future
build will offer a modernised-spelling toggle; do not treat the archaic forms as
transcription errors.

## Audience and use

- Marathi-reading devotees, broad age range, many of them older readers.
- Non-Marathi-reading family members and second-generation diaspora who want the
  English but value seeing the Marathi.
- The dominant use is **one page a day, in the morning**, often on a phone.
- A secondary use is reference — looking up a remembered line later.
- Content is spiritual and, for many readers, sacred. Treatments that feel
  flippant, gamified, or "content-marketing" are a real failure mode.

## The intended deliverable

Undecided between an e-book and an app; that decision is partly what this review
should inform. All three prototypes read from the **same sentence-aligned JSON**
(`content/2026-01-01.json`), which is the project's actual architectural bet:
each sentence carries its Marathi, its English, and a highlight flag, so any
number of presentations can be generated from one source.

## The three designs

Described factually and in equal detail. No recommendation is offered here.

### Design A — Reader (`design-a-reader.html`)

A conventional single-column reading page on warm paper, with a sidebar.

- Language control: **मराठी / English / Both**. "Both" becomes a sentence-aligned
  two-column view.
- Highlight control: **Marks** (underlines shown as a soft marker), **Focus**
  (dims everything that is not underlined), **Off**.
- Tapping any sentence slides its translation up in a docked strip.
- A sidebar card lists 8 plain-language "essence" points; clicking one scrolls to
  and flashes the source sentence.
- A second sidebar card holds the day's practice and a japa (repetition) counter.
- Three themes (Day / Sepia / Night), four text sizes, reading-progress bar,
  365-day pager.

### Design B — Linked deck (`design-b-deck.html`)

A two-panel split screen. Left: a vertical card deck, one passage per card.
Right: the complete continuous text.

- Scrolling the deck **lights the corresponding sentence(s)** in the full text on
  the right and scrolls them to centre. Clicking a line in the text jumps the deck
  to that card. The link runs both ways.
- The three two-sentence underlines are **single cards**, badged "2 sentences",
  and light both sentences together.
- "✦ Marked" filters the deck to the 11 underlined passages only; switching it off
  gives all 23 sentences as cards.
- English appears three ways: a permanent gloss strip under the text showing the
  live card's translation; per-card tap-to-reveal; and an "Inline translation"
  toggle that puts English under each Marathi paragraph.
- Auto-advance (7s/card) with a progress ring; ↑/↓ keys; clickable progress pips;
  an ambient background glow that warms on underlined cards.
- Day / Night themes. Below 1000px the right panel drops and the deck goes
  full-width.

### Design C — Margin edition (`design-c-margin.html`)

A print-fidelity book page: justified Devanagari, running heads, folio, first-word
versal, footnote in place.

- Underlines are rendered as fine gold rules plus superscript numbers, treated as
  editorial apparatus rather than decoration.
- Each underlined passage's English sits in the **right margin, vertically aligned
  to the line it glosses** (positioned at runtime, nudged apart on collision).
  Hovering either the passage or its note lights both.
- "Underlines" toggle hides the apparatus for a clean reading page.
- "Facsimile" opens a panel showing **the original scanned page** beneath the set
  text, so fidelity to the printed original can be checked directly.
- "Print / PDF" produces a real book page; the print stylesheet forces the light
  palette and strips all UI.
- Day / Night themes.

## Constraints to respect when judging

- **Devanagari typography.** Needs looser leading than Latin (the prototypes use
  2.0–2.25). `::first-letter` drop caps shear the akshara apart and are not usable;
  Design C uses a first-word versal instead.
- **Original orthography is intentional.**
- **The English translation is unreviewed.** It was produced in-session and has not
  been checked against any authorised published translation. Judge its *presentation*,
  not its scholarly accuracy.
- **One page only.** Navigation across 365 days is stubbed, not built.

## Known limitations — please do not report these as findings

1. Only 1 January is implemented; the day pager is non-functional.
2. No audio, though the brief anticipates it (morning listening is a major use case).
3. Only the 1 January page has a scan; the other 364 are not digitised here.
4. The passage-grouping map (`GROUP = {5:1,6:1,7:2,8:2,11:3,12:3}`) is duplicated in
   B and C rather than living in the JSON. Known; slated to move into the data.
5. No personal highlighting, bookmarking, search, or cross-page theme tagging yet.
6. Fonts come from a CDN; there is no offline font strategy yet.
7. These are prototypes: no tests, no build, no accessibility audit has been run.
