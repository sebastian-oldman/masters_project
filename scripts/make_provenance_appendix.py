#!/usr/bin/env python
"""Write report/tables/provenance_ch{1,2,3}.tex: for every figure, the processed files it is drawn from, the raw sources
(manifest ids) behind those files, and the code that produces them. The appendix section report/sections/07_appendix_provenance.tex
inputs these tables. Rows are checked against the file system: every processed file and figure named here must exist."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402

from src.paths import FIGURES, PROCESSED, RAW, ROOT  # noqa: E402

OUT = ROOT / "report" / "tables"
MAN = pd.read_csv(RAW / "manifest.csv").sort_values("access_date").groupby("source_id").tail(1).set_index("source_id")


def esc(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_\allowbreak{}").replace("#", r"\#")


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
    ],
    2: [
        ("fig2_01", "Census data center construction spending with ChatGPT annotation; month-over-month growth; shares of nonresidential construction", ["ch2_census_c30_data_center.csv"], ["census_c30_privsatime", "census_c30_privtime"], "ch2_growth.census_c30; run_chapter2 step 1"),
        ("fig2_02", "Log-linear trends, Chow test, Bai-Perron breaks, segment growth, sequential test; ARIMA and ETS forecasts with bands and backtest", ["ch2_census_break_summary.json", "ch2_census_bai_perron.csv", "ch2_census_segment_growth.csv", "ch2_census_forecast_arima.csv", "ch2_census_forecast_ets.csv", "ch2_census_forecast_backtest.csv"], ["census_c30_privsatime"], "ch2_growth.chow_test, bai_perron, sequential_supF, arima_forecast, ets_forecast, backtest_forecasts; run_chapter2 step 2"),
        ("fig2_03", "California proxies: QCEW employment and establishments, CBRE Silicon Valley construction and inventory, Epoch cumulative power; break-test summary", ["ch2_qcew_518210_california.csv", "ch2_cbre_california.csv", "ch2_epoch_timeline.csv", "ch2_break_test_comparison.csv"], ["qcew_518210_2014q1 .. 2026q1", "cbre_*_infogram tables via cbre_california_market_series.csv", "epoch_data_center_timelines", "epoch_data_centers"], "ch2_growth.qcew_california, cbre_california, epoch_timeline, break_analysis; run_chapter2 step 3"),
        ("fig2_04", "Energization requests by vintage and tier; Nevada separated; SCE cancellations; PG\\&E pipeline; ratios to CAISO record peak and existing load", ["ch2_tier_vintages.csv", "ch2_rq1_denominators.json", "ch1_dc_load_estimates.csv"], ["cec_dc_forecast_2024iepr", "cec_prelim_dc_forecast_2025", "cec_dc_methodology_memo_2026", "cec_assembly_hearing_2026_01_28", "cec_tn266008", "cec_tn268459", "cec_tn272026", "cec_tn272065", "cec_tn272807", "caiso_key_statistics_2026_08"], "ch2_growth.tier_vintages; run_chapter2 steps 4 and 5"),
    ],
    3: [
        ("fig3_01", "In-state generation by resource and CEC net imports 2010-2025; shares", ["ch3_supply_by_year.csv", "ch3_eia923_generation_by_resource.csv", "ch3_cec_generation_multi_year.csv"], ["eia923_2010 .. 2025", "cec_elec_energy_generation_page", "ch1 EIA-930 imports"], "ch3_supply.eia923_ca_generation, cec_multi_year_generation; run_chapter3 step 1"),
        ("fig3_02", "Operable capacity by technology; battery power and energy; CAISO curtailment; July 2026 snapshot", ["ch3_eia860_capacity_by_resource.csv", "ch3_battery_capacity.csv", "ch3_caiso_curtailment_annual.csv", "ch3_capacity_snapshot_2026_07.json"], ["eia860_2010 .. 2025", "eia860m_2026_07", "caiso_curtailments_monthly_csv"], "ch3_supply.eia860_ca_capacity, eia860_ca_battery_energy, caiso_curtailment_annual, eia860m_capacity_snapshot; run_chapter3 step 1"),
        ("fig3_03", "Scheduled retirements: EIA-860M planned dates and once-through-cooling compliance dates", ["ch3_eia860m_planned_retirements.csv", "ch3_otc_units.csv"], ["eia860m_2026_07", "swrcb_otc_policy_2023"], "ch3_supply.retirement_schedule; run_chapter3 step 2"),
        ("fig3_04", "Realization model: outcomes by vintage and technology; logistic model; delay and cumulative-incidence curves", ["ch3_vintage_outcomes.csv", "ch3_realization_by_vintage.csv", "ch3_realization_by_technology.csv", "ch3_logit_coefficients.csv", "ch3_logit_summary.json", "ch3_delay_km.csv", "ch3_delay_cif.csv"], ["eia860m_2016_01 .. 2022_01", "eia860m_2016_12 .. 2025_12"], "ch3_supply.eia860m_vintage_outcomes, fit_completion_logit, km_delay; run_chapter3 step 3"),
        ("fig3_05", "Capacity, energy and ELCC-derated peak in 2030: existing fleet and three cases", ["ch3_cases_2030.csv", "ch3_cases_2030_summary.json", "ch3_planned_current_weighted.csv", "ch3_existing_capacity_2025.csv", "ch3_capacity_factors.csv", "ch3_elcc_values.csv"], ["eia860m_2026_07", "eia860m_2025_12", "cpuc_e3_astrape_incremental_elcc_2023"], "ch3_supply.current_planned, cases_2030, capacity_factors, elcc_table; run_chapter3 step 4"),
    ],
    4: [
        ("fig4_01", "Data center demand in 2030 under each counting rule; statewide peak by IEPR case against ELCC supply", ["ch4_demand_cases_2030.csv", "ch4_demand_totals_2030.csv", "ch4_cec_replication.csv", "ch4_cec_ramp_profile.csv", "ch4_ca_tiers.csv", "ch4_iepr_growth_summary.csv", "ch4_ercot_chain.csv", "ch3_cases_2030_summary.json"], ["cec_assembly_hearing_2026_01_28", "cec_dc_methodology_memo_2026", "cec_tn268722 .. 268727 (CED 2025 forms)", "cec_tn268124", "cec_tn268824", "ERCOT decks and monthlies (see fig4_05)", "pjm_lar_summary_2025_11_24"], "ch4_gap.ca_tiers, cec_parameters, cec_forecast_replication, ced2025_scenarios, iepr_growth_cases, ercot_chain, demand_cases_2030, demand_totals_2030; run_chapter4 steps 1-3"),
        ("fig4_02", "Monte Carlo distributions of the 2030 energy and net-peak gap, by IEPR case; upper bound", ["ch4_mc_draws.parquet", "ch4_mc_summary.csv", "ch4_upper_bound_2030.csv", "ch4_mc_inputs.csv", "ch4_mc_key_numbers.json"], ["chapter 3 outputs (eia860m_2026_07, eia860m_2025_12, cpuc_e3_astrape_incremental_elcc_2023, eia923, cec_elec_energy_generation_page)", "CED 2025 forms as above"], "ch4_gap.SupplyModel, mc_inputs, monte_carlo, evaluate_gap, summarize, upper_bound_rows; run_chapter4 step 4"),
        ("fig4_03", "One-at-a-time tornado and Sobol indices for both gaps", ["ch4_tornado.csv", "ch4_sobol.csv", "ch4_mc_draws.parquet"], ["as fig4_02"], "ch4_gap.tornado, sobol_indices (SALib); run_chapter4 step 5"),
        ("fig4_04", "Curtailment-enabled headroom on CAISO hourly demand; hours curtailed; headroom against the cases and the gap", ["ch4_headroom_curve.csv", "ch4_headroom_summary.csv", "ch4_headroom_detail.csv", "ch4_headroom_by_year.csv", "ch4_headroom_vs_gap.csv", "ch4_energy_side.csv", "ciso_hourly_2019_2025_clean.parquet"], ["eia930_balance_2019 .. 2025 (CISO adjusted demand)", "duke_rethinking_load_growth_2025_mirror (method, CAISO values)", "caiso_oasis dam_lmp", "caiso_curtailments_monthly_csv"], "ch4_gap.headroom, headroom_by_year; run_chapter4 step 6"),
        ("fig4_05", "ERCOT tracked requests by month, approvals and observed load, queue by status at each snapshot", ["ch4_ercot_queue_monthly.csv", "ch4_ercot_approvals_monthly.csv", "ch4_ercot_status_snapshots.csv", "ch4_ercot_narrative.csv", "ch4_ercot_transition_rates.csv"], ["ercot_board_2025_12_system_planning", "ercot_tac_2026_03_large_load_status", "ercot_monthly_2025_07 .. 2026_06", "ercot_house_hearing_2026_04_09", "ercot_board_2026_05_interconnection_update", "ercot_ops_overview_2026_04 .. 2026_08"], "ch4_gap.ercot_series, ercot_transition_rates; run_chapter4 steps 2 and 7"),
        ("fig4_06", "CAISO hourly intensity 2025 and emissions of a flat, curtailed or shifted 1 MW load", ["ch4_emissions_flat_vs_flexible.csv", "caiso_co2_intensity_hourly.parquet"], ["caiso_outlook co2 and demand daily files"], "ch4_gap.flat_vs_flexible_emissions; run_chapter4 step 8"),
        ("fig4_07", "Scored crosswalk of the six regimes (0-3 per criterion)", ["ch4_regime_scores.csv", "ch4_regime_rubric.csv", "ch4_regime_crosswalk.csv"], ["the regime sources of Table ch4_crosswalk (CEC, ERCOT, PJM, EIA, Texas SB 6, FERC RM26-4 filings)"], "ch4_regimes.regime_scores, crosswalk_matrix; run_chapter4 step 7"),
    ],
}


def main() -> int:
    problems = []
    for ch, rows in ROWS.items():
        lines = [r"\begin{tabular}{lp{4.6cm}p{5.2cm}p{4.6cm}p{4.8cm}}", r"\toprule", r"Figure & Content & Processed files (data/processed) & Raw sources (manifest ids) & Code \\", r"\midrule"]
        for fig, what, files, raws, code in rows:
            if not list(FIGURES.glob(f"{fig}_*.png")):
                problems.append(f"missing figure {fig}")
            for f in files:
                if not (PROCESSED / f).exists():
                    problems.append(f"missing processed file {f}")
            lines.append(f"{esc(fig)} & {esc(what)} & " + esc("; ".join(files)) + " & " + esc("; ".join(raws)) + " & " + esc(code) + r" \\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        (OUT / f"provenance_ch{ch}.tex").write_text("\n".join(lines)); print("  table", f"provenance_ch{ch}")
    if problems:
        print("PROBLEMS:", problems); return 1
    print("all referenced figures and processed files exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
