"""Transparent phrase-lexicon hawk/dove scorer for MPC communications.

score_per_1k = 1000 * (hawkish hits - dovish hits) / words
balance      = (hawkish - dovish) / (hawkish + dovish)   in [-1, 1]

Rules
- Phrases come from lexicon.csv (direction +1 hawkish / -1 dovish). A trailing
  '*' on a token is a prefix wildcard (persist* -> persistent, persistence).
- Longest phrases are matched first; matched tokens are consumed so
  'weaker than expected' is not also counted as 'weak*'.
- Negation: if a negator ('not', 'no', 'little', 'limited', ...) appears in the
  3 tokens before a phrase, its direction is flipped
  ("limited evidence of knock-on effects" counts as dovish).
- Vote mechanics are stripped from the text before scoring (parse.py), so the
  score cannot mechanically encode the vote it is validated against.
"""
import csv
import pathlib
import re
from collections import Counter

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
NEGATORS = {"not", "no", "little", "limited", "without", "lack", "lacking", "less",
            "fewer", "nor", "never", "absence", "neither", "unlikely", "nothing"}
NEG_WINDOW = 3
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'.][a-z0-9]+)*%?")


def tokenize(text: str):
    return TOKEN_RE.findall(text.lower().replace("’", "'"))


def load_lexicon(path=ROOT / "lexicon.csv"):
    with open(path, newline="") as f:
        rows = [(r["phrase"].strip(), int(r["direction"]), r["category"]) for r in csv.DictReader(f)]
    lex = [(p.lower().split(), d, c, p) for p, d, c in rows]
    lex.sort(key=lambda x: -len(x[0]))
    return lex


def _tok_match(pat: str, tok: str) -> bool:
    return tok.startswith(pat[:-1]) if pat.endswith("*") else tok == pat


def score_tokens(tokens, lex):
    used = [False] * len(tokens)
    hits = []  # (phrase, direction_after_negation, category, negated)
    first = {}
    for i, t in enumerate(tokens):
        first.setdefault(t[:3], []).append(i)
    for pats, d, cat, raw in lex:
        p0 = pats[0]
        cand = first.get(p0.rstrip("*")[:3], []) if len(p0.rstrip("*")) >= 3 else range(len(tokens))
        n = len(pats)
        for i in cand:
            if i + n > len(tokens) or any(used[i:i + n]):
                continue
            if all(_tok_match(p, tokens[i + k]) for k, p in enumerate(pats)):
                neg = any(w in NEGATORS for w in tokens[max(0, i - NEG_WINDOW):i])
                hits.append((raw, -d if neg else d, cat, neg))
                for k in range(n):
                    used[i + k] = True
    return hits


def score_text(text: str, lex=None):
    lex = lex or load_lexicon()
    toks = tokenize(text)
    hits = score_tokens(toks, lex)
    h = sum(1 for _, d, _, _ in hits if d > 0)
    dv = sum(1 for _, d, _, _ in hits if d < 0)
    n = max(len(toks), 1)
    return {"n_words": len(toks), "hawk_hits": h, "dove_hits": dv,
            "negated_hits": sum(1 for x in hits if x[3]),
            "score_per_1k": 1000 * (h - dv) / n,
            "balance": (h - dv) / (h + dv) if h + dv else 0.0,
            "top_phrases": "; ".join(f"{p}({'+' if d > 0 else '-'}){c}" for (p, d), c in
                                     Counter((p, d) for p, d, _, _ in hits).most_common(6))}


def main():
    lex = load_lexicon()
    m = pd.read_csv(PROC / "meetings.csv")
    rows = []
    for key in m["key"]:
        text = (PROC / "text" / f"{key}.txt").read_text(encoding="utf-8")
        rows.append({"key": key, **score_text(text, lex)})
    s = pd.DataFrame(rows)
    out = m.merge(s, on="key")
    out.to_csv(PROC / "scored.csv", index=False)
    print(out[["key", "n_words", "hawk_hits", "dove_hits", "score_per_1k", "net_hawk_dissent"]].to_string())
    return out


if __name__ == "__main__":
    main()
