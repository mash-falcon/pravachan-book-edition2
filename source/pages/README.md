# Page scans

One image per day, named by month and day:

```
source/pages/01-01.jpg     1 January
source/pages/01-02.jpg     2 January
...
source/pages/12-31.jpg     31 December
```

`.jpg`, `.jpeg` and `.png` all work; the day file records the exact filename in
`source.page_image`.

**Nothing here is committed yet.** See [`/RIGHTS.md`](../../RIGHTS.md) — this
repository is public and the rights position for reproducing this printed edition
has not been established. Decide that before pushing 365 page images.

Once images are here, `python3 conversion/validate.py` stops warning about
missing page images, and the full-page reader's **Facsimile** panel finds them.
