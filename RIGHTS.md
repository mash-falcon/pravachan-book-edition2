# Rights, provenance, and what is unresolved

Read this before adding page scans or publishing anything from this repository.

## This repository is public

Everything pushed here is world-readable and, once pushed, effectively permanent —
deleting a file does not remove it from the git history unless the history is
rewritten. Decide what belongs here *before* committing it.

## The page scans are not committed

`source/pages/` is empty on purpose. The scan of 1 January was used throughout the
design work but has been kept out of this repository because:

- the **publisher, edition and date** of the printed source are unconfirmed;
- the **rights position for reproducing the pages** has not been established;
- the repository is **public**.

Three ways forward, in order of preference:

1. **Establish the rights position** with the publisher or trust that holds them,
   and record the answer here. Then commit the scans.
2. **Make the repository private** while the work is in progress. The scans can be
   added immediately; publication is a separate later decision.
3. **Keep scans out of git entirely** — store them in a private bucket or drive and
   have `source/pages/` populated locally. `.gitignore` is already set up for this.

To add a scan once that is settled, drop it at `source/pages/01-01.jpg` and remove
the matching ignore line from `.gitignore`.

## Three voices, and who owns each

The apps keep these visually distinct, and so should any future work.

| Layer | Whose | Status |
|---|---|---|
| **The discourse** | श्री ब्रह्मचैतन्य गोंदवलेकर महाराज | Transcribed from a printed edition; rights unconfirmed |
| **The underlines** | An unidentified previous reader of one physical copy | Reproduced as an inherited layer; no editorial claim |
| **Translation, commentary, summary** | Drafted in this project | **Unreviewed.** No named author. Not checked by a Marathi editor or by the publisher |

The underlines are **not** the author's emphasis. Every surface that shows them
says so, and that must not be dropped for brevity.

## What is unverified

- The English translation was drafted in-session and has not been checked against
  any authorised published translation.
- The Marathi connective prose in `summary/` is machine-drafted. It is structurally
  faithful and reuses the discourse's own wording where possible, but it is **not
  idiomatic at the level this material deserves** and needs a native Marathi editor.
- The biographical and bibliographic facts shown in the full-page reader's context
  band are stated from general knowledge and are **not sourced**. Treat them as
  placeholders.

## Before any public release

- [ ] Rights position for the printed source established and recorded here
- [ ] Translation reviewed against an authorised version, or marked as original
- [ ] Marathi commentary and summary rewritten or edited by a named Marathi editor
- [ ] Biographical facts sourced to a citable edition
- [ ] Named author or editor recorded in each `*_status.author` field
- [ ] A decision on whether the inherited underlines may be reproduced at all
