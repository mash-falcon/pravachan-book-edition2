#!/usr/bin/env python3
"""Make one self-contained HTML file to send to a reviewer.

    python3 tools/package.py --id 01-01 --out review/jan01.html
    python3 tools/package.py --id 01-01 --page short --out review/jan01-summary.html
    python3 tools/package.py --id 01-01 --out jan01.html --no-fonts --no-scan

A built page in apps/ is not portable: the facsimile is a relative path that will not
exist on anyone else's disk, and the fonts come from a CDN, so the Devanagari falls
back to a system serif if the reader is offline or behind a firewall that blocks
Google. Both are embedded here, so the file opens correctly by double-click with no
network at all.

It also prepends a banner saying what the reader is looking at and what has not been
checked — because the one thing worse than no review is a reviewer assuming the
translation and commentary have been approved by someone.
"""
import argparse, base64, json, mimetypes, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def embed_fonts(html: str) -> str:
    """Fetch the CDN stylesheet and inline every font file as a data URI."""
    link = re.search(r'<link href="(https://fonts\.googleapis\.com/css2[^"]+)"[^>]*>', html)
    if not link:
        print("  fonts: no Google Fonts link found, leaving as-is")
        return html
    try:
        req = urllib.request.Request(link.group(1).replace("&amp;", "&"),
                                     headers={"User-Agent": UA})
        css = urllib.request.urlopen(req, timeout=30).read().decode()
    except Exception as e:
        print(f"  fonts: could not fetch ({type(e).__name__}) — leaving the CDN link in")
        return html

    cache, total = {}, 0
    for url in sorted(set(re.findall(r"url\((https[^)]+)\)", css))):
        try:
            data = urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": UA}), timeout=30).read()
        except Exception:
            continue
        kind = "woff2" if url.endswith(".woff2") else "truetype"
        cache[url] = f"data:font/{'woff2' if kind=='woff2' else 'ttf'};base64," \
                     + base64.b64encode(data).decode()
        total += len(data)
    for url, uri in cache.items():
        css = css.replace(url, uri)
    print(f"  fonts: embedded {len(cache)} file(s), {total/1024:.0f} KB")
    # drop the preconnect/link tags and inline the stylesheet instead
    html = re.sub(r'<link rel="preconnect"[^>]*>\s*', "", html)
    html = re.sub(r'<link href="https://fonts\.googleapis\.com/css2[^"]+"[^>]*>',
                  f"<style>\n{css}\n</style>", html)
    return html


def embed_scan(html: str, day_id: str) -> str:
    m = re.search(r"DATA\.page_image", html)
    day = ROOT / "content" / "days" / f"{day_id}.json"
    rel = json.loads(day.read_text(encoding="utf-8")).get("source", {}).get("page_image", "")
    img = ROOT / rel if rel else None
    if not img or not img.exists():
        print(f"  scan  : {rel or '(none recorded)'} not present — facsimile will be empty")
        return html
    mime = mimetypes.guess_type(img.name)[0] or "image/jpeg"
    uri = f"data:{mime};base64," + base64.b64encode(img.read_bytes()).decode()
    print(f"  scan  : embedded {img.name}, {img.stat().st_size/1024:.0f} KB")
    # the page builds its own src from DATA.page_image; hand it the data URI instead
    return html.replace("const rel=DATA.page_image ? '../../'+DATA.page_image : null;",
                        f"const rel={json.dumps(uri)};")


BANNER = """
<div id="review-banner" style="font-family:'Inter',system-ui,sans-serif;max-width:66rem;
     margin:1rem auto 0;padding:.9rem 1.1rem;border:1px solid #c8a05a;border-radius:4px;
     background:#fdf6e8;color:#4a3a1d;font-size:.8rem;line-height:1.55">
  <b style="letter-spacing:.14em;text-transform:uppercase;font-size:.62rem;color:#9c5527">
    For review — {DATE}</b><br>
  A prototype page from a digital edition of <b>प्रवचने</b>. The Marathi is transcribed from a
  printed edition in its <b>original orthography</b>; older spellings such as नांव, कांहीं and
  नाहीं are deliberate, not errors.<br><br>
  <b>Not yet checked by anyone:</b> the English translation, the margin commentary and the
  summary were drafted for this edition and have had <b>no review by a Marathi editor or by the
  publisher</b>. The gold underlines are <b>one previous reader's hand marks</b> in a physical
  copy — not the author's emphasis. Publisher, edition and rights position for the printed
  source are unconfirmed.<br><br>
  Comments most useful on: the Marathi typography, whether the translation reads faithfully,
  and whether the commentary oversteps.
  <span style="float:right;cursor:pointer;opacity:.6"
        onclick="document.getElementById('review-banner').remove()">hide ✕</span>
</div>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--page", choices=["full", "short", "passages"], default="full")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-fonts", action="store_true")
    ap.add_argument("--no-scan", action="store_true")
    ap.add_argument("--no-banner", action="store_true")
    a = ap.parse_args()

    src = {"full": ROOT / "apps" / "full-page" / f"{a.id}.html",
           "short": ROOT / "apps" / "short-page" / f"{a.id}.html",
           "passages": ROOT / "apps" / "short-page" / f"{a.id}-passages.html"}[a.page]
    if not src.exists():
        sys.exit(f"{src} does not exist — run: python3 tools/build.py {a.id}")

    html = src.read_text(encoding="utf-8")
    print(f"packaging {src.relative_to(ROOT)}")
    if not a.no_fonts:
        html = embed_fonts(html)
    if not a.no_scan and a.page == "full":
        html = embed_scan(html, a.id)
    if not a.no_banner:
        day = json.loads((ROOT / "content" / "days" / f"{a.id}.json").read_text(encoding="utf-8"))
        label = f"{day['date']['label_mr']} · {day['date']['label_en']}"
        # the banner goes just inside <body>, not before it
        html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BANNER.replace("{DATE}", label),
                      html, count=1)

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    kb = out.stat().st_size / 1024
    print(f"\nwrote {out}  ({kb:.0f} KB)")
    print("Self-contained: open by double-click, no network needed." if not a.no_fonts
          else "Fonts still load from the CDN — the reader needs to be online.")
    if kb > 15000:
        print("Large for email — try --no-scan, which drops the facsimile.")
    print("\nFor a reviewer who would rather have a PDF: open it, then Print → Save as PDF.")
    print("The print stylesheet drops the toolbar and forces the light palette.")


if __name__ == "__main__":
    main()
