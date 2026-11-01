# Kathmandu US AQI Project: Decision Log

Status as of 1 November 2026. Workflow agreed: Claude presents scenarios and trade-offs, Aethor decides, and implementation starts only after all decisions are made. **Nothing has been implemented yet.**

---

## 0. Where the project stands

### Files
| File | What it is |
|---|---|
| `kathmandu_final.csv` | Full dataset: 36,427 hourly rows, 24 columns, 2022-08-05 05:00 to 2026-09-30 23:00 |
| `kathmandu_weather.csv` | Weather-only subset saved by the notebook (15 columns, includes `time`, `hour`, `month`, target `us_aqi`) |
| `column_dtype_missing_unique_value.csv` | Per-column dtype, missing count, unique count |
| `data_exploration.ipynb` | Exploration notebook |

### What the notebook has done
1. Loaded the data. Checked shape, dtypes, `describe()`, missing values (none) and duplicate timestamps (none).
2. Converted `time` to datetime and added `hour` and `month`.
3. Explored `us_aqi`: histogram, hourly mean, monthly mean, AQI category counts. Almost all hours are Moderate (51–100) or Unhealthy for Sensitive Groups (101–150). Very few are Good.
4. Ran correlations with `us_aqi`. Strongest: `pm2_5` 0.73, `pm10` 0.72, `sulphur_dioxide` 0.57. Strongest weather link: `dew_point_2m` −0.54.
5. Selected weather and time features and saved `kathmandu_weather.csv`. All pollutant columns were dropped.

### Data facts checked during this session
- No gaps: 36,427 rows equals the number of hours in the date range.
- `rain` equals `precipitation` on every row.
- `us_aqi` autocorrelation: lag 1 is 0.997, lag 24 is 0.90 (very sticky hour to hour).
- Mean `us_aqi` by year: 2023 about 91, 2024 about 99, 2025 about 116, 2026 (to Sep) about 114. Later years are dirtier.

### Notebook issues spotted (not yet fixed)
- `plt` is used in cell 20 but imported in cell 21 (works only because of execution order).
- `df.corr()` was run with `time` as a column, giving a meaningless 0.17 for `time`. The correlation was run on a different dataframe state than the one that was saved.
- `rain` and `precipitation` are both kept in the saved file (addressed by Decision 3).
- The variable `coumn_info` is misspelled (harmless).

---

## 1. The lecturer's question and the formula

**Question from the lecturer:** why were certain columns chosen, and why were others excluded?

**Aethor's reasoning:** the pollutant columns (CO and others) have a formula relationship with the US AQI, so they should not be used to predict it. Aethor wanted to prove this.

### The US AQI formula
Step 1, a sub-score for each pollutant, by linear interpolation inside a breakpoint range:

```
sub_AQI = (I_high − I_low) / (C_high − C_low) × (C − C_low) + I_low
```

Step 2, the final AQI is the worst sub-score:

```
AQI = max(PM2.5, PM10, CO, NO2, SO2, O3 sub-scores)
```

Analogy used: a school report where the overall grade equals the worst subject. Another analogy used: predicting a cake from its flour and eggs, since the pollutants are the ingredients the AQI is cooked from.

PM2.5 breakpoints used in the check below (pre-2024 EPA table):

| PM2.5 (µg/m³) | AQI range |
|---|---|
| 0 – 12 | 0 – 50 |
| 12.1 – 35.4 | 51 – 100 |
| 35.5 – 55.4 | 101 – 150 |
| 55.5 – 150.4 | 151 – 200 |
| 150.5 – 250.4 | 201 – 300 |
| 250.5 – 500.4 | 301 – 500 |

Worked example (2025-06-11 21:00): 24-hour mean PM2.5 is about 65 µg/m³, which falls in 55.5–150.4, so sub-AQI is about (200 − 151) / (150.4 − 55.5) × (65 − 55.5) + 151 ≈ 164. Actual `us_aqi` for that hour: 169.

### Averaging windows (important detail)
Particulates are averaged over time before scoring, not used as single hourly readings. This is why the raw hourly correlation in the notebook is only about 0.73 even though the true relationship is much tighter.

| Column | Window used in the reconstruction |
|---|---|
| `pm2_5`, `pm10` | past 24 hours |
| `ozone` | past 8 hours |
| `carbon_monoxide` | past 8 hours |
| `nitrogen_dioxide`, `sulphur_dioxide` | single hour |

### Reconstruction results (all 36,427 rows)
| Method | Correlation with `us_aqi` | Mean absolute error | Within ±5 points |
|---|---|---|---|
| PM2.5 and PM10, raw hourly values | 0.75 | 21.8 | 17% |
| PM2.5 and PM10, 24-hour averages | 0.957 | 4.9 | 84% |
| All six pollutants, with windows above | **0.995** | **2.9** | **88%** (96% within ±10) |

**Which pollutant sets the AQI in Kathmandu:** PM2.5 on 88.1% of hours, ozone on 11.8%, none of the others in any meaningful share.

| Sub-score | Mean value | Correlation with `us_aqi` |
|---|---|---|
| PM2.5 | 99.8 | 0.96 |
| PM10 | 41.3 | 0.90 |
| Ozone | 56.1 | 0.43 |
| SO₂ | 3.9 | 0.57 |
| CO | 7.2 | 0.45 |
| NO₂ | 7.3 | 0.18 |

### How the columns fit and don't fit
- **Fit (formula inputs):** `pm2_5`, `pm10`, `carbon_monoxide`, `nitrogen_dioxide`, `sulphur_dioxide`, `ozone`. Using them to predict `us_aqi` is target leakage: the model would recompute the formula instead of learning anything.
- **Nuance for the lecturer:** in Kathmandu, CO, NO₂ and SO₂ are always far below the level where they could set the AQI, so they are formula inputs but almost never matter. A sharper claim is that the AQI here is essentially PM2.5 (plus ozone some of the time).
- **Not formula inputs but still particle-related:** `aerosol_optical_depth` (correlation 0.39) and `dust` (0.29). They are leaky by association, not by formula, so the reason for dropping them should be worded that way.
- **Weather columns:** not in the formula. They act on the ingredients, not the recipe. Correlation of weather with the 24-hour PM2.5 average: dew point −0.51, temperature −0.47, cloud cover −0.33, pressure +0.24, relative humidity −0.17, rain −0.18, shortwave radiation −0.04.
- **Overlapping weather columns:** `apparent_temperature` and `temperature_2m` correlate at 0.97, `dew_point_2m` and `temperature_2m` at 0.67, and `rain` equals `precipitation` exactly.

### Caveats on the reconstruction (be honest about these in the report)
- This was done with approximate EPA breakpoints and approximate unit conversions for gases (µg/m³ to ppm or ppb at about 25 °C). It is a close reconstruction, not an exact copy.
- The pre-2024 PM2.5 breakpoints were used, and they matched well. The May 2024 EPA update was **not** tested, so no claim is made about it.
- Open-Meteo also exposes per-pollutant US AQI variables (`us_aqi_pm2_5`, `us_aqi_pm10`, `us_aqi_ozone`, and so on). Pulling those would let you verify the max rule exactly, without approximating anything. This is an optional upgrade if the lecturer wants a tighter proof.

---

## 2. Decisions

### Decision 1: What is the prediction task? **LOCKED**

**Situation:** the project needed a clear task.

**Options presented:**
- **A.** Predict current AQI from weather only (plus time). Clean, no leakage, easy to justify. Limited accuracy; an explanation model more than a forecast.
- **B.** Forecast future AQI (e.g. 24 hours ahead) from weather plus past AQI as lag columns. More accurate, because AQI is very sticky. A random forest just sees the lag as one more column and can split on it. Risk: the model may mostly copy the previous value, and a lecturer may ask whether it learned anything.
- **C.** Do both and compare.

**Decision:** **A.** Weather columns only (plus time features), no past AQI, no pollutant columns.

**Aethor's reasoning:** creating a past-AQI column seemed like a hassle and "weirdish", not how he anticipated the project working. He did not want to add comparison variants beyond comparing algorithms.

**Claude's reasoning and caveats:**
- "Weather alone" means the whole weather group, not just `weather_code`.
- Weather cannot see the pollution sources (smoke, dust, traffic), so accuracy will be moderate. The best single weather correlation is about −0.54 (dew point). Claude's expectation that weather might explain roughly a third to a half of the variation was a guess, **not a measured result**.
- Framed honestly, the report question becomes "how much of Kathmandu's air quality can weather and time of year explain?"

### Decision 2: How to defend the column choice to the lecturer? **LOCKED**

**Options presented:**
- **A.** Written reasoning only.
- **B.** Written reasoning plus the formula reconstruction (Section 1).
- **C.** B plus an experiment training a model with and without pollutant columns.

**Decision:** **B.** Show the formula, verify it against the data, reason through why the formula-linked columns are excluded, and emphasise time and weather (including rain) as environmental drivers.

**Aethor's reasoning:** the formula reconstruction is the proof he wanted. He did not want to add more comparison experiments to the assignment.

**Claude's note (flagged at the time):** with option B there is no with/without model experiment, so the leakage claim rests on the formula evidence alone. The weather columns are justified by plausibility and correlation, not by an experiment.

### Decision 3: Overlapping weather columns **LOCKED**

**Options presented:**
- **A.** Keep everything.
- **B.** Drop only the exact duplicate.
- **C.** Drop duplicates and near-duplicates, justifying each removal.

**Decision:** **C.** Keep `precipitation`, drop `rain`. Keep `temperature_2m`, drop `apparent_temperature`. Keep `dew_point_2m`.

**Reasoning:**
- *Precipitation vs rain.* Precipitation is the umbrella term for all water falling from the sky (rain, snow, drizzle). Rain is the liquid part. In this data they are identical on every row, so one is redundant. Aethor chose precipitation because it is the more general term.
- *Temperature vs apparent temperature.* Temperature is the thermometer reading. Apparent temperature is the "feels like" number, a formula combining temperature with humidity and wind (and sometimes radiation). They correlate at 0.97, and humidity is already kept as its own column, so apparent temperature adds little. Aethor chose temperature because it is a direct measurement, so the model's reaction to heat can be told apart from its reaction to humidity. Aethor raised the fair counterpoint that apparent temperature includes wind and humidity; Claude's answer was that it is a judgment call either way, and that apparent temperature is itself a derived formula, which is the same flavour of issue as the pollutants but milder.
- *Dew point stays.* It correlates with temperature at only 0.67 and has the strongest weather link to AQI (−0.54).

### Decision 4: Train and test split **LOCKED**

**Options presented:**
- **A.** Random split. Rejected because neighbouring hours are near-copies, which inflates scores.
- **B.** Chronological split.
- **C.** Rolling time-based testing.

**Decision:** chronological split (option B), with a custom cut chosen by Aethor:
- Drop 2022-08-05 to 2022-09-30 (about 1,363 rows, about 4% of the data).
- Data then runs **2022-10-01 to 2026-09-30** as four October-to-September years, each with one full set of seasons.
- **Train:** first three years (Oct 2022 to Sep 2025), about 26,304 rows.
- **Test:** last year (Oct 2025 to Sep 2026), about 8,760 rows.

**Aethor's reasoning:** wanted every season represented and the test year to be complete. He also considered a two-years-train, two-years-test split and weighed it against the three-and-one split. The three-and-one split keeps more training data.

**Numbers behind the choice (mean `us_aqi` by water year):**
| Year block | Rows | Mean AQI |
|---|---|---|
| Oct 2022 – Sep 2023 | 8,760 | 100.2 |
| Oct 2023 – Sep 2024 | 8,784 | 88.2 |
| Oct 2024 – Sep 2025 | 8,760 | 118.3 |
| Oct 2025 – Sep 2026 | 8,760 | 115.3 |

**Caveats to state in the report:**
- The test year is dirtier on average than the training years, which may lower scores. Aethor will mention this in the report.
- A random forest cannot extrapolate beyond the target values it saw in training, so it tends to underpredict when the test period is dirtier than anything it trained on. Since all models are compared on the same test year, this affects comparison fairly, but it is worth a sentence.
- No re-pull from the API is needed: the data already ends on 30 September 2026, so October 2022 to September 2026 is exactly four full years.
- **Idea for later (not now):** extract October 2026 and try the model on that extra unseen month.

### Decision 5: How to encode time **NOT YET CONFIRMED**

**Situation:** the file has `time` (full timestamp), `hour` (0–23) and `month` (1–12).

**Options presented:**
- **A.** Keep hour and month as plain numbers. Simple, but the model sees month 12 and month 1 as 11 steps apart (and hour 23 and hour 0 as 23 steps apart) although they are neighbours.
- **B.** Cyclical (sine and cosine) encoding of hour and month.
- **C.** Plain numbers, with the full timestamp dropped.
- **Sub-choice raised by Aethor:** use day-of-year (1–365) instead of month. This gives smoother seasonal resolution but only about three examples per calendar day in training, so more risk of fitting noise.

**Where the discussion landed:** Aethor leaned toward month and hour with sine and cosine, and asked to see what it looks like. His last message to Claude on this was a request for the summary file, so a final "lock it in" has **not** been given. **Claude's recommendation:** hour and month with sine and cosine, full timestamp dropped.

**Explanations given (for the report):**
- *Why drop the full timestamp.* It holds the exact date and hour (e.g. 5 Oct 2023, 7 pm). The test year consists entirely of dates the model never saw in training, so such a column cannot help on the test year and can only let the model memorise training years. Hour and month already carry the repeating pattern you actually want. The year is dropped for the same reason.
- *Why days don't need their own column.* Month gives the season, and the weather columns (for example precipitation) carry the day-to-day variation. The model learns a general picture such as "a winter evening looks like this", not a separate fact for each calendar day.
- *How a random forest uses time.* Each tree asks threshold questions such as "is the month between 11 and 2, and is the hour after 18?".

**How the encoding looks:**
```
month_sin = sin(2π × month / 12)     month_cos = cos(2π × month / 12)
hour_sin  = sin(2π × hour / 24)      hour_cos  = cos(2π × hour / 24)
```
Clock-face analogy: describe a time with two numbers, how far across and how far up on a circle, so the calendar and the day wrap around.

| Month | month_sin | month_cos |
|---|---|---|
| Jan (1) | 0.50 | 0.87 |
| Mar (3) | 1.00 | 0.00 |
| Jun (6) | 0.00 | −1.00 |
| Sep (9) | −1.00 | 0.00 |
| Oct (10) | −0.87 | 0.50 |
| Nov (11) | −0.50 | 0.87 |
| Dec (12) | 0.00 | 1.00 |

| Hour | hour_sin | hour_cos |
|---|---|---|
| 0 | 0.00 | 1.00 |
| 6 | 1.00 | 0.00 |
| 12 | 0.00 | −1.00 |
| 18 | −1.00 | 0.00 |
| 23 | −0.26 | 0.97 |

Distances on the circle: December to January is 0.52 apart (neighbours), January to July is 2.0 (opposites).

**Trade-off:** you can no longer read a single column and see "winter" or "evening". The sine and cosine pair carries the position together, so feature-importance charts will show them as separate columns that work as a team.

### Decision 6: Model choice **OPEN, NOT YET DISCUSSED**

Known so far: the assignment expects a random forest compared against other algorithms. Options to present when we get there (draft):
- **A.** Linear regression only. Simple, likely underfits.
- **B.** A simple baseline plus tree-based models (random forest, gradient boosting).
- **C.** Add a neural network. Fits an AI specialisation but is heavier and harder to defend on this data size.

Things to decide alongside: evaluation metrics, and whether to report scores by season or by AQI category.

---

## 3. Planned feature set (if Decision 5 is confirmed as recommended)

**Target:** `us_aqi`

**Features:** `temperature_2m`, `dew_point_2m`, `relative_humidity_2m`, `cloud_cover`, `weather_code`, `precipitation`, `surface_pressure`, `shortwave_radiation`, `uv_index`, plus `month_sin`, `month_cos`, `hour_sin`, `hour_cos`.

**Dropped:** all pollutants and particle columns, `rain`, `apparent_temperature`, `time`, and plain `hour` and `month` (replaced by the cyclical pair). Also `wind_speed_10m`, `wind_gusts_10m` and `wind_direction_10m`, which were never in the saved weather file; no decision has been made about wind, and it is worth deciding explicitly.

---

## 4. Open items
1. Confirm Decision 5.
2. Decision 6 (models and metrics).
3. Decide whether wind columns belong in the feature set (they were excluded from the saved weather file without a recorded reason).
4. Optional: pull per-pollutant US AQI variables from Open-Meteo for an exact max-rule proof.
5. Optional later: extract October 2026 as an extra unseen test month.
6. Fix the notebook issues listed in Section 0.
7. Only after all decisions: implement.

---

## 5. Sources

1. US EPA, *Technical Assistance Document for the Reporting of Daily Air Quality – the Air Quality Index (AQI)*, September 2018 (EPA 454/B-18-007), covers the calculation, breakpoints and averaging: https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf
2. AirNow landing page for the current Technical Assistance Document: https://www.airnow.gov/publications/air-quality-index/technical-assistance-document-for-reporting-the-daily-aqi/
3. 40 CFR Appendix G to Part 58, *Uniform Air Quality Index (AQI) and Daily Reporting*: https://www.law.cornell.edu/cfr/text/40/appendix-G_to_part_58
4. AirNow forum, *AQI Calculations Overview: Ozone, PM2.5 and PM10* (24-hour PM average, 8-hour ozone average): https://forum.airnowtech.org/t/aqi-calculations-overview-ozone-pm2-5-and-pm10/168
5. EPA AQS AQI breakpoint table: https://aqs.epa.gov/aqsweb/documents/codetables/aqi_breakpoints.html
6. EPA AirData, *How is the AQI calculated?*: https://19january2025snapshot.epa.gov/outdoor-air-quality-data/how-aqi-calculated
7. Open-Meteo Air Quality API documentation (defines `us_aqi` as the consolidated maximum, plus per-pollutant `us_aqi_*` variables): https://open-meteo.com/en/docs/air-quality-api
8. Secondary source, on the May 2024 PM2.5 breakpoint change (not an EPA page, so verify against source 1 before citing): https://filterbuy.com/resources/air-quality/aqi-education/how-is-the-air-quality-index-calculated

**Source caveat:** sources 1 to 6 are official or EPA-related. Source 7 is the provider documentation for your dataset. The numerical results in Section 1 come from our own reconstruction on `kathmandu_final.csv`, not from any of these sources, and the unit conversions and averaging windows are our approximations.
