# Kathmandu US AQI: Decision Reasons and Pipeline Status

Status as of 1 November 2026. Nothing has been implemented yet. This file holds the reasons behind each decision (for the report and the viva) and the full pipeline with current status.

---

## Part 1: Reasons behind each decision

### D1. Prediction task: weather and time only (LOCKED)
- **Decision:** predict current `us_aqi` from weather and time features. No pollutant columns, no past AQI (lags).
- **Why:** US AQI is calculated from the pollutants (the worst sub-score of PM2.5, PM10, CO, NO2, SO2, O3). Using them as inputs would only make the model recompute a formula. Past AQI is dropped because AQI is extremely sticky (lag 1 = 0.997), so the model would mostly copy the previous hour and learn little about weather.
- **Report question it creates:** "How much of Kathmandu's air quality can weather and time of year explain?"
- **Caveat to state:** weather cannot see pollution sources (smoke, dust, traffic), so accuracy will be moderate.

### D2. Defending the column choice: formula reconstruction (LOCKED)
- **Decision:** show the AQI formula and verify it on the data, rather than running a with/without-pollutants model experiment.
- **Evidence:** all six pollutants with the correct averaging windows reproduce `us_aqi` at correlation 0.995, mean absolute error 2.9. PM2.5 sets the AQI on 88.1% of hours, ozone on 11.8%.
- **Why this option:** it is the proof Aethor wanted, and it avoids extra comparison experiments.
- **Caveat to state:** the claim rests on the formula evidence alone. Approximate EPA breakpoints and gas unit conversions were used, the May 2024 EPA update was not tested, and the weather columns are justified by plausibility and correlation, not by an experiment.
- **Wording for `aerosol_optical_depth` and `dust`:** not in the formula, but dropped because they are particle-related (leaky by association).

### D3. Overlapping weather columns (LOCKED, extended on 1 Nov)
| Column | Decision | Reason |
|---|---|---|
| `rain` | Drop | Identical to `precipitation` on every row. |
| `precipitation` | Keep | More general term (rain, snow, drizzle). |
| `apparent_temperature` | Drop | Correlates 0.97 with temperature. It is a derived "feels like" formula, so it adds little beyond temperature and humidity. A direct measurement keeps the model's response to heat separable from humidity. |
| `relative_humidity_2m` | Drop | Dew point is calculated from temperature and humidity, so it already carries the moisture information. Humidity is relative to temperature, dew point is an absolute moisture measure. |
| `dew_point_2m` | Keep | Strongest weather link to AQI (-0.54). |
| `temperature_2m` | Keep | Dew point is moisture plus some temperature information (they correlate only 0.67), so temperature still adds the cold/warm signal on its own, which is tied to winter cold and trapped air. It also allows a later "temperature minus dew point" feature if wanted. |

- **Honest caveat on dew point:** part of its -0.54 is probably because it marks the monsoon (humid air means monsoon, which means rain, which means clean air). Month already carries the season, so dew point and month may overlap more than the correlation suggests.
- **Wording for the report:** do not say "dew point comes from temperature". Say dew point is derived from temperature and humidity, and that temperature is kept for the cold signal it carries separately.

### D4. Train/test split: chronological (LOCKED)
- **Decision:** drop 2022-08-05 to 2022-09-30 (about 1,363 rows). Use Oct 2022 to Sep 2026 as four October-to-September years. Train on the first three (about 26,304 rows), test on the last (about 8,760 rows).
- **Why not random:** neighbouring hours are near-copies, so a random split inflates scores.
- **Why this cut:** every season appears in train and the test year is complete. Three-and-one keeps more training data than two-and-two.
- **Caveats to state:** the test year (mean AQI about 115) is dirtier than the first two training years (100 and 88), so scores may drop. Random forests cannot extrapolate beyond target values seen in training, so they tend to underpredict a dirtier test period. All models share the same test year, so the comparison stays fair.

### D5. Time encoding: sine and cosine (leaning confirmed 1 Nov)
- **Decision:** `hour` and `month` as sine/cosine pairs. Drop `time`, plain `hour` and plain `month`.
- **Why cyclical:** December and January are neighbours, and so are hour 23 and hour 0, but plain numbers put them far apart. The sin/cos pair places time on a circle so the calendar and the day wrap around.
- **Why drop the full timestamp and the year:** the test year consists of dates the model never saw, so a timestamp column can only help it memorise the training years. Month and hour carry the repeating pattern.
- **Trade-off:** you can no longer read one column as "winter" or "evening". The sin/cos pair works as a team, so feature-importance charts show them as separate columns.
- **Rejected for now:** day-of-year (smoother seasons, but only about three examples per calendar day in training, so more noise-fitting risk).

### D6. Wind columns: dropped (decided 1 Nov)
- **Decision:** drop `wind_speed_10m`, `wind_gusts_10m`, `wind_direction_10m`.
- **Aethor's reasoning:** Kathmandu is a valley, and wind was not expected to change pollution much.
- **Evidence-based reason to use in the report:** weak correlations with AQI (0.10, 0.09, 0.06).
- **Counterpoint to be ready for in the viva:** a valley traps pollution when wind is weak, so a lecturer could argue wind matters. A possible explanation (a guess, not checked) is that Open-Meteo is gridded model data and may not represent valley-floor wind well. So word the reason as "weak correlation in the data", not "it's a valley".

### D7. UV index: dropped (decided 1 Nov)
- Mostly "is it daytime and is it cloudy". The hour encoding carries daytime and cloud cover carries cloudiness. Correlation with AQI is -0.08.
- `shortwave_radiation` (-0.03) is the same idea. **Not explicitly confirmed yet**, assumed dropped. Confirm.

### D8. Weather code: dropped (decided 1 Nov)
- It is built from cloud cover and precipitation (clear, cloudy, drizzle, rain, thunderstorm), so it is not an independent signal.
- It is a category stored as a number (61 is not "bigger" than 3), which suits tree models poorly without extra encoding.
- Correlation is -0.32, so it is not useless, but its information is already kept through cloud cover and precipitation.
- Only extra it might hold is fog (codes 45 and 48). Not checked whether fog appears in the data.

### D9. Cloud cover: kept (decided 1 Nov)
- Direct measurement, not derived from the other columns. Correlation -0.37.
- Hypothesis (not proven): more cloud makes rain more likely, which makes the air cleaner. Word it as a hypothesis in the report.

---

## Part 2: The locked feature set (pending the shortwave confirmation)

**Target:** `us_aqi`

**Inputs (8):**
- `temperature_2m`
- `dew_point_2m`
- `cloud_cover`
- `precipitation`
- `month_sin`, `month_cos`
- `hour_sin`, `hour_cos`

**Dropped, with reason:**
| Column(s) | Reason |
|---|---|
| All pollutants, `aerosol_optical_depth`, `dust` | Formula inputs or particle-related (leakage) |
| `rain` | Identical to precipitation |
| `apparent_temperature` | Derived, 0.97 with temperature |
| `relative_humidity_2m` | Covered by dew point |
| `weather_code` | Derived from cloud cover and precipitation, category-as-number |
| `uv_index`, `shortwave_radiation` | Daytime and cloud already captured, weak correlation |
| Wind (3 columns) | Weak correlation |
| `time`, plain `hour`, plain `month` | Replaced by cyclical pairs, no timestamp memorisation |

---

## Part 3: The full ML pipeline and status

| # | Step | Question it answers | Status |
|---|---|---|---|
| 1 | Define the problem | What are we predicting, for whom? | Done (D1). Track 10, Air Quality Monitoring. |
| 2 | Collect the data | Where did the numbers come from? | Done. Open-Meteo, Kathmandu, 36,427 hourly rows. |
| 3 | Understand the data | What does each column mean, is anything broken? | Mostly done. Paper notes table not confirmed. |
| 4 | EDA | What patterns exist? | Done. Hourly, monthly, AQI bands, correlations. |
| 5 | Lock the framing | Which inputs are honest? | Done (D1, D2). |
| 6 | Cleaning | Can I trust the data? | Half done. Duplicates and gaps checked. Impossible values and outliers still to write up. Plan: keep pollution spikes because they are real days. |
| 7 | Feature selection | Which columns go in? | Decided (D3, D6, D7, D8, D9). Only shortwave radiation to confirm. |
| 8 | Feature engineering | Can I build better inputs? | Design decided (D5). Not built. Optional: temperature minus dew point. |
| 9 | Train/test split | How do I test honestly? | Decided (D4). Not built. |
| 10 | Scaling | Do models need inputs on one scale? | OPEN. Trees do not need it, other group models may. If used, fit on train only. |
| 11 | Model selection | Which algorithms, and why? | OPEN (Decision 6 in the old log). |
| 12 | Training | Fit the models. | Not started. |
| 13 | Hyperparameter tuning | What settings work best? | Not started. Use time-ordered validation inside the training years, not random shuffling. |
| 14 | Evaluation | How good is it, really? | Not started. Metrics to choose (MAE, RMSE, R2), scores by season and AQI band. |
| 15 | Interpretation and critical analysis | What did it learn, where does it fail? | Not started. |
| 16 | Deployment / export | How would it be used? | Not started. |
| 17 | Report, evidence, presentation, viva | The actual marks | Not started. Draft sentences exist from Log 2. |

---

## Part 4: Open items

1. Confirm `shortwave_radiation` is dropped.
2. Scaling: yes or no, and what the group needs.
3. Model choice: baseline plus which models. A simple baseline such as "average AQI for that month" shows whether weather adds anything beyond season.
4. Isolation Forest: it is for anomaly detection, not regression, so decide its role or let the group's unsupervised model cover it.
5. Metrics and breakdowns (by season, by AQI band).
6. Tuning method (time-ordered validation).
7. Group alignment: all 5 group models must use the same dataset and the same split. Check this matches what teammates are doing.
8. Optional: random forest feature importance on the training years as evidence for the column choices (not run).
9. Optional: pull per-pollutant US AQI variables from Open-Meteo for an exact max-rule proof.
10. Optional later: test on October 2026 as an extra unseen month.
11. Clean up the notebook issues listed in the old decision log.

## Deadlines (from the assignment paper)
- Meeting logs and individual evidence: 16 Nov 2026
- Report, presentation, viva: 17 or 18 Nov 2026 (the paper shows both dates, confirm with the lecturer)
