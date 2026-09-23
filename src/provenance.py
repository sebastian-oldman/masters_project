"""Provenance of every figure: the processed files it is drawn from, the raw sources (manifest ids) behind them and the code that
produces it. Used by scripts/make_provenance_appendix.py (appendix tables and per-figure source lines) and by every chapter script,
which stamps the same information on the figure itself through stamp(). FREEZE_DATE is the data freeze recorded in docs/DATA_FREEZE.md."""
from __future__ import annotations

import textwrap

FREEZE_DATE = "2026-09-22"

ROWS = {
    1: [
        ("fig1_01", "Load duration curves; annual demand range, record peak, load factor", ["ch1_load_duration_curves.csv", "ch1_ciso_annual_summary.csv", "ciso_hourly_2019_2025_clean.parquet"], ["eia930_balance_2019_jan_jun .. 2025_jul_dec", "caiso_outlook demand and fuelsource (fills, artifact filter)"], "ch1_baseline.load_eia930_ciso, clean_demand_against_caiso, fill_from_caiso, duration_curves; run_chapter1 step 1"),
        ("fig1_02", "Net-load duration curves; minimum net load; hours below zero with and without battery charging", ["ch1_net_load_duration_curves.csv", "ch1_ciso_annual_summary.csv", "ciso_hourly_2019_2025_clean.parquet"], ["eia930 balance files", "caiso_outlook fuelsource (Batteries)"], "ch1_baseline.add_storage_adjusted, duration_curves; run_chapter1 step 1"),
        ("fig1_03", "Seasonal daily profiles; 12-14h and 20h means for 2019 and 2025", ["ch1_seasonal_profiles.csv"], ["eia930 balance files"], "ch1_baseline.seasonal_profiles; run_chapter1 step 1"),
        ("fig1_04", "Top-100 net-load hours by month and hour; median start, Jul-Sep and 17-21h shares", ["ch1_top100_net_load_hours.csv", "ch1_top100_net_load_timing.csv"], ["eia930 balance files"], "ch1_baseline.top_hours, top_hours_timing; run_chapter1 step 1"),
        ("fig1_05", "Day-ahead price duration and diurnal means; extremes; 11-14h and 18-20h mean price ranges", ["caiso_dam_lmp_hourly.parquet", "ch1_price_duration_curves.csv", "ch1_price_by_hour_of_day.csv", "ch1_price_stats.csv"], ["caiso_oasis dam_lmp monthly files (PRC_LMP DAM, DLAP nodes)"], "ch1_baseline.load_dam_lmp, price_duration, price_by_hour, price_stats; run_chapter1 step 2"),
        ("fig1_06", "Negative-price hours: full years, matched Jan 1 to Sep 22 windows, by month; share in 10-16h", ["ch1_negative_price_hours_windows.csv", "ch1_negative_price_hours_by_month.csv", "ch1_price_stats.csv"], ["caiso_oasis dam_lmp monthly files"], "ch1_baseline.negative_hours_by_month, price_stats; run_chapter1 step 2"),
        ("fig1_07", "CO2 accounting intensity: annual, duration, diurnal; percentiles; eGRID reference", ["ch1_carbon_intensity_annual.csv", "ch1_carbon_intensity_duration.csv", "ch1_carbon_intensity_diurnal.csv", "ch1_egrid_camx_2023.json", "caiso_co2_intensity_hourly.parquet"], ["caiso_outlook co2 and demand daily files", "epa_egrid2023_rev1"], "ch1_baseline.load_caiso_outlook_hourly, carbon_summary, egrid_camx; run_chapter1 step 3"),
        ("fig1_08", "Existing data center electricity use: statewide estimate, assumed conversion, sensitivity, utility subset", ["ch1_dc_load_estimates.csv", "ch1_ca_retail_sales_eia861.csv", "ch1_svp_fact_sheets.csv", "ch1_kollar_grady_points_california_flag.csv", "ch1_bottom_up_inputs.json"], ["epri_powering_intelligence_2024", "cec_dc_methodology_memo_2026", "eia861_2019 .. 2024", "svp_fact_sheet_2017 .. 2023", "kollar_grady_2025_zenodo", "epoch_data_centers"], "ch1_baseline.dc_load_estimates, bottom_up_estimate, ca_retail_sales_eia861, svp_fact_sheet_energy, kollar_grady_california; run_chapter1 step 4"),
        ("fig1_09", "Workshop format: hourly CAISO demand and in-CAISO net generation, 2026; minimum, maximum and mean", ["ch1_hourly_2026_workshop.csv", "ch1_workshop_stats.csv", "caiso_co2_intensity_hourly_2026.parquet", "caiso_fuelmix_hourly_2026.parquet"], ["eia930_balance_2026_jan_jun .. 2026_jul_dec", "caiso_outlook demand and fuelsource 2026 (artifact filter)"], "ch1_baseline.load_eia930_ciso, clean_demand_against_caiso, hourly_stats; run_chapter1 step 5"),
        ("fig1_10", "Workshop format: hourly day-ahead prices at the three DLAPs, January 2025 to September 2026; minimum, maximum and mean", ["caiso_dam_lmp_hourly.parquet", "ch1_workshop_stats.csv"], ["caiso_oasis dam_lmp monthly files 2025-01 .. 2026-09"], "ch1_baseline.load_dam_lmp, hourly_stats; run_chapter1 step 5"),
        ("fig1_11", "Workshop format: hourly CO2 intensity of CAISO demand (accounting) and of in-CAISO generation (production factor), 2026", ["ch1_carbon_intensity_hourly_2026.csv", "ch1_workshop_stats.csv", "caiso_co2_intensity_hourly_2026.parquet", "caiso_fuelmix_hourly_2026.parquet"], ["caiso_outlook co2, demand and fuelsource 2026 daily files"], "ch1_baseline.load_caiso_outlook_hourly, load_caiso_fuelmix_hourly, production_intensity, hourly_stats; run_chapter1 step 5"),
        ("fig1_12", "Workshop format: gross imports and exports of CAISO by month, January 2025 to August 2026, from the neighbour-level interchange; annual totals", ["ch1_imports_exports_monthly.csv", "ciso_interchange_gross_2025_2026.parquet"], ["eia930_interchange_2025_jan_jun .. 2026_jul_dec", "eia930_balance_2025_jan_jun .. 2026_jul_dec (net check)"], "ch1_baseline.load_eia930_interchange_ciso, monthly_imports_exports; run_chapter1 step 5"),
        ("fig1_13", "Workshop format: hourly wind and solar generation in CAISO, 2026, against installed nameplate in the CAISO balancing authority", ["ch1_hourly_2026_workshop.csv", "ch1_installed_wind_solar_2026_07.csv", "ch1_workshop_stats.csv"], ["eia930_balance_2026_jan_jun .. 2026_jul_dec", "eia860m_2026_07"], "ch1_baseline.load_eia930_ciso, eia860m_ba_capacity, hourly_stats; run_chapter1 step 5"),
    ],
    2: [
        ("fig2_01", "Census data center construction spending with ChatGPT annotation; month-over-month growth; shares of nonresidential construction", ["ch2_census_c30_data_center.csv"], ["census_c30_privsatime", "census_c30_privtime"], "ch2_growth.census_c30; run_chapter2 step 1"),
        ("fig2_02", "Log-linear trends, Chow test, Bai-Perron breaks, segment growth, sequential test; ARIMA and ETS forecasts with bands and backtest", ["ch2_census_break_summary.json", "ch2_census_bai_perron.csv", "ch2_census_segment_growth.csv", "ch2_census_forecast_arima.csv", "ch2_census_forecast_ets.csv", "ch2_census_forecast_backtest.csv"], ["census_c30_privsatime"], "ch2_growth.chow_test, bai_perron, sequential_supF, arima_forecast, ets_forecast, backtest_forecasts; run_chapter2 step 2"),
        ("fig2_03", "California proxies: QCEW employment and establishments, CBRE Silicon Valley construction and inventory, Epoch cumulative power; break-test summary", ["ch2_qcew_518210_california.csv", "ch2_cbre_california.csv", "ch2_epoch_timeline.csv", "ch2_break_test_comparison.csv"], ["qcew_518210_2014q1 .. 2026q1", "cbre_*_infogram tables via cbre_california_market_series.csv", "epoch_data_center_timelines", "epoch_data_centers"], "ch2_growth.qcew_california, cbre_california, epoch_timeline, break_analysis; run_chapter2 step 3"),
        ("fig2_04", "Energization requests by vintage and tier; Nevada separated; SCE cancellations; PG\\&E pipeline; ratios to CAISO record peak and existing load", ["ch2_tier_vintages.csv", "ch2_rq1_denominators.json", "ch1_dc_load_estimates.csv"], ["cec_dc_forecast_2024iepr", "cec_prelim_dc_forecast_2025", "cec_dc_methodology_memo_2026", "cec_assembly_hearing_2026_01_28", "cec_tn266008", "cec_tn268459", "cec_tn272026", "cec_tn272065", "cec_tn272807", "caiso_key_statistics_2026_08"], "ch2_growth.tier_vintages; run_chapter2 steps 4 and 5"),
        ("fig2_05", "Workshop format: current data center capacity (SVP cluster within the statewide 2023 estimate; CEC existing peak) and statistics of the projects by stage with ratios to the existing peak and the CAISO record peak; largest SCE request", ["ch2_project_statistics.csv", "ch2_sce_largest_requests.csv", "ch1_dc_load_estimates.csv", "ch2_rq1_denominators.json"], ["cec_assembly_hearing_2026_01_28", "cec_dc_methodology_memo_2026", "cec_tn268459", "epri_powering_intelligence_2024", "svp_fact_sheet_2023", "svp_assembly_hearing_2026_01_28", "caiso_key_statistics_2026_08"], "ch2_growth.sce_largest_requests; run_chapter2 step 6"),
        ("fig2_06", "Workshop format: annual energy of the requests (flat and at the CEC utilization) in electric-car years; existing 2023 use as reference", ["ch2_ev_equivalents.csv", "ch2_sce_largest_requests.csv", "ch1_dc_load_estimates.csv"], ["cec_assembly_hearing_2026_01_28", "cec_dc_methodology_memo_2026", "cec_tn268459", "epri_powering_intelligence_2024"], "run_chapter2 step 6 (3 MWh per car-year assumption from Manner 2026)"),
    ],
    3: [
        ("fig3_01", "In-state generation by resource and CEC net imports 2010-2025; shares", ["ch3_supply_by_year.csv", "ch3_eia923_generation_by_resource.csv", "ch3_cec_generation_multi_year.csv"], ["eia923_2010 .. 2025", "cec_elec_energy_generation_page", "ch1 EIA-930 imports"], "ch3_supply.eia923_ca_generation, cec_multi_year_generation; run_chapter3 step 1"),
        ("fig3_02", "Operable capacity by technology; battery power and energy; CAISO curtailment; July 2026 snapshot", ["ch3_eia860_capacity_by_resource.csv", "ch3_battery_capacity.csv", "ch3_caiso_curtailment_annual.csv", "ch3_capacity_snapshot_2026_07.json"], ["eia860_2010 .. 2025", "eia860m_2026_07", "caiso_curtailments_monthly_csv"], "ch3_supply.eia860_ca_capacity, eia860_ca_battery_energy, caiso_curtailment_annual, eia860m_capacity_snapshot; run_chapter3 step 1"),
        ("fig3_03", "Scheduled retirements: EIA-860M planned dates and once-through-cooling compliance dates", ["ch3_eia860m_planned_retirements.csv", "ch3_otc_units.csv"], ["eia860m_2026_07", "swrcb_otc_policy_2023"], "ch3_supply.retirement_schedule; run_chapter3 step 2"),
        ("fig3_04", "Realization model: outcomes by vintage and technology; logistic model; delay and cumulative-incidence curves", ["ch3_vintage_outcomes.csv", "ch3_realization_by_vintage.csv", "ch3_realization_by_technology.csv", "ch3_logit_coefficients.csv", "ch3_logit_summary.json", "ch3_delay_km.csv", "ch3_delay_cif.csv"], ["eia860m_2016_01 .. 2022_01", "eia860m_2016_12 .. 2025_12"], "ch3_supply.eia860m_vintage_outcomes, fit_completion_logit, km_delay; run_chapter3 step 3"),
        ("fig3_05", "Capacity, energy and ELCC-derated peak in 2030: existing fleet and three cases", ["ch3_cases_2030.csv", "ch3_cases_2030_summary.json", "ch3_planned_current_weighted.csv", "ch3_existing_capacity_2025.csv", "ch3_capacity_factors.csv", "ch3_elcc_values.csv"], ["eia860m_2026_07", "eia860m_2025_12", "cpuc_e3_astrape_incremental_elcc_2023"], "ch3_supply.current_planned, cases_2030, capacity_factors, elcc_table; run_chapter3 step 4"),
        ("fig3_06", "Workshop format: electricity production by technology, 2025 as generated and the three 2030 cases at realised capacity factors", ["ch3_production_projection.csv", "ch3_eia923_generation_by_resource.csv", "ch3_cases_2030.csv", "ch1_ciso_annual_summary.csv"], ["eia923_2010 .. 2025", "eia860m_2026_07", "cpuc_e3_astrape_incremental_elcc_2023", "eia930_balance_2019_jan_jun .. 2025_jul_dec"], "run_chapter3 step 5 (groups the chapter 3 case table and the EIA-923 2025 generation)"),
    ],
    4: [
        ("fig4_01", "Data center demand in 2030 under each counting rule; statewide peak by IEPR case against ELCC supply", ["ch4_demand_cases_2030.csv", "ch4_demand_totals_2030.csv", "ch4_cec_replication.csv", "ch4_cec_ramp_profile.csv", "ch4_ca_tiers.csv", "ch4_iepr_growth_summary.csv", "ch4_ercot_chain.csv", "ch3_cases_2030_summary.json"], ["cec_assembly_hearing_2026_01_28", "cec_dc_methodology_memo_2026", "cec_tn268722 .. 268727 (CED 2025 forms)", "cec_tn268124", "cec_tn268824", "ERCOT decks and monthlies (see fig4_05)", "pjm_lar_summary_2025_11_24"], "ch4_gap.ca_tiers, cec_parameters, cec_forecast_replication, ced2025_scenarios, iepr_growth_cases, ercot_chain, demand_cases_2030, demand_totals_2030; run_chapter4 steps 1-3"),
        ("fig4_02", "Monte Carlo distributions of the 2030 energy and net-peak gap, by IEPR case; upper bound", ["ch4_mc_draws.parquet", "ch4_mc_summary.csv", "ch4_upper_bound_2030.csv", "ch4_mc_inputs.csv", "ch4_mc_key_numbers.json"], ["chapter 3 outputs (eia860m_2026_07, eia860m_2025_12, cpuc_e3_astrape_incremental_elcc_2023, eia923, cec_elec_energy_generation_page)", "CED 2025 forms as above"], "ch4_gap.SupplyModel, mc_inputs, monte_carlo, evaluate_gap, summarize, upper_bound_rows; run_chapter4 step 4"),
        ("fig4_03", "One-at-a-time tornado and Sobol indices for both gaps", ["ch4_tornado.csv", "ch4_sobol.csv", "ch4_mc_draws.parquet"], ["as fig4_02"], "ch4_gap.tornado, sobol_indices (SALib); run_chapter4 step 5"),
        ("fig4_04", "Curtailment-enabled headroom on CAISO hourly demand; hours curtailed; headroom against the cases and the gap", ["ch4_headroom_curve.csv", "ch4_headroom_summary.csv", "ch4_headroom_detail.csv", "ch4_headroom_by_year.csv", "ch4_headroom_vs_gap.csv", "ch4_energy_side.csv", "ciso_hourly_2019_2025_clean.parquet"], ["eia930_balance_2019 .. 2025 (CISO adjusted demand)", "duke_rethinking_load_growth_2025_mirror (method, CAISO values)", "caiso_oasis dam_lmp", "caiso_curtailments_monthly_csv"], "ch4_gap.headroom, headroom_by_year; run_chapter4 step 6"),
        ("fig4_05", "ERCOT tracked requests by month, approvals and observed load, queue by status at each snapshot", ["ch4_ercot_queue_monthly.csv", "ch4_ercot_approvals_monthly.csv", "ch4_ercot_status_snapshots.csv", "ch4_ercot_narrative.csv", "ch4_ercot_transition_rates.csv"], ["ercot_board_2025_12_system_planning", "ercot_tac_2026_03_large_load_status", "ercot_monthly_2025_07 .. 2026_06", "ercot_house_hearing_2026_04_09", "ercot_board_2026_05_interconnection_update", "ercot_ops_overview_2026_04 .. 2026_08"], "ch4_gap.ercot_series, ercot_transition_rates; run_chapter4 steps 2 and 7"),
        ("fig4_06", "CAISO hourly intensity 2025 and emissions of a flat, curtailed or shifted 1 MW load", ["ch4_emissions_flat_vs_flexible.csv", "caiso_co2_intensity_hourly.parquet"], ["caiso_outlook co2 and demand daily files"], "ch4_gap.flat_vs_flexible_emissions; run_chapter4 step 8"),
        ("fig4_07", "Scored crosswalk of the six regimes (0-3 per criterion)", ["ch4_regime_scores.csv", "ch4_regime_rubric.csv", "ch4_regime_crosswalk.csv"], ["the regime sources of Table ch4_crosswalk (CEC, ERCOT, PJM, EIA, Texas SB 6, FERC RM26-4 filings)"], "ch4_regimes.regime_scores, crosswalk_matrix; run_chapter4 step 7"),
        ("fig4_08", "Data centers as a share of California's electricity: history (EPRI 2023, CEC ~1,000 MW converted), CED 2025 Planning and Local Reliability trajectories with the existing range, and the 2030 upper bounds", ["ch4_dc_share_trajectory.csv", "ch1_dc_load_estimates.csv", "ch4_ced2025_data_center_energy.csv", "ch4_ced2025_scenarios.csv", "ch4_demand_cases_2030.csv"], ["epri_powering_intelligence_2024", "cec_dc_methodology_memo_2026", "eia861_2019 .. 2024", "cec_tn268727", "cec_tn268725", "cec_tn268824", "cec_tn268124", "cec_assembly_hearing_2026_01_28"], "run_chapter4 step 9"),
    ],
}


def row(fig_name: str):
    for ch, rows in ROWS.items():
        for r in rows:
            if fig_name.startswith(r[0]):
                return ch, r
    raise KeyError(fig_name)


def source_line(fig_name: str) -> str:
    """One line: figure id, processed files, manifest ids, code, freeze date."""
    _, (fig, what, files, raws, code) = row(fig_name)
    return f"{fig}. Data: {'; '.join(files)}. Sources (manifest ids): {'; '.join(raws)}. Code: {code}. Data frozen {FREEZE_DATE}; data/raw/manifest.csv holds URL, access date and SHA-256 for each id."


def stamp(fig, fig_name: str, fontsize: float = 5.8) -> None:
    """Write the source line under everything already drawn on the figure (below any legend placed under the axes)."""
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    w_in, h_in = fig.get_figwidth(), fig.get_figheight()
    width_chars = max(90, int(bb.width * 24))
    txt = textwrap.fill(source_line(fig_name), width=width_chars)
    fig.text(bb.x0 / w_in, bb.y0 / h_in - 0.012, txt, ha="left", va="top", fontsize=fontsize, color="0.3", linespacing=1.25)


# ---------------------------------------------------------------- resolving the raw-source labels of ROWS to manifest ids
_CED_FORMS = ["cec_tn268722", "cec_tn268725", "cec_tn268726", "cec_tn268727"]
_REGIME_SOURCES = ["cec_dc_methodology_memo_2026", "cec_tn272026", "cec_assembly_hearing_2026_01_28", "cec_tn268459", "ercot_tac_2026_03_large_load_status", "ercot_monthly_2025_11",
                   "ercot_ops_overview_2026_06", "ercot_house_hearing_2026_04_09", "ercot_nprr1267_status_report_proposal", "pjm_lar_summary_2025_11_24", "pjm_2026_load_forecast_report",
                   "pjm_2026_load_report_tables", "eia_press585_dc_pilot_surveys", "texas_sb6_2025_enrolled", "caiso_comments_ferc_rm26_4_2025_11", "nerc_rm26_4_accelerated_plan_2026_03",
                   "ferc_news_2026_04_16_large_load", "ferc_news_2026_06_18_show_cause"]
_EIA930 = r"^eia930_balance_20(19|2[0-5])_(jan_jun|jul_dec)$"
# label as written in ROWS -> regex patterns (start with ^) or exact ids; "@figX" means the labels of another figure
RAW_LABEL_IDS = {
    "eia930_balance_2019_jan_jun .. 2025_jul_dec": [_EIA930], "eia930 balance files": [_EIA930], "eia930_balance_2019 .. 2025 (CISO adjusted demand)": [_EIA930], "ch1 EIA-930 imports": [_EIA930],
    "caiso_outlook demand and fuelsource (fills, artifact filter)": ["caiso_outlook_demand", "caiso_outlook_fuelsource"], "caiso_outlook fuelsource (Batteries)": ["caiso_outlook_fuelsource"],
    "caiso_outlook co2 and demand daily files": ["caiso_outlook_co2", "caiso_outlook_demand"],
    "eia930_balance_2026_jan_jun .. 2026_jul_dec": [r"^eia930_balance_2026_(jan_jun|jul_dec)$"], "eia930_balance_2025_jan_jun .. 2026_jul_dec (net check)": [r"^eia930_balance_202[56]_(jan_jun|jul_dec)$"],
    "eia930_interchange_2025_jan_jun .. 2026_jul_dec": [r"^eia930_interchange_202[56]_(jan_jun|jul_dec)$"],
    "caiso_outlook demand and fuelsource 2026 (artifact filter)": ["caiso_outlook_demand", "caiso_outlook_fuelsource"], "caiso_outlook co2, demand and fuelsource 2026 daily files": ["caiso_outlook_co2", "caiso_outlook_demand", "caiso_outlook_fuelsource"],
    "caiso_oasis dam_lmp monthly files 2025-01 .. 2026-09": ["caiso_dam_lmp_monthly_dlap", "caiso_dam_lmp_monthly_hubs"],
    "caiso_oasis dam_lmp monthly files (PRC_LMP DAM, DLAP nodes)": ["caiso_dam_lmp_monthly_dlap", "caiso_dam_lmp_monthly_hubs"], "caiso_oasis dam_lmp monthly files": ["caiso_dam_lmp_monthly_dlap", "caiso_dam_lmp_monthly_hubs"], "caiso_oasis dam_lmp": ["caiso_dam_lmp_monthly_dlap", "caiso_dam_lmp_monthly_hubs"],
    "eia861_2019 .. 2024": [r"^eia861_20(19|2[0-4])$"], "svp_fact_sheet_2017 .. 2023": [r"^svp_fact_sheet_20(1[7-9]|2[0-3])$"],
    "eia923_2010 .. 2025": [r"^eia923_20(1\d|2[0-5])$"], "eia860_2010 .. 2025": [r"^eia860_20(1\d|2[0-5])$"],
    "eia860m_2016_01 .. 2022_01": [r"^eia860m_20(1[6-9]|2[0-2])_01$"], "eia860m_2016_12 .. 2025_12": [r"^eia860m_20(1[6-9]|2[0-5])_12$"],
    "qcew_518210_2014q1 .. 2026q1": [r"^qcew_518210_20(1[4-9]|2[0-6])q[1-4]$"], "cbre_*_infogram tables via cbre_california_market_series.csv": [r"^cbre_.*infogram"],
    "cec_tn268722 .. 268727 (CED 2025 forms)": _CED_FORMS, "CED 2025 forms as above": _CED_FORMS + ["cec_tn268124", "cec_tn268824"],
    "chapter 3 outputs (eia860m_2026_07, eia860m_2025_12, cpuc_e3_astrape_incremental_elcc_2023, eia923, cec_elec_energy_generation_page)": ["eia860m_2026_07", "eia860m_2025_12", "cpuc_e3_astrape_incremental_elcc_2023", "cec_elec_energy_generation_page", r"^eia923_20(1\d|2[0-5])$"],
    "as fig4_02": ["@fig4_02"], "ERCOT decks and monthlies (see fig4_05)": ["@fig4_05"],
    "ercot_monthly_2025_07 .. 2026_06": [r"^ercot_monthly_(2025_(0[7-9]|1[0-2])|2026_0[1-6])$"], "ercot_ops_overview_2026_04 .. 2026_08": [r"^ercot_ops_overview_2026_0[4-8]$"],
    "duke_rethinking_load_growth_2025_mirror (method, CAISO values)": ["duke_rethinking_load_growth_2025_mirror"],
    "the regime sources of Table ch4_crosswalk (CEC, ERCOT, PJM, EIA, Texas SB 6, FERC RM26-4 filings)": _REGIME_SOURCES,
}


def resolve_label(label: str, manifest_ids, _depth=0) -> list[str]:
    """Manifest ids behind one raw-source label of ROWS. Exact ids resolve to themselves; the patterns above expand; unknown labels raise."""
    import re
    ids = set(manifest_ids)
    if label in ids:
        return [label]
    if label not in RAW_LABEL_IDS:
        raise KeyError(f"raw-source label not resolvable: {label!r}")
    out = []
    for pat in RAW_LABEL_IDS[label]:
        if pat.startswith("@"):
            if _depth > 2:
                raise RecursionError(label)
            _, r = row(pat[1:]); [out.extend(resolve_label(l, manifest_ids, _depth + 1)) for l in r[3]]
        elif pat.startswith("^"):
            hits = sorted(i for i in ids if re.match(pat, i))
            if not hits:
                raise KeyError(f"pattern {pat!r} of label {label!r} matches no manifest id")
            out.extend(hits)
        elif pat in ids:
            out.append(pat)
        else:
            raise KeyError(f"id {pat!r} of label {label!r} not in the manifest")
    return sorted(dict.fromkeys(out))


def figure_manifest_ids(fig_name: str, manifest_ids) -> list[str]:
    _, r = row(fig_name)
    out = []
    for lab in r[3]:
        out.extend(resolve_label(lab, manifest_ids))
    return sorted(dict.fromkeys(out))
