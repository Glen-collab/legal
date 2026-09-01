#!/usr/bin/env python3
"""Generate each app's legal pages from the markdown that lives WITH the app.

The source of truth is docs/PRIVACY.md inside each app's own repository, so the
policy is versioned alongside the code it describes. Copying the prose into this
repo would guarantee the two drift, and a privacy policy that no longer matches
the app is worse than not having one at all.

Run from this directory:  python3 build.py
"""
import pathlib, html as H, re, sys

HOME = pathlib.Path.home()
STYLE = pathlib.Path("/tmp/house.css").read_text() if pathlib.Path("/tmp/house.css").exists() else None

APPS = [
    dict(slug="spotter", name="Spotter",
         tagline="Check-in and client records for a one-person gym.",
         source=HOME / "gym-crm-ios/docs/PRIVACY.md"),
    dict(slug="bizledger", name="BizLedger",
         tagline="Income, expenses and mileage for a small business.",
         source=HOME / "business-ledger/docs/PRIVACY.md"),
]

def inline(text):
    text = H.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'(?<![\w>@.])([\w.+-]+@[\w-]+\.[\w.]+)', r'<a href="mailto:\1">\1</a>', text)
    return text

def render(md):
    """Markdown to the subset of HTML the house style knows about."""
    out, para, listing = [], [], False
    def flush():
        nonlocal para
        if para:
            out.append("  <p>" + inline(" ".join(para)) + "</p>")
            para = []
    def close():
        nonlocal listing
        if listing:
            out.append("  </ul>")
            listing = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush(); close(); continue
        if line.startswith("## "):
            flush(); close(); out.append(f"  <h2>{inline(line[3:])}</h2>")
        elif line.startswith("# ") or line.startswith("---"):
            # The title and the rules become the page header, not body text.
            flush(); close(); continue
        elif line.lstrip().startswith("- "):
            flush()
            if not listing:
                out.append("  <ul>"); listing = True
            out.append(f"    <li>{inline(line.lstrip()[2:])}</li>")
        else:
            if listing:
                out[-1] = out[-1][:-5] + " " + inline(line.strip()) + "</li>"
            else:
                para.append(line.strip())
    flush(); close()
    return "\n".join(out)

def page(app, kind, body, stamp):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{kind} — {H.escape(app['name'])}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="wrap">
  <div class="kicker">{H.escape(app['name'])}</div>
  <h1>{kind}</h1>
  <div class="date">Last updated: {stamp}</div>
{body}
  <footer>{H.escape(app['name'])} — {H.escape(app['tagline'])}</footer>
</div>
</body>
</html>
"""

if STYLE is None:
    sys.exit("house style not found — lift it from cabin/privacy.html first")

for app in APPS:
    source = app["source"]
    if not source.exists():
        sys.exit(f"missing {source} — the policy lives with the app it describes")
    md = source.read_text()
    found = re.search(r"\*\*Last updated:\s*(.+?)\*\*", md)
    stamp = found.group(1) if found else "1 September 2026"
    # Drop the date line from the body; it becomes the header stamp.
    md = re.sub(r"\*\*Last updated:.+?\*\*\s*", "", md, count=1)

    folder = pathlib.Path(app["slug"])
    folder.mkdir(exist_ok=True)
    html = page(app, "Privacy Policy", render(md), stamp)

    # The promises the page exists to make. If the markdown ever loses one,
    # stop rather than quietly publish something weaker.
    for claim in ["no server", "wisco.barbell@gmail.com"]:
        assert claim in html, f"{app['slug']}: page lost '{claim}'"
    assert "**" not in html and "\n- " not in html, f"{app['slug']}: raw markdown survived"

    (folder / "privacy.html").write_text(html)
    print(f"  {app['slug']}/privacy.html   {len(html):,} bytes")

    terms = (pathlib.Path(app["slug"] + "-terms.md"))
    if terms.exists():
        (folder / "terms.html").write_text(
            page(app, "Terms of Use", render(terms.read_text()), stamp))
        print(f"  {app['slug']}/terms.html    written")
