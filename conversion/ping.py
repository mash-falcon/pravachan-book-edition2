#!/usr/bin/env python3
"""Check which models on a gateway actually work, and which can see an image.

    python3 conversion/ping.py --models conversion/models.example.txt
    python3 conversion/ping.py --models a/b,c/d --image source/pages/01-02.jpg

Sends a trivial prompt to each model and reports what came back. With --image it
also sends a one-pixel picture, which separates text-only models from vision ones
without spending a real page.

Exists because a failing call from a hand-written snippet usually surfaces as
KeyError: 'choices' — the script indexing a response it never checked. Errors here
print the gateway's own message instead.

Environment:
    PRAVACHAN_BASE_URL   default http://localhost:11434/v1
    PRAVACHAN_API_KEY    your token — NOT the literal string "$API_KEY"
"""
import argparse, base64, json, os, pathlib, sys, time, urllib.request, urllib.error

BASE_URL = os.environ.get("PRAVACHAN_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("PRAVACHAN_API_KEY", "")

# a 1x1 PNG — enough to learn whether a model accepts images at all
ONE_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def check_key() -> None:
    if not API_KEY:
        sys.exit("PRAVACHAN_API_KEY is not set.\n"
                 "  export PRAVACHAN_API_KEY=<your token>")
    if API_KEY.startswith("$") or API_KEY in ("$API_KEY", "$NVIDIA_API_KEY"):
        sys.exit(f"PRAVACHAN_API_KEY is the literal text {API_KEY!r}.\n"
                 "A shell variable inside a Python string is not expanded — set the\n"
                 "real token in the environment instead.")


def ask(model: str, image: pathlib.Path | None, timeout: int) -> tuple[str, str]:
    content = [{"type": "text", "text": "Reply with only: ok"}]
    if image is not None:
        data = base64.b64encode(image.read_bytes()).decode() if image.name != "-" \
            else base64.b64encode(ONE_PIXEL).decode()
        mime = "image/png" if image.name == "-" or image.suffix.lower() == ".png" else "image/jpeg"
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"}})
    body = json.dumps({"model": model, "max_tokens": 16,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(
        BASE_URL.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        try:                                    # gateways bury the reason at varying depths
            j = json.loads(detail)
            msg = (j.get("error", {}).get("message") if isinstance(j.get("error"), dict)
                   else j.get("error")) or j.get("message") or detail
        except Exception:
            msg = detail
        return "FAIL", f"HTTP {e.code}: {str(msg)[:120]}"
    except urllib.error.URLError as e:
        return "FAIL", f"unreachable: {e.reason}"
    except TimeoutError:
        return "FAIL", f"timed out after {timeout}s"

    if "choices" not in payload:                # the KeyError, caught and explained
        return "FAIL", f"no 'choices' in response — got keys {list(payload)[:6]}"
    return "ok", (payload["choices"][0]["message"].get("content") or "").strip()[:40]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", required=True, help="comma-separated, or a file of names")
    ap.add_argument("--image", nargs="?", const="-", default=None,
                    help="also test vision; bare flag uses a 1x1 pixel")
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    check_key()

    mp = pathlib.Path(a.models)
    models = ([ln.strip() for ln in mp.read_text().splitlines()
               if ln.strip() and not ln.startswith("#")] if mp.exists()
              else [m.strip() for m in a.models.split(",") if m.strip()])
    image = pathlib.Path(a.image) if a.image else None

    print(f"{BASE_URL}   {len(models)} model(s)"
          + ("   + image test" if image else "") + "\n")
    rows = []
    for m in models:
        t0 = time.time()
        status, note = ask(m, None, a.timeout)
        vis = ""
        if image is not None and status == "ok":
            vstatus, vnote = ask(m, image, a.timeout)
            vis = "sees images" if vstatus == "ok" else f"text only ({vnote[:50]})"
        rows.append((m, status, f"{time.time()-t0:.1f}s", note, vis))
        print(f"  {status:<4} {m}")
        if status != "ok":
            print(f"       {note}")
        elif vis:
            print(f"       {vis}")

    ok = [r for r in rows if r[1] == "ok"]
    print(f"\n{len(ok)}/{len(rows)} responded")
    if image is not None:
        seeing = [r[0] for r in rows if r[4] == "sees images"]
        print(f"vision-capable: {seeing or 'none'}")
    bad = [r[0] for r in rows if r[1] != "ok"]
    if bad:
        print(f"not usable    : {bad}")


if __name__ == "__main__":
    main()
