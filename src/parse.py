"""Parse cached BoE MPC pages/PDFs into one row per decision.

Output: data/processed/meetings.csv (+ data/processed/text/<key>.txt cleaned text)

Per meeting:
  announce_date     date the decision was published (market event date)
  decision          hike / cut / hold, decision_bp, rate_after (%)
  majority, n_dissent  from the headline vote ("voted by a majority of 7-2")
  n_hike, n_hold, n_cut  members by the Bank Rate action they voted for
  hawk_dissent, dove_dissent, net_hawk_dissent  dissenters wanting a higher /
                    lower Bank Rate than the decision (ground-truth anchor)
  vote_tilt_bp      sum over dissenters of (preferred - decided) bp / 9
"""
import datetime as dt
import pathlib
import re
import sys

import pandas as pd
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
COMMITTEE = 9
NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
            "seven": 7, "eight": 8, "nine": 9}

# Market event dates that differ from the page's "Published on" date.
# 10 Mar 2020 special meeting: decision announced 07:00 on 11 Mar 2020
# (minutes page published 13 Mar). Source: BoE minutes text, para on publication.
ANNOUNCE_OVERRIDE = {"2020-03-special-10": "2020-03-11"}

# Manual vote corrections, each justified from the minutes text.
# Aug 2025 used a two-round vote. Final vote 5-4 for a 25bp cut; Alan Taylor's
# first-round preference for 50bp is NOT a recorded dissent ("One of these
# members (Alan Taylor), who would otherwise have preferred to reduce Bank Rate
# by 0.5 percentage points, voted for a 0.25 percentage points reduction").
VOTE_OVERRIDE = {
    "2025-08": [(4, 0)],  # four members preferred to maintain (pref change 0bp)
}


def norm(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-").replace("’", "'")
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def html_text(path: pathlib.Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    main = soup.find("main") or soup
    for tag in main.find_all(["script", "style", "nav"]):
        tag.decompose()
    return norm(main.get_text(" ", strip=True))


def pdf_text(path: pathlib.Path) -> str:
    from pypdf import PdfReader
    r = PdfReader(str(path))
    return norm(" ".join((p.extract_text() or "") for p in r.pages))


def to_bp(num: str, unit: str) -> float:
    x = float(num)
    return x * 100 if unit.startswith("percentage") else x


DECISION_RE = re.compile(
    r"voted (?:(?P<how>unanimously|by (?:a majority of )?(?P<split>\d(?:-\d){1,2})))?"
    r"[^.%]*?\bto (?P<act>increase|reduce|maintain) Bank Rate"
    r"(?: by (?P<num>[\d.]+) (?P<unit>percentage points?|basis points))?,? (?:to|at) (?P<lvl>\d+(?:\.\d+)?) ?%")

PROP_RE = re.compile(
    r"Bank Rate should be (?P<act>increased|reduced|maintained)"
    r"(?: by (?P<num>[\d.]+) (?P<unit>percentage points?|basis points))?,? (?:to|at) (?P<lvl>\d+(?:\.\d+)?) ?%")

PREF_RE = re.compile(
    r"(?P<who>[^.;]*?)\b(?:preferring|preferred) to (?P<act>increase|reduce|maintain|leave) Bank Rate"
    r"(?: unchanged)?(?: by (?P<num>[\d.]+) (?P<unit>percentage points?|basis points))?")


def parse_decision(text: str):
    m = DECISION_RE.search(text)
    if not m:
        # Fallback: the formal proposition in the minutes (e.g. 10 Mar 2020 special)
        p = PROP_RE.search(text)
        if not p or "voted unanimously in favour" not in text:
            raise ValueError("decision sentence not found")
        act = {"increased": "increase", "reduced": "reduce", "maintained": "maintain"}[p["act"]]
        bp = 0.0 if act == "maintain" else to_bp(p["num"], p["unit"])
        return {"decision_bp": -bp if act == "reduce" else bp, "rate_after": float(p["lvl"]),
                "majority": COMMITTEE, "n_dissent": 0, "decision_sentence": p.group(0)}
    act = m["act"]
    bp = 0.0 if act == "maintain" else to_bp(m["num"], m["unit"])
    bp = -bp if act == "reduce" else bp
    if m["how"] == "unanimously":
        majority, n_dissent = COMMITTEE, 0
    elif m["how"] is None:  # e.g. Sep 2022 "the MPC voted to increase" (5-3-1 given in later text)
        majority, n_dissent = None, None
    else:
        parts = [int(x) for x in m["split"].split("-")]
        majority, n_dissent = parts[0], sum(parts[1:])
    return {"decision_bp": bp, "rate_after": float(m["lvl"]),
            "majority": majority, "n_dissent": n_dissent,
            "decision_sentence": m.group(0)}


def count_who(who: str) -> int:
    who = re.split(r"\bvoted\b|\bpreferr", who)[0].strip(" ,")
    w = who.lower()
    m = re.search(r"\b(one|two|three|four|five|six|seven|eight)\b (?:of these )?members?", w)
    if m:
        return NUMWORDS[m.group(1)]
    names = re.sub(r"\(.*?\)", "", who).strip()
    return max(1, len(re.split(r",| and ", names)))


def vote_section(text: str) -> str:
    anchors = [text.find(a) for a in ("invited the Committee to vote", "Regarding Bank Rate",
                                       "voted in favour of the proposition")]
    anchors = [a for a in anchors if a >= 0]
    if not anchors:
        return ""
    i = min(anchors)
    seg = text[i:i + 3000]
    cut = [seg.find(k) for k in ("Operational considerations", "The following members",
                                 "MPC members' views", "Members set out the rationale")]
    cut = [c for c in cut if c > 0]
    return seg[:min(cut)] if cut else seg


def parse_dissents(vote_text: str, decision_bp: float):
    """Return list of (n_members, preferred_change_bp) for Bank Rate dissents."""
    out = []
    clauses = re.split(r"(?<=\.) (?=[A-Z])|, and (?=[A-Z][a-z]+ [A-Z])", vote_text)
    for c in clauses:
        if "would otherwise have preferred" in c:
            continue
        for m in PREF_RE.finditer(c):
            act = m["act"]
            if act in ("maintain", "leave"):
                pref = 0.0
            else:
                pref = to_bp(m["num"], m["unit"]) if m["num"] else 25.0
                pref = -pref if act == "reduce" else pref
            out.append((count_who(m["who"]), pref))
    return out


def clean_for_scoring(text: str) -> str:
    """Drop vote mechanics (scored text must not mechanically encode the vote),
    running headers and the attendance list."""
    text = re.sub(r"Bank of England Minutes of the (?:special )?Monetary Policy Committee meeting[^0-9]*?\d{4}(?: \d+)?", " ", text)
    text = re.sub(r"The following members of the Committee were present.*", " ", text)
    sents = re.split(r"(?<=[.;]) (?=[A-Z0-9])", text)
    keep = [s for s in sents if not re.search(
        r"\bvoted\b|\bvote\b|proposition|preferr(?:ed|ing) to (?:increase|reduce|maintain|leave)", s)]
    return " ".join(keep)


def main():
    rows = []
    (PROC / "text").mkdir(parents=True, exist_ok=True)
    for html in sorted((RAW / "mpc").glob("*.html")):
        key = html.stem
        h = html_text(html)
        pub = re.search(r"Published on\s+(\d{1,2} \w+ \d{4})", h)
        announce = dt.datetime.strptime(pub.group(1), "%d %B %Y").date().isoformat()
        announce = ANNOUNCE_OVERRIDE.get(key, announce)
        pdf = RAW / "mpc_pdf" / f"{key}.pdf"
        full = pdf_text(pdf) if pdf.exists() else h
        source = "pdf" if pdf.exists() else "html"
        d = parse_decision(h if DECISION_RE.search(h) else full)
        if key == "2020-03":  # page = 25 Mar meeting; PDF opens with 19 Mar special
            d = parse_decision(full[full.find("meeting ending on 25 March 2020, the MPC"):] or h)
        dis = VOTE_OVERRIDE.get(key) or parse_dissents(vote_section(full), d["decision_bp"])
        n_parsed = sum(n for n, _ in dis)
        if d["majority"] is None:
            d["majority"], d["n_dissent"] = COMMITTEE - n_parsed, n_parsed
        hawk = sum(n for n, p in dis if p > d["decision_bp"])
        dove = sum(n for n, p in dis if p < d["decision_bp"])
        members = [(d["majority"], d["decision_bp"])] + dis
        n_hike = sum(n for n, p in members if p > 0)
        n_cut = sum(n for n, p in members if p < 0)
        n_hold = sum(n for n, p in members if p == 0)
        tilt = sum(n * (p - d["decision_bp"]) for n, p in dis) / COMMITTEE
        scored = clean_for_scoring(full)
        (PROC / "text" / f"{key}.txt").write_text(scored, encoding="utf-8")
        meet = (re.search(r"meeting ending on (\d{1,2} \w+ \d{4})", h)
                or re.search(r"meeting on (\d{1,2} \w+ \d{4})", h))
        rows.append({
            "key": key,
            "meeting_end": dt.datetime.strptime(meet.group(1), "%d %B %Y").date().isoformat() if meet else "",
            "announce_date": announce,
            "decision": "hike" if d["decision_bp"] > 0 else "cut" if d["decision_bp"] < 0 else "hold",
            "decision_bp": d["decision_bp"], "rate_after": d["rate_after"],
            "majority": d["majority"], "n_dissent": d["n_dissent"],
            "n_dissent_parsed": n_parsed, "vote_check_ok": n_parsed == d["n_dissent"],
            "n_hike": n_hike, "n_hold": n_hold, "n_cut": n_cut,
            "hawk_dissent": hawk, "dove_dissent": dove, "net_hawk_dissent": hawk - dove,
            "vote_tilt_bp": round(tilt, 2),
            "dissent_detail": "; ".join(f"{n}x{p:+.0f}bp" for n, p in dis),
            "text_source": source, "n_words_scored": len(scored.split()),
            "decision_sentence": d["decision_sentence"],
            "url_key": key,
        })
    df = pd.DataFrame(rows).sort_values("announce_date").reset_index(drop=True)
    # Consistency: rate level change should equal decision_bp vs previous meeting
    df["rate_check_ok"] = (((df["rate_after"].diff() * 100).round(1) == df["decision_bp"].round(1))
                           | df.index.isin([0]))
    df.to_csv(PROC / "meetings.csv", index=False)
    bad = df[~df.vote_check_ok | ~df.rate_check_ok]
    print(f"{len(df)} decisions {df.announce_date.min()} -> {df.announce_date.max()}")
    print(f"vote parse mismatches: {int((~df.vote_check_ok).sum())}; rate-path mismatches: {int((~df.rate_check_ok).sum())}")
    if len(bad):
        print(bad[["key", "decision_bp", "rate_after", "n_dissent", "n_dissent_parsed", "dissent_detail"]].to_string())
    return df


if __name__ == "__main__":
    main()
