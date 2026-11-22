"""Join scores to SONIA OIS moves, run validation / surprise / divergence tests,
write results.md and chart.png.

Event window: BoE end-of-day OIS spot on the last business day BEFORE the
announcement date (close before) to the announcement date itself (close after;
regular decisions are released at 12:00 UK, before the end-of-day curve).
"""
import datetime as dt
import json
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
MIN_WORDS = 1000          # texts shorter than this are not scored (19 Mar 2020 summary only)
DIV_OIS_BP = 5.0          # |d1y OIS| threshold for a divergence, bp
DIV_SCORE_SD = 0.5        # |d score| threshold, in SDs of d score


def ols(y, x_cols, data):
    d = data[[y] + x_cols].dropna()
    Y = d[y].to_numpy(float)
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in x_cols])
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ Y
    e = Y - X @ b
    s2 = e @ e / (n - k)
    se = np.sqrt(np.diag(XtX_inv) * s2)
    # HC1 robust
    meat = X.T @ (X * (e ** 2)[:, None])
    se_hc1 = np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv) * n / (n - k))
    r2 = 1 - (e @ e) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return {"coef": b[1], "se": se[1], "t": b[1] / se[1], "t_hc1": b[1] / se_hc1[1],
            "p": 2 * stats.t.sf(abs(b[1] / se[1]), n - k), "const": b[0], "r2": r2, "n": n}


def event_moves(meet: pd.DataFrame, ois: pd.DataFrame) -> pd.DataFrame:
    ois = ois.set_index("date").sort_index()
    rows = []
    for _, r in meet.iterrows():
        t = pd.Timestamp(r.announce_date)
        before = ois[ois.index < t]
        after = ois[ois.index >= t]
        if before.empty or after.empty:
            rows.append({"key": r.key})
            continue
        b, a = before.iloc[-1], after.iloc[0]
        rows.append({"key": r.key, "pre_date": before.index[-1].date(), "post_date": after.index[0].date(),
                     "ois_1y_pre": b.ois_1y, "ois_1y_post": a.ois_1y,
                     **{f"d_{c}_bp": 100 * (a[c] - b[c]) for c in ["ois_6m", "ois_1y", "ois_2y"]}})
    return pd.DataFrame(rows)


def label(key):
    if "special-10" in key:
        return "Mar-20 (special 10th)"
    if "special-19" in key:
        return "Mar-20 (special 19th)"
    y, m = key[:4], int(key[5:7])
    return dt.date(int(y), m, 1).strftime("%b-%y")


def main():
    sc = pd.read_csv(PROC / "scored.csv")
    ois = pd.read_csv(PROC / "ois_daily.csv", parse_dates=["date"])
    sc = sc.sort_values("announce_date").reset_index(drop=True)
    sc.loc[sc.n_words < MIN_WORDS, ["score_per_1k", "balance"]] = np.nan
    sc["vote_mean_bp"] = sc.decision_bp + sc.vote_tilt_bp
    valid = sc.score_per_1k.notna()
    sc["d_score"] = np.nan
    sc.loc[valid, "d_score"] = sc.loc[valid, "score_per_1k"].diff()
    sc["d_net_hawk_dissent"] = sc.net_hawk_dissent.diff()
    df = sc.merge(event_moves(sc, ois), on="key", how="left")
    df["label"] = df.key.map(label)

    res = {}
    v = df[valid]
    for target in ["net_hawk_dissent", "vote_mean_bp"]:
        pr = stats.pearsonr(v.score_per_1k, v[target])
        sr = stats.spearmanr(v.score_per_1k, v[target])
        res[f"corr_{target}"] = {"pearson": pr[0], "p": pr[1], "spearman": sr[0], "sp_p": sr[1], "n": len(v)}
    dv = df.dropna(subset=["d_score", "d_net_hawk_dissent"])
    pr = stats.pearsonr(dv.d_score, dv.d_net_hawk_dissent)
    res["corr_changes"] = {"pearson": pr[0], "p": pr[1], "n": len(dv)}

    res["reg_1y"] = ols("d_ois_1y_bp", ["d_score"], df)
    res["reg_2y"] = ols("d_ois_2y_bp", ["d_score"], df)
    res["reg_6m"] = ols("d_ois_6m_bp", ["d_score"], df)
    ex = df[~df.key.str.startswith("2020-03")]
    res["reg_1y_ex_mar20"] = ols("d_ois_1y_bp", ["d_score"], ex)
    res["reg_1y_dissent"] = ols("d_ois_1y_bp", ["d_net_hawk_dissent"], df)

    sd = df.d_score.std()
    thr = DIV_SCORE_SD * sd
    div = df[(df.d_score.abs() >= thr) & (df.d_ois_1y_bp.abs() >= DIV_OIS_BP)
             & (np.sign(df.d_score) != np.sign(df.d_ois_1y_bp))].copy()
    div["type"] = np.where(div.d_score > 0, "words hawkish, 1y OIS fell", "words dovish, 1y OIS rose")
    df["divergence"] = df.key.isin(div.key)
    res["div"] = {"n": len(div), "score_thr": thr, "ois_thr": DIV_OIS_BP, "sd_dscore": sd,
                  "n_eligible": int(df.dropna(subset=["d_score", "d_ois_1y_bp"]).shape[0])}

    last = df[valid].iloc[-1]
    hist = df[valid].score_per_1k
    res["latest"] = {"key": last.key, "announce": last.announce_date, "score": last.score_per_1k,
                     "pctile": stats.percentileofscore(hist, last.score_per_1k, kind="weak"),
                     "z": (last.score_per_1k - hist.mean()) / hist.std(),
                     "rank": int((hist > last.score_per_1k).sum() + 1), "n": len(hist),
                     "d_score": last.d_score, "d1y": last.d_ois_1y_bp, "d2y": last.d_ois_2y_bp,
                     "vote": f"{last.majority}-{last.n_dissent}", "decision_bp": last.decision_bp,
                     "dissent": last.dissent_detail, "top": last.top_phrases,
                     "ois_last_date": str(ois.date.max().date()),
                     "ois_1y_last": float(ois.ois_1y.iloc[-1]), "ois_2y_last": float(ois.ois_2y.iloc[-1]),
                     "hist_mean": hist.mean(), "hist_max_key": df.loc[hist.idxmax(), "key"],
                     "hist_max": hist.max()}

    df.to_csv(PROC / "events.csv", index=False)
    div.to_csv(PROC / "divergences.csv", index=False)
    (PROC / "results.json").write_text(json.dumps(res, indent=2, default=float))
    make_chart(df, ois)
    write_results(df, div, res, ois)
    r = res["reg_1y"]
    print(f"corr(score, net hawk dissent) = {res['corr_net_hawk_dissent']['pearson']:.2f} (n={res['corr_net_hawk_dissent']['n']})")
    print(f"d1y OIS on d score: b={r['coef']:.2f}bp t={r['t']:.2f} (HC1 {r['t_hc1']:.2f}) R2={r['r2']:.3f} n={r['n']}")
    print(f"divergences: {len(div)}; latest {last.key} score {last.score_per_1k:.2f} pctile {res['latest']['pctile']:.0f}")
    return df, res


def make_chart(df, ois):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    surf, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    blue, orange = "#2a78d6", "#eb6834"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": ink2,
                         "axes.labelcolor": ink2, "xtick.color": ink2, "ytick.color": ink2})
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True, facecolor=surf,
                                   gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.12})
    o = ois[ois.date >= "2018-01-01"]
    ax1.plot(o.date, o.ois_1y, color=blue, lw=1.6, label="1y SONIA OIS (BoE spot curve, daily)")
    d = df.dropna(subset=["score_per_1k"])
    dates = pd.to_datetime(d.announce_date)
    cols = np.where(d.score_per_1k >= 0, orange, blue)
    ax2.bar(dates, d.score_per_1k, width=22, color=cols, edgecolor=surf, linewidth=0.5)
    ax2.axhline(0, color=ink2, lw=0.8)
    dv = df[df.divergence]
    dvd = pd.to_datetime(dv.announce_date)
    for x in dvd:
        for ax in (ax1, ax2):
            ax.axvline(x, color=ink2, lw=0.7, ls=(0, (2, 2)), zorder=0)
    ax1.scatter(dvd, dv.ois_1y_post, s=46, facecolor="none", edgecolor=ink, lw=1.4, zorder=5,
                label=f"Divergence: words vs 1y OIS moved opposite ways (n={len(dv)})")
    ax2.scatter(dvd, dv.score_per_1k, s=46, facecolor="none", edgecolor=ink, lw=1.4, zorder=5)
    for _, r in dv.iterrows():
        ax1.annotate(r.label, (pd.Timestamp(r.announce_date), r.ois_1y_post), xytext=(0, 12),
                     textcoords="offset points", ha="center", fontsize=7.5, color=ink, zorder=6,
                     bbox=dict(boxstyle="round,pad=0.2", fc=surf, ec=grid, lw=0.6))
    ax1.set_ylabel("1y OIS, %")
    ax2.set_ylabel("Hawk score\n(net hawkish phrases per 1,000 words)")
    for ax in (ax1, ax2):
        ax.set_facecolor(surf)
        ax.grid(axis="y", color=grid, lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    ax1.legend(loc="upper left", frameon=False, fontsize=8.5)
    from matplotlib.patches import Patch
    ax2.legend(handles=[Patch(color=orange, label="Hawkish (MPC Summary + Minutes)"),
                        Patch(color=blue, label="Dovish")], loc="lower left", frameon=False, fontsize=8.5)
    ax2.set_xlim(pd.Timestamp("2017-12-15"), pd.Timestamp("2026-12-31"))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("BoE words vs SONIA pricing: MPC hawk score and 1y OIS, Feb 2018 - Nov 2026",
                 x=0.06, ha="left", fontsize=12, color=ink, weight="bold")
    fig.text(0.06, 0.915, "Rings: meetings where the hawk score changed one way vs the prior meeting and 1y OIS "
             "moved >= 5bp the other way on the day. Source: Bank of England.", fontsize=8.5, color=ink2)
    fig.savefig(ROOT / "chart.png", dpi=160, bbox_inches="tight", facecolor=surf)
    plt.close(fig)


def f(x, n=2):
    return "n/a" if pd.isna(x) else f"{x:+.{n}f}"


def write_results(df, div, res, ois):
    c, cm, cc = res["corr_net_hawk_dissent"], res["corr_vote_mean_bp"], res["corr_changes"]
    L = res["latest"]
    lines = []
    A = lines.append
    A("# Results: BoE words vs SONIA pricing\n")
    A(f"_Generated {dt.date.today().isoformat()} by `src/analyse.py` from cached BoE downloads in `data/raw/`._\n")
    A("## Data\n")
    A(f"- **MPC decisions:** {len(df)} (announcements {df.announce_date.min()} to {df.announce_date.max()}), "
      f"including the two March 2020 special meetings. Text = Monetary Policy Summary + Minutes "
      f"({int((df.text_source == 'pdf').sum())} from the official PDF, {int((df.text_source == 'html').sum())} from HTML).")
    A(f"- **Scored:** {int(df.score_per_1k.notna().sum())} decisions (19 Mar 2020 special excluded: "
      "only a ~470-word summary exists; its minutes were published jointly with 26 Mar 2020).")
    A(f"- **Vote splits:** parsed from the minutes for all {len(df)} decisions. Every parsed dissent count matches the "
      "headline split (e.g. 7-2), and every Bank Rate change matches the rate path. One manual override, "
      "documented in `src/parse.py`: Aug 2025's two-round vote.")
    A(f"- **OIS:** BoE SONIA OIS spot curve (6m, 1y, 2y), {len(ois)} business days, {ois.date.min().date()} to "
      f"{ois.date.max().date()}. Source: the `oisddata.zip` archive plus `latest-yield-curve-data.zip`.\n")
    A("## Headline stats\n")
    A("| Test | Result |")
    A("|---|---|")
    A(f"| Score vs net hawkish-dissent count (level) | Pearson r = {c['pearson']:.2f} (p = {c['p']:.3f}), Spearman = {c['spearman']:.2f}, n = {c['n']} |")
    A(f"| Score vs committee mean preferred move, bp | Pearson r = {cm['pearson']:.2f} (p = {cm['p']:.3f}), Spearman = {cm['spearman']:.2f}, n = {cm['n']} |")
    A(f"| Change in score vs change in net hawkish dissent | Pearson r = {cc['pearson']:.2f} (p = {cc['p']:.3f}), n = {cc['n']} |")
    for k, name in [("reg_1y", "1y OIS"), ("reg_2y", "2y OIS"), ("reg_6m", "6m OIS"),
                    ("reg_1y_ex_mar20", "1y OIS, ex-Mar 2020")]:
        r = res[k]
        A(f"| Surprise regression: d{name} (bp) on d score | coef = {r['coef']:+.2f} bp per point, t = {r['t']:.2f} "
          f"(HC1 t = {r['t_hc1']:.2f}), R^2 = {r['r2']:.3f}, n = {r['n']} |")
    r = res["reg_1y_dissent"]
    A(f"| Benchmark: d1y OIS on change in net hawkish dissent | coef = {r['coef']:+.2f} bp per dissenter, t = {r['t']:.2f} "
      f"(HC1 t = {r['t_hc1']:.2f}), R^2 = {r['r2']:.3f}, n = {r['n']} |")
    A("")
    r1 = res["reg_1y"]
    sig = abs(r1["t_hc1"]) >= 1.96
    A(f"**Reading.** The lexicon score tracks the vote split (r = {c['pearson']:.2f} on levels). "
      f"The words-to-pricing link on announcement day is "
      f"{'statistically significant' if sig else 'weak and not significant at 5%'}: "
      f"R^2 = {r1['r2']:.3f} for 1y OIS. A one-SD change in the score ({res['div']['sd_dscore']:.1f} points) maps to about "
      f"{r1['coef'] * res['div']['sd_dscore']:+.1f}bp in 1y OIS. Most of the day's move is driven by things this "
      "score does not capture: the decision versus expectations, the vote split versus expectations, the MPR "
      "projections, and the press conference.\n")
    A("## Divergences\n")
    A(f"Rule: the hawk score moved by at least {DIV_SCORE_SD} SD ({res['div']['score_thr']:.2f} points) versus the prior "
      f"meeting, and 1y OIS moved at least {DIV_OIS_BP:.0f}bp the opposite way (close before to close after). "
      f"**{len(div)} of {res['div']['n_eligible']} eligible meetings are flagged.**\n")
    A("| Announced | Decision | Vote | Dissent (pref. vs decision) | d score | d 6m | d 1y | d 2y | Type |")
    A("|---|---|---|---|---|---|---|---|---|")
    for _, r in div.iterrows():
        A(f"| {r.announce_date} | {r.decision} {r.decision_bp:+.0f}bp to {r.rate_after:g}% | {r.majority}-{r.n_dissent} | "
          f"{r.dissent_detail if isinstance(r.dissent_detail, str) else '-'} | {r.d_score:+.2f} | {r.d_ois_6m_bp:+.1f} | "
          f"{r.d_ois_1y_bp:+.1f} | {r.d_ois_2y_bp:+.1f} | {r.type} |")
    A("\nIn the dissent column, `4x+0bp` means four members preferred no change.\n")
    A("## Current reading\n")
    A(f"- **Latest decision: {L['announce']}.** {'Hike' if L['decision_bp'] > 0 else 'Cut' if L['decision_bp'] < 0 else 'Hold'} "
      f"{L['decision_bp']:+.0f}bp, vote {L['vote']} (dissent: {L['dissent']}).")
    A(f"- **Hawk score {L['score']:+.2f}.** That is the {L['pctile']:.0f}th percentile of {L['n']} scored meetings since 2018 "
      f"(rank {L['rank']} most hawkish), z = {L['z']:+.2f}, change versus the prior meeting {f(L['d_score'])}. "
      f"The most hawkish on record is {L['hist_max_key']} ({L['hist_max']:+.2f}).")
    A(f"- **Pricing.** 1y OIS moved {f(L['d1y'], 1)}bp and 2y {f(L['d2y'], 1)}bp on the day. Latest curve "
      f"({L['ois_last_date']}): 1y {L['ois_1y_last']:.2f}%, 2y {L['ois_2y_last']:.2f}%.")
    A(f"- **Top phrases:** {L['top']}\n")
    A("## All meetings\n")
    A("Full table: `data/processed/events.csv`.\n")
    A("| Announced | Dec. bp | Vote | Net hawk dissent | Score | d score | d 1y bp | d 2y bp |")
    A("|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        A(f"| {r.announce_date} | {r.decision_bp:+.0f} | {r.majority}-{r.n_dissent} | {r.net_hawk_dissent:+d} | "
          f"{f(r.score_per_1k)} | {f(r.d_score)} | {f(r.d_ois_1y_bp, 1)} | {f(r.d_ois_2y_bp, 1)} |")
    A("\n## Limitations\n")
    for s in [
        "**Daily close-to-close window.** BoE curve estimates are end-of-day. Data releases and global moves on "
        "the same day contaminate the window, and an intraday window around 12:00 is not available from public BoE data.",
        "**No expectations baseline.** The score change versus the prior meeting is a crude proxy for surprise. "
        "Market expectations of the decision and the vote are not modelled, and these dominate the day's move.",
        "**Bag of phrases.** The lexicon (`lexicon.csv`, 104 phrases) was written before any results were seen and "
        "was not tuned to them. It cannot read conditionality ('if X persists, then...'), attribution (whether a "
        "phrase is the Committee's view or one member's), or sterling direction ('weaker sterling' is "
        "inflationary but scores dovish). Minutes length and format changed a lot over time: 2024+ minutes are "
        "shorter and include per-member views.",
        "**What gets scored.** Summary and Minutes only, not the MPR or the press conference. On 26 Mar 2020 the "
        "PDF combines the minutes of the 19 Mar special meeting and the 25 Mar meeting.",
        "**Vote anchor is Bank Rate only.** QE and QT dissents (e.g. Haldane in 2020-21, the Sep 2025 QT split) "
        "are not counted.",
        "**Sample size.** n is about 70 decisions, spanning very different regimes (the ZLB, COVID, 2022 hiking, "
        "2024-25 cutting, the 2026 energy shock). The divergence thresholds are judgement calls and are set as "
        "constants in `src/analyse.py`.",
    ]:
        A(f"- {s}")
    (ROOT / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
