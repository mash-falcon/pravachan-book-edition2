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
    PRAVACHAN_API_KEY    your token (falls back to NVIDIA_API_KEY, OPENAI_API_KEY). NVIDIA_API_KEY or OPENAI_API_KEY are used as
                         fallbacks, so an existing provider key already works.
"""
import argparse, base64, json, os, pathlib, sys, time, urllib.request, urllib.error

BASE_URL = os.environ.get("PRAVACHAN_BASE_URL", "http://localhost:11434/v1")
def _api_key() -> str:
    """Read the token from whichever variable is already set.

    PRAVACHAN_API_KEY exists so the project can be pointed at any gateway, but most
    people already have a provider key exported. Requiring a new name for the same
    secret is friction for nothing."""
    for name in ("PRAVACHAN_API_KEY", "NVIDIA_API_KEY", "OPENAI_API_KEY"):
        v = os.environ.get(name)
        if v and not v.startswith("$"):
            return v
    return "local"          # most local servers ignore it entirely


API_KEY = _api_key()

# a 1x1 PNG — enough to learn whether a model accepts images at all
ONE_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def check_key() -> None:
    if API_KEY == "local":
        sys.exit("No API key found.\n"
                 "  export PRAVACHAN_API_KEY=<token>     (or NVIDIA_API_KEY / OPENAI_API_KEY)\n"
                 "It is the same value you would put after 'Bearer ' in a request.")
    if API_KEY.startswith("$"):
        sys.exit(f"The API key is the literal text {API_KEY!r}.\n"
                 "A shell variable inside a Python string is not expanded — set the\n"
                 "real token in the environment instead.")


def ask(model: str, image: pathlib.Path | None, timeout: int,
        max_tokens: int = 256) -> tuple[str, str]:
    content = [{"type": "text", "text": "Reply with only: ok"}]
    if image is not None:
        data = base64.b64encode(image.read_bytes()).decode() if image.name != "-" \
            else base64.b64encode(ONE_PIXEL).decode()
        mime = "image/png" if image.name == "-" or image.suffix.lower() == ".png" else "image/jpeg"
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{data}"}})
    body = json.dumps({"model": model, "max_tokens": max_tokens,
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
        return "FAIL", f"HTTP {e.code}: {str(msg)[:400]}"
    except urllib.error.URLError as e:
        return "FAIL", f"unreachable: {e.reason}"
    except TimeoutError:
        return "FAIL", f"timed out after {timeout}s"

    choices = payload.get("choices")
    if choices is None:
        return "FAIL", f"no 'choices' in response — keys {list(payload)[:6]}"
    if not choices:
        # Reasoning models spend the budget thinking and emit no text if it runs out.
        # usage with completion tokens but no choices is that, not a broken model.
        u = payload.get("usage") or {}
        spent = u.get("completion_tokens") or u.get("total_tokens") or 0
        if spent and max_tokens < 2048:
            return "RETRY", f"produced {spent} tokens but no text — budget too small"
        return "FAIL", ("empty 'choices' — body "
                        + json.dumps(payload, ensure_ascii=False)[:300])
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    return ("ok", text[:40]) if text else ("ok", "(empty content)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", required=True, help="comma-separated, or a file of names")
    ap.add_argument("--image", nargs="?", const="-", default=None,
                    help="also test vision; bare flag uses a 1x1 pixel")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--max-tokens", type=int, default=256,
                    help="reasoning models need room to answer at all (default 256)")
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
        try:
            status, note = ask(m, None, a.timeout, a.max_tokens)
            if status == "RETRY":
                print(f"  ...  {m}\n       {note}; retrying with 4096")
                status, note = ask(m, None, a.timeout, 4096)
        except Exception as e:                      # one bad model must not end the sweep
            status, note = "FAIL", f"{type(e).__name__}: {e}"
        vis = ""
        if image is not None and status == "ok":
            try:
                vstatus, vnote = ask(m, image, a.timeout, max(a.max_tokens, 1024))
                if vstatus == "RETRY":
                    vstatus, vnote = ask(m, image, a.timeout, 4096)
            except Exception as e:
                vstatus, vnote = "FAIL", f"{type(e).__name__}: {e}"
            vis = "sees images" if vstatus == "ok" else f"text only ({vnote[:60]})"
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
