#!/usr/bin/env python3
"""Promote a reviewed draft into the content the readers use.

    python3 conversion/accept.py 01-02              # show the draft for review
    python3 conversion/accept.py 01-02 --promote    # write content/days/01-02.json

Deliberately two steps. The first prints the draft as the model produced it, with the
things most likely to be silently wrong called out. Read it against the scan. Only
then promote.

Promoting records that a human accepted it. It does not claim the text is correct —
it claims someone looked.
"""
import argparse, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("day")
    ap.add_argument("--promote", action="store_true")
    ap.add_argument("--by", default=None, help="who reviewed it")
    a = ap.parse_args()

    dp = ROOT / "content" / "drafts" / f"{a.day}.json"
    if not dp.exists():
        raise SystemExit(f"no draft at {dp.relative_to(ROOT)}")
    d = json.loads(dp.read_text(encoding="utf-8"))
    out = ROOT / "content" / "days" / f"{a.day}.json"

    if not a.promote:
        print(f"DRAFT {a.day} — produced by {d.get('_provenance',{}).get('vision_model','?')}\n")
        print(f"title : {d.get('title_mr','')}")
        print(f"date  : {d.get('date',{}).get('label_mr','')}")
        print(f"paras : {d.get('paras')}\n")
        for s in d.get("sentences", []):
            mark = " ___" if s.get("highlight") else "    "
            print(f"[{s['n']:>2}]{mark} {s['mr']}")
            if s.get("en"):
                print(f"         {s['en']}")
        fn = d.get("footnote", {})
        if fn.get("mr"):
            print(f"\nfootnote {fn.get('marker','')}: {fn['mr']}")
        print("\nCHECK THESE AGAINST THE SCAN:")
        print(f"  · orthography — नांव not नाव, कांहीं not काही, नाहीं not नाही")
        print(f"  · the underlines: model marked {[s['n'] for s in d.get('sentences',[]) if s.get('highlight')]}")
        if d.get("_marks_uncertain"):
            print(f"  · model was UNSURE about {d['_marks_uncertain']}")
        if d.get("_illegible"):
            print(f"  · {d['_illegible']} illegible spot(s) marked [?]")
        if out.exists():
            print(f"\n  NOTE: {out.relative_to(ROOT)} already exists and would be overwritten.")
        print(f"\nWhen it is right:  python3 conversion/accept.py {a.day} --promote --by 'Your Name'")
        return

    if not a.by:
        raise SystemExit("--by 'Your Name' is required: promoting records who checked it")
    for k in ("_draft", "_provenance", "_illegible", "_marks_uncertain", "_marks_note"):
        d.pop(k, None)
    d.setdefault("marks", {})["confirmed_by_human"] = True
    d["source"]["transcription_reviewed_by"] = a.by
    d.setdefault("commentary", [])
    d.setdefault("commentary_status", {"state": "draft", "author": None,
                                       "reviewed_by_marathi_editor": False,
                                       "reviewed_by_publisher": False})
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}  (reviewed by {a.by})")
    print(f"next: python3 conversion/validate.py {a.day} && python3 tools/build.py {a.day}")


if __name__ == "__main__":
    main()
