# Drafts

Model output lands here and goes no further on its own.

`conversion/assist.py` writes `<id>.json` into this folder. Nothing in this folder is
used by the readers. A draft becomes content only when a person runs
`conversion/accept.py <id> --promote --by "Name"`, which records who checked it.

Draft files are not committed — they are regenerable, and a draft containing
modernised spelling sitting in the repo is exactly the kind of thing that gets
mistaken for the real text later.
