"""Chapter 2: data center growth in California (RQ1).

Functions read only data/raw (through the manifest) or data/processed tables made by earlier
chapters, and return pandas objects. scripts/run_chapter2.py writes tables and figures.

Statistical conventions
- Trend regressions are on log levels: log y_t = a + b t, t in months (or quarters / half-years).
- Compound growth per year = exp(b * periods_per_year) - 1, with a Newey-West (HAC) standard error
  on b; the 95 percent interval maps the slope interval through the same transform.
- Chow test: F for a break in intercept and slope at a known date (classical F, plus a HAC-robust
  Wald test of the same restrictions).
- Bai-Perron: global least-squares minimisation over all partitions with a minimum segment length
  (trimming 15 percent), for m = 1..M breaks; the number of breaks is chosen by BIC and by the LWZ
  criterion; supF(0|m) statistics are reported with a moving-block residual bootstrap p-value
  under the no-break null; the break date for m = 1 gets a residual-bootstrap 90 percent interval.
"""
from __future__ import annotations

import glob
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from .ch1_baseline import raw_path
from .paths import PROCESSED

CHATGPT = pd.Timestamp("2022-11-30")  # launch date, used for annotations
CHATGPT_FIRST_POST = pd.Timestamp("2022-12-31")  # first full post-launch monthly observation (December 2022)


# ------------------------------------------------------------------------------------------------
# 1. Census C30 construction spending, data center line
# ------------------------------------------------------------------------------------------------
def _parse_c30_date(label: str) -> pd.Timestamp:
    m = re.match(r"([A-Za-z]{3})-(\d{2})([pr]?)", str(label).strip())
    if not m:
        return pd.NaT
    return pd.Timestamp(f"20{m.group(2)}-{m.group(1)}-01") + pd.offsets.MonthEnd(0)


def census_c30() -> pd.DataFrame:
    """Monthly national construction spending: data center line, SAAR (privsatime) and NSA (privtime),
    plus total private and nonresidential SAAR, millions of dollars."""
    out = {}
    for sid, tag in (("census_c30_privsatime", "saar"), ("census_c30_privtime", "nsa")):
        d = pd.read_excel(raw_path(sid), header=None)
        hdr = d.iloc[3].astype(str).str.replace("\n", " ").str.replace("_x000D_", "").str.strip().tolist()
        col = {h: i for i, h in enumerate(hdr)}
        dc = next(i for h, i in col.items() if h.startswith("Data center"))
        tot = next(i for h, i in col.items() if h.startswith("Total"))
        nonres = next(i for h, i in col.items() if h.startswith("Nonresidential"))
        office = next(i for h, i in col.items() if h == "Office")
        rows = d.iloc[4:].copy()
        rows["date"] = rows[0].map(_parse_c30_date)
        rows = rows.dropna(subset=["date"])
        rows["flag"] = rows[0].astype(str).str.extract(r"([pr])$")[0].fillna("")
        s = pd.DataFrame({"date": rows["date"].values,
                          f"data_center_{tag}": pd.to_numeric(rows[dc], errors="coerce").values,
                          f"total_private_{tag}": pd.to_numeric(rows[tot], errors="coerce").values,
                          f"nonresidential_{tag}": pd.to_numeric(rows[nonres], errors="coerce").values,
                          f"office_{tag}": pd.to_numeric(rows[office], errors="coerce").values,
                          f"flag_{tag}": rows["flag"].values}).set_index("date").sort_index()
        out[tag] = s
    df = out["saar"].join(out["nsa"], how="outer")
    df = df[df["data_center_saar"].notna() | df["data_center_nsa"].notna()]
    df["dc_share_of_nonres_pct"] = df["data_center_saar"] / df["nonresidential_saar"] * 100
    df["mom_growth_pct"] = df["data_center_saar"].pct_change() * 100
    df["yoy_growth_pct"] = df["data_center_saar"].pct_change(12) * 100
    return df


# ------------------------------------------------------------------------------------------------
# 2. Trend, Chow, growth rates, Bai-Perron, forecasts
# ------------------------------------------------------------------------------------------------
def _ols_ssr(y: np.ndarray, X: np.ndarray) -> float:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return float(r @ r)


def trend_X(n: int) -> np.ndarray:
    return np.column_stack([np.ones(n), np.arange(n, dtype=float)])


def growth_rate(y_log: np.ndarray, periods_per_year: int, maxlags: int | None = None) -> dict:
    """OLS log-linear trend with Newey-West SE; returns annualised compound growth and 95% CI."""
    import statsmodels.api as sm
    n = len(y_log)
    X = trend_X(n)
    maxlags = maxlags if maxlags is not None else max(1, int(round(periods_per_year)))
    res = sm.OLS(y_log, X).fit(cov_type="HAC", cov_kwds={"maxlags": min(maxlags, max(1, n // 3))})
    b, se = float(res.params[1]), float(res.bse[1])
    g = lambda s: float(np.exp(s * periods_per_year) - 1)  # noqa: E731
    return {"n": n, "slope": b, "se_hac": se, "cagr": g(b), "cagr_lo95": g(b - 1.96 * se), "cagr_hi95": g(b + 1.96 * se),
            "r2": float(res.rsquared)}


def chow_test(y_log: np.ndarray, break_idx: int, maxlags: int = 12) -> dict:
    """Break in intercept and slope at break_idx (first observation of the second regime)."""
    import statsmodels.api as sm
    from scipy import stats
    n = len(y_log)
    k = 2
    X = trend_X(n)
    ssr_r = _ols_ssr(y_log, X)
    ssr_u = _ols_ssr(y_log[:break_idx], X[:break_idx]) + _ols_ssr(y_log[break_idx:], X[break_idx:])
    F = ((ssr_r - ssr_u) / k) / (ssr_u / (n - 2 * k))
    p = float(1 - stats.f.cdf(F, k, n - 2 * k))
    D = (np.arange(n) >= break_idx).astype(float)
    Xu = np.column_stack([X, D, D * X[:, 1]])
    res = sm.OLS(y_log, Xu).fit(cov_type="HAC", cov_kwds={"maxlags": min(maxlags, max(1, n // 3))})
    R = np.zeros((2, 4)); R[0, 2] = 1; R[1, 3] = 1
    w = res.wald_test(R, scalar=True)
    return {"break_idx": int(break_idx), "chow_F": float(F), "chow_p": p, "df": (k, n - 2 * k),
            "wald_hac_chi2": float(w.statistic), "wald_hac_p": float(w.pvalue),
            "slope_change": float(res.params[3]), "slope_change_se_hac": float(res.bse[3])}


def _segment_ssr_table(y: np.ndarray, X: np.ndarray, h: int) -> np.ndarray:
    """ssr[i, j] = SSR of the linear-trend regression on observations i..j inclusive (j - i + 1 >= h),
    else inf. Closed form from prefix sums so that the bootstrap stays fast."""
    n = len(y)
    t = X[:, 1]
    cs = lambda v: np.concatenate([[0.0], np.cumsum(v)])  # noqa: E731
    Sx, Sy, Sxx, Sxy, Syy = cs(t), cs(y), cs(t * t), cs(t * y), cs(y * y)
    i = np.arange(n)[:, None]; j = np.arange(n)[None, :]
    m = (j - i + 1).astype(float)
    sx, sy = Sx[j + 1] - Sx[i], Sy[j + 1] - Sy[i]
    sxx, sxy, syy = Sxx[j + 1] - Sxx[i], Sxy[j + 1] - Sxy[i], Syy[j + 1] - Syy[i]
    with np.errstate(divide="ignore", invalid="ignore"):
        den = m * sxx - sx * sx
        slope = np.where(den != 0, (m * sxy - sx * sy) / den, 0.0)
        icpt = (sy - slope * sx) / m
        ssr = syy - icpt * sy - slope * sxy
    ssr = np.where(m >= h, np.maximum(ssr, 0.0), np.inf)
    return ssr


def bai_perron(y_log: np.ndarray, max_breaks: int = 5, trim: float = 0.15, k: int = 2) -> dict:
    """Global minimisation of SSR over partitions with m = 0..max_breaks breaks (Bai & Perron 1998, 2003).
    With 15 percent trimming at most five breaks are feasible, so max_breaks=5 leaves the BIC/LWZ choice uncensored."""
    n = len(y_log)
    X = trend_X(n)
    h = max(int(np.ceil(trim * n)), k + 1)
    ssr = _segment_ssr_table(y_log, X, h)
    # cost[m][j]: min SSR for observations 0..j split into m+1 segments
    cost = np.full((max_breaks + 1, n), np.inf)
    arg = np.full((max_breaks + 1, n), -1, dtype=int)
    cost[0] = ssr[0]
    for m in range(1, max_breaks + 1):
        for j in range(n):
            idx = np.arange(m * h - 1, j - h + 1)  # last break after obs i (segment m+1 = i+1..j)
            if len(idx) == 0:
                continue
            cand = cost[m - 1, idx] + ssr[idx + 1, j]
            b = int(np.argmin(cand))
            cost[m, j], arg[m, j] = cand[b], idx[b]
    results = {}
    for m in range(0, max_breaks + 1):
        if not np.isfinite(cost[m, n - 1]):
            continue
        breaks, j = [], n - 1
        for mm in range(m, 0, -1):
            i = arg[mm, j]
            breaks.append(i + 1)  # first observation of the new regime
            j = i
        breaks = sorted(breaks)
        p_star = (m + 1) * k + m
        S = cost[m, n - 1]
        bic = np.log(S / n) + p_star * np.log(n) / n
        lwz = np.log(S / (n - p_star)) + p_star * 0.299 * (np.log(n)) ** 2.1 / n
        supF = ((n - (m + 1) * k) / (m * k)) * (cost[0, n - 1] - S) / S if m > 0 else np.nan
        results[m] = {"breaks": breaks, "ssr": float(S), "bic": float(bic), "lwz": float(lwz), "supF": float(supF)}
    m_bic = min(results, key=lambda m: results[m]["bic"])
    m_lwz = min(results, key=lambda m: results[m]["lwz"])
    return {"n": n, "h": h, "by_m": results, "m_bic": m_bic, "m_lwz": m_lwz, "breaks_bic": results[m_bic]["breaks"]}


def bootstrap_supF(y_log: np.ndarray, m: int = 1, reps: int = 299, block: int = 12, trim: float = 0.15, seed: int = 7) -> dict:
    """Moving-block residual bootstrap p-value for supF(0|m) under the single-trend null."""
    rng = np.random.default_rng(seed)
    n = len(y_log)
    X = trend_X(n)
    beta, *_ = np.linalg.lstsq(X, y_log, rcond=None)
    fit = X @ beta
    resid = y_log - fit
    obs = bai_perron(y_log, max_breaks=m, trim=trim)["by_m"][m]["supF"]
    block = max(2, min(block, n // 4))
    count = 0
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))])[:n]
        yb = fit + resid[idx]
        bp = bai_perron(yb, max_breaks=m, trim=trim)
        if bp["by_m"].get(m, {"supF": -np.inf})["supF"] >= obs:
            count += 1
    return {"supF_obs": float(obs), "bootstrap_p": (count + 1) / (reps + 1), "reps": reps, "block": block}


def _segment_fit(y_log: np.ndarray, breaks: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Piecewise OLS fit and residuals for a given partition (breaks = first obs of each new regime)."""
    n = len(y_log); X = trend_X(n)
    fit = np.empty(n)
    for lo, hi in zip([0] + list(breaks), list(breaks) + [n]):
        beta, *_ = np.linalg.lstsq(X[lo:hi], y_log[lo:hi], rcond=None)
        fit[lo:hi] = X[lo:hi] @ beta
    return fit, y_log - fit


def _supF_one_more(y_log: np.ndarray, breaks: list[int], h: int, k: int = 2) -> float:
    """supF(l+1|l): the largest single-break F statistic across the l+1 segments of a given partition
    (Bai & Perron 1998, eq. 13), with the minimum segment length h imposed within each segment."""
    n = len(y_log); best = -np.inf
    for lo, hi in zip([0] + list(breaks), list(breaks) + [n]):
        T = hi - lo
        if T < 2 * h:
            continue
        yseg = y_log[lo:hi]; X = trend_X(T)
        ssr = _segment_ssr_table(yseg, X, h)
        ssr0 = ssr[0, T - 1]
        i = np.arange(h - 1, T - h)
        ssr1 = float(np.min(ssr[0, i] + ssr[i + 1, T - 1]))
        tiny = 1e-10 * max(1.0, float(np.var(yseg)) * T)  # numerically exact fits (flat log series) carry no evidence
        if ssr1 <= tiny:
            F = np.inf if ssr0 > tiny else -np.inf
        else:
            F = max(0.0, ((T - 2 * k) / k) * (ssr0 - ssr1) / ssr1)
        best = max(best, F)
    return float(best)


def sequential_supF(y_log: np.ndarray, max_breaks: int = 5, trim: float = 0.15, reps: int = 199, block: int = 12,
                    seed: int = 13, alpha: float = 0.05) -> dict:
    """Bai-Perron sequential procedure: test l+1 versus l breaks for l = 0..max_breaks-1, each with a moving-block
    residual bootstrap p-value under the l-break null; m_seq is the first l whose null is not rejected at alpha."""
    rng = np.random.default_rng(seed)
    n = len(y_log)
    bp = bai_perron(y_log, max_breaks=max_breaks, trim=trim)
    h = bp["h"]; block = max(2, min(block, n // 4))
    out = {"levels": {}, "m_seq": None}
    for l in range(0, max_breaks):
        if l not in bp["by_m"] or (l + 1) not in bp["by_m"]:
            break
        breaks = bp["by_m"][l]["breaks"]
        obs = _supF_one_more(y_log, breaks, h)
        if not np.isfinite(obs):
            break
        fit, resid = _segment_fit(y_log, breaks)
        count = 0
        for _ in range(reps):
            idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))])[:n]
            yb = fit + resid[idx]
            bb = bai_perron(yb, max_breaks=l, trim=trim)["by_m"][l]["breaks"] if l > 0 else []
            if _supF_one_more(yb, bb, h) >= obs:
                count += 1
        p = (count + 1) / (reps + 1)
        out["levels"][l + 1] = {"supF_seq": obs, "boot_p": p}
        if p >= alpha and out["m_seq"] is None:
            out["m_seq"] = l
    if out["m_seq"] is None:
        out["m_seq"] = max(out["levels"]) if out["levels"] else 0
    out["reps"] = reps; out["block"] = block
    return out


def bootstrap_break_date(y_log: np.ndarray, reps: int = 299, trim: float = 0.15, seed: int = 11) -> dict:
    """Residual bootstrap (within-segment, moving blocks) of the single-break location."""
    rng = np.random.default_rng(seed)
    n = len(y_log)
    bp = bai_perron(y_log, max_breaks=1, trim=trim)
    b = bp["by_m"][1]["breaks"][0]
    X = trend_X(n)
    fit = np.empty(n); resid = np.empty(n)
    for lo, hi in ((0, b), (b, n)):
        beta, *_ = np.linalg.lstsq(X[lo:hi], y_log[lo:hi], rcond=None)
        fit[lo:hi] = X[lo:hi] @ beta
        resid[lo:hi] = y_log[lo:hi] - fit[lo:hi]
    block = max(2, min(12, n // 4))
    locs = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))])[:n]
        yb = fit + resid[idx]
        locs.append(bai_perron(yb, max_breaks=1, trim=trim)["by_m"][1]["breaks"][0])
    locs = np.array(locs)
    return {"break_idx": int(b), "ci90": (int(np.percentile(locs, 5)), int(np.percentile(locs, 95))), "reps": reps}


def arima_forecast(y_log: pd.Series, horizon: int = 24, freq: str = "ME") -> tuple[pd.DataFrame, dict]:
    """ARIMA(p,1,q) with drift on log levels, order chosen by AIC over p,q in {0,1,2}; forecasts in levels."""
    from statsmodels.tsa.arima.model import ARIMA
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in (0, 1, 2):
            for q in (0, 1, 2):
                try:
                    r = ARIMA(y_log.values, order=(p, 1, q), trend="t").fit()
                except Exception:
                    continue
                if best is None or r.aic < best[1]:
                    best = ((p, 1, q), r.aic, r)
    order, aic, res = best
    fc = res.get_forecast(horizon)
    idx = pd.date_range(y_log.index[-1] + pd.offsets.MonthEnd(1), periods=horizon, freq=freq)
    out = pd.DataFrame({"mean": np.exp(fc.predicted_mean)}, index=idx)
    for a, lab in ((0.20, "80"), (0.05, "95")):
        ci = fc.conf_int(alpha=a)
        out[f"lo{lab}"] = np.exp(ci[:, 0]); out[f"hi{lab}"] = np.exp(ci[:, 1])
    return out, {"order": order, "aic": float(aic), "drift_per_month": float(res.params[0]) if "x1" in getattr(res, "param_names", []) or True else np.nan,
                 "params": {k: float(v) for k, v in zip(res.param_names, res.params)}}


def ets_forecast(y_log: pd.Series, horizon: int = 24, freq: str = "ME") -> tuple[pd.DataFrame, dict]:
    """ETS(A,Ad,N): additive error, damped additive trend on log levels; simulation-based intervals."""
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ys = pd.Series(np.asarray(y_log.values, dtype=float), index=pd.DatetimeIndex(y_log.index, freq=freq))
        model = ETSModel(ys, error="add", trend="add", damped_trend=True)
        res = model.fit(disp=False)
        pred = res.get_prediction(start=len(y_log), end=len(y_log) + horizon - 1)
        sf80 = pred.summary_frame(alpha=0.20); sf95 = pred.summary_frame(alpha=0.05)
    idx = pd.date_range(y_log.index[-1] + pd.offsets.MonthEnd(1), periods=horizon, freq=freq)
    out = pd.DataFrame({"mean": np.exp(sf80["mean"].values), "lo80": np.exp(sf80["pi_lower"].values), "hi80": np.exp(sf80["pi_upper"].values),
                        "lo95": np.exp(sf95["pi_lower"].values), "hi95": np.exp(sf95["pi_upper"].values)}, index=idx)
    return out, {"aic": float(res.aic), "alpha": float(res.params[0]), "beta": float(res.params[1]), "phi": float(res.params[2]) if len(res.params) > 2 else np.nan}


def backtest_forecasts(y_log: pd.Series, n_origins: int = 24, horizons=(1, 3, 6, 12), freq: str = "ME") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling-origin evaluation of the ARIMA and ETS forecasts against naive and drift benchmarks.
    For each of the last n_origins months that leave room for the longest horizon, the models are refit on the
    data up to the origin and forecast max(horizons) months ahead. Errors are absolute percentage errors on the
    level scale and log errors; coverage is the share of actuals inside the 80 and 95 percent bands."""
    y = y_log.dropna(); n = len(y); H = max(horizons)
    recs = []
    for origin in range(n - n_origins - H + 1, n - H + 1):
        train, actual = y.iloc[:origin], y.iloc[origin:origin + H]
        fa, _ = arima_forecast(train, horizon=H, freq=freq)
        fe, _ = ets_forecast(train, horizon=H, freq=freq)
        last = float(train.iloc[-1]); drift = float((train.iloc[-1] - train.iloc[0]) / (len(train) - 1))
        for h in horizons:
            a = float(np.exp(actual.iloc[h - 1]))
            preds = {"ARIMA (log, drift)": (float(fa["mean"].iloc[h - 1]), fa.iloc[h - 1]), "ETS(A,Ad,N) (log)": (float(fe["mean"].iloc[h - 1]), fe.iloc[h - 1]),
                     "drift benchmark (log random walk)": (float(np.exp(last + h * drift)), None), "naive benchmark (last value)": (float(np.exp(last)), None)}
            for model, (pt, row) in preds.items():
                rec = {"origin": y.index[origin - 1], "horizon": h, "model": model, "actual": a, "forecast": pt, "ape_pct": abs(pt - a) / a * 100, "log_err": float(np.log(pt) - np.log(a))}
                if row is not None:
                    rec["in80"] = bool(row["lo80"] <= a <= row["hi80"]); rec["in95"] = bool(row["lo95"] <= a <= row["hi95"])
                recs.append(rec)
    d = pd.DataFrame(recs)
    g = d.groupby(["model", "horizon"])
    out = pd.DataFrame({"n": g.size(), "mape_pct": g["ape_pct"].mean(), "rmse_log": g["log_err"].apply(lambda e: float(np.sqrt(np.mean(e ** 2)))),
                        "bias_log": g["log_err"].mean(), "coverage80_pct": g["in80"].mean() * 100, "coverage95_pct": g["in95"].mean() * 100}).reset_index()
    return out, d


def break_analysis(series: pd.Series, periods_per_year: int, known_break: pd.Timestamp, max_breaks: int = 5,
                   bootstrap_reps: int = 199, label: str = "") -> dict:
    """Run the full battery on one positive series: Chow at the first period >= known_break, Bai-Perron,
    pre/post growth rates. Returns a flat dict for the comparison table."""
    s = series.dropna()
    s = s[s > 0]
    y = np.log(s.values)
    n = len(y)
    dates = s.index
    kb = int(np.searchsorted(dates.values, np.datetime64(known_break)))
    out = {"series": label, "periods_per_year": periods_per_year, "n": n, "start": dates[0].strftime("%Y-%m"), "end": dates[-1].strftime("%Y-%m"),
           "known_break_period": dates[min(kb, n - 1)].strftime("%Y-%m")}
    if 3 <= kb <= n - 3:
        ch = chow_test(y, kb, maxlags=periods_per_year)
        out.update({"chow_F": ch["chow_F"], "chow_p": ch["chow_p"], "wald_hac_p": ch["wald_hac_p"]})
        pre, post = growth_rate(y[:kb], periods_per_year), growth_rate(y[kb:], periods_per_year)
        out.update({"cagr_pre": pre["cagr"], "cagr_pre_lo": pre["cagr_lo95"], "cagr_pre_hi": pre["cagr_hi95"],
                    "cagr_post": post["cagr"], "cagr_post_lo": post["cagr_lo95"], "cagr_post_hi": post["cagr_hi95"]})
    trim = 0.15 if n >= 20 else 0.2
    mb = min(max_breaks, max(1, (n // max(int(np.ceil(trim * n)), 3)) - 1))  # every feasible number of breaks
    bp = bai_perron(y, max_breaks=mb, trim=trim)
    fmt = lambda i: dates[min(i, n - 1)].strftime("%Y-%m")  # noqa: E731
    out.update({"bp_max_breaks": mb, "bp_m_bic": bp["m_bic"], "bp_m_lwz": bp["m_lwz"], "bp_breaks_bic": ", ".join(fmt(b) for b in bp["breaks_bic"]),
                "bp_break1": fmt(bp["by_m"][1]["breaks"][0]) if 1 in bp["by_m"] else None,
                "bp_supF_1": bp["by_m"][1]["supF"] if 1 in bp["by_m"] else np.nan, "bp_h": bp["h"]})
    if bootstrap_reps:
        sq = sequential_supF(y, max_breaks=mb, trim=trim, reps=bootstrap_reps, block=max(2, periods_per_year))
        out["bp_m_seq"] = sq["m_seq"]
        out["bp_seq_p"] = "; ".join(f"{l}|{l-1}: F={v['supF_seq']:.1f} p={v['boot_p']:.3f}" for l, v in sq["levels"].items())
        out["bp_breaks_seq"] = ", ".join(fmt(b) for b in bp["by_m"][sq["m_seq"]]["breaks"]) if sq["m_seq"] in bp["by_m"] else ""
    if 1 in bp["by_m"] and bootstrap_reps:
        bs = bootstrap_supF(y, m=1, reps=bootstrap_reps, block=max(2, periods_per_year), trim=trim)
        out["bp_supF_1_boot_p"] = bs["bootstrap_p"]
        bd = bootstrap_break_date(y, reps=bootstrap_reps, trim=trim)
        out["bp_break1_ci90"] = f"{fmt(bd['ci90'][0])} to {fmt(bd['ci90'][1])}"
        b1 = bp["by_m"][1]["breaks"][0]
        pre, post = growth_rate(y[:b1], periods_per_year), growth_rate(y[b1:], periods_per_year)
        out.update({"bp_cagr_pre": pre["cagr"], "bp_cagr_post": post["cagr"], "bp_cagr_post_lo": post["cagr_lo95"], "bp_cagr_post_hi": post["cagr_hi95"]})
    return out


# ------------------------------------------------------------------------------------------------
# 3. California proxies
# ------------------------------------------------------------------------------------------------
CA_COUNTIES = {"06085": "Santa Clara", "06037": "Los Angeles", "06075": "San Francisco", "06001": "Alameda", "06081": "San Mateo",
               "06067": "Sacramento", "06073": "San Diego", "06059": "Orange", "06999": "Unknown/statewide"}


def qcew_california() -> pd.DataFrame:
    """Quarterly NAICS 518210 establishments, employment (third month) and wages for California and key counties."""
    rows = []
    for f in sorted(glob.glob(str(raw_path("qcew_518210_2024q1").parent / "qcew_518210_*q*.csv"))):
        q = pd.read_csv(f, usecols=["area_fips", "own_code", "agglvl_code", "year", "qtr", "qtrly_estabs", "month1_emplvl", "month2_emplvl", "month3_emplvl", "total_qtrly_wages", "disclosure_code"])
        q["fips"] = q["area_fips"].astype(str).str.zfill(5)
        q = q[(q["own_code"] == 5) & (q["fips"].str.startswith("06")) & (q["agglvl_code"].isin([58, 78]))]
        rows.append(q)
    d = pd.concat(rows)
    d["area"] = d["fips"].map(lambda f: "California" if f == "06000" else CA_COUNTIES.get(f, f))
    d["period"] = pd.PeriodIndex(year=d["year"], quarter=d["qtr"], freq="Q").to_timestamp(how="end").normalize()
    d["employment"] = d[["month1_emplvl", "month2_emplvl", "month3_emplvl"]].mean(axis=1)
    return d.sort_values(["fips", "period"])[["fips", "area", "year", "qtr", "period", "qtrly_estabs", "employment", "month3_emplvl", "total_qtrly_wages", "disclosure_code"]].reset_index(drop=True)


def cbre_california() -> pd.DataFrame:
    """Semiannual CBRE series from data/processed/cbre_california_market_series.csv (chapter history + overview tables)."""
    cb = pd.read_csv(PROCESSED / "cbre_california_market_series.csv")
    cb["value"] = pd.to_numeric(cb["value"], errors="coerce")  # rent strings become NaN
    cb["date"] = cb["period"].map(lambda p: pd.Timestamp(f"{p.split()[1]}-06-30") if p.startswith("H1") else pd.Timestamp(f"{p.split()[1]}-12-31"))
    hist = cb[cb["edition"].str.contains("chapter history")].copy()
    hist = hist.sort_values(["metric", "date", "edition"]).drop_duplicates(["metric", "date"], keep="last")  # newest edition wins
    ov = cb[~cb["edition"].str.contains("chapter history")].copy()
    ov = ov.sort_values(["market", "metric", "date", "edition"]).drop_duplicates(["market", "metric", "date"], keep="last")
    return pd.concat([hist.assign(kind="chapter_history"), ov.assign(kind="overview")], ignore_index=True)


def epoch_timeline() -> pd.DataFrame:
    """Monthly cumulative facility power (MW) from Epoch's timelines, United States and California."""
    t = pd.read_csv(raw_path("epoch_data_center_timelines"))
    dc = pd.read_csv(raw_path("epoch_data_centers"))
    t["date"] = pd.to_datetime(t["Date"], errors="coerce")
    t = t.dropna(subset=["date"])
    us_names = set(dc.loc[dc["Country"] == "United States", "Name"])
    ca_names = set(dc.loc[dc["Address"].astype(str).str.contains(r", CA\b|California", regex=True), "Name"])
    months = pd.date_range("2018-12-31", pd.Timestamp.today().normalize() + pd.offsets.MonthEnd(0), freq="ME")
    out = pd.DataFrame(index=months)
    for label, names in (("us", us_names), ("california", ca_names)):
        tot = pd.Series(0.0, index=months)
        for name, g in t[t["Data center"].isin(names)].groupby("Data center"):
            s = g.set_index("date")["Power (MW)"].astype(float).sort_index()
            s = s[~s.index.duplicated(keep="last")]
            tot = tot.add(s.reindex(months, method="ffill").fillna(0.0), fill_value=0.0)
        out[f"power_MW_{label}"] = tot
        out[f"facilities_{label}"] = len(names)
    return out


# ------------------------------------------------------------------------------------------------
# 4. CEC tier vintages and RQ1 denominators
# ------------------------------------------------------------------------------------------------
def tier_vintages() -> pd.DataFrame:
    """Every vintage of the CEC energization tiers found in the record, long format."""
    rows = []
    # 2024 IEPR Update, December 2024 data: agreements + applications (no inquiries), PG&E and SCE only
    for u, mw in (("PG&E", 5808), ("SCE", 963)):
        rows.append(dict(vintage="2024-12", label="Dec 2024 (2024 IEPR Update)", utility=u, tier="Agreements + applications (no inquiries)", mw=mw, source="cec_prelim_dc_forecast_2025 p.7", complete_tiers=False))
    # 2025 IEPR preliminary, summer 2025 data: totals by utility (p.6); PG&E and SCE split into agreements + applications
    # versus inquiries (p.7, "Total Capacity of Applications, does not include inquiries"). The Nov 12 2025 workshop copy of
    # the deck (TN267165) labelled SCE 2025 as 2,492 MW and SVP as 1,382 MW; the published deck corrects these to 143 and 1,375.
    summer = {"PG&E": 11668, "SVP": 1375, "Palo Alto": 85, "SCE": 5828, "SDG&E": 100, "Burbank": 100, "VEA": 2600}
    split = {"PG&E": 10080, "SCE": 143}
    for u, mw in summer.items():
        if u in split:
            rows.append(dict(vintage="2025-08", label="Summer 2025 (2025 IEPR preliminary)", utility=u, tier="Agreements + applications (no inquiries)", mw=split[u], source="cec_prelim_dc_forecast_2025 p.7", complete_tiers=False,
                             note="workshop copy TN267165 p.8 labelled SCE 2025 as 2,492 MW; published deck says 143 MW" if u == "SCE" else ""))
            rows.append(dict(vintage="2025-08", label="Summer 2025 (2025 IEPR preliminary)", utility=u, tier="Inquiry", mw=mw - split[u], source="cec_prelim_dc_forecast_2025 p.6 minus p.7", complete_tiers=False, note="residual: utility total minus agreements + applications"))
        else:
            rows.append(dict(vintage="2025-08", label="Summer 2025 (2025 IEPR preliminary)", utility=u, tier="All tiers", mw=mw, source="cec_prelim_dc_forecast_2025 p.6", complete_tiers=False,
                             note="workshop copy TN267165 p.7 labelled SVP as 1,382 MW; published deck says 1,375 MW" if u == "SVP" else ""))
    # 2025 IEPR final, December 2025 data: by utility and tier (memo Table 1); statewide equals Assembly slide 7
    memo = {"PG&E": (4356, 3617, 6774), "SVP": (644, 196, 198), "Palo Alto": (14, 0, 55), "SCE": (72, 3174, 1378), "SDG&E": (0, 0, 100), "Burbank": (0, 0, 100), "VEA": (0, 2600, 0)}
    for u, (a, b, c) in memo.items():
        for tier, mw in (("Signed agreement", a), ("Active application", b), ("Inquiry", c)):
            rows.append(dict(vintage="2025-12", label="Dec 2025 (2025 IEPR final)", utility=u, tier=tier, mw=mw, source="cec_dc_methodology_memo_2026 Table 1 p.5; cec_assembly_hearing_2026_01_28 p.7", complete_tiers=True))
    # SCE public project databases: two vintages with cancellations
    for sid, v, lab in (("cec_tn266008", "2025-08", "SCE database Aug 29 2025"), ("cec_tn268459", "2026-01", "SCE database Jan 29 2026")):
        d = pd.read_excel(raw_path(sid))
        rp = [c for c in d.columns if "Requested Peak" in str(c)][0]
        g = d.groupby("CEC Grouping")[rp].sum()
        for grp, tier in ((1, "Signed agreement"), (2, "Active application"), (3, "Inquiry"), ("Canceled", "Canceled")):
            if grp in g.index:
                rows.append(dict(vintage=v, label=lab, utility="SCE", tier=tier, mw=float(g[grp]), source=sid, complete_tiers=True))
    # 2026 IEPR cycle, August 2026 workshop: restates December 2025 tiers; June 2026 known-load charts are images only
    rows.append(dict(vintage="2026-08", label="Aug 2026 workshop (restates Dec 2025)", utility="all", tier="Total restated", mw=23278, source="cec_tn272026 p.5", complete_tiers=False))
    # PG&E's own pipeline by PG&E stage (PG&E Q2 2026 earnings table reproduced in its Aug 20 2026 CEC presentation, TN272065 p.9;
    # Cal Advocates TN272807 p.3 quotes the same 3,880 MW WPA-signed and 630 MW ICA-or-later figures). Excludes inquiries.
    pge = {"2026-03": (1700, 3110, 140, 140), "2026-06": (8200, 3880, 490, 140)}
    for v, (appl, fe, ica, con) in pge.items():
        lab = f"PG&E earnings pipeline {pd.Timestamp(v + '-01'):%b %Y}"
        for tier, mw in (("PG&E: application + preliminary engineering", appl), ("PG&E: final engineering (WPA signed)", fe),
                         ("PG&E: interconnection construction agreement", ica), ("PG&E: construction", con)):
            rows.append(dict(vintage=v, label=lab, utility="PG&E", tier=tier, mw=mw, source="cec_tn272065 p.9 (PG&E Q2 2026 earnings); cec_tn272807 p.3", complete_tiers=False,
                             note="PG&E stage definitions (PES fee paid and later); no inquiries"))
    df = pd.DataFrame(rows)
    df["note"] = df["note"].fillna("")
    return df


def cec_forecast_reference_points() -> pd.DataFrame:
    """CEC data center forecast values quoted in the record, for the tier-versus-forecast comparison."""
    return pd.DataFrame([
        dict(vintage="2024-12", scenario="2024 IEPR Update mid (Dec)", year=2024, mw=987, note="existing + forecast total data center peak demand", source="cec_dc_forecast_2024iepr p.9"),
        dict(vintage="2024-12", scenario="2024 IEPR Update mid (Dec)", year=2025, mw=1190, note="", source="cec_dc_forecast_2024iepr p.9"),
        dict(vintage="2024-12", scenario="2024 IEPR Update mid (Dec)", year=2030, mw=3294, note="", source="cec_dc_forecast_2024iepr p.9"),
        dict(vintage="2024-12", scenario="2024 IEPR Update mid (Dec)", year=2040, mw=4507, note="", source="cec_dc_forecast_2024iepr p.9"),
        dict(vintage="2025-12", scenario="2025 IEPR Planning (mid)", year=2025, mw=413, note="incremental beyond ~1,000 MW existing", source="cec_dc_methodology_memo_2026 Fig. 4"),
        dict(vintage="2025-12", scenario="2025 IEPR Planning (mid)", year=2040, mw=4855, note="incremental", source="cec_dc_methodology_memo_2026 Fig. 4"),
        dict(vintage="2025-12", scenario="2025 IEPR Local Reliability (high)", year=2025, mw=684, note="incremental", source="cec_dc_methodology_memo_2026 Fig. 5"),
        dict(vintage="2025-12", scenario="2025 IEPR Local Reliability (high)", year=2040, mw=7381, note="incremental", source="cec_dc_methodology_memo_2026 Fig. 5"),
        dict(vintage="2025-12", scenario="Existing data center peak demand", year=2025, mw=1000, note="as of December 2025", source="cec_dc_methodology_memo_2026 p.2"),
    ])


def _form_years_table(sheet: pd.DataFrame) -> tuple[pd.DataFrame, list[int]]:
    hdr_row = next(i for i in range(len(sheet)) if pd.to_numeric(sheet.iloc[i, 2:], errors="coerce").notna().sum() > 5)
    years = [int(v) for v in pd.to_numeric(sheet.iloc[hdr_row, 2:], errors="coerce") if pd.notna(v)]
    body = sheet.iloc[hdr_row + 1:].copy()
    body.columns = ["ba", "agency"] + years + list(body.columns[2 + len(years):])
    body["ba"] = body["ba"].ffill()
    return body, years


def ced2025_planning_totals() -> pd.DataFrame:
    """CED 2025 Planning Forecast statewide totals for 2025-2030: energy to serve load (Form 1.5a, GWh),
    1-in-2 coincident and noncoincident peak (Form 1.5b, MW), total deliveries (Form 1.1c, GWh) and
    data-center-only deliveries (Form 1.1c Data Centers, TN 268824, GWh)."""
    out = []
    years_keep = (2024, 2025, 2026, 2027, 2028, 2029, 2030, 2035, 2040)
    def grab(sheet, metric, unit, patterns, source):
        body, years = _form_years_table(sheet)
        lab = (body["ba"].astype(str) + " | " + body["agency"].astype(str)).str.strip()
        for scope, pat in patterns:
            sub = body[lab.str.contains(pat, case=False, regex=True)]
            if len(sub):
                r = sub.iloc[0]
                out.append({"metric": metric, "unit": unit, "scope": scope, "row_label": lab[sub.index[0]], "source": source,
                            **{f"y{y}": float(pd.to_numeric(r[y], errors="coerce")) for y in years if y in years_keep}})
    x = pd.ExcelFile(raw_path("cec_tn268727"))
    grab(x.parse("Form 1.5a", header=None), "energy_to_serve_load", "GWh", [("Statewide total", r"^Total STATEWIDE")], "cec_tn268727 Form 1.5a")
    grab(x.parse("Form 1.5b", header=None), "net_peak_1in2", "MW", [("Statewide coincident", r"Total STATEWIDE Coincident"), ("Statewide noncoincident", r"Total STATEWIDE Noncoincident")], "cec_tn268727 Form 1.5b")
    grab(x.parse("Form 1.1c", header=None), "deliveries_total", "GWh", [("Statewide total", r"^STATEWIDE Total \|"), ("Statewide excl. pumping", r"Excluding Pumping")], "cec_tn268727 Form 1.1c")
    xd = pd.ExcelFile(raw_path("cec_tn268824"))
    body, years = _form_years_table(xd.parse("Form 1.1c Data Centers", header=None))
    lab = (body["ba"].astype(str) + " | " + body["agency"].astype(str)).str.strip()
    areas = body[lab.str.match(r"^(PG&E|SCE|SDG&E|NCNC|BUGL|OTHER) Total \| nan$")]  # the form's STATEWIDE row is empty
    out.append({"metric": "data_center_deliveries", "unit": "GWh", "scope": "Statewide total (sum of planning-area totals)",
                "row_label": "; ".join(lab[areas.index]), "source": "cec_tn268824 Form 1.1c Data Centers",
                **{f"y{y}": float(pd.to_numeric(areas[y], errors="coerce").sum()) for y in years if y in years_keep}})
    for _, r in areas.iterrows():
        out.append({"metric": "data_center_deliveries", "unit": "GWh", "scope": str(r["ba"]).strip(), "row_label": str(r["ba"]), "source": "cec_tn268824 Form 1.1c Data Centers",
                    **{f"y{y}": float(pd.to_numeric(r[y], errors="coerce")) for y in years if y in years_keep}})
    return pd.DataFrame(out)


def ced2025_caiso_peaks() -> pd.DataFrame:
    """CED 2025 hourly-forecast annual coincident peaks for the CAISO TAC area by scenario (TN 268124)."""
    a = pd.read_excel(raw_path("cec_tn268124"), sheet_name="annual_peaks")
    a = a[(a["TAC"].astype(str).str.upper() == "CAISO") & (a["COINCIDENT"] == True)]  # noqa: E712
    return a
