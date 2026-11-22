"""Fetch and cache raw public data from bankofengland.co.uk.

1. MPC "Monetary Policy Summary and Minutes" pages, 2018 onwards (HTML).
   The BoE listing page is rendered by JavaScript and there is no sitemap, so we
   enumerate the stable URL pattern /monetary-policy-summary-and-minutes/YYYY/month-YYYY
   for every month and keep the ones that return HTTP 200, plus the known
   special-meeting pages (March 2020).
2. BoE OIS (SONIA) daily yield-curve zips from the yield-curves statistics page.

Everything is cached under data/raw; re-running only downloads what is missing
(use --refresh to re-download the "latest"/current-year files).
"""
import argparse
import datetime as dt
import io
import pathlib
import sys
import time
import zipfile

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MPC_DIR = RAW / "mpc"
BASE = "https://www.bankofengland.co.uk"
UA = {"User-Agent": "Mozilla/5.0 (research script; BoE public statistics)"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
SPECIAL = {
    "2020-03-special-10": "/monetary-policy-summary-and-minutes/2020/13march-2020",
    "2020-03-special-19": "/monetary-policy-summary-and-minutes/2020/monetary-policy-summary-for-the-special-monetary-policy-committee-meeting-on-19-march-2020",
}
OIS_ZIPS = ["oisddata.zip", "latest-yield-curve-data.zip"]


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=60, **kw)
    return r


def fetch_mpc(start_year=2018, refresh=False):
    MPC_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    found, missing = [], []
    targets = {}
    for y in range(start_year, today.year + 1):
        for i, m in enumerate(MONTHS, 1):
            if dt.date(y, i, 1) > today:
                break
            targets[f"{y}-{i:02d}"] = f"/monetary-policy-summary-and-minutes/{y}/{m}-{y}"
    targets.update(SPECIAL)
    for key, path in targets.items():
        out = MPC_DIR / f"{key}.html"
        if out.exists() and not refresh:
            found.append(key)
            continue
        if (MPC_DIR / f"{key}.404").exists() and not (refresh and key.startswith(str(today.year))):
            missing.append(key)
            continue
        r = get(BASE + path, allow_redirects=False)
        time.sleep(0.4)
        if r.status_code == 200 and "Monetary Policy" in r.text:
            out.write_text(r.text, encoding="utf-8")
            found.append(key)
        else:
            (MPC_DIR / f"{key}.404").write_text(f"{r.status_code} {BASE + path}\n")
            missing.append(key)
    print(f"MPC pages: {len(found)} found, {len(missing)} months without a decision page")
    return found


def fetch_mpc_pdfs(refresh=False):
    """Pre-Nov-2021 HTML pages carry only the Summary; the full minutes are in the
    linked PDF. Download the PDF linked from every decision page."""
    import re
    pdf_dir = RAW / "mpc_pdf"
    pdf_dir.mkdir(exist_ok=True)
    got, none = 0, []
    for html in sorted(MPC_DIR.glob("*.html")):
        out = pdf_dir / (html.stem + ".pdf")
        if out.exists() and not refresh:
            got += 1
            continue
        links = re.findall(r'href="(/-/media/boe/files/monetary-policy-summary-and-minutes/[^"]+\.pdf)', html.read_text(encoding="utf-8"))
        if not links:
            none.append(html.stem)
            continue
        r = get(BASE + links[0])
        time.sleep(0.4)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            out.write_bytes(r.content)
            got += 1
        else:
            none.append(html.stem)
    print(f"MPC minutes PDFs: {got} downloaded/cached; no PDF for {none}")


def fetch_ois(refresh=False):
    for name in OIS_ZIPS:
        out = RAW / name
        if out.exists() and not refresh:
            continue
        r = get(f"{BASE}/-/media/boe/files/statistics/yield-curves/{name}")
        r.raise_for_status()
        out.write_bytes(r.content)
        print(f"downloaded {name}: {len(r.content):,} bytes")
    for name, sub in [("oisddata.zip", "ois"), ("latest-yield-curve-data.zip", "latest")]:
        with zipfile.ZipFile(RAW / name) as z:
            members = [m for m in z.namelist() if m.lower().startswith("ois") and m.endswith(".xlsx")]
            (RAW / sub).mkdir(exist_ok=True)
            for m in members:
                (RAW / sub / pathlib.Path(m).name).write_bytes(z.read(m))
            print(f"{name}: extracted {members}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    fetch_ois(a.refresh)
    fetch_mpc(refresh=a.refresh)
    fetch_mpc_pdfs(refresh=a.refresh)
