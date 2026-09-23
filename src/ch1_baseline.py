"""Chapter 1: current status of the California grid and existing data center load.

Every function reads only from data/raw (via the manifest) and returns pandas objects;
`scripts/run_chapter1.py` writes the processed tables and figures, and the notebook
`notebooks/01_baseline_grid.ipynb` calls the same functions.

Conventions
- Hourly EIA-930 series are indexed by the UTC hour-ending timestamp converted to
  America/Los_Angeles; `hour` is the local hour of the interval start (0-23).
- Net load = demand - utility-scale solar - wind (EIA-930 "Adjusted" series).
- Imports = -Total Interchange (positive = net imports into CISO).
- Carbon intensity = CAISO reported CO2 (metric tons per hour, incl. imports) divided by
  CAISO demand (MWh), in g CO2 per kWh.
"""
from __future__ import annotations

import glob
import io
import re
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import RAW, PROCESSED, MANIFEST

TZ = "America/Los_Angeles"
SEASON = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
SEASON_ORDER = ["DJF", "MAM", "JJA", "SON"]
DLAPS = {"DLAP_PGAE-APND": "PG&E DLAP", "DLAP_SCE-APND": "SCE DLAP", "DLAP_SDGE-APND": "SDG&E DLAP"}
HUBS = {"TH_NP15_GEN-APND": "NP15", "TH_SP15_GEN-APND": "SP15", "TH_ZP26_GEN-APND": "ZP26"}


def manifest() -> pd.DataFrame:
    m = pd.read_csv(MANIFEST)
    return m.sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")


def raw_path(source_id: str) -> Path:
    return RAW.parent.parent / manifest().loc[source_id, "local_path"]


# --------------------------------------------------------------------------------------
# 1. EIA-930: CISO hourly demand, generation by fuel, interchange
# --------------------------------------------------------------------------------------
_FUEL_MAP = {  # output column -> substrings matched against EIA-930 "(Adjusted)" column names
    "coal": ["from Coal"],
    "gas": ["from Natural Gas"],
    "nuclear": ["from Nuclear"],
    "petroleum": ["from All Petroleum Products"],
    "hydro": ["from Hydropower and Pumped Storage", "from Hydropower Excluding Pumped Storage", "from Pumped Storage"],
    "solar": ["from Solar"],
    "wind": ["from Wind"],
    "battery": ["from Battery Storage", "from Other Energy Storage", "from Unknown Energy Storage"],
    "geothermal": ["from Geothermal"],
    "other": ["from Other Fuel Sources", "from Unknown Fuel Sources"],
}


VARIANTS = (" (Adjusted)", " (Imputed)", "")  # preference order: EIA adjusted, then imputed, then as reported


def _pick(cols: list[str], subs: list[str], variant: str = " (Adjusted)") -> list[str]:
    """Columns for a fuel group in one reporting variant ('' = raw column with no suffix)."""
    out = []
    for c in cols:
        if not any(sub in c for sub in subs):
            continue
        base = c.replace("  ", " ")
        if variant:
            if variant.strip() in c:
                out.append(c)
        else:
            if "(Adjusted)" not in c and "(Imputed)" not in c:
                out.append(c)
    return out


def _coalesce(frames):
    """Element-wise first non-null across a list of Series (preference order)."""
    out = frames[0].copy()
    for f in frames[1:]:
        out = out.where(out.notna(), f)
    return out


def load_eia930_ciso(first_year: int = 2019, last_year: int = 2025, ba: str = "CISO") -> pd.DataFrame:
    """Hourly CISO series from the EIA-930 six-month BALANCE files (Adjusted values)."""
    frames = []
    for f in sorted(glob.glob(str(RAW / "eia930" / "*" / "EIA930_BALANCE_*.csv"))):
        yr = int(re.search(r"_BALANCE_(\d{4})_", f).group(1))
        if yr < first_year or yr > last_year:
            continue
        cols = pd.read_csv(f, nrows=0).columns.tolist()
        totals = {"demand": "Demand (MW)", "net_generation": "Net Generation (MW)", "interchange": "Total Interchange (MW)"}
        total_cols = [c for k, base in totals.items() for v in VARIANTS for c in [base + v] if c in cols]
        fuel_cols = {k: {v: _pick(cols, subs, v) for v in VARIANTS} for k, subs in _FUEL_MAP.items()}
        usecols = ["Balancing Authority", "UTC Time at End of Hour"] + total_cols + sorted({c for k in fuel_cols.values() for cs in k.values() for c in cs})
        parts = []
        for chunk in pd.read_csv(f, usecols=usecols, chunksize=400_000, low_memory=False):
            parts.append(chunk[chunk["Balancing Authority"] == ba])
        d = pd.concat(parts).reset_index(drop=True)
        out = pd.DataFrame({"time_utc": pd.to_datetime(d["UTC Time at End of Hour"], format="%m/%d/%Y %I:%M:%S %p", utc=True)})
        for k, base in totals.items():  # adjusted, else imputed, else as reported
            series = [pd.to_numeric(d[base + v], errors="coerce") for v in VARIANTS if base + v in d]
            out[k] = _coalesce(series).values if series else np.nan
        for k, byvar in fuel_cols.items():
            series = [d[cs].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1) for v, cs in byvar.items() if cs]
            out[k] = _coalesce(series).values if series else np.nan
        frames.append(out)
    df = pd.concat(frames).drop_duplicates("time_utc").sort_values("time_utc").set_index("time_utc")
    df.index = df.index.tz_convert(TZ)
    df.index.name = "hour_ending_local"
    start = df.index - pd.Timedelta(hours=1)
    df["year"] = start.year
    df["month"] = start.month
    df["hour"] = start.hour
    df["season"] = df["month"].map(SEASON)
    df["dow"] = start.dayofweek
    df["imports"] = -df["interchange"]
    df["net_load"] = df["demand"] - df["solar"].fillna(0) - df["wind"].fillna(0)
    return df[(df["year"] >= first_year) & (df["year"] <= last_year)]


def annual_summary(h: pd.DataFrame) -> pd.DataFrame:
    g = h.groupby("year")
    hours_in_year = h.groupby("year").size()
    s = pd.DataFrame({
        "hours": g["demand"].count(),
        "hours_in_year": hours_in_year,
        "missing_hours": hours_in_year - g["demand"].count(),
        "energy_TWh": g["demand"].mean() * hours_in_year / 1e6,  # mean of valid hours x calendar hours: missing hours imputed at the annual mean
        "avg_demand_MW": g["demand"].mean(),
        "peak_demand_MW": g["demand"].max(),
        "peak_demand_time": g["demand"].idxmax(),
        "min_demand_MW": g["demand"].min(),
        "peak_net_load_MW": g["net_load"].max(),
        "peak_net_load_time": g["net_load"].idxmax(),
        "min_net_load_MW": g["net_load"].min(),
        "min_net_load_time": g["net_load"].idxmin(),
        "solar_TWh": g["solar"].sum() / 1e6,
        "wind_TWh": g["wind"].sum() / 1e6,
        "gas_TWh": g["gas"].sum() / 1e6,
        "hydro_TWh": g["hydro"].sum() / 1e6,
        "nuclear_TWh": g["nuclear"].sum() / 1e6,
        "net_imports_TWh": g["imports"].sum() / 1e6,
        "battery_net_TWh": g["battery"].sum() / 1e6,
    })
    s["load_factor"] = s["avg_demand_MW"] / s["peak_demand_MW"]
    s["import_share_of_demand"] = s["net_imports_TWh"] / s["energy_TWh"]
    s["solar_wind_share_of_demand"] = (s["solar_TWh"] + s["wind_TWh"]) / s["energy_TWh"]
    return s


def duration_curves(h: pd.DataFrame, col: str) -> pd.DataFrame:
    """Sorted values per year on a common 0-100 percent-of-hours axis (1,000 points)."""
    q = np.linspace(0, 1, 1001)
    out = {}
    for y, g in h.groupby("year"):
        v = np.sort(g[col].dropna().values)[::-1]
        out[y] = np.interp(q, np.linspace(0, 1, len(v)), v)
    return pd.DataFrame(out, index=pd.Index(q * 100, name="pct_hours"))


def seasonal_profiles(h: pd.DataFrame, cols=("demand", "net_load", "solar", "wind", "imports")) -> pd.DataFrame:
    p = h.groupby(["year", "season", "hour"])[list(cols)].mean().reset_index()
    p["season"] = pd.Categorical(p["season"], SEASON_ORDER, ordered=True)
    return p.sort_values(["year", "season", "hour"]).reset_index(drop=True)


def top_hours(h: pd.DataFrame, col: str = "net_load", n: int = 100) -> pd.DataFrame:
    rows = []
    for y, g in h.groupby("year"):
        t = g.nlargest(n, col)
        t = t.assign(rank=np.arange(1, len(t) + 1), start_local=t.index - pd.Timedelta(hours=1))
        keep = ["rank", "start_local", "month", "hour", "dow", col, "demand", "solar", "wind", "imports", "gas", "battery"]
        keep = list(dict.fromkeys(keep))  # no duplicate columns when col == "demand"
        rows.append(t[keep].assign(year=y))
    return pd.concat(rows).reset_index(drop=True)


def top_hours_timing(top: pd.DataFrame, col: str = "net_load") -> pd.DataFrame:
    """Per year: month and hour distribution of the top-N hours, plus the number of distinct days."""
    out = []
    for y, g in top.groupby("year"):
        out.append({
            "year": y,
            f"top{len(g)}_{col}_min_MW": g[col].min(), f"top{len(g)}_{col}_max_MW": g[col].max(),
            "distinct_days": g["start_local"].dt.date.nunique(),
            "share_Jul_Sep": g["month"].isin([7, 8, 9]).mean(),
            "share_Jun_Oct": g["month"].isin([6, 7, 8, 9, 10]).mean(),
            "share_hours_17_21": g["hour"].between(17, 21).mean(),
            "median_hour": g["hour"].median(),
            "earliest_hour": g["hour"].min(), "latest_hour": g["hour"].max(),
            "months": ", ".join(f"{int(k)}:{int(v)}" for k, v in g["month"].value_counts().sort_index().items()),
            "mean_solar_MW": g["solar"].mean(), "mean_imports_MW": g["imports"].mean(), "mean_gas_MW": g["gas"].mean(),
        })
    return pd.DataFrame(out).set_index("year")


# --------------------------------------------------------------------------------------
# 2. CAISO OASIS day-ahead prices
# --------------------------------------------------------------------------------------
def load_dam_lmp() -> pd.DataFrame:
    """Hourly day-ahead LMP (USD/MWh) by node, local time (interval start)."""
    files = sorted(glob.glob(str(RAW / "caiso_oasis" / "*" / "dam_lmp" / "dam_lmp_*_20??-??.csv")))
    parts = []
    for f in files:
        d = pd.read_csv(f, usecols=["INTERVALSTARTTIME_GMT", "NODE", "LMP_TYPE", "MW"])
        d = d[d["LMP_TYPE"] == "LMP"]
        parts.append(d)
    d = pd.concat(parts)
    d["t"] = pd.to_datetime(d["INTERVALSTARTTIME_GMT"], utc=True).dt.tz_convert(TZ)
    p = d.pivot_table(index="t", columns="NODE", values="MW", aggfunc="first").sort_index()
    p.index.name = "interval_start_local"
    return p


def price_stats(p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for node in p.columns:
        s = p[node].dropna()
        for y, g in s.groupby(s.index.year):
            rows.append({"node": node, "label": {**DLAPS, **HUBS}.get(node, node), "year": y, "hours": len(g),
                         "full_year": len(g) >= 8700, "mean": g.mean(), "median": g.median(), "p5": g.quantile(0.05), "p95": g.quantile(0.95),
                         "min": g.min(), "max": g.max(), "hours_negative": int((g < 0).sum()), "hours_le_0": int((g <= 0).sum()),
                         "hours_le_5": int((g <= 5).sum()), "hours_ge_200": int((g >= 200).sum()),
                         "share_negative": (g < 0).mean(), "neg_hours_10_16_share": ((g < 0) & g.index.hour.isin(range(10, 17))).sum() / max(1, (g < 0).sum())})
    return pd.DataFrame(rows)


def price_duration(p: pd.DataFrame) -> pd.DataFrame:
    q = np.linspace(0, 1, 1001)
    out = {}
    for node in p.columns:
        s = p[node].dropna()
        for y, g in s.groupby(s.index.year):
            if len(g) < 8700:
                continue
            v = np.sort(g.values)[::-1]
            out[(node, y)] = np.interp(q, np.linspace(0, 1, len(v)), v)
    df = pd.DataFrame(out, index=pd.Index(q * 100, name="pct_hours"))
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["node", "year"])
    return df


def negative_hours_by_month(p: pd.DataFrame) -> pd.DataFrame:
    neg = (p < 0)
    return neg.groupby([neg.index.year.rename("year"), neg.index.month.rename("month")]).sum()


def price_by_hour(p: pd.DataFrame) -> pd.DataFrame:
    return p.groupby([p.index.year.rename("year"), p.index.hour.rename("hour")]).mean()


def load_ice_daily() -> pd.DataFrame:
    """EIA daily ICE day-ahead hub prices (NP15, SP15) 2015-2026: wtd avg price, low, high."""
    rows = []
    for f in sorted(glob.glob(str(RAW / "eia_wholesale" / "*" / "*ice_electric-*.xls*"))):
        x = pd.ExcelFile(f)
        for sh in x.sheet_names:
            d = x.parse(sh, header=None)
            # locate header row containing 'Price hub'
            hdr = None
            for i in range(min(10, len(d))):
                if d.iloc[i].astype(str).str.contains("Price hub", case=False).any():
                    hdr = i
                    break
            if hdr is None:
                continue
            d = x.parse(sh, header=hdr)
            d.columns = [str(c).strip() for c in d.columns]
            hubcol = [c for c in d.columns if "hub" in c.lower()][0]
            d = d[d[hubcol].astype(str).str.contains("NP15|SP15", case=False)]
            rows.append(d)
    d = pd.concat(rows)
    return d


# --------------------------------------------------------------------------------------
# 3. Carbon intensity from CAISO Today's Outlook (co2, demand) and eGRID
# --------------------------------------------------------------------------------------

def _outlook_day_files(sub: str) -> dict:
    """CAISO Today's Outlook daily CSVs (YYYYMMDD.csv) for one series folder, keyed by date string."""
    base = sorted(glob.glob(str(RAW / "caiso_outlook" / "*")))[-1]
    return {Path(f).stem: f for f in sorted(glob.glob(f"{base}/{sub}/*.csv")) if re.fullmatch(r"\d{8}", Path(f).stem)}


def _hourly_means(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Five-minute rows of one calendar day -> hourly means by clock hour, plus the number of non-missing
    intervals per hour. CAISO publishes a fixed 24 x 12 clock grid for every day, including the two daylight-
    saving transition days, so the repeated autumn hour and the skipped spring hour cannot be separated; the
    grid is taken as published (an error of at most two hours per year)."""
    d = df.dropna(subset=["Time"]).copy()
    hh = pd.to_numeric(d["Time"].astype(str).str.split(":").str[0], errors="coerce")
    keep = hh.notna() & (hh < 24)
    d = d[keep]
    d["hour"] = hh[keep].astype(int)
    vals = d[cols].apply(pd.to_numeric, errors="coerce")
    g = vals.groupby(d["hour"])
    return g.mean(), g.count()


def load_caiso_outlook_hourly(first_year: int = 2019, last_year: int = 2025, min_intervals: int = 6) -> pd.DataFrame:
    """Hourly CAISO CO2 accounting (t/h by source, imports net of exports) and demand (MW) from the five-minute
    Today's Outlook files. An hour is valid when CO2 and demand each have at least `min_intervals` of 12 intervals
    and demand exceeds 5 GW. Total CO2 is NaN, not zero, when every source is missing. Two intensities are kept:
    the accounting series (net CO2 / demand, negative in export-heavy hours) and a floored-at-zero sensitivity."""
    co2_files, dem_files = _outlook_day_files("co2"), _outlook_day_files("demand")
    out = []
    for day, f in co2_files.items():
        y = int(day[:4])
        if y < first_year or y > last_year or day not in dem_files:
            continue
        try:
            c = pd.read_csv(f); dm = pd.read_csv(dem_files[day])
        except Exception:
            continue
        if "Time" not in c or "Time" not in dm or "Current demand" not in dm:
            continue
        src = [k for k in c.columns if k.endswith("CO2")]
        cm, cn = _hourly_means(c, src)
        dmm, dn = _hourly_means(dm, ["Current demand"])
        h = cm.copy()
        h["co2_total_tph"] = cm[src].sum(axis=1, min_count=1)
        h["n_intervals_co2"] = cn[src].max(axis=1)
        h["demand_MW"] = dmm["Current demand"]
        h["n_intervals_demand"] = dn["Current demand"]
        h["date"] = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}")
        out.append(h.reset_index())
    d = pd.concat(out)
    d["t"] = d["date"] + pd.to_timedelta(d["hour"], unit="h")
    d = d.set_index("t").sort_index()
    d["n_intervals_demand"] = d["n_intervals_demand"].fillna(0); d["n_intervals_co2"] = d["n_intervals_co2"].fillna(0)
    ok = (d["n_intervals_co2"] >= min_intervals) & (d["n_intervals_demand"] >= min_intervals) & (d["demand_MW"] > 5000) & d["co2_total_tph"].notna()
    d["valid_hour"] = ok
    d["net_co2_negative"] = ok & (d["co2_total_tph"] < 0)
    d["co2_total_clipped_tph"] = d["co2_total_tph"].clip(lower=0)
    d["intensity_accounting_g_per_kWh"] = np.where(ok, d["co2_total_tph"] / d["demand_MW"] * 1000.0, np.nan)
    d["intensity_floored_g_per_kWh"] = np.where(ok, d["co2_total_clipped_tph"] / d["demand_MW"] * 1000.0, np.nan)
    d["intensity_g_per_kWh"] = d["intensity_accounting_g_per_kWh"]  # primary indicator: CAISO accounting, unclipped
    d["year"] = d.index.year
    d["month"] = d.index.month
    d["season"] = d["month"].map(SEASON)
    return d



def carbon_summary(ci: pd.DataFrame) -> pd.DataFrame:
    """Annual CAISO CO2 accounting intensity: the unclipped accounting series is the headline, the floored
    series is the sensitivity; coverage counts the valid hours against the calendar."""
    v = ci[ci["valid_hour"]]
    g = v.groupby("year")
    cal = pd.Series({y: pd.Timestamp(f"{y}-12-31").dayofyear * 24 for y in g.size().index})
    s = pd.DataFrame({
        "hours": g.size(),
        "hours_in_year": cal,
        "hours_net_co2_negative": g["net_co2_negative"].sum(),
        "energy_weighted_g_per_kWh": g["co2_total_tph"].sum() / g["demand_MW"].sum() * 1000,
        "energy_weighted_floored_g_per_kWh": g["co2_total_clipped_tph"].sum() / g["demand_MW"].sum() * 1000,
        "hourly_mean_g_per_kWh": g["intensity_accounting_g_per_kWh"].mean(),
        "p5_g_per_kWh": g["intensity_accounting_g_per_kWh"].quantile(0.05),
        "p95_g_per_kWh": g["intensity_accounting_g_per_kWh"].quantile(0.95),
        "min_g_per_kWh": g["intensity_accounting_g_per_kWh"].min(),
        "max_g_per_kWh": g["intensity_accounting_g_per_kWh"].max(),
        "co2_Mt": g["co2_total_tph"].sum() / 1e6,
        "imports_co2_share": g["Imports CO2"].sum() / g["co2_total_tph"].sum(),
        "gas_co2_share": g["Natural Gas CO2"].sum() / g["co2_total_tph"].sum(),
        "implied_gas_kg_per_MWh": np.nan,
    })
    s["coverage_pct"] = s["hours"] / s["hours_in_year"] * 100
    return s


def egrid_camx() -> dict:
    x = pd.ExcelFile(raw_path("epa_egrid2023_rev1"))
    sr = x.parse("SRL23", header=1)
    r = sr[sr["SUBRGN"] == "CAMX"].iloc[0]
    return {"subregion": "CAMX", "year": 2023, "co2_output_rate_lb_per_MWh": float(r["SRCO2RTA"]),
            "co2_output_rate_g_per_kWh": float(r["SRCO2RTA"]) * 0.45359237,
            "co2e_output_rate_g_per_kWh": float(r["SRC2ERTA"]) * 0.45359237,
            "net_generation_TWh": float(r["SRNGENAN"]) / 1e6, "co2_Mt": float(r["SRCO2AN"]) / 1e6}


# --------------------------------------------------------------------------------------
# 4. Existing data center load: four estimates against California retail sales
# --------------------------------------------------------------------------------------
def ca_retail_sales_eia861(year: int) -> dict:
    """California retail sales (MWh) from EIA-861 Sales_Ult_Cust: Parts A + C + D (B is delivery-only and duplicates C)."""
    z = zipfile.ZipFile(raw_path(f"eia861_{year}"))
    name = [n for n in z.namelist() if n.startswith("Sales_Ult_Cust_") and "CS" not in n][0]
    s = pd.read_excel(io.BytesIO(z.read(name)), header=[0, 1, 2])
    s.columns = [" ".join(str(x) for x in c if not str(x).startswith("Unnamed")).strip() for c in s.columns]
    state = [c for c in s.columns if c.endswith("State")][0]
    part = [c for c in s.columns if c.endswith("Part")][0]
    tot = [c for c in s.columns if c.startswith("TOTAL") and "Megawatthours" in c][0]
    ca = s[s[state] == "CA"].copy()
    ca[tot] = pd.to_numeric(ca[tot], errors="coerce")
    by = ca.groupby(part)[tot].sum()
    return {"year": year, "MWh_A_bundled": float(by.get("A", 0)), "MWh_B_delivery_only": float(by.get("B", 0)),
            "MWh_C_energy_only": float(by.get("C", 0)), "MWh_D_adjustment": float(by.get("D", 0)),
            "retail_sales_TWh": float(by.get("A", 0) + by.get("C", 0) + by.get("D", 0)) / 1e6}


def cec_statewide_consumption() -> pd.DataFrame:
    t = pd.read_excel(raw_path("cec_cons_elec_total"))
    return t



def svp_fact_sheet_energy() -> pd.DataFrame:
    """Silicon Valley Power utility fact sheets: peak demand, system load factor, retail kWh sales and total
    purchased/generated energy. energy_GWh_est = peak x load factor x 8760 approximates the supply total."""
    from pypdf import PdfReader
    rows = []
    for y in range(2017, 2024):
        sid = f"svp_fact_sheet_{y}"
        try:
            t = " ".join(re.sub(r"\s+", " ", p.extract_text() or "") for p in PdfReader(raw_path(sid)).pages)
        except Exception:
            continue
        pk = re.search(r"Peak Demand\s*([\d,]+\.?\d*)\s*MW", t)
        lf = re.search(r"Load Factor\s*([\d.]+)\s*%", t)
        acc = re.search(r"Electric Accounts\s*([\d,]+)", t)
        sales = re.search(r"kWh Sales\d?\s*([\d,]{9,})", t)
        supply = re.search(r"Total\s*([\d,]{9,})\s*100\.0%", t)
        rows.append({"fact_sheet_year": y, "peak_MW": float(pk.group(1).replace(",", "")) if pk else np.nan,
                     "load_factor": float(lf.group(1)) / 100 if lf else np.nan,
                     "electric_accounts": int(acc.group(1).replace(",", "")) if acc else np.nan,
                     "retail_sales_GWh": float(sales.group(1).replace(",", "")) / 1e6 if sales else np.nan,
                     "supply_GWh": float(supply.group(1).replace(",", "")) / 1e6 if supply else np.nan})
    d = pd.DataFrame(rows)
    d["energy_GWh_est"] = d["peak_MW"] * d["load_factor"] * 8760 / 1000
    return d



def dc_load_estimates(retail: pd.DataFrame) -> pd.DataFrame:
    """Evidence and assumptions for existing California data center electricity use, in four groups that are
    not interchangeable: (A) a statewide historical estimate, (B) an assumed conversion of the CEC's existing
    peak, (D) a single-utility subset. Group C, the count-based sensitivity, is appended by the caller.
    Shares use the retail-sales year that matches each estimate (EIA-861 Parts A + C + D)."""
    rs = retail.set_index("year")["retail_sales_TWh"]
    rows = []
    rows.append(dict(group="A. Statewide estimate", method="EPRI 2024 state table, 2023 consumption", year=2023, denominator_year=2023,
                     low_TWh=9.33, central_TWh=9.33, high_TWh=9.33,
                     basis="9,331,619 MWh = 3.70% of state consumption in 2023 (EPRI Table, p.13 and Appendix p.28); share below uses EIA-861 2023 retail sales",
                     source="epri_powering_intelligence_2024"))
    mw, (lf_lo, lf_c, lf_hi) = 1000.0, (0.80, 0.88, 0.95)
    rows.append(dict(group="B. Assumed conversion", method="CEC ~1,000 MW existing peak (Dec 2025) x assumed annual load factor 0.80-0.95", year=2025, denominator_year=int(rs.index.max()),
                     low_TWh=mw * lf_lo * 8760 / 1e6, central_TWh=mw * lf_c * 8760 / 1e6, high_TWh=mw * lf_hi * 8760 / 1e6,
                     basis="~1,000 MW existing data center peak demand as of Dec 2025 (CEC methodology memo, Apr 2026, pp. 2 and 18); the annual load factor is an assumption bracketed by the CEC's daily load-factor profiles (75-100% of annual max), not a measured annual value; share uses the latest EIA-861 year",
                     source="cec_dc_methodology_memo_2026; cec_prelim_dc_forecast_2025"))
    svp = svp_fact_sheet_energy()
    r23 = svp.loc[svp["fact_sheet_year"] == 2023].iloc[0]
    sales23 = float(r23["retail_sales_GWh"]) / 1000
    rows.append(dict(group="D. Utility subset", method="Silicon Valley Power only: 53-60% of SVP 2023 retail sales", year=2023, denominator_year=2023,
                     low_TWh=0.53 * sales23, central_TWh=0.55 * sales23, high_TWh=0.60 * sales23,
                     basis=f"SVP 2023 fact sheet: retail kWh sales {sales23:.2f} TWh (purchased and generated supply {float(r23['supply_GWh'])/1000:.2f} TWh; peak 669.2 MW, load factor 78.3%); data center share of power use 53% (SVP data center page), 55% (SVP Assembly deck Jan 2026), ~60% (Santa Clara officials, 2025), statements from different dates applied to 2023 sales",
                     source="svp_fact_sheet_2023; svp_data_centers_page_wayback; svp_assembly_hearing_2026_01_28; sjspotlight_santa_clara_capacity_2025"))
    df = pd.DataFrame(rows)
    df["retail_sales_TWh"] = df["denominator_year"].map(rs)
    for k in ("low", "central", "high"):
        df[f"{k}_share_pct"] = df[f"{k}_TWh"] / df["retail_sales_TWh"] * 100
    return df


# --------------------------------------------------------------------------------------
# 5. Additional series: CAISO fuel mix (batteries), ICE daily hub prices, facility counts
# --------------------------------------------------------------------------------------

def load_caiso_fuelmix_hourly(first_year: int = 2019, last_year: int = 2025, min_intervals: int = 6) -> pd.DataFrame:
    """Hourly means of the CAISO five-minute fuel mix (MW): batteries (negative = charging), solar, wind, imports,
    natural gas, hydro, nuclear, geothermal, other. Column names are normalised because the files switched from
    'Natural gas' / 'Large hydro' to 'Natural Gas' / 'Large Hydro' in mid-2021. Hours with fewer than
    `min_intervals` intervals are set to NaN rather than averaged over a few rows."""
    out = []
    for day, f in _outlook_day_files("fuelsource").items():
        y = int(day[:4])
        if y < first_year or y > last_year:
            continue
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if "Time" not in d:
            continue
        d.columns = [str(c).strip().lower().replace(" ", "_") for c in d.columns]
        d = d.rename(columns={"time": "Time"})
        cols = [c for c in ["solar", "wind", "batteries", "imports", "natural_gas", "large_hydro", "small_hydro", "nuclear", "geothermal", "biomass", "biogas", "coal", "other"] if c in d.columns]
        m, n = _hourly_means(d, cols)
        m[m.columns] = m.where(n >= min_intervals)
        m["n_intervals"] = n.max(axis=1)
        m["hydro_total"] = m[[c for c in ("large_hydro", "small_hydro") if c in m.columns]].sum(axis=1, min_count=1)
        m["date"] = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}")
        out.append(m.reset_index())
    d = pd.concat(out)
    d["t"] = d["date"] + pd.to_timedelta(d["hour"], unit="h")
    d = d.set_index("t").sort_index().drop(columns=["date"])
    d["year"] = d.index.year
    return d


def battery_summary(fm: pd.DataFrame) -> pd.DataFrame:
    """Annual battery discharge (positive) and charge (negative) energy and peak discharge from CAISO fuel mix."""
    b = fm["batteries"]
    g = b.groupby(fm["year"])
    return pd.DataFrame({"discharge_TWh": g.apply(lambda s: s.clip(lower=0).sum()) / 1e6,
                         "charge_TWh": g.apply(lambda s: s.clip(upper=0).sum()) / 1e6,
                         "peak_discharge_MW": g.max(), "peak_charge_MW": g.min(),
                         "hours": g.count()})


def ice_negative_days() -> pd.DataFrame:
    """Days per year with a negative day-ahead block price at NP15 / SP15 (EIA daily ICE data, 2015-2026)."""
    rows = []
    for f in sorted(glob.glob(str(RAW / "eia_wholesale" / "*" / "*ice_electric-*.xls*"))):
        x = pd.ExcelFile(f)
        for sh in x.sheet_names:
            raw = x.parse(sh, header=None, nrows=12)
            hdr = next((i for i in range(len(raw)) if raw.iloc[i].astype(str).str.contains("Price hub", case=False).any()), None)
            if hdr is None:
                continue
            d = x.parse(sh, header=hdr)
            d.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in d.columns]
            hub = [c for c in d.columns if "hub" in c.lower()][0]
            d = d[d[hub].astype(str).str.contains(r"NP15|SP15", case=False)].copy()
            dcol = [c for c in d.columns if "delivery start" in c.lower()][0]
            lo = [c for c in d.columns if c.lower().startswith("low price")][0]
            wa = [c for c in d.columns if "wtd avg" in c.lower()][0]
            d["date"] = pd.to_datetime(d[dcol], errors="coerce")
            d["low"] = pd.to_numeric(d[lo], errors="coerce")
            d["wavg"] = pd.to_numeric(d[wa], errors="coerce")
            d["hub"] = d[hub].astype(str).str.strip()
            rows.append(d[["hub", "date", "low", "wavg"]])
    d = pd.concat(rows).dropna(subset=["date"])
    d["year"] = d["date"].dt.year
    g = d.groupby(["hub", "year"])
    return pd.DataFrame({"trading_days": g["date"].nunique(), "days_wavg_negative": g["wavg"].apply(lambda s: int((s < 0).sum())),
                         "days_low_negative": g["low"].apply(lambda s: int((s < 0).sum())), "mean_wavg": g["wavg"].mean(),
                         "min_low": g["low"].min()}).reset_index()


def _point_in_ring(x: float, y: float, ring) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def kollar_grady_california() -> pd.DataFrame:
    """Kollar & Grady (2025) facility points that fall inside California (Census 2018 state polygon shipped in the bundle)."""
    import shapefile  # pyshp
    z = zipfile.ZipFile(raw_path("kollar_grady_2025_zenodo"))
    pts = pd.read_csv(io.BytesIO(z.read("DataCenterRiskRepository/data/01_PreProcessing/data_centers_06_02_2025_Format.csv")))
    pts.columns = ["id", "name", "lat", "lon"]
    base = "DataCenterRiskRepository/data/05_ChiSq_Morans/cb_2018_us_state_5m/cb_2018_us_state_5m"
    sf = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")), shx=io.BytesIO(z.read(base + ".shx")))
    fields = [f[0] for f in sf.fields[1:]]
    ca = next(sr for sr in sf.shapeRecords() if dict(zip(fields, sr.record)).get("NAME") == "California")
    parts = list(ca.shape.parts) + [len(ca.shape.points)]
    rings = [ca.shape.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
    inside = [any(_point_in_ring(lon, lat, r) for r in rings) for lat, lon in zip(pts["lat"], pts["lon"])]
    pts["in_california"] = inside
    # Santa Clara cluster: within 12 km of the SVP service area centre (37.354, -121.955)
    lat0, lon0 = 37.354, -121.955
    dkm = np.sqrt(((pts["lat"] - lat0) * 111.0) ** 2 + ((pts["lon"] - lon0) * 111.0 * np.cos(np.radians(lat0))) ** 2)
    pts["santa_clara_12km"] = dkm <= 12
    return pts



def bottom_up_estimate(n_ca: int, n_svp_cluster: int, svp_dc_energy_GWh: float, svp_dc_count: int = 58,
                       size_scale=(0.50, 0.75, 1.00), n_epoch_ca: int = 0) -> dict:
    """Illustrative count-based sensitivity: facilities x assumed annual energy per facility.

    The per-facility energy is the Silicon Valley Power cluster average (its data centers' share of SVP retail
    sales divided by the 58 facilities SVP reports); size_scale brackets it because the SVP cluster hosts
    unusually large facilities and the statewide inventory includes small ones. This is a transparent
    assumption set, not a measurement: it uses no peak-demand or utilization factor."""
    per_fac = svp_dc_energy_GWh / svp_dc_count
    lo, c, hi = (n_ca * per_fac * sc / 1000 for sc in size_scale)
    return {"n_california_facilities_kollar_grady": n_ca, "n_within_12km_of_santa_clara": n_svp_cluster,
            "n_epoch_california_sites": n_epoch_ca, "svp_data_centers": svp_dc_count, "svp_dc_energy_GWh": svp_dc_energy_GWh,
            "avg_energy_GWh_per_facility_svp_anchor": per_fac, "avg_load_MW_per_facility_svp_anchor": per_fac * 1000 / 8760,
            "size_scale_low_central_high": list(size_scale), "low_TWh": lo, "central_TWh": c, "high_TWh": hi}


def _to_hour_ending(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = s.index.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT") if s.index.tz is None else s.index
    s = s[~s.index.isna()]
    s.index = s.index + pd.Timedelta(hours=1)  # CAISO hourly means are labelled by interval start
    return s[~s.index.duplicated()]


def clean_demand_against_caiso(h: pd.DataFrame, caiso_hourly: pd.DataFrame, tol: float = 0.15,
                               fuelmix_hourly: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Null EIA-930 demand (and net load) in hours where it is implausibly low relative to CAISO's
    own demand plus battery charging (EIA-930 demand includes charging). Returns (clean, flagged)."""
    cd = _to_hour_ending(caiso_hourly["demand_MW"])
    if fuelmix_hourly is not None and "batteries" in fuelmix_hourly:
        chg = (-_to_hour_ending(fuelmix_hourly["batteries"])).clip(lower=0)
        cd = (cd + chg.reindex(cd.index).fillna(0)).rename("caiso_demand_plus_charging")
    j = h[["demand"]].join(cd.rename("caiso_demand"), how="left")
    ratio = j["demand"] / j["caiso_demand"]
    # One-sided: EIA-930 CISO demand includes storage charging and pumping, CAISO's 'Current demand'
    # excludes charging, so EIA can legitimately exceed CAISO by the charging amount (up to ~9 GW in
    # 2025). Hours where EIA is implausibly LOW relative to CAISO are reporting artifacts.
    bad = (j["caiso_demand"] > 5000) & (ratio < 1 - tol)
    bad |= h["demand"] < 5000
    flagged = h.loc[bad, ["demand", "solar", "wind", "net_load"]].join(j.loc[bad, ["caiso_demand"]])
    out = h.copy()
    out.loc[bad, ["demand", "net_load"]] = np.nan
    return out, flagged



def add_storage_adjusted(h: pd.DataFrame, fm: pd.DataFrame) -> pd.DataFrame:
    """Add demand_ex_storage and net_load_ex_storage: EIA-930 demand minus the estimated net battery charging
    of the CAISO fleet (the five-minute 'Batteries' series is negative when the fleet is a net charger). This
    is an approximation: it does not remove pumped storage or hydro pumping, and it cannot recover gross
    charging when part of the fleet charges while another part discharges. Hours without a CAISO battery
    value stay NaN rather than being treated as zero charging."""
    b = _to_hour_ending(fm["batteries"])
    out = h.join(b.rename("battery_caiso"), how="left")
    charging = (-out["battery_caiso"]).clip(lower=0)
    out["demand_ex_storage"] = out["demand"] - charging
    out["net_load_ex_storage"] = out["net_load"] - charging
    return out


def fill_from_caiso(h: pd.DataFrame, target: str, source: pd.Series, min_overlap: int = 2000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill gaps in an EIA-930 series from a CAISO series through a per-year linear calibration
    (EIA = a x CAISO + b, fitted on hours where both exist). Returns (filled frame, fill log)."""
    src = _to_hour_ending(source).reindex(h.index)
    out = h.copy()
    log = []
    for y, idx in h.groupby("year").groups.items():
        e = h.loc[idx, target]
        c = src.loc[idx]
        both = e.notna() & c.notna()
        missing = e.isna() & c.notna()
        if both.sum() < min_overlap or missing.sum() == 0:
            log.append({"year": y, "target": target, "n_missing": int(e.isna().sum()), "n_filled": 0, "slope": np.nan, "intercept": np.nan, "corr": np.nan})
            continue
        a, b = np.polyfit(c[both].values, e[both].values, 1)
        out.loc[idx[missing.values], target] = a * c[missing].values + b
        log.append({"year": y, "target": target, "n_missing": int(e.isna().sum()), "n_filled": int(missing.sum()),
                    "slope": float(a), "intercept": float(b), "corr": float(np.corrcoef(c[both], e[both])[0, 1])})
    return out, pd.DataFrame(log)


# --------------------------------------------------------------------------------------
# 7. The workshop format (Manner, IRTF SUSTAIN, July 2026): 2025-2026 hourly series, gross imports and
#    exports by month, installed wind and solar, and min / max / mean summaries
# --------------------------------------------------------------------------------------
def load_eia930_interchange_ciso(first_year: int = 2025, last_year: int = 2026, ba: str = "CISO") -> pd.DataFrame:
    """Hourly gross imports and exports of one balancing authority from the EIA-930 INTERCHANGE files, which report
    the flow with each directly interconnected balancing authority (positive = flow out of `ba`). Exports sum the
    positive neighbour flows and imports the negative ones, so their difference is the net interchange of the
    BALANCE files (checked in run_chapter1 step 5). Files repeated across raw folders keep the later copy."""
    frames = []
    for f in sorted(glob.glob(str(RAW / "eia930" / "*" / "EIA930_INTERCHANGE_*.csv"))):
        yr = int(re.search(r"_INTERCHANGE_(\d{4})_", f).group(1))
        if yr < first_year or yr > last_year:
            continue
        parts = []
        cols = ["Balancing Authority", "Directly Interconnected Balancing Authority", "Interchange (MW)", "UTC Time at End of Hour"]
        for chunk in pd.read_csv(f, usecols=cols, chunksize=400_000, low_memory=False):
            parts.append(chunk[chunk["Balancing Authority"] == ba])
        d = pd.concat(parts)
        d["mw"] = pd.to_numeric(d["Interchange (MW)"], errors="coerce")
        d["time_utc"] = pd.to_datetime(d["UTC Time at End of Hour"], format="%m/%d/%Y %I:%M:%S %p", utc=True)
        d["exports"] = d["mw"].clip(lower=0)
        d["imports"] = -d["mw"].clip(upper=0)
        g = d.groupby("time_utc")
        frames.append(pd.DataFrame({"exports": g["exports"].sum(min_count=1), "imports": g["imports"].sum(min_count=1), "n_neighbours": g["mw"].count()}))
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index = df.index.tz_convert(TZ)
    df.index.name = "hour_ending_local"
    df["net_imports"] = df["imports"] - df["exports"]
    start = df.index - pd.Timedelta(hours=1)
    df["year"] = start.year
    df["month"] = start.month
    return df[(df["year"] >= first_year) & (df["year"] <= last_year)]


def monthly_imports_exports(ix: pd.DataFrame) -> pd.DataFrame:
    """Monthly gross imports, exports and net imports (GWh), the hours behind them and a complete-month flag
    (at least 95 percent of the calendar hours present; EIA-930 has a day of missing neighbour rows in some months)."""
    g = ix.groupby(["year", "month"])
    out = pd.DataFrame({"imports_GWh": g["imports"].sum() / 1e3, "exports_GWh": g["exports"].sum() / 1e3, "hours": g["imports"].count()})
    out["net_imports_GWh"] = out["imports_GWh"] - out["exports_GWh"]
    out["calendar_hours"] = [pd.Period(f"{y}-{m:02d}").days_in_month * 24 for y, m in out.index]
    out["complete"] = out["hours"] >= 0.95 * out["calendar_hours"]
    return out.reset_index()


_860M_TECH = {"Onshore Wind Turbine": "wind", "Offshore Wind Turbine": "wind", "Solar Photovoltaic": "solar",
              "Solar Thermal with Energy Storage": "solar", "Solar Thermal without Energy Storage": "solar"}


def eia860m_ba_capacity(source_id: str = "eia860m_2026_07", ba: str = "CISO") -> pd.DataFrame:
    """Operating nameplate wind and solar capacity (MW) inside one balancing authority and inside California, from
    the Operating sheet of an EIA-860M monthly file. The balancing-authority total is the one to set against the
    EIA-930 CISO generation series, which counts plants by balancing authority rather than by state."""
    op = pd.read_excel(raw_path(source_id), sheet_name="Operating", header=2)
    op["mw"] = pd.to_numeric(op["Nameplate Capacity (MW)"], errors="coerce")
    op["label"] = op["Technology"].map(_860M_TECH)
    op = op[op["label"].notna()]
    rows = []
    for label, sub in op.groupby("label"):
        in_ba = sub[sub["Balancing Authority Code"] == ba]
        in_ca = sub[sub["Plant State"] == "CA"]
        rows.append({"technology": label, "ba": ba, "ba_nameplate_mw": float(in_ba["mw"].sum()), "ba_units": int(len(in_ba)),
                     "california_nameplate_mw": float(in_ca["mw"].sum()), "california_units": int(len(in_ca)), "source": source_id})
    return pd.DataFrame(rows)


def hourly_stats(s: pd.Series, label: str, unit: str, period: str) -> dict:
    """Minimum, maximum and mean of an hourly series with the hours behind them and the times of the extremes."""
    s = s.dropna()
    return {"series": label, "period": period, "unit": unit, "hours": int(len(s)), "min": float(s.min()), "min_time": str(s.idxmin()),
            "max": float(s.max()), "max_time": str(s.idxmax()), "mean": float(s.mean())}


def production_intensity(ci: pd.DataFrame, fm: pd.DataFrame, min_generation_mw: float = 1000.0) -> pd.Series:
    """In-CAISO production emission factor (g CO2 per kWh): the CO2 that CAISO's accounting assigns to sources inside
    CAISO (imports excluded) divided by the generation of the fuel-mix sources inside CAISO (imports and batteries
    excluded), on hours that are valid in the CO2 file. The consumption-side counterpart is the accounting intensity
    of section 3 (imports net of exports, divided by demand)."""
    co2_cols = [c for c in ci.columns if c.endswith(" CO2") and c != "Imports CO2"]
    gen_cols = [c for c in ("solar", "wind", "geothermal", "biomass", "biogas", "small_hydro", "large_hydro", "coal", "nuclear", "natural_gas", "other") if c in fm.columns]
    num = ci[co2_cols].sum(axis=1, min_count=1)
    den = fm[gen_cols].sum(axis=1, min_count=1).reindex(ci.index)
    ok = ci["valid_hour"] & den.gt(min_generation_mw)
    return (num / den * 1000.0).where(ok)
