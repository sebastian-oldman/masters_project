"""Chapter 3: energy production growth in California, the supply side of RQ2.

1. Generation by resource 2010-2025 (EIA-923 in-state, CEC total-system imports), capacity by technology
   (EIA-860 annual), battery storage capacity (EIA-860 energy storage file), CAISO curtailment volumes.
2. Retirement schedule: EIA-860M planned retirement dates plus the State Water Board once-through-cooling
   compliance dates (Alamitos, Huntington Beach, Ormond Beach 2026; Haynes, Harbor, Scattergood 2029; Diablo Canyon 2030).
3. Supply-side realization model from EIA-860M vintages: every California planned unit in the January file of
   2016-2022, outcome by December 2025 (operating, cancelled, still planned, dropped), a logistic model of completion
   on technology, size, planned lead time and observation window, and Kaplan-Meier / cumulative-incidence delay curves.
4. Probability-weighted planned capacity, energy and ELCC-derated peak contribution for 2030 in three cases.

All readers take the raw files as downloaded (manifest ids in comments); nothing is hand-edited.
"""
from __future__ import annotations

import glob
import io
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .ch1_baseline import raw_path
from .paths import PROCESSED, RAW

# ------------------------------------------------------------------------------------------------
# Resource classification (EIA energy source + prime mover -> chapter resource class)
# ------------------------------------------------------------------------------------------------
RESOURCES = ["Natural gas", "Nuclear", "Large hydro", "Small hydro", "Geothermal", "Biomass", "Wind", "Solar",
             "Batteries", "Pumped storage", "Coal and petcoke", "Oil", "Other"]
_BIOMASS = {"WDS", "WDL", "LFG", "OBG", "AB", "MSW", "MSB", "MSN", "OBS", "OBL", "SLW", "BLQ", "WO"}
_COAL = {"BIT", "SUB", "LIG", "RC", "WC", "PC", "ANT", "SGC", "SC"}
_OIL = {"DFO", "RFO", "JF", "KER", "PG"}
_GAS = {"NG", "OG", "BFG", "SGP"}


def classify(energy_source, prime_mover=None, nameplate_mw=None, technology=None) -> str:
    es = str(energy_source).strip().upper() if pd.notna(energy_source) else ""
    pm = str(prime_mover).strip().upper() if pd.notna(prime_mover) else ""
    tech = str(technology) if pd.notna(technology) else ""
    if pm == "BA" or es == "MWH" or tech == "Batteries":
        return "Batteries"
    if pm == "PS" or tech == "Hydroelectric Pumped Storage":
        return "Pumped storage"
    if es == "WAT":
        mw = float(nameplate_mw) if pd.notna(nameplate_mw) else np.nan
        return "Small hydro" if (pd.notna(mw) and mw <= 30) else "Large hydro"
    if es == "NUC":
        return "Nuclear"
    if es == "GEO":
        return "Geothermal"
    if es == "SUN":
        return "Solar"
    if es == "WND":
        return "Wind"
    if es in _GAS:
        return "Natural gas"
    if es in _BIOMASS:
        return "Biomass"
    if es in _COAL:
        return "Coal and petcoke"
    if es in _OIL:
        return "Oil"
    return "Other"


def _find_header(x: pd.ExcelFile, sheet: str, needle: str, nrows: int = 12) -> int:
    raw = x.parse(sheet, header=None, nrows=nrows)
    for i in range(len(raw)):
        if any(needle in str(v).lower() for v in raw.iloc[i].values):
            return i
    raise ValueError(f"header with '{needle}' not found in {sheet}")


def _norm(c: str) -> str:
    return re.sub(r"\s+", " ", str(c).replace("\n", " ")).strip()


# ------------------------------------------------------------------------------------------------
# 1a. EIA-923: California net generation by resource, 2010-2025
# ------------------------------------------------------------------------------------------------
def eia923_ca_generation(years=range(2010, 2026)) -> pd.DataFrame:
    """Annual California net generation (GWh) by resource class from the EIA-923 Page 1 schedule."""
    rows = []
    for y in years:
        zz = zipfile.ZipFile(raw_path(f"eia923_{y}"))
        name = [n for n in zz.namelist() if "2_3_4_5" in n.upper().replace(" ", "_") and n.lower().endswith(("xlsx", "xls"))][0]
        x = pd.ExcelFile(io.BytesIO(zz.read(name)))
        sheet = [s for s in x.sheet_names if s.lower().startswith("page 1 generation")][0]
        hdr = _find_header(x, sheet, "plant id")
        d = x.parse(sheet, header=hdr)
        d.columns = [_norm(c) for c in d.columns]
        st = [c for c in d.columns if c.lower() in ("plant state", "state")][0]
        fuel = [c for c in d.columns if "reported" in c.lower() and "fuel" in c.lower()][0]
        pm = [c for c in d.columns if "prime mover" in c.lower()][0]
        ng = [c for c in d.columns if "net generation" in c.lower()][0]
        ca = d[d[st].astype(str).str.strip() == "CA"].copy()
        ca["gwh"] = pd.to_numeric(ca[ng], errors="coerce") / 1000.0
        ca["resource"] = [classify(e, p) for e, p in zip(ca[fuel], ca[pm])]
        ca["resource"] = ca["resource"].replace({"Large hydro": "Hydro"})  # EIA-923 carries no unit size, so hydro is not split
        g = ca.groupby("resource")["gwh"].sum()
        for r, v in g.items():
            rows.append({"year": y, "resource": r, "gwh": float(v)})
        rows.append({"year": y, "resource": "Total in-state", "gwh": float(ca["gwh"].sum())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# 1b. CEC Energy Almanac: total system electric generation (in-state by fuel, NW and SW imports)
# ------------------------------------------------------------------------------------------------
def _almanac_dir() -> Path:
    return Path(sorted(glob.glob(str(RAW / "cec_almanac" / "*")))[-1])


def cec_multi_year_generation() -> pd.DataFrame:
    """CEC 'California Electrical Energy Generation' table: in-state generation by fuel and net imports, GWh, 2012-2024."""
    tabs = pd.read_html(_almanac_dir() / "cec_california_electrical_energy_generation.html")
    t = tabs[0].copy()
    t.columns = [_norm(c) for c in t.columns]
    t = t.rename(columns={t.columns[0]: "category"})
    long = t.melt(id_vars="category", var_name="year", value_name="gwh")
    long["year"] = long["year"].str.extract(r"(\d{4})").astype(int)
    long["gwh"] = pd.to_numeric(long["gwh"].astype(str).str.replace(",", "").str.replace("-", "").str.strip(), errors="coerce")
    long["category"] = long["category"].str.replace(r"\*", "", regex=True).str.strip()
    return long


def cec_total_system_by_year() -> pd.DataFrame:
    """Per-year CEC total system pages (2015-2024): in-state, NW imports, SW imports, total imports by fuel, GWh."""
    rows = []
    for f in sorted(glob.glob(str(_almanac_dir() / "cec_*_total_system_electric_generation.html"))):
        y = int(re.search(r"cec_(\d{4})_", f).group(1))
        t = pd.read_html(f)[0]
        t.columns = [_norm(c) for c in t.columns]
        fuel = t.columns[0]
        def num(col):
            return pd.to_numeric(t[col].astype(str).str.replace(",", "").str.replace("%", "").str.strip().replace({"-": np.nan, "": np.nan}), errors="coerce")
        ins = [c for c in t.columns if "In-State Generation (GWh)" in c][0]
        nw = [c for c in t.columns if "Northwest Imports" in c][0]
        sw = [c for c in t.columns if "Southwest Imports" in c][0]
        mix = [c for c in t.columns if "Energy Mix (GWh)" in c][0]
        for i, r in t.iterrows():
            rows.append({"year": y, "fuel": str(r[fuel]).strip(), "in_state_gwh": num(ins).iloc[i], "nw_imports_gwh": num(nw).iloc[i],
                         "sw_imports_gwh": num(sw).iloc[i], "energy_mix_gwh": num(mix).iloc[i]})
    return pd.DataFrame(rows)


def cec_capacity_and_energy_page() -> tuple[pd.DataFrame, pd.DataFrame]:
    """CEC 'electric generation capacity and energy' page: in-state generation (GWh) and capacity (MW) by fuel, 2021-2025."""
    tabs = pd.read_html(_almanac_dir() / "cec_electric_generation_capacity_and_energy.html")
    out = []
    for t in tabs[:2]:
        t = t.copy(); t.columns = [_norm(c) for c in t.columns]; t = t.rename(columns={t.columns[0]: "fuel"})
        long = t.melt(id_vars="fuel", var_name="year", value_name="value")
        long["year"] = long["year"].astype(str).str.extract(r"(\d{4})").astype(int)
        long["value"] = pd.to_numeric(long["value"].astype(str).str.replace(",", "").replace({"-": np.nan}), errors="coerce")
        out.append(long)
    return out[0].rename(columns={"value": "gwh"}), out[1].rename(columns={"value": "mw"})


# ------------------------------------------------------------------------------------------------
# 1c. EIA-860 annual: California capacity by technology, battery energy capacity
# ------------------------------------------------------------------------------------------------
def _eia860_generator_frame(year: int, which: str = "operable") -> pd.DataFrame:
    zz = zipfile.ZipFile(raw_path(f"eia860_{year}"))
    names = [n for n in zz.namelist() if re.search(r"generator", n, re.I) and not n.startswith("__") and n.lower().endswith(("xlsx", "xls"))]
    name = sorted(names, key=lambda n: ("3_1" not in n, n))[0]
    x = pd.ExcelFile(io.BytesIO(zz.read(name)))
    pick = {"operable": ("exist", "operable"), "proposed": ("prop",), "retired": ("ret", "retired")}[which]
    sheet = [s for s in x.sheet_names if s.lower().startswith(pick)][0]
    hdr = _find_header(x, sheet, "plant")
    d = x.parse(sheet, header=hdr)
    d.columns = [_norm(c) for c in d.columns]
    ren = {}
    for c in d.columns:
        cl = c.lower()
        if cl in ("state",): ren[c] = "state"
        elif cl in ("plant_code", "plant code"): ren[c] = "plant_id"
        elif cl in ("plant_name", "plant name"): ren[c] = "plant_name"
        elif cl in ("generator_id", "generator id"): ren[c] = "gen_id"
        elif cl in ("prime_mover", "prime mover"): ren[c] = "prime_mover"
        elif cl in ("energy_source_1", "energy source 1"): ren[c] = "energy_source"
        elif cl in ("nameplate", "nameplate capacity (mw)"): ren[c] = "nameplate_mw"
        elif cl in ("summer_capability", "summer capacity (mw)"): ren[c] = "summer_mw"
        elif cl == "status": ren[c] = "status"
        elif cl == "technology": ren[c] = "technology"
        elif cl in ("operating_year", "operating year"): ren[c] = "operating_year"
        elif cl in ("planned retirement year",): ren[c] = "planned_retirement_year"
        elif cl in ("planned retirement month",): ren[c] = "planned_retirement_month"
        elif cl in ("retirement year", "retirement_year"): ren[c] = "retirement_year"
    d = d.rename(columns=ren)
    d = d[d["state"].astype(str).str.strip() == "CA"].copy()
    d["nameplate_mw"] = pd.to_numeric(d["nameplate_mw"], errors="coerce")
    d["resource"] = [classify(e, p, m, d["technology"].iloc[i] if "technology" in d else None) for i, (e, p, m) in enumerate(zip(d["energy_source"], d["prime_mover"], d["nameplate_mw"]))]
    d["year"] = year
    return d


def eia860_ca_capacity(years=range(2010, 2026)) -> pd.DataFrame:
    """Operable nameplate capacity (MW) in California by resource class and year, EIA-860 annual files."""
    rows = []
    for y in years:
        d = _eia860_generator_frame(y, "operable")
        g = d.groupby("resource").agg(nameplate_mw=("nameplate_mw", "sum"), units=("nameplate_mw", "size"))
        for r, v in g.iterrows():
            rows.append({"year": y, "resource": r, "nameplate_mw": float(v.nameplate_mw), "units": int(v.units)})
        rows.append({"year": y, "resource": "Total", "nameplate_mw": float(d["nameplate_mw"].sum()), "units": int(len(d))})
    return pd.DataFrame(rows)


def eia860_ca_battery_energy(years=range(2016, 2026)) -> pd.DataFrame:
    """Battery power (MW) and energy (MWh) capacity in California from the EIA-860 energy storage file (2016 onward)."""
    rows = []
    for y in years:
        zz = zipfile.ZipFile(raw_path(f"eia860_{y}"))
        names = [n for n in zz.namelist() if "3_4_Energy_Storage" in n]
        if not names:
            continue
        x = pd.ExcelFile(io.BytesIO(zz.read(names[0])))
        sheet = [s for s in x.sheet_names if s.lower().startswith("operable")][0]
        d = x.parse(sheet, header=_find_header(x, sheet, "plant")); d.columns = [_norm(c) for c in d.columns]
        d = d[d["State"].astype(str).str.strip() == "CA"]
        mwh = [c for c in d.columns if "Energy Capacity (MWh)" in c]
        rows.append({"year": y, "units": int(len(d)), "power_mw": float(pd.to_numeric(d["Nameplate Capacity (MW)"], errors="coerce").sum()),
                     "energy_mwh": float(pd.to_numeric(d[mwh[0]], errors="coerce").sum()) if mwh else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# 1d. CAISO curtailment
# ------------------------------------------------------------------------------------------------
def caiso_curtailment_annual() -> pd.DataFrame:
    d = pd.read_csv(raw_path("caiso_curtailments_monthly_csv"), encoding="utf-8-sig")
    d = d.iloc[:, :2]; d.columns = ["date", "mwh"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce"); d = d.dropna(subset=["date"])
    d["mwh"] = pd.to_numeric(d["mwh"], errors="coerce")
    g = d.groupby(d["date"].dt.year).agg(curtailed_gwh=("mwh", lambda s: s.sum() / 1000), months=("mwh", "count")).reset_index().rename(columns={"date": "year"})
    return g


# ------------------------------------------------------------------------------------------------
# 2. Retirements: EIA-860M planned dates plus the once-through-cooling compliance schedule
# ------------------------------------------------------------------------------------------------
def _load_860m(source_id: str, sheet: str) -> pd.DataFrame:
    x = pd.ExcelFile(raw_path(source_id))
    hdr = _find_header(x, sheet, "plant id")
    d = x.parse(sheet, header=hdr); d.columns = [_norm(c) for c in d.columns]
    d = d[d["Plant State"].astype(str).str.strip() == "CA"].copy()
    d["plant_id"] = pd.to_numeric(d["Plant ID"], errors="coerce").astype("Int64").astype(str)
    d["gen_id"] = d["Generator ID"].astype(str).str.strip()
    d["key"] = d["plant_id"] + "|" + d["gen_id"]
    cap = "Nameplate Capacity (MW)" if "Nameplate Capacity (MW)" in d.columns else [c for c in d.columns if "Summer Capacity" in c][0]
    d["mw"] = pd.to_numeric(d[cap], errors="coerce")
    d["capacity_basis"] = "nameplate" if cap.startswith("Nameplate") else "net summer"
    d["resource"] = [classify(e, p, m, t) for e, p, m, t in zip(d["Energy Source Code"], d["Prime Mover Code"], d["mw"], d["Technology"])]
    return d


OTC_SCHEDULE = [  # State Water Board OTC Policy as amended 2023-08-15, Table 1 (manifest swrcb_otc_policy_2023)
    dict(plant_id="315", plant="AES Alamitos", units="3, 4, 5", compliance="2026-12-31", milestone=37),
    dict(plant_id="335", plant="AES Huntington Beach", units="2", compliance="2026-12-31", milestone=37),
    dict(plant_id="350", plant="Ormond Beach", units="1, 2", compliance="2026-12-31", milestone=37),
    dict(plant_id="400", plant="Haynes (LADWP)", units="1, 2, 8", compliance="2029-12-31", milestone=38),
    dict(plant_id="399", plant="Harbor (LADWP)", units="5", compliance="2029-12-31", milestone=39),
    dict(plant_id="404", plant="Scattergood (LADWP)", units="1, 2", compliance="2029-12-31", milestone=41),
    dict(plant_id="6099", plant="Diablo Canyon (PG&E)", units="1, 2", compliance="2030-10-31", milestone=42),
]


def retirement_schedule(latest: str = "eia860m_2026_07") -> tuple[pd.DataFrame, pd.DataFrame]:
    """(a) every California operating unit with a planned retirement date in the latest EIA-860M file;
    (b) the OTC compliance units with their EIA capacity and the schedule date used in the 2030 cases."""
    op = _load_860m(latest, "Operating")
    op["planned_retirement_year"] = pd.to_numeric(op["Planned Retirement Year"], errors="coerce")
    op["planned_retirement_month"] = pd.to_numeric(op["Planned Retirement Month"], errors="coerce")
    sched = op[op["planned_retirement_year"].notna()][["plant_id", "Plant Name", "gen_id", "Technology", "resource", "mw", "Operating Year", "planned_retirement_month", "planned_retirement_year"]].copy()
    sched = sched.rename(columns={"Plant Name": "plant_name", "Operating Year": "operating_year"})
    otc_rows = []
    for r in OTC_SCHEDULE:
        units = [u.strip() for u in r["units"].split(",")]
        sub = op[(op["plant_id"] == r["plant_id"]) & (op["gen_id"].isin(units))]
        for _, u in sub.iterrows():
            otc_rows.append(dict(plant_id=r["plant_id"], plant_name=u["Plant Name"], gen_id=u["gen_id"], technology=u["Technology"], resource=u["resource"], mw=u["mw"],
                                 operating_year=u["Operating Year"], eia_planned_retirement_year=u["planned_retirement_year"], otc_compliance_date=r["compliance"],
                                 otc_milestone=r["milestone"], schedule_year=int(r["compliance"][:4])))
    otc = pd.DataFrame(otc_rows)
    sched["otc_unit"] = sched.set_index(["plant_id", "gen_id"]).index.isin(otc.set_index(["plant_id", "gen_id"]).index)
    return sched, otc


# ------------------------------------------------------------------------------------------------
# 3. Realization model from EIA-860M vintages
# ------------------------------------------------------------------------------------------------
STATUS_GROUP = {"V": "under construction", "U": "under construction", "TS": "construction complete", "T": "approved, not started",
                "L": "approvals pending", "P": "approvals not initiated", "OT": "approvals not initiated", "OP": "operating"}


def _status_code(s) -> str:
    m = re.match(r"\((\w+)\)", str(s).strip())
    return m.group(1) if m else str(s).strip()[:2]


def eia860m_vintage_outcomes(vintages=range(2016, 2023), reference: str = "eia860m_2025_12") -> pd.DataFrame:
    """One row per (California planned unit, January vintage): outcome by the December 2025 file."""
    ref = {sh: _load_860m(reference, sh) for sh in ("Operating", "Planned", "Retired", "Canceled or Postponed")}
    ops = ref["Operating"].set_index("key"); rets = ref["Retired"].set_index("key"); pls = ref["Planned"].set_index("key"); cans = set(ref["Canceled or Postponed"]["key"])
    ref_date = pd.Timestamp("2025-12-31")
    # cancellation timing: first December file in which the unit is in the canceled sheet or absent from every sheet
    dec = {}
    for y in range(2016, 2026):
        sheets = {sh: _load_860m(f"eia860m_{y}_12", sh) for sh in ("Operating", "Planned", "Retired", "Canceled or Postponed")}
        dec[y] = {"present": set(sheets["Operating"]["key"]) | set(sheets["Planned"]["key"]) | set(sheets["Retired"]["key"]), "canceled": set(sheets["Canceled or Postponed"]["key"])}
    rows = []
    for v in vintages:
        p = _load_860m(f"eia860m_{v}_01", "Planned")
        for _, u in p.iterrows():
            k = u["key"]
            py, pm = pd.to_numeric(u["Planned Operation Year"], errors="coerce"), pd.to_numeric(u["Planned Operation Month"], errors="coerce")
            planned_date = pd.Timestamp(year=int(py), month=int(pm) if pd.notna(pm) and 1 <= pm <= 12 else 6, day=15) if pd.notna(py) else pd.NaT
            rec = dict(key=k, plant_id=u["plant_id"], gen_id=u["gen_id"], plant_name=u["Plant Name"], technology=u["Technology"], resource=u["resource"],
                       mw=u["mw"], capacity_basis=u["capacity_basis"], status_code=_status_code(u["Status"]), vintage=v, planned_year=py, planned_month=pm,
                       planned_date=planned_date, balancing_authority=u.get("Balancing Authority Code", np.nan))
            if k in ops.index or k in rets.index:
                src = ops if k in ops.index else rets
                oy, om = pd.to_numeric(src.loc[k, "Operating Year"], errors="coerce"), pd.to_numeric(src.loc[k, "Operating Month"], errors="coerce")
                if isinstance(oy, pd.Series): oy, om = oy.iloc[0], om.iloc[0]
                actual = pd.Timestamp(year=int(oy), month=int(om) if pd.notna(om) and 1 <= om <= 12 else 6, day=15) if pd.notna(oy) else pd.NaT
                rec.update(outcome="operating" if k in ops.index else "operated then retired", actual_date=actual, completed=True)
            elif k in cans:
                rec.update(outcome="cancelled", actual_date=pd.NaT, completed=False)
            elif k in pls.index:
                rec.update(outcome="still planned", actual_date=pd.NaT, completed=False)
            else:
                rec.update(outcome="dropped from survey", actual_date=pd.NaT, completed=False)
            # timing of cancellation / drop: first December file year with the unit canceled or absent
            cy = np.nan
            if rec["outcome"] in ("cancelled", "dropped from survey"):
                for y in range(v, 2026):
                    if k in dec[y]["canceled"] or k not in dec[y]["present"]:
                        cy = y; break
            rec["exit_year"] = cy
            rows.append(rec)
    d = pd.DataFrame(rows)
    d["status_group"] = d["status_code"].map(STATUS_GROUP).fillna("approvals not initiated")
    d["vintage_date"] = pd.to_datetime(d["vintage"].astype(str) + "-01-15")
    d["lead_years"] = (d["planned_date"] - d["vintage_date"]).dt.days / 365.25
    d["window_years"] = (ref_date - d["vintage_date"]).dt.days / 365.25
    d["delay_months"] = (d["actual_date"] - d["planned_date"]).dt.days / 30.44
    # time from the planned date to the event (completion) or censoring (Dec 2025 for still planned; exit year end for cancelled)
    exit_date = pd.to_datetime(d["exit_year"].astype("Int64").astype(str) + "-12-31", errors="coerce")
    d["event_date"] = d["actual_date"].where(d["completed"], exit_date.fillna(ref_date))
    d["t_months"] = ((d["event_date"] - d["planned_date"]).dt.days / 30.44).clip(lower=0)
    d["event"] = np.where(d["completed"], 1, np.where(d["outcome"].isin(["cancelled", "dropped from survey"]), 2, 0))  # 1 complete, 2 cancel, 0 censored
    return d


def realization_by(d: pd.DataFrame, by: str) -> pd.DataFrame:
    g = d.groupby(by)
    out = pd.DataFrame({"units": g.size(), "mw_planned": g["mw"].sum(), "completed_units": g["completed"].sum(),
                        "completed_mw": g.apply(lambda x: x.loc[x.completed, "mw"].sum()),
                        "cancelled_mw": g.apply(lambda x: x.loc[x.outcome.isin(["cancelled", "dropped from survey"]), "mw"].sum()),
                        "still_planned_mw": g.apply(lambda x: x.loc[x.outcome == "still planned", "mw"].sum())})
    out["completion_rate_units"] = out["completed_units"] / out["units"]
    out["completion_rate_mw"] = out["completed_mw"] / out["mw_planned"]
    out["median_delay_months_completed"] = g.apply(lambda x: x.loc[x.completed, "delay_months"].median())
    return out.reset_index()


def fit_completion_logit(d: pd.DataFrame, with_status: bool = True):
    """Logistic model of completion by December 2025 on technology, log size, planned lead time and observation window
    (and construction status), with standard errors clustered by unit."""
    import statsmodels.formula.api as smf
    m = d.dropna(subset=["mw", "lead_years", "window_years"]).copy()
    m = m[m["mw"] > 0]
    m["log_mw"] = np.log(m["mw"])
    m["completed_i"] = m["completed"].astype(int)
    top = m["resource"].value_counts()
    m["tech"] = np.where(m["resource"].isin(top[top >= 15].index), m["resource"], "Other")
    formula = "completed_i ~ C(tech, Treatment('Solar')) + log_mw + lead_years + window_years" + (" + C(status_group, Treatment('approvals not initiated'))" if with_status else "")
    model = smf.logit(formula, data=m)
    res = model.fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": pd.factorize(m["key"])[0]})
    m["p_hat"] = res.predict(m)
    return res, m


def _auc(y, p) -> float:
    y = np.asarray(y); p = np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())


def km_delay(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(a) Kaplan-Meier of time from planned to actual commercial date, cancellations and still-planned censored;
    (b) cumulative incidence of completion and cancellation treating cancellation as a competing risk (Aalen-Johansen);
    (c) delay statistics among completers."""
    from lifelines import KaplanMeierFitter
    x = d.dropna(subset=["t_months"]).copy()
    kmf = KaplanMeierFitter().fit(x["t_months"], event_observed=(x["event"] == 1).astype(int))
    km = kmf.survival_function_.reset_index(); km.columns = ["t_months", "S_not_yet_operating"]
    ci = kmf.confidence_interval_.reset_index(); km["S_lo95"], km["S_hi95"] = ci.iloc[:, 1].values, ci.iloc[:, 2].values
    # Aalen-Johansen by hand (exact ties)
    t = np.sort(x.loc[x["event"] > 0, "t_months"].unique()); S = 1.0; cif1 = cif2 = 0.0; rows = [{"t_months": 0.0, "cif_complete": 0.0, "cif_cancel": 0.0}]
    for tt in t:
        n = int((x["t_months"] >= tt).sum()); d1 = int(((x["t_months"] == tt) & (x["event"] == 1)).sum()); d2 = int(((x["t_months"] == tt) & (x["event"] == 2)).sum())
        cif1 += S * d1 / n; cif2 += S * d2 / n; S *= 1 - (d1 + d2) / n
        rows.append({"t_months": float(tt), "cif_complete": cif1, "cif_cancel": cif2})
    cif = pd.DataFrame(rows)
    comp = x[x["completed"]]["delay_months"].dropna()
    stats = {"n_completed": int(len(comp)), "median_delay_months": float(comp.median()), "mean_delay_months": float(comp.mean()),
             "share_on_time_or_early": float((comp <= 0).mean()), "share_late_over_12m": float((comp > 12).mean()), "p90_delay_months": float(comp.quantile(0.9)),
             "km_median_months_to_operation": float(kmf.median_survival_time_), "cif_complete_36m": float(np.interp(36, cif.t_months, cif.cif_complete)),
             "cif_complete_60m": float(np.interp(60, cif.t_months, cif.cif_complete)), "cif_cancel_60m": float(np.interp(60, cif.t_months, cif.cif_cancel))}
    return km, cif, stats


# ------------------------------------------------------------------------------------------------
# 4. Current planned list, ELCC, capacity factors and the 2030 cases
# ------------------------------------------------------------------------------------------------
ELCC_2028 = {  # E3/Astrape Updated Incremental ELCC Study (Jan 2023 update), Table 1, Tranche 6 (2028); manifest cpuc_e3_astrape_incremental_elcc_2023
    "Solar": 0.088, "Wind": 0.147, "Batteries": 0.765, "Pumped storage": 0.887,
}
ELCC_FIRM = {"Natural gas": 0.95, "Nuclear": 0.95, "Geothermal": 0.95, "Biomass": 0.90, "Coal and petcoke": 0.95, "Oil": 0.90, "Other": 0.80}
ELCC_HYDRO = {"Large hydro": 0.55, "Small hydro": 0.45}  # assumed summer-peak availability; CAISO NQC counts hydro on historical exceedance


def elcc_table() -> pd.DataFrame:
    rows = []
    for r in RESOURCES:
        if r in ELCC_2028: rows.append(dict(resource=r, elcc=ELCC_2028[r], basis="CPUC/E3-Astrape 2023 MTR ELCC study, Table 1, Tranche 6 (2028): 4-hour battery, 8-hour PSH, utility solar, in-state wind"))
        elif r in ELCC_HYDRO: rows.append(dict(resource=r, elcc=ELCC_HYDRO[r], basis="assumption: summer-peak availability of hydro (CAISO NQC uses historical exceedance)"))
        else: rows.append(dict(resource=r, elcc=ELCC_FIRM[r], basis="assumption: firm resource net of forced-outage and ambient derate"))
    return pd.DataFrame(rows)


def capacity_factors(gen: pd.DataFrame, cap: pd.DataFrame, years=(2023, 2024, 2025)) -> pd.DataFrame:
    """Realised capacity factors by resource: EIA-923 generation over EIA-860 operable nameplate, averaged over years."""
    rows = []
    for r in RESOURCES:
        gres = "Hydro" if r in ("Large hydro", "Small hydro") else r
        g = gen[(gen.resource == gres) & gen.year.isin(years)].groupby("year")["gwh"].sum()
        cres = ["Large hydro", "Small hydro"] if r in ("Large hydro", "Small hydro") else [r]
        c = cap[cap.resource.isin(cres) & cap.year.isin(years)].groupby("year")["nameplate_mw"].sum()
        cf = (g.reindex(c.index) * 1000 / (c * 8760)).dropna()
        rows.append(dict(resource=r, capacity_factor=float(cf.mean()) if len(cf) else np.nan, years=f"{min(years)}-{max(years)}", gwh_mean=float(g.mean()) if len(g) else np.nan, mw_mean=float(c.mean()) if len(c) else np.nan,
                         note="hydro capacity factor computed on large plus small hydro together" if r in ("Large hydro", "Small hydro") else ""))
    return pd.DataFrame(rows)


def current_planned(latest: str = "eia860m_2026_07") -> pd.DataFrame:
    p = _load_860m(latest, "Planned")
    p["status_code"] = p["Status"].map(_status_code); p["status_group"] = p["status_code"].map(STATUS_GROUP).fillna("approvals not initiated")
    p["planned_year"] = pd.to_numeric(p["Planned Operation Year"], errors="coerce"); p["planned_month"] = pd.to_numeric(p["Planned Operation Month"], errors="coerce")
    p["planned_date"] = pd.to_datetime(dict(year=p["planned_year"], month=p["planned_month"].fillna(6).clip(1, 12), day=15), errors="coerce")
    file_date = pd.Timestamp("2026-07-15")
    p["lead_years"] = (p["planned_date"] - file_date).dt.days / 365.25
    p["window_years"] = (pd.Timestamp("2030-12-31") - file_date).days / 365.25
    return p[["key", "plant_id", "gen_id", "Plant Name", "Technology", "resource", "mw", "status_code", "status_group", "planned_year", "planned_month", "planned_date", "lead_years", "window_years", "Balancing Authority Code"]].rename(columns={"Plant Name": "plant_name", "Balancing Authority Code": "balancing_authority"})


def existing_capacity_2025(reference: str = "eia860m_2025_12") -> pd.DataFrame:
    op = _load_860m(reference, "Operating")
    return op.groupby("resource").agg(nameplate_mw=("mw", "sum"), units=("mw", "size")).reset_index()


def cases_2030(existing: pd.DataFrame, planned: pd.DataFrame, sched: pd.DataFrame, otc: pd.DataFrame, cf: pd.DataFrame, elcc: pd.DataFrame,
               horizon_year: int = 2030) -> pd.DataFrame:
    """Three cases by resource: everything builds; model-weighted; model-weighted minus retirements (EIA planned dates
    through the horizon, OTC compliance units without an EIA date, and Diablo Canyon at its OTC compliance date)."""
    pl = planned[planned["planned_year"] <= horizon_year]
    add_all = pl.groupby("resource")["mw"].sum()
    add_w = pl.assign(w=pl["mw"] * pl["p_2030"]).groupby("resource")["w"].sum()
    ret_eia = sched[sched["planned_retirement_year"] <= horizon_year].groupby("resource")["mw"].sum()
    otc_no_eia = otc[otc["eia_planned_retirement_year"].isna() & (otc["schedule_year"] <= horizon_year)]
    ret_otc = otc_no_eia.groupby("resource")["mw"].sum()
    ex = existing.set_index("resource")["nameplate_mw"]
    cfm = cf.set_index("resource")["capacity_factor"]; el = elcc.set_index("resource")["elcc"]
    rows = []
    for r in RESOURCES:
        e = float(ex.get(r, 0.0)); a = float(add_all.get(r, 0.0)); w = float(add_w.get(r, 0.0)); rt = float(ret_eia.get(r, 0.0)) + float(ret_otc.get(r, 0.0))
        energy_cf = 0.0 if r in ("Batteries", "Pumped storage") else float(cfm.get(r, np.nan))
        for case, mw in (("A. Everything builds", e + a), ("B. Model-weighted", e + w), ("C. Model-weighted minus retirements", e + w - rt)):
            rows.append(dict(case=case, resource=r, existing_mw=e, planned_mw=a, weighted_planned_mw=w, retirements_mw=rt if case.startswith("C") else 0.0, capacity_mw=mw,
                             energy_twh=mw * energy_cf * 8760 / 1e6, elcc=float(el.get(r, np.nan)), peak_contribution_mw=mw * float(el.get(r, np.nan))))
    return pd.DataFrame(rows)
