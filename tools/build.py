#!/usr/bin/env python3
"""Build the reader apps from the content files.

    python3 tools/build.py            # build every day found in content/days/
    python3 tools/build.py 01-01      # build one day

Templates in templates/ carry a /*DATA*/ and (for the short page) a /*SUMMARY*/
placeholder. This injects the JSON inline, which is what lets the built pages open
straight from the filesystem — no server, no fetch, no CORS.

Output: apps/full-page/<id>.html, apps/short-page/<id>.html,
        apps/short-page/<id>-passages.html, plus index.html for the earliest day.
"""
import json, pathlib, sys, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
DAYS = ROOT / "content" / "days"
SUMS = ROOT / "summary" / "days"
TPL  = ROOT / "templates"


def as_app_data(day: dict) -> dict:
    """The shape the app templates expect. Kept narrow on purpose: if an app needs a
    new field, add it here rather than reaching into the day file from the page."""
    return {
        "id": day["id"],
        "date": day["date"],
        "title_mr": day["title_mr"],
        "title_en": day["title_en"],
        "footnote": {k: day["footnote"][k] for k in ("marker", "mr", "en")},
        "paras": day["paras"],
        "sentences": [[s["n"], s["mr"], s["en"], 1 if s["highlight"] else 0]
                      for s in day["sentences"]],
        "groups": {str(s["n"]): s["group"] for s in day["sentences"] if s.get("group")},
        "points": [[p["mr"], p["en"], p["anchor"]] for p in day.get("commentary", [])],
    }


def render(tpl_name: str, data: dict, summary: dict | None) -> str:
    html = (TPL / tpl_name).read_text(encoding="utf-8")
    html = html.replace("/*DATA*/", "\nconst DATA = %s;\n"
                        % json.dumps(data, ensure_ascii=False))
    if summary is not None:
        html = html.replace("/*SUMMARY*/", "\nconst SUMMARY = %s;\n"
                            % json.dumps(summary, ensure_ascii=False))
    for placeholder in ("/*DATA*/", "/*SUMMARY*/"):
        if placeholder in html:
            raise SystemExit(f"{tpl_name}: {placeholder} was never filled")
    return html


def build(day_id: str) -> None:
    day = json.loads((DAYS / f"{day_id}.json").read_text(encoding="utf-8"))
    spath = SUMS / f"{day_id}.json"
    summary = json.loads(spath.read_text(encoding="utf-8")) if spath.exists() else None
    data = as_app_data(day)

    (ROOT / "apps" / "full-page" / f"{day_id}.html").write_text(
        render("full-page.html", data, None), encoding="utf-8")

    if summary is None:
        print(f"  {day_id}: no summary yet — short page skipped")
        return
    (ROOT / "apps" / "short-page" / f"{day_id}.html").write_text(
        render("short-page.html", data, summary), encoding="utf-8")
    (ROOT / "apps" / "short-page" / f"{day_id}-passages.html").write_text(
        render("passages.html", data, summary), encoding="utf-8")


def main() -> None:
    ids = sys.argv[1:] or sorted(p.stem for p in DAYS.glob("*.json"))
    if not ids:
        raise SystemExit("no days found in content/days/")
    for day_id in ids:
        print(f"building {day_id}")
        build(day_id)
    first = ids[0]
    for app, name in (("full-page", f"{first}.html"),
                      ("short-page", f"{first}.html")):
        src = ROOT / "apps" / app / name
        if src.exists():
            shutil.copyfile(src, ROOT / "apps" / app / "index.html")
    print(f"done — {len(ids)} day(s); index.html points at {first}")


if __name__ == "__main__":
    main()
