#!/usr/bin/env python3
"""Turn raw OCR text into the transcript structure, in code rather than by prompt.

An OCR model returns a page of text. Asking it for JSON, sentence numbers and
paragraph maps is asking it to do a job it was not built for — and when it obliges,
it is guessing. The splitting is deterministic, so do it here where it can be tested
and corrected, and let the OCR do OCR.

    python3 conversion/structure.py raw.txt            # prints the JSON
    python3 conversion/structure.py raw.txt --out 1-transcript.json
"""
import argparse, json, pathlib, re, sys

DEV_DIGITS = "०१२३४५६७८९"
MONTHS = ("जानेवारी फेब्रुवारी मार्च एप्रिल मे जून जुलै ऑगस्ट "
          "सप्टेंबर ऑक्टोबर नोव्हेंबर डिसेंबर").split()
# a sentence ends at . ? ! or danda — keep the mark with the sentence
SENT_END = re.compile(r"(?<=[.?!।])\s+")
FOOTNOTE = re.compile(rf"^\s*([{DEV_DIGITS}]+)\s*[.)]\s*(.+)$", re.S)


def is_date(line: str) -> bool:
    return any(m in line for m in MONTHS) and len(line) < 40


def structure(raw: str) -> dict:
    lines = [ln.strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln and not set(ln) <= set("-—_= ")]

    title = date = ""
    body: list[str] = []
    foot_marker = foot_text = ""

    for i, ln in enumerate(lines):
        if not title and i < 3 and not is_date(ln) and not ln.endswith((".", "?")):
            title = ln
            continue
        if not date and is_date(ln):
            date = ln
            continue
        m = FOOTNOTE.match(ln)
        # a numbered line late in the page is the footnote, not body text
        if m and i > len(lines) * 0.6 and not foot_text:
            foot_marker, foot_text = m.group(1), m.group(2).strip()
            continue
        if foot_text:
            foot_text += " " + ln
            continue
        body.append(ln)

    # OCR wraps mid-sentence; join first, then split on sentence endings
    joined = re.sub(r"\s+", " ", " ".join(body)).strip()
    sentences = [s.strip() for s in SENT_END.split(joined) if s.strip()]

    return {
        "title_mr": title,
        "date_label_mr": date,
        "sentences": [{"n": i + 1, "mr": s} for i, s in enumerate(sentences)],
        "paras": [[1, len(sentences)]] if sentences else [],
        "footnote": {"marker": foot_marker, "mr": foot_text},
        "_structured_by": "conversion/structure.py",
        "_check": "Paragraph breaks are NOT recoverable from OCR text — paras is one "
                  "block covering every sentence. Split it by reading the scan.",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="file of OCR text, or - for stdin")
    ap.add_argument("--out")
    a = ap.parse_args()
    text = sys.stdin.read() if a.raw == "-" else pathlib.Path(a.raw).read_text(encoding="utf-8")
    r = structure(text)
    out = json.dumps(r, ensure_ascii=False, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(out, encoding="utf-8")
        print(f"{len(r['sentences'])} sentences -> {a.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
