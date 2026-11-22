"""Build a daily SONIA OIS spot-curve panel (6m, 1y, 2y) from BoE yield-curve files.

Source: Bank of England 'UK OIS curve data', sheet '4. spot curve' (end-of-day
estimated OIS spot rates, % p.a.), from oisddata.zip (2009-present archive) plus
latest-yield-curve-data.zip (current month). Output: data/processed/ois_daily.csv
"""
import datetime as dt
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TENORS = {0.5: "ois_6m", 1.0: "ois_1y", 2.0: "ois_2y"}
SHEET = "4. spot curve"


def load_sheet(path: pathlib.Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=SHEET, header=None, engine="openpyxl")
    hdr_row = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower() == "years:"][0]
    header = raw.iloc[hdr_row]
    cols = {}
    for j, v in header.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f in TENORS:
            cols[j] = TENORS[f]
    body = raw.iloc[hdr_row + 1:]
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce")
    out = body[list(cols)].rename(columns=cols).apply(pd.to_numeric, errors="coerce")
    out.insert(0, "date", dates)
    out = out.dropna(subset=["date"]).dropna(subset=list(TENORS.values()), how="all")
    out["source_file"] = path.name
    return out


def main():
    files = sorted((RAW / "ois").glob("*.xlsx")) + sorted((RAW / "latest").glob("OIS*.xlsx"))
    # The 2009-2015 workbook uses a different layout (formula tenors) and predates
    # the 2018+ sample, so only workbooks with the '4. spot curve' sheet are used.
    import openpyxl
    files = [f for f in files if SHEET in openpyxl.load_workbook(f, read_only=True).sheetnames]
    frames = [load_sheet(f) for f in files]
    df = pd.concat(frames).sort_values("date")
    df = df.drop_duplicates("date", keep="last")  # later file (current month) wins
    df = df[df.date >= "2017-06-01"].reset_index(drop=True)
    df["date"] = df["date"].dt.date
    df.to_csv(PROC / "ois_daily.csv", index=False)
    for f in frames:
        print(f"{f.source_file.iloc[0]}: {len(f)} days {f.date.min().date()} -> {f.date.max().date()}")
    print(f"panel: {len(df)} days {df.date.min()} -> {df.date.max()}; NaN 1y: {df.ois_1y.isna().sum()}")
    return df


if __name__ == "__main__":
    main()
