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
    # Put the data URI on the img itself rather than in the script, so the facsimile
    # is there with JavaScript off too — and read it back in the script instead of
    # rebuilding it, so the ~1 MB is carried once and not twice.
    html = html.replace('<img id="faxImg"', f'<img id="faxImg" src={json.dumps(uri)}')
    return html.replace("const rel=DATA.page_image ? '../../'+DATA.page_image : null;",
                        "const rel=img.getAttribute('src')||null;")


# --------------------------------------------------------------- no-JS prerender
# The built page writes its title, text, translation, footnote and commentary into
# empty divs on load. That is fine in a browser and useless everywhere else: iOS
# Quick Look — which is what opens an HTML attachment from Messages or Mail — does
# not run JavaScript, so the reviewer gets the static furniture (rules, headings,
# folio) around a blank page. So bake the text into the HTML here. The script still
# runs when it can and rewrites the same nodes with the same content; this only
# decides whether the words survive when it cannot.

DEV = str.maketrans("0123456789", "०१२३४५६७८९")
WORDS = ("no one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split()


def esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def num(x: int) -> str:
    return WORDS[x] if x < len(WORDS) else str(x)


def fill(html: str, eid: str, inner: str) -> str:
    """Put `inner` inside the empty element with this id, leaving its tag and attributes."""
    pat = re.compile(r'(<(\w+)\b[^>]*\bid="%s"[^>]*>)(</\2>)' % re.escape(eid))
    out, n = pat.subn(lambda m: m.group(1) + inner + m.group(3), html, count=1)
    if not n:
        print(f"  prerender: no empty element #{eid} — skipped")
    return out


NOSCRIPT = """
<noscript><style>
  /* Controls that only a running script can honour would be lying about their state. */
  .bar .btn,.bar .seg,.bar .fitbadge,.mala{display:none}
  /* .note is absolutely positioned and placed by measurement; with no script every
     note would stack at the top of the column. This is the script's own fallback. */
  .notes .note{position:static;margin-bottom:1rem;border-left:1px solid var(--rule)}
  .notes .note::before{display:none}
  /* Nothing can toggle the translation or open the facsimile, so show both. */
  p.tr,.foot .fen{display:block}
  #fax{display:block!important}
</style></noscript>
"""


def prerender(html: str, day_id: str) -> str:
    d = json.loads((ROOT / "content" / "days" / f"{day_id}.json").read_text(encoding="utf-8"))
    S = {s["n"]: s for s in d["sentences"]}
    comm = d.get("commentary", [])
    at = {}
    for i, c in enumerate(comm):
        at.setdefault(c["anchor"], []).append(i)

    # group consecutive sentences the same way the app does, to count marked PASSAGES
    units, prev_g = [], object()
    for s in d["sentences"]:
        g = s.get("group")
        if g and g == prev_g:
            units[-1].append(s)
        else:
            units.append([s])
        prev_g = g
    n_marked = sum(1 for u in units if u[0]["highlight"])

    paras = []
    for a, b in d["paras"]:
        ss = [S[n] for n in range(a, b + 1)]
        spans = []
        for s in ss:
            t = esc(s["mr"])
            if s["n"] == 1:  # first word as a versal — ::first-letter shears the akshara
                t = re.sub(r"^(\S+)", r'<span class="versal">\1</span>', t)
            anch = "".join(f'<span class="anch" data-c="{i}"></span>'
                           for i in at.get(s["n"], []))
            spans.append(f'<span class="s {"hl" if s["highlight"] else ""}" '
                         f'data-n="{s["n"]}">{t}</span>{anch} ')
        paras.append('<p class="t">' + "".join(spans) + '</p>'
                     + '<p class="tr">' + " ".join(esc(s["en"]) for s in ss) + '</p>')

    fn = d["footnote"]
    n, c = len(d["sentences"]), len(comm)
    m = d.get("marks", {})
    count = m.get("count_passages") or 0
    has_fn = bool(fn.get("mr"))

    parts = {
        "dl": esc(f'{d["date"]["label_mr"]}  ·  {d["date"]["label_en"]}'),
        "tmr": esc(d["title_mr"]),
        "ten": esc(d["title_en"]),
        "provN": str(n_marked).translate(DEV),
        "foot": f'<span class="num">{esc(fn["marker"])}.</span>{esc(fn["mr"])}'
                f'<em class="fen">{esc(fn["en"])}</em>',
        "body": "".join(paras),
        "notes": "".join(
            f'<div class="note" data-n="{c_["anchor"]}" data-c="{i}">'
            f'<b class="k">{esc(c_["mr"])}</b><span class="x">{esc(c_["en"])}</span></div>'
            for i, c_ in enumerate(sorted(comm, key=lambda x: (x["anchor"] == "fn",
                                                              x["anchor"])))),
        "ctxDay": esc(d["date"]["label_mr"]),
        "ctxPage": f'Title: <b>{esc(d["title_mr"])}</b>. {num(n).capitalize()} '
                   f'sentence{"" if n == 1 else "s"} of continuous prose'
                   f'{" and one footnote" if has_fn else ""}. Set from a scanned copy of a '
                   f'printed Marathi edition, in its <b>original orthography</b> — नांव, '
                   f'कांहीं, नाहीं — retained deliberately rather than modernised.',
        "ctxMarks": (f'{num(count).capitalize()} passage{"" if count == 1 else "s"} '
                     f'{"is" if count == 1 else "are"} marked. The marks were made <b>by hand, '
                     f'by a previous reader of this copy</b>, and are reproduced as an '
                     f'inherited layer. They are not the author\'s emphasis, and no editorial '
                     f'claim is made for them.'
                     + (' <b>Not yet confirmed against the scan.</b>'
                        if m.get("confirmed_by_human") is False else '')
                     if count else
                     '<b>No underlines have been recorded for this page yet.</b> '
                     + (m.get("note", "") + " " if m.get("note") else "")
                     + 'Zero here means <b>unknown</b>, not none.'),
        "ctxEdition": f'A prototype. The English translation'
                      f'{" and the margin commentary were" if c else " was"} drafted for this '
                      f'edition and {"have" if c else "has"} <b>not been reviewed</b>. '
                      + ("" if c else "There is no commentary for this page. ")
                      + 'Publisher, edition, and date of the printed source, and the rights '
                        'position for reproducing it, remain <b>to be confirmed</b>.',
    }
    for eid, inner in parts.items():
        html = fill(html, eid, inner)
    html = re.sub(r"(<body[^>]*>)", lambda mm: mm.group(1) + NOSCRIPT, html, count=1)
    print(f"  text  : prerendered {n} sentences, {c} note(s) — readable without JavaScript")
    return html


BANNER = """
<style>
  /* On a phone this notice is otherwise a full screen before a word of the page is
     visible. Tighten it rather than hiding any of it behind a tap — a disclosure
     control would need JavaScript, and surviving without JavaScript is the point. */
  @media(max-width:700px){
    #review-banner{font-size:.72rem!important;line-height:1.45!important;
      padding:.65rem .8rem!important;margin:.45rem auto 0!important}
  }
</style>
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
    ap.add_argument("--no-prerender", action="store_true",
                    help="leave the text to JavaScript (blank in iOS Quick Look)")
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
    if not a.no_prerender and a.page == "full":
        html = prerender(html, a.id)
    elif a.page != "full":
        print("  text  : only the full page is prerendered — this one needs JavaScript")
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
