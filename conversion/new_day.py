#!/usr/bin/env python3
"""Scaffold a day file from a page image.

    python3 conversion/new_day.py 01-02

Creates content/days/01-02.json with the right shape and empty fields, ready for
transcription. It does NOT attempt OCR: this book is set in older Marathi
orthography (नांव, कांहीं, नाहीं) that general OCR silently modernises, and a
silent change to a devotional text is worse than no automation. Transcribe by
hand against source/pages/<id>.jpg, then run conversion/validate.py.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

SKELETON = {
    "id": None,
    "date": {"day": None, "month": None, "label_mr": "", "label_en": ""},
    "title_mr": "", "title_en": "",
    "source": {"page_image": None, "orthography": "original",
               "transcribed_by": None, "translation_by": None,
               "translation_reviewed": False},
    "marks": {"kind": "inherited",
              "by": "an unidentified previous reader of this copy",
              "count_passages": 0},
    "paras": [],
    "sentences": [{"n": 1, "mr": "", "en": "", "highlight": 0}],
    "footnote": {"marker": "", "mr": "", "en": ""},
    "commentary": [],
    "commentary_status": {"state": "draft", "author": None,
                          "reviewed_by_marathi_editor": False,
                          "reviewed_by_publisher": False},
}

def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    day_id = sys.argv[1]
    out = ROOT / "content" / "days" / f"{day_id}.json"
    if out.exists():
        raise SystemExit(f"{out} already exists")
    mm, dd = day_id.split("-")
    d = json.loads(json.dumps(SKELETON))
    d["id"] = day_id
    d["date"]["month"], d["date"]["day"] = int(mm), int(dd)
    d["source"]["page_image"] = f"source/pages/{day_id}.jpg"
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"created {out.relative_to(ROOT)} — transcribe it, then run conversion/validate.py")

if __name__ == "__main__":
    main()
