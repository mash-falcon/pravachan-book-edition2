#!/usr/bin/env python3
"""Check the content files before they reach the apps.

    python3 conversion/validate.py            # every day
    python3 conversion/validate.py 01-01      # one day

Exits non-zero if anything is wrong, so it can run in CI. Errors block a build;
warnings are things a human should look at but that will still render.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DAYS = ROOT / "content" / "days"
SUMS = ROOT / "summary" / "days"
PAGES = ROOT / "source" / "pages"

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
ID = re.compile(r"^\d{2}-\d{2}$")


def check_day(day_id, errors, warnings):
    path = DAYS / f"{day_id}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    E = lambda m: errors.append(f"{day_id}: {m}")
    W = lambda m: warnings.append(f"{day_id}: {m}")

    if not ID.match(day_id):
        E("id must be MM-DD")
    for k in ("id", "date", "title_mr", "title_en", "paras", "sentences", "footnote"):
        if k not in d:
            E(f"missing key '{k}'")
    if errors:
        return d

    ns = [s["n"] for s in d["sentences"]]
    if ns != list(range(1, len(ns) + 1)):
        E("sentence numbers must run 1..N with no gaps")
    for s in d["sentences"]:
        if not DEVANAGARI.search(s["mr"]):
            E(f"sentence {s['n']} has no Devanagari in .mr")
        if not s["en"].strip():
            W(f"sentence {s['n']} has no translation yet")
        if s["highlight"] not in (0, 1, True, False):
            E(f"sentence {s['n']}: highlight must be 0/1")

    # paragraph map must cover every sentence exactly once, in order
    covered = []
    for a, b in d["paras"]:
        covered += list(range(a, b + 1))
    if covered != ns:
        E("paras do not tile the sentences exactly once in order")

    # a group must be a run of consecutive sentences, and every member underlined
    groups = {}
    for s in d["sentences"]:
        if s.get("group"):
            groups.setdefault(s["group"], []).append(s)
    for gid, members in groups.items():
        nums = [m["n"] for m in members]
        if nums != list(range(min(nums), max(nums) + 1)):
            E(f"group {gid} is not a consecutive run: {nums}")
        if len(nums) < 2:
            W(f"group {gid} has one member; groups are for multi-sentence passages")
        if not all(m["highlight"] for m in members):
            E(f"group {gid} mixes underlined and unmarked sentences")

    for c in d.get("commentary", []):
        if c.get("anchor") not in ns and c.get("anchor") != "fn":
            E(f"commentary anchored to sentence {c.get('anchor')}, which does not exist")

    img = ROOT / d.get("source", {}).get("page_image", "")
    if not img.exists():
        W(f"page image not present: {d.get('source', {}).get('page_image')}")
    return d


def check_summary(day_id, day, errors, warnings):
    path = SUMS / f"{day_id}.json"
    if not path.exists():
        warnings.append(f"{day_id}: no summary yet")
        return
    s = json.loads(path.read_text(encoding="utf-8"))
    E = lambda m: errors.append(f"{day_id} summary: {m}")
    W = lambda m: warnings.append(f"{day_id} summary: {m}")

    marked = {x["n"] for x in day["sentences"] if x["highlight"]}
    ns = {x["n"] for x in day["sentences"]}

    for i, p in enumerate(s.get("essay", [])):
        if "pull" in p:
            if p["pull"] not in ns:
                E(f"pull quote cites sentence {p['pull']}, which does not exist")
            continue
        for lang in ("mr", "en"):
            if lang not in p:
                E(f"essay block {i} missing '{lang}'")
                continue
            for cited in map(int, re.findall(r"\{\{(\d+)\}\}", p[lang])):
                if cited not in ns:
                    E(f"essay block {i} ({lang}) cites sentence {cited}, which does not exist")
                elif cited not in marked:
                    # the summary claims to be built from the inherited marks
                    E(f"essay block {i} ({lang}) cites sentence {cited}, which is NOT underlined")
        mr_cites = re.findall(r"\{\{(\d+)\}\}", p.get("mr", ""))
        en_cites = re.findall(r"\{\{(\d+)\}\}", p.get("en", ""))
        if mr_cites != en_cites:
            W(f"essay block {i}: Marathi and English cite different sentences "
              f"({mr_cites} vs {en_cites})")

    for a in s.get("practice_actions", []):
        if a["sentence"] != "fn" and a["sentence"] not in ns:
            E(f"practice action cites sentence {a['sentence']}, which does not exist")

    st = s.get("status", {})
    if not st.get("author"):
        W("summary has no named author — it will render as 'unattributed'")
    if not st.get("reviewed_by_marathi_editor"):
        W("Marathi text has not been reviewed by an editor")


def main():
    ids = sys.argv[1:] or sorted(p.stem for p in DAYS.glob("*.json"))
    if not ids:
        raise SystemExit("no days found in content/days/")
    errors, warnings = [], []
    for day_id in ids:
        day = check_day(day_id, errors, warnings)
        if day:
            check_summary(day_id, day, errors, warnings)

    for w in warnings:
        print(f"warning  {w}")
    for e in errors:
        print(f"ERROR    {e}")
    print(f"\n{len(ids)} day(s) checked — {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
