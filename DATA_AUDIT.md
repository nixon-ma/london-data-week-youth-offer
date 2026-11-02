# London Data Week 2026 — Youth Offer for London
## Data Audit and Evidence Log

**Status:** D9c development model-comparison metrics implemented and QA-verified; 2022/23 predictive evaluation remains locked
**Purpose:** Preserve the factual findings, checks, examples, anomalies, and rationale that support project decisions.
**Relationship to `DECISIONS.md`:** `DECISIONS.md` records accepted decisions; this file records the evidence behind them and unresolved findings still under investigation.

---

# 1. Source material

## 1.1 Organiser problem statement

> **How might we tailor the Youth Offer for London to help the most young people into work or training?**

The supplied starting point is the Department for Education **Key stage 4 leavers destinations** dataset. The organiser material suggests supervised learning and data cleaning but does not prescribe a particular model or prediction target.

## 1.2 Organiser methodology framing

The introduction deck emphasises explaining and evaluating analytical decisions, methodology and engagement with the issue, and accelerating decisions without compromising the analysis. This supports a workflow in which the problem, data-generating structure, outcome and validation design are understood before model selection.

## 1.3 Raw dataset supplied

- Archive: `key-stage-4-destination-measures_2023-24.zip`
- Data file: `data/ees_ks4_202223_api.csv`
- Guidance file: `data-guidance/data-guidance.txt`
- Raw CSV size: **1,871,739 rows × 35 columns**

The file exceeds Excel's worksheet limit of 1,048,576 rows, so Excel cannot be relied on to display the full raw dataset. Programmatic inspection is required.

---

# 2. Raw-data structure

## 2.1 Geographic levels

The raw file contains:

- Local authority
- Local authority district
- National
- Parliamentary constituency
- Regional
- School

**Finding relevant to D1:** Local Authority is the most useful available borough-level geography for the Youth Offer question.

**Interpretive limitation:** Local Authority should be interpreted according to the administrative LA associated with the pupil's school/institution rather than automatically as pupil residence. Borough results therefore should not be described as outcomes for all young people living in that borough.

## 2.2 Time coverage

The raw file spans coded cohorts **200910–202223**.

Local Authority rows are present for:

`201617, 201718, 201819, 201920, 202021, 202122, 202223`

For the chosen primary population, the London headline panel contains exactly **32 LAs in every one of the seven cohorts**.

| Cohort | Primary London LAs |
|---|---:|
| 2016/17 | 32 |
| 2017/18 | 32 |
| 2018/19 | 32 |
| 2019/20 | 32 |
| 2020/21 | 32 |
| 2021/22 | 32 |
| 2022/23 | 32 |

**Finding relevant to D2:** 2016/17–2022/23 is the complete borough-level period available for the chosen primary population in the supplied file.

D5 subsequently confirmed that the target destination categories and five main subgroup families are structurally available throughout this period; see §12.8.

---

# 3. What one row represents

A row is **not one pupil**. It is an aggregated statistical cell defined by dimensions including cohort/year, geography, establishment population, pupil-characteristic slice and destination measure.

> **Conceptual grain:** cohort × geography × establishment population × pupil-characteristic slice × destination measure

The same underlying pupil cohort therefore appears repeatedly through different subgroup views and destination measures. Rows cannot be treated as independent individual-level observations, and overlapping subgroup rows must not be summed across characteristic families.

D5 confirmed that these repeated views are structured slices rather than duplicate records; see §12.1.

---

# 4. Pupil-characteristic structure

| Conceptual family | Raw field(s) carrying subgroup value |
|---|---|
| Sex | `sex` |
| Major ethnicity | `ethnicity_major` |
| Disadvantage | `disadvantage_status` |
| FSM status | `breakdown_topic == "FSM status"` and `breakdown` |
| SEN provision | `breakdown_topic == "SEN provision"` and `breakdown` |

Observed non-total values in the primary London LA population are stable over the chosen period:

- **Sex:** Female, Male
- **Major ethnicity:** Asian / Asian British, Black / African / Caribbean / Black British, Mixed / Multiple ethnic groups, Other ethnic group, Unknown, White
- **Disadvantage:** Disadvantaged, Not known to be disadvantaged
- **FSM status:** FSM eligible, Not known to be FSM eligible
- **SEN provision:** Identified SEN, No identified SEN, SEN support, SEN with EHC plan or statement

Fine-grained `ethnicity_minor` categories are not populated as non-total categories at this LA resolution.

The maximum number of characteristic families varying simultaneously in the primary LA rows is **1**.

**Finding:** subgroup rows are essentially one-dimensional slices rather than intersectional combinations such as Black + female + FSM.

**Limitation:** the dataset does not support intersectional subgroup analysis at this geography.

---

# 5. Establishment populations and D3 evidence

## 5.1 2022/23 London cohort totals by establishment population

These are **derived London totals** obtained by summing LA-level `cohort_count` after fixing pupil-characteristic fields to `Total` and selecting one headline destination measure so that each borough/population is counted once.

| Establishment population | London cohort |
|---|---:|
| State-funded mainstream and special | 89,811 |
| State-funded mainstream schools | 87,852 |
| State-funded (inc. non-maintained) special | 1,959 |
| Alternative provision | 1,735 |

The combined `State-funded mainstream and special` population equals the mainstream population plus the standalone special-school population at the London aggregate level for 2022/23.

D5 confirmed that this is not merely a London-wide coincidence: the count relationship holds exactly at borough/year/destination level throughout 2016/17–2022/23; see §12.3.

## 5.2 Subgroup availability by establishment population

| Establishment population | Sex | Major ethnicity | Disadvantage | FSM / SEN breakdowns |
|---|---|---|---|---|
| Alternative provision | No | No | No | No |
| State-funded (inc. non-maintained) special | No | No | No | No |
| State-funded mainstream and special | Yes | Yes | Yes | Yes |
| State-funded mainstream schools | Yes | Yes | Yes | Yes |

**Finding relevant to D3:** the combined mainstream + special population retains the borough-level subgroup breakdowns needed for the primary analysis. Standalone special-school and alternative-provision populations do not provide equivalent subgroup detail.

## 5.3 Composition effect from special schools

The combined borough outcome is a weighted average of mainstream and special-school outcomes. A borough can therefore have a higher combined adverse rate because of worse mainstream outcomes, worse special-school outcomes, a larger special-school share, or a combination.

Illustrative 2022/23 boroughs with relatively large upward effects on the combined adverse rate:

| Borough | Mainstream adverse rate | Special-school adverse rate | Special share | Combined adverse rate | Combined − mainstream |
|---|---:|---:|---:|---:|---:|
| Hammersmith and Fulham | 6.99% | 16.47% | 5.56% | 7.52% | 0.53 pp |
| Camden | 8.08% | 26.67% | 1.87% | 8.43% | 0.35 pp |
| Merton | 6.61% | 17.02% | 2.75% | 6.90% | 0.29 pp |
| Sutton | 3.31% | 14.10% | 2.38% | 3.57% | 0.26 pp |
| Waltham Forest | 6.81% | 15.07% | 2.60% | 7.02% | 0.21 pp |

**Finding relevant to D3:** separate mainstream and special-school headline analysis is useful as a composition diagnostic even though subgroup analysis within standalone special schools is unavailable.

**Decision supported:** primary population = `State-funded mainstream and special`; analyse mainstream and special separately at borough/year aggregate level; keep alternative provision as a separate secondary population.

---

# 6. Destination outcomes and D4 evidence

## 6.1 Destination measures available at Local Authority level

- Activity not captured
- Advanced and Higher apprenticeships (level 3 and above)
- Further education
- Intermediate apprenticeships (level 2)
- Not recorded as a sustained destination
- Other education destination
- School sixth form
- Sixth form college
- Sustained apprenticeships
- Sustained education destination
- Sustained education, employment & apprenticeships
- Sustained employment destination

## 6.2 Headline accounting identity

For the primary population, the following count identity was checked over **224 London borough-year observations**:

> **KS4 cohort = Sustained education, employment & apprenticeships + Not recorded as a sustained destination + Activity not captured**

Exact count identity held for every checked borough-year observation: **Yes**.

This supports the derived adverse outcome:

> **Outside recorded sustained destinations = Not recorded as a sustained destination + Activity not captured**

and equivalently:

> **Outside recorded sustained destinations = KS4 cohort − Sustained education, employment & apprenticeships**

## 6.3 Camden 2022/23 headline example

| Measure | Count | Percent |
|---|---:|---:|
| Sustained education, employment & apprenticeships | 1,466 | 91.6% |
| Not recorded as a sustained destination | 78 | 4.9% |
| Activity not captured | 57 | 3.6% |
| Cohort | 1,601 | — |

The pupil counts reconcile exactly: `1,466 + 78 + 57 = 1,601`.

## 6.4 Count-based derivation rule

For headline borough totals and subgroup families whose displayed counts are exact in this LA file, published percentages are rounded, so the derived adverse outcome should be calculated from counts rather than by adding displayed percentages.

```text
outside_recorded_sustained_count = not_recorded_count + activity_not_captured_count
outside_recorded_sustained_rate = outside_recorded_sustained_count / cohort_count
```

**D5 qualification:** disadvantage displayed counts are not exact and require the separate handling documented in §§12.6–12.7 and D5c.

## 6.5 Interpretation boundary

The derived adverse outcome is **not a NEET rate**.

The supplied guidance states:
- `Not recorded as a sustained destination` includes pupils captured in source data who had some participation but did not complete the sustained requirement.
- `Activity not captured` means the pupil was not found to have participation in education, apprenticeship or employment and was not recorded as receiving out-of-work benefits; possible reasons include living, working or studying abroad or attending a Scottish or Welsh institution.

Therefore activity not captured cannot be equated mechanically with NEET.

**Decision supported:** use the derived adverse outcome for the primary borough analysis while retaining the two official DfE components separately.

---

# 7. Concrete subgroup example: Camden 2022/23

For `Not recorded as a sustained destination`, the raw data includes:

| Subgroup | Cohort count | Pupil count | Percent |
|---|---:|---:|---:|
| Female | 866 | 41 | 4.7% |
| Male | 735 | 37 | 5.0% |
| Disadvantaged | 785 | 60 | 7.5% |
| Not known to be disadvantaged | 815 | 20 | 2.3% |
| FSM eligible | 688 | 55 | 8.0% |
| Not known to be FSM eligible | 913 | 23 | 2.5% |
| Identified SEN | 301 | 26 | 8.6% |
| No identified SEN | 1,300 | 52 | 4.0% |

Observed consistency:

- Female + Male cohort = `866 + 735 = 1,601`, exactly the headline cohort.
- FSM cohort = `688 + 913 = 1,601`, exactly the headline cohort.
- Disadvantage cohort = `785 + 815 = 1,600`, one below the exact headline cohort.
- Disadvantage destination counts = `60 + 20 = 80`, while the exact headline count is 78.

D5 resolved the earlier open question: the disadvantage displayed counts show a systematic disclosure-rounding pattern rather than a failure of the cohort classification; see §§12.6–12.7.

---

# 8. Publication-code conventions from supplied guidance

The supplied `data-guidance.txt` defines:

- `(0)` zero
- `(c)` small number suppressed to preserve confidentiality or for accountability reasons
- `(z)` not applicable
- `(x)` not available
- `(low)` positive percentage less than 0.5

The CSV stores these as tokens without parentheses: `c`, `z`, `x`, `low`.

The supplied guidance also states that the blanket rule suppressing cohorts below six applies at **institution level**, not at other geographic levels.

These codes are semantic publication states, not interchangeable forms of ordinary missing data.

---

# 9. Accepted decisions supported before D5

## D1 — Geography
Primary geography: **London Local Authority**, with the explicit school/institution-location interpretation.

## D2 — Period
Primary borough-level period: **2016/17–2022/23**.

## D3 — Analytical population
Primary population: **state-funded mainstream + special**. Also examine mainstream and special separately for composition effects. Treat alternative provision separately.

## D4 — Primary analytical outcome
Use the **rate and count outside recorded sustained destinations**, defined as `Not recorded as a sustained destination + Activity not captured`, while retaining both official components separately and avoiding the label NEET.

D5 did not reopen these substantive decisions. It added implementation and reporting rules recorded as D5a–D5f in `DECISIONS.md`.

---

# 10. Source-guidance notes relevant to comparability

The supplied guidance contains several directly relevant footnotes:

1. **Prior attainment:** the calculation for prior-attainment categories changed in 2020/21 following the introduction of Key Stage 2 scaled scores. The guidance explicitly warns that caution is required when comparing prior-attainment results over time.
2. **Series boundary:** changes to the data have been implemented from the **2016/17 cohort onwards**, so comparisons with earlier cohorts should be treated with caution.
3. **SEND:** following SEND reforms, `SEN support` replaced school action / school action plus; the guidance notes that some legacy categories could remain in earlier cohorts.
4. **Disadvantage definition:** disadvantaged pupils include pupils known to be eligible for FSM during the relevant six-year window, looked-after children, and pupils adopted from care, as defined by the publication guidance.

For the chosen primary London LA slice:

- prior-attainment breakdowns are not available;
- the five target subgroup families use stable labels throughout 2016/17–2022/23;
- no legacy SEN categories appear in the selected LA data.

---

# 11. External DfE verification used in D5

The supplied data and guidance remain the primary source of truth. External DfE documentation was used only where D5 required clarification of methodology over time or disclosure conventions not fully specified in the supplied guidance.

## 11.1 Current KS4 destination methodology

DfE's current **Key stage 4 destination measures: methodology** confirms that:

- from 2016/17 a new apprenticeship methodology was introduced and applied to a back series for comparability;
- self-employment from HMRC data is included from 2016/17;
- in the latest release, NCCIS was removed as an employment source and cohorts **2016/17–2022/23 were recalculated** on that basis so the current series is consistent;
- the major ethnicity grouping was retrospectively adjusted in February 2023 so Chinese pupils are included in `Asian / Asian British` in the published historical series.

These points support using the current supplied/recalculated series consistently rather than combining it with values copied from older releases.

## 11.2 Related DfE destinations disclosure documentation

A closely related DfE Local Authority destinations dataset states that numbers in the **Disadvantage Status** breakdown are rounded to the nearest five for confidentiality and values of 1 or 2 may be represented by `low`.

The supplied KS4 guidance does **not** explicitly state that nearest-five count rule. However, the rule is strongly corroborated in the present file by the fact that every ordinary numeric disadvantage cohort and pupil count in the London LA slice is a multiple of five and the resulting discrepancies are bounded by four pupils.

Accordingly, the nearest-five interpretation is recorded as **externally corroborated and empirically supported**, not as wording taken directly from the supplied KS4 guidance.

---

# 12. D5 — systematic data-quality and comparability audit

## 12.1 Grain / uniqueness

### Check

The following full conceptual key was tested over the **96,792 London LA rows** from 2016/17–2022/23:

`time_period × new_la_code × establishment_type_group × sex × ethnicity_major × ethnicity_minor × disadvantage_status × breakdown_topic × breakdown × destination_description`

### Finding

**Duplicate rows at this full key: 0.**

For combined mainstream + special and mainstream-only populations, each destination has **17 characteristic slices**:

- 1 headline `Total` slice;
- 2 sex slices;
- 6 major-ethnicity slices;
- 2 disadvantage slices;
- 2 FSM slices;
- 4 SEN labels.

Standalone special schools and AP have only the headline slice at LA level.

The normalised five-family subgroup table can therefore be constructed without duplicate keys once `subgroup_family` and `subgroup_value` are explicit.

### Why it matters

Rows that appear repetitive at `borough × year × destination` are normally different overlapping subgroup views of the same underlying cohort. Treating them as duplicate pupils or deduplicating them broadly would destroy valid information.

### Action

**Preprocessing treatment.** Freeze the analytical table grains in D5a and assert uniqueness at those grains during implementation.

---

## 12.2 Geography coverage

### Check

LA coverage was counted by year and establishment population, and code/name mappings were tested for consistency.

### Finding

| Cohort | Combined | Mainstream | Special | AP |
|---|---:|---:|---:|---:|
| 2016/17 | 32 | 32 | 32 | 32 |
| 2017/18 | 32 | 32 | 32 | **33** |
| 2018/19 | 32 | 32 | 32 | **33** |
| 2019/20 | 32 | 32 | 32 | 32 |
| 2020/21 | 32 | 32 | 32 | 32 |
| 2021/22 | 32 | 32 | 32 | 32 |
| 2022/23 | 32 | 32 | 32 | 32 |

The extra AP authority in 2017/18 and 2018/19 is **City of London**.

City of London AP observations:

| Cohort | Cohort count | Sustained overall | Outside recorded sustained destinations |
|---|---:|---:|---:|
| 2017/18 | 1 | 1 | 0 |
| 2018/19 | 1 | 0 | 1 |

No City of London observations occur in the chosen primary population.

Code/name mapping checks found:

- each `new_la_code` maps to one LA name;
- each LA name maps to one `new_la_code`;
- no London LA name/code changes occur within the seven-year analytical panel;
- no unintended non-London authorities enter the filtered London LA slice.

### Why it matters

The primary population forms a genuinely balanced **32-LA panel**. AP does not, because two City of London observations with denominator one appear in only two years.

### Action

**No change to D1.**
**Panel rule for AP:** D5e retains those records in the audit layer but excludes them from ordinary 32-borough comparisons.

---

## 12.3 Establishment-population consistency

### Check

For headline characteristic slices, the identity

`State-funded mainstream and special = State-funded mainstream schools + State-funded (inc. non-maintained) special`

was tested for both `cohort_count` and `pupil_count` at:

`year × LA × destination`.

### Finding

- `cohort_count`: **2,688 / 2,688 identities exact**
- `pupil_count`: **2,688 / 2,688 identities exact**
- total count checks across both measures: **5,376 / 5,376 exact**

No exceptions were found.

### Why it matters

This validates the arithmetic basis for later mainstream/special composition decomposition. The combined rate can legitimately be interpreted as the cohort-weighted combination of the two components.

### Action

**No action beyond a future QA assertion. D3 remains valid and is strengthened.**

---

## 12.4 Destination accounting

### Check

Four nested count identities were tested for combined, mainstream, special and AP headline observations:

1. `cohort = sustained overall + not recorded sustained + activity not captured`
2. `sustained overall = sustained education + sustained employment + sustained apprenticeships`
3. `sustained education = FE + school sixth form + sixth-form college + other education`
4. `sustained apprenticeships = intermediate + advanced/higher apprenticeships`

### Finding

Every identity held exactly wherever the population was present:

| Population | Borough-years | Identity failures |
|---|---:|---:|
| Combined mainstream + special | 224 | 0 |
| Mainstream | 224 | 0 |
| Special | 224 | 0 |
| AP | 226 | 0 |

Published percentage components can differ from exact totals by small amounts because each percentage is rounded separately.

### Why it matters

The destination taxonomy behaves as a coherent accounting system in the analytical slice. Exact counts, where genuinely exact, are the correct QA reference; a percentage total such as 99.9% or 100.1% is not by itself evidence of an error.

### Action

**No reopening of D4.** Use count identities as QA checks and tolerate ordinary one-decimal percentage rounding.

---

## 12.5 Missingness, suppression and publication codes

### Check

Publication-code prevalence was inspected in the full raw file and the target London LA 2016/17–2022/23 slice.

### Full raw file

| Field | `c` | `z` | `x` | `low` | Numeric |
|---|---:|---:|---:|---:|---:|
| `institution_count` | 0 | 1,869,301 | 0 | 0 | 2,438 |
| `cohort_count` | 12,240 | 0 | 0 | 432 | 1,859,067 |
| `pupil_count` | 144,513 | 6,374 | 0 | 5,979 | 1,714,873 |
| `pupil_percent` | 144,513 | 6,374 | 0 | 3,579 | 1,717,273 |

No blank/null numeric tokens were found in these four fields.

### Target London LA slice

| Field | Finding |
|---|---|
| `institution_count` | `z` on all 96,792 rows |
| `cohort_count` | 100% numeric |
| `pupil_count` | 426 `c`, 342 `low`; all are disadvantage rows |
| `pupil_percent` | 426 `c`, 22 `low`; remaining non-disadvantage `low` values occur only in very small published percentages |

The guidance defines `z` as **not applicable**, so LA-level `institution_count = z` is not ordinary missingness.

A documentation peculiarity was also identified: the supplied guidance defines `low` as a positive **percentage** below 0.5, yet the token also appears in the disadvantage `pupil_count` field. Related DfE destinations documentation says small disadvantage counts may be represented by `low`, which is consistent with the observed data, but this count-field use is not explicitly described by the supplied KS4 guidance.

### Why it matters

Replacing every non-numeric token with ordinary `NaN`, and especially replacing `low` or `c` with zero, would erase important semantics and bias subgroup analysis.

### Action

**Preprocessing treatment: D5b.** Preserve semantic status separately from any numeric representation. Do not impute suppressed values in the main analysis.

---

## 12.6 Subgroup consistency

### Check

For the primary combined population and mainstream population, subgroup cohort sums and destination pupil-count sums were tested against their appropriate parents.

### Sex

Primary combined population:

- cohort: **224 / 224 exact**
- destination pupil counts: **2,688 / 2,688 exact**

Mainstream gives the same exact reconciliation pattern.

### Major ethnicity

Using all six categories, including `Unknown`:

- cohort: **224 / 224 exact**
- destination pupil counts: **2,688 / 2,688 exact**

`Unknown` is therefore part of the accounting universe and must not be silently dropped when testing totals.

### FSM

- cohort: **224 / 224 exact**
- destination pupil counts: **2,688 / 2,688 exact**

### SEN

Two separate identities hold exactly throughout:

`Identified SEN + No identified SEN = headline`

and

`SEN support + SEN with EHC plan or statement = Identified SEN`

Thus the four SEN labels are hierarchical rather than four mutually exclusive peer categories.

### Disadvantage

The pattern is different.

For the primary combined population:

- disadvantage cohort categories fail to equal the exact headline cohort in **176 / 224** borough-years;
- maximum absolute difference = **4 pupils**;
- mean absolute difference among mismatches ≈ **1.99 pupils**.

For destination pupil counts where both disadvantage category counts are numeric:

- complete comparable cells = **2,447**;
- mismatches = **1,938**;
- maximum absolute difference = **4 pupils**.

Mainstream shows essentially the same pattern:

- cohort mismatches = **180 / 224**;
- complete destination cells = **2,412**;
- destination mismatches = **1,940**;
- maximum absolute difference = **4 pupils**.

Most importantly:

> **100% of ordinary numeric disadvantage `cohort_count` and `pupil_count` values are multiples of five.**

This deterministic pattern, together with external DfE disclosure documentation described in §11.2, supports interpreting the displayed disadvantage counts as disclosure-rounded rather than exact.

### Why it matters

The disadvantage mismatches are not evidence that the two disadvantage categories omit a material population. They are the expected consequence of separately rounded public counts.

### Action

- sex, major ethnicity, FSM and the correctly structured SEN categories may use exact count accounting in this LA file;
- disadvantage must follow D5c;
- SEN analysis must follow the hierarchy in D5d.

---

## 12.7 Rate/count consistency

### Check

For numeric cells, `100 × pupil_count / cohort_count` was compared with published `pupil_percent`.

For the primary combined population:

| Slice | Maximum absolute discrepancy |
|---|---:|
| Headline | 0.050 pp |
| Sex | 0.050 pp |
| Major ethnicity | 0.050 pp |
| FSM | 0.050 pp |
| SEN | 0.050 pp |
| **Disadvantage** | **1.421 pp** |

For headline, sex, ethnicity, FSM and SEN, the maximum discrepancy is exactly what is expected when an underlying percentage is rounded to one decimal place.

For disadvantage, **3,581 of 5,011 numeric primary-population cells** exceed a 0.051 pp tolerance because the displayed numerator and denominator have themselves been disclosure-rounded.

### Concrete example: Camden 2022/23

For disadvantaged pupils, `Not recorded as a sustained destination` shows:

- displayed cohort = 785
- displayed pupil count = 60
- published percent = 7.5%

But `60 / 785 × 100 = 7.64%`, confirming that the published percentage is not calculated from the displayed rounded counts.

### Stronger example: Kingston upon Thames 2017/18

For disadvantaged pupils and the sustained headline measure:

- displayed cohort = 265
- displayed sustained count = 235
- published sustained rate = 90.1%
- `235 / 265 × 100 = 88.68%`

The artificial discrepancy is approximately **1.42 percentage points** if the rounded displayed counts are incorrectly treated as exact.

### Why it matters

A general rule of “always recompute percentages from displayed counts” would be correct for most of the LA file but materially wrong for disadvantage.

### Action

**D4 implementation qualification + D5c:** use published disadvantage percentages for subgroup rates and do not claim exact disadvantage adverse counts.

---

## 12.8 Time comparability

### Check

Comparability was reviewed using:

1. category availability in the supplied data;
2. the supplied `data-guidance.txt`;
3. current authoritative DfE methodology where the supplied guidance did not fully describe later methodological revisions.

### Core destination measures

The same 12 destination categories appear throughout the chosen 2016/17–2022/23 primary LA series.

The supplied guidance explicitly states that changes to the data were implemented from the **2016/17 cohort onwards**, and comparisons with earlier years should be treated with caution. This supports the existing D2 start point.

Current DfE methodology further states that the removal of NCCIS from employment destinations was retrospectively applied to **2016/17–2022/23**, keeping the currently published series on a consistent basis.

**Implication:** use the current supplied series consistently; do not combine it casually with figures taken from older release vintages.

### Major ethnicity

The same six major categories occur throughout the target panel. Current DfE methodology states that historical major-ethnicity groupings were adjusted so Chinese pupils are included within `Asian / Asian British` in the published series.

**Implication:** the supplied/current series is suitable for longitudinal use at this broad ethnicity level; older extracts could differ.

### SEN

The same target labels occur throughout the chosen LA panel, and no legacy categories appear in this analytical slice.

The supplied guidance explains the SEND reform background and notes that legacy categories may remain in some earlier data, but they do not appear in the chosen 2016/17–2022/23 LA subgroup rows.

**Implication:** no shortened period is required for the selected SEN categories.

### Disadvantage and FSM

Category structures are stable across all seven cohorts.

**Implication:** the principal issue is disclosure treatment of disadvantage counts, not a time-definition break.

### Prior attainment

The supplied guidance explicitly states that prior-attainment category calculation changed in 2020/21 following Key Stage 2 scaled scores and that comparisons over time require caution.

However, prior-attainment breakdowns are **not available in the chosen primary London LA slice**.

**Implication:** do not design the primary borough analysis or model around a prior-attainment feature that is absent. If another geography/population is analysed later, the 2020/21 break must be handled explicitly.

### COVID-affected cohorts

The pandemic changed the real education and labour-market environment and affected qualification/grading contexts. This is analytically different from a pure variable-definition change.

**Implication:** retain the cohorts, but later trend analysis and validation must be time-aware and should test sensitivity to the pandemic period where relevant.

### Action

**D2 remains valid.** No general shortening of 2016/17–2022/23 is required for the chosen outcome or five target subgroup families.

---

## 12.9 Coverage by subgroup and establishment type

### Check

Availability of the five target subgroup families was inventoried across year, geography and establishment population.

### Finding

For the primary combined population, all five target subgroup families are present for **all 32 boroughs in all seven cohorts**:

| Family | Categories used at LA level | Seven-cohort coverage |
|---|---|---|
| Sex | Female; Male | Complete |
| Major ethnicity | Asian; Black; Mixed; Other; Unknown; White | Complete |
| Disadvantage | Disadvantaged; Not known disadvantaged | Complete |
| FSM | FSM eligible; Not known FSM eligible | Complete |
| SEN | Identified; No identified; SEN support; EHC/statement | Complete |

Mainstream has the same subgroup coverage.

Standalone special schools and AP have **no equivalent LA subgroup breakdowns** in the supplied data.

Fine `ethnicity_minor` categories are not available in the primary LA slice, and no intersectional combinations are available.

### Why it matters

The main combined-population subgroup analysis can genuinely be longitudinal across the seven cohorts. The same claim cannot be made for subgroup analysis of standalone special schools or AP at LA level.

### Action

**No additional population decision required.** Preserve this coverage inventory as a hard boundary on later EDA/model design.

---

## 12.10 Small-denominator risk in special schools and AP

### Check

Headline cohort denominators were summarised across borough-years.

| Population | N borough-years | Minimum | Median | `<20` | `<50` |
|---|---:|---:|---:|---:|---:|
| Combined primary | 224 | 718 | 2,632.5 | 0 | 0 |
| Mainstream | 224 | 707 | 2,601.5 | 0 | 0 |
| Special | 224 | **9** | **45.5** | **14** | **129** |
| AP | 226 | **1** | **52** | **19** | **101** |

### Why it matters

A one-pupil change can move a special-school or AP borough rate by several percentage points. Raw rankings would therefore mix underlying outcome differences with substantial denominator-driven noise.

This does not invalidate D3: the standalone populations remain useful diagnostics, especially for understanding composition. It limits how strongly their raw borough rates can be interpreted.

### Action

**Reporting limitation + later sensitivity/uncertainty treatment: D5f.** Always show denominators and avoid unqualified rankings. The exact uncertainty method is deferred until after EDA.

---

## 12.11 Consolidated analytical-risk register

| Risk | Potential distortion | Treatment |
|---|---|---|
| Disadvantage counts are disclosure-rounded/suppressed | subgroup count identities and rates | Preprocessing + limitation; D5c |
| Publication codes collapsed to zero/NA | derived features and denominators | Semantic preprocessing; D5b |
| SEN parent and child labels treated as peers | double counting / invalid subgroup totals | Hierarchical design rule; D5d |
| City of London AP `n=1` observations | AP panel consistency and extreme rates | 32-borough comparison panel; D5e |
| Small special/AP denominators | borough comparisons and apparent volatility | Denominator display + later uncertainty treatment; D5f |
| COVID-affected cohorts | trend interpretation and model validation | Time-aware sensitivity / validation |
| LA is school/institution location, not residence | policy interpretation | Existing D1 limitation |
| Administrative matching may miss some activity | interpretation of `Activity not captured` | Existing D4 interpretation limitation |
| Mixing publication vintages | artificial time-series changes | Use one current supplied series consistently |
| No LA intersectional breakdowns | disparity interpretation | Explicit limitation |
| No primary-LA prior-attainment breakdown | feature/model design | Do not use in primary analysis |

---

# 13. D5 conclusion and decisions supported

D5 found no evidence requiring a substantive reopening of D1–D4.

- **D1 remains valid:** the primary data form a stable 32-LA panel.
- **D2 remains valid:** the selected core variables are structurally available across all seven cohorts, with known methodological caveats recorded above.
- **D3 remains valid and is strengthened:** combined mainstream + special counts reconcile exactly with their components at the required analytical grain.
- **D4 remains valid:** all relevant destination accounting identities hold exactly. The implementation rule is qualified only for disadvantage subgroup counts because those displayed counts are disclosure-controlled/rounded.

The following D5 decisions are now accepted in `DECISIONS.md`:

- **D5a:** analytical table grains;
- **D5b:** publication-code handling;
- **D5c:** disadvantage disclosure treatment;
- **D5d:** SEN hierarchy;
- **D5e:** AP geography panel;
- **D5f:** small-population interpretation for special schools and AP.

---

---

# 14. D6 — Exploratory Data Analysis

D6 examined the accepted D1–D5 analytical structure without reopening it: the stable 32-LA panel, 2016/17–2022/23 period, combined mainstream + special primary population, the adverse outcome and its two official components, subgroup rules, and the separate treatment of AP.

The purpose was descriptive: identify robust temporal, geographic, population and subgroup structure that should shape the next modelling-question and validation stages. The aggregate data do not support causal attribution.

## 14.1 London-wide time trend

### Check

Exact headline counts were summed across the frozen 32-LA panel, and the adverse outcome and its two components were tracked through time.

| Cohort | Cohort size | Adverse rate | Not recorded sustained | Activity not captured |
|---|---:|---:|---:|---:|
| 2016/17 | 75,538 | 5.96% | 4.11% | 1.85% |
| 2017/18 | 76,246 | 5.92% | 3.88% | 2.04% |
| 2018/19 | 79,770 | 5.85% | 3.70% | 2.15% |
| 2019/20 | 83,150 | 5.39% | 2.94% | 2.46% |
| 2020/21 | 85,671 | 5.31% | 3.32% | 1.99% |
| 2021/22 | 86,169 | 5.89% | 3.77% | 2.12% |
| 2022/23 | 89,811 | **6.58%** | 3.94% | **2.65%** |

The adverse count rose from **4,505** in 2016/17 to **5,912** in 2022/23.

Destination composition also changed. Sustained education rose unusually in 2019/20 while sustained employment and apprenticeships fell; the two adverse components likewise moved differently in 2019/20 and 2020/21.

### Finding

The series is clearly **non-linear**: broadly stable through 2018/19, lower in 2019/20–2020/21, then increasing to the seven-cohort high in 2022/23. The latest deterioration is not attributable to only one adverse component.

### Why it matters

A single smooth trend would hide relevant time structure. The two official adverse components should remain visible, and later validation must respect chronological ordering.

### Action

D2 and D4 remain valid. Temporal structure is formalised in **D6d**.

---

## 14.2 Borough variation, persistence and count-versus-rate interpretation

### Check

Borough adverse-rate distributions, year-to-year movements, rank persistence and adverse counts were compared across the 32-LA panel.

Selected distribution summaries:

| Cohort | Median rate | Middle 50% | Min–max |
|---|---:|---:|---:|
| 2016/17 | 6.04% | 5.39–6.75% | 3.30–8.42% |
| 2018/19 | 5.85% | 5.10–6.92% | 3.57–8.81% |
| 2020/21 | 5.41% | 4.85–5.95% | 2.69–7.39% |
| 2022/23 | **6.72%** | **5.88–7.66%** | **3.57–9.22%** |

Adjacent-year Spearman rank correlations are approximately **0.56–0.74**; the 2016/17 versus 2022/23 correlation is **0.68**.

From 2021/22 to 2022/23, **27 of 32 boroughs** had a higher adverse rate. The largest borough contributes only around 5–6% of London's adverse count in a typical year, so the outcome is not dominated by one or two authorities.

### Finding

Borough differences are substantial and moderately persistent, but borough positions also move. The recent deterioration is geographically broad rather than an artefact of a few extreme boroughs.

Counts and rates provide different information. Larger boroughs can have high adverse counts without having the highest adverse rate.

### Why it matters

Later analysis needs to distinguish:

- comparative prevalence (**rate**);
- potential support-demand scale (**count**);
- persistent borough differences;
- common year effects;
- borough-specific changes.

A one-year borough league table would discard much of that structure.

### Action

Accept **D6a**. Preserve both rates and counts where they answer distinct policy questions.

---

## 14.3 Mainstream / special-school composition

### Check

Using the exact identity established in D5,

`combined = mainstream + standalone special`,

the combined adverse rate was decomposed into mainstream outcomes, special-school outcomes and the special-school cohort share.

London-level examples:

| Cohort | Special share | Mainstream adverse | Special adverse | Combined adverse |
|---|---:|---:|---:|---:|
| 2016/17 | 1.71% | 5.92% | 8.65% | 5.96% |
| 2018/19 | 1.89% | 5.78% | 9.16% | 5.85% |
| 2020/21 | 1.89% | 5.25% | 8.34% | 5.31% |
| 2021/22 | 2.02% | 5.81% | 9.82% | 5.89% |
| 2022/23 | **2.18%** | **6.55%** | **7.96%** | **6.58%** |

Across boroughs, combined and mainstream adverse rates have Pearson correlations of approximately **0.99 in every year**. The median absolute difference between the two is generally around **0.07–0.08 percentage points**, although individual borough effects can exceed 0.5 pp.

### Finding

The primary borough pattern is overwhelmingly a **within-mainstream** pattern, not an artefact of differing special-school shares. Special-school composition can nevertheless matter for individual boroughs.

The 2021/22→2022/23 London deterioration occurred while the special-school adverse rate fell, so changing special-school composition does not explain the recent headline increase.

### Why it matters

The primary combined population remains appropriate, while mainstream provides a useful robustness/composition diagnostic. Standalone special-school borough rates remain noisy because of small denominators.

### Action

D3 and D5f remain valid. No additional composition adjustment is required for the primary descriptive analysis.

---

## 14.4 Subgroup disparities

### Check

Sex, major ethnicity, disadvantage, FSM and SEN were examined London-wide, across boroughs and through time. Exact counts were used where appropriate; disadvantage followed D5c and SEN followed D5d.

Selected London-wide contrasts:

| Contrast | 2016/17 | 2022/23 | Gap 2016/17 | Gap 2022/23 |
|---|---:|---:|---:|---:|
| Male vs female | 7.32% vs 4.57% | 7.47% vs 5.66% | 2.74 pp | 1.80 pp |
| Disadvantaged vs other | 8.8% vs 4.3% | 10.8% vs 4.6% | 4.5 pp | **6.2 pp** |
| FSM eligible vs other | 9.53% vs 5.18% | 10.93% vs 4.95% | 4.35 pp | **5.98 pp** |
| Identified SEN vs no SEN | 10.40% vs 5.27% | 11.38% vs 5.63% | 5.13 pp | **5.75 pp** |

In 2022/23 the adverse rate by major ethnicity was approximately:

- Asian / Asian British: **3.64%**;
- Black / African / Caribbean / Black British: **6.45%**;
- Mixed / Multiple ethnic groups: **8.46%**;
- Other ethnic group: **6.82%**;
- White: **7.73%**;
- Unknown: **8.37%**.

Within SEN in 2022/23, `SEN support` had an adverse rate of approximately **12.28%**, compared with **9.22%** for `SEN with EHC plan or statement`.

### Finding

The largest, most geographically widespread disparities are associated with **socioeconomic disadvantage/FSM and SEN**. Sex differences are persistent but smaller.

Ethnicity is more nuanced than the organiser's wider youth-unemployment framing: this specific KS4 sustained-destination outcome does not show Black pupils as the highest-adverse-rate major ethnic group at London level. This should not be generalised to overall youth unemployment or NEET outcomes.

The lower adverse rate for pupils with an EHC plan/statement than for pupils receiving SEN support is an exploratory association, not evidence that EHC provision causes better outcomes.

### Why it matters

Subgroup narrative should follow the evidence in this dataset rather than an assumed ordering. FSM and disadvantage should not be presented as independent confirmations because they overlap conceptually and empirically.

### Action

Accept **D6b**. Retain all five families, but prioritise disadvantage/FSM and SEN in the substantive narrative and respect the D5 disclosure/hierarchy rules.

---

## 14.5 Alternative provision

### Check

AP was analysed separately using the stable 32-borough comparison panel required by D5e.

| Cohort | AP cohort | Adverse rate | Not sustained | Activity not captured |
|---|---:|---:|---:|---:|
| 2016/17 | 2,169 | 39.8% | 21.7% | 18.1% |
| 2017/18 | 2,050 | 41.3% | 23.6% | 17.8% |
| 2018/19 | 2,063 | 37.1% | 19.2% | 17.9% |
| 2019/20 | 2,097 | 32.2% | 17.5% | 14.7% |
| 2020/21 | 1,623 | 33.0% | 19.6% | 13.4% |
| 2021/22 | 1,534 | 33.9% | 17.7% | 16.2% |
| 2022/23 | 1,735 | **35.0%** | 16.7% | **18.3%** |

In 2022/23 AP recorded **607** pupils outside recorded sustained destinations. Its cohort was only about 1.9% of the size of the primary cohort, but its adverse count was equivalent to about 10% of the primary-population adverse count; this is a scale comparison between separate populations, not a decomposition of one population.

Borough-level instability remains substantial. In 2022/23 the median AP cohort was **44.5**, **17 of 32** boroughs had fewer than 50 pupils, and observed raw borough adverse rates ranged from **0% to 80.8%**.

### Finding

AP is too substantively important to omit, but its small borough denominators make raw annual rankings unreliable.

### Why it matters

The final analysis should make AP visible without giving unstable borough rates the same interpretive weight as the primary population.

### Action

Accept **D6c**. AP becomes a dedicated secondary analysis, primarily at London level.

---

## 14.6 Time structure

### Check

London trends, borough movements, rank persistence, dispersion and subgroup gaps were considered jointly.

Key observations:

- 2016/17–2018/19: London adverse rate broadly stable around 5.9%;
- 2019/20–2020/21: lower headline rates, reaching 5.31% in 2020/21;
- 2021/22–2022/23: strong rebound to 6.58%;
- 23 of 32 boroughs improved from 2018/19 to 2019/20;
- 24 of 32 worsened from 2020/21 to 2021/22;
- 27 of 32 worsened from 2021/22 to 2022/23;
- borough dispersion compressed in 2020/21 and widened again by 2022/23;
- socioeconomic and SEN gaps also narrowed around 2019/20 and widened later.

### Finding

There is evidence of both a **common London time component** and **persistent borough structure**. The two pandemic-era cohorts are unusual but are not identical to one another, particularly in the composition of the adverse outcome.

### Why it matters

Randomly shuffling borough-year observations later would allow information from later regimes to inform earlier observations and would obscure the real temporal generalisation problem.

With only seven annual cohorts, formal breakpoint detection would add little confidence and could overfit. The observed time structure is better preserved descriptively and handled explicitly in later validation.

### Action

Accept **D6d**. The exact validation protocol is deliberately deferred.

---

## 14.7 Robust versus tentative EDA findings

### Robust

- the London trend is non-linear and the latest rise is broad across boroughs;
- borough differences are substantial and moderately persistent;
- counts and rates answer different policy questions;
- mainstream outcomes explain nearly all of the combined borough pattern, while special-school composition occasionally matters locally;
- disadvantage/FSM and SEN show the largest and most widespread subgroup disparities;
- AP has a much higher adverse rate than the primary population but unstable borough rates because of small denominators;
- temporal ordering matters for any later predictive evaluation.

### Tentative / descriptive only

- the post-pandemic widening of subgroup gaps may indicate a meaningful regime change, but seven annual cohorts cannot establish a statistical break;
- the SEN-support versus EHC-plan difference is an association and should not be interpreted as a treatment effect;
- extreme borough subgroup, special-school and AP rates can be denominator-sensitive;
- the aggregate data cannot establish whether COVID, policy changes, labour-market conditions, cohort composition or other mechanisms caused the observed time changes.

---

## 14.8 Modelling signal identified by EDA

EDA suggests two distinct questions that could add information beyond description, but neither is yet an accepted modelling decision.

### Candidate predictive question

> Using information available up to cohort `t`, can we predict which London boroughs will have higher rates outside recorded sustained destinations in cohort `t+1`, and does that prediction generalise to genuinely later cohorts?

A key leakage constraint follows immediately: **same-year subgroup destination rates must not be used to predict the same-year headline destination rate**, because they are overlapping slices of the same underlying outcome.

The internal panel is small: 32 boroughs and only six one-year forecast transitions. Complex ML is therefore not justified by sample size alone and would need to beat simple baselines under time-aware validation.

### Candidate explanatory question

> How much of observed borough variation is associated with persistent borough differences, common year effects, population composition and borough-specific temporal movement?

This question follows directly from the strongest EDA structure but is explanatory/descriptive rather than a causal identification strategy.

### Action

Do **not** select a model yet. The next stage is to decide which analytical question is actually useful, what information would be available at prediction time, and whether external point-in-time predictors are needed.

---

# 15. D6 conclusion and decisions supported

D6 found no evidence requiring D1–D5 to be reopened.

The following D6 decisions are accepted in `DECISIONS.md`:

- **D6a:** use rates for comparative prevalence and counts for scale/context;
- **D6b:** subgroup reporting hierarchy, with disadvantage/FSM and SEN prioritised without treating overlapping families as independent;
- **D6c:** AP as a dedicated secondary analysis, primarily at London level;
- **D6d:** preserve temporal structure and require genuinely time-aware later validation.

The EDA also resolves two D5 open questions:

- AP deserves explicit secondary analysis rather than a footnote;
- the final subgroup narrative should be led by socioeconomic disadvantage/FSM and SEN, with sex and ethnicity retained as distinct descriptive analyses.

---

# 16. D7 — Modelling Question Definition

D7 reviewed the candidate modelling questions against the frozen D1–D6 structure before any algorithm selection. The review focused on statistical validity, leakage, policy usefulness, sample size, interpretability and whether the supplied aggregate data can genuinely answer the proposed question.

## 16.1 Primary explanatory / structural question

### Candidate question

> **How much of the observed variation in London borough rates outside recorded sustained destinations is associated with persistent borough differences, common cohort-year effects and observable cohort composition, and how much borough-specific variation remains after accounting for those structures?**

### Target and unit

- unit: **borough × cohort**;
- primary panel: 32 London LAs × seven cohorts = **224 borough-years**;
- estimand: borough-year adverse **rate / probability**;
- retain the exact adverse count and cohort denominator rather than reducing each observation to an unweighted percentage only.

### Why the denominator must be retained

Borough cohort sizes differ materially, so observed adverse rates have different statistical precision. Treating each percentage as equally precise would discard known information contained in the exact count and denominator.

D7 therefore freezes the substantive target as a rate / probability but leaves the precise statistical treatment to later model selection.

### Why this question is useful

D6 showed simultaneously:
- substantial and moderately persistent borough differences;
- strong common London-wide year movement;
- borough-specific movement around that common pattern;
- some measurable composition differences.

A structured borough-year analysis therefore adds information beyond one-year rankings or descriptive plots by quantifying how much variation is associated with those distinct sources.

### Interpretation boundary

This is an **associational**, not causal, question. The supplied aggregate data do not identify the effect of Youth Offer interventions or establish why a borough has a higher or lower rate.

With only seven annual cohorts, D7 also rejects any presumption that elaborate borough-specific trends or formal structural breaks can be estimated reliably. The appropriate concept is **borough-specific deviation from the common London time pattern**.

### Decision

**Accept as the primary modelling question — D7a.**

---

## 16.2 Secondary one-cohort-ahead prediction

### Candidate question

> **Using only information genuinely available through cohort `t`, can we predict borough adverse rates in cohort `t+1` better than simple historical baselines?**

### Target and unit

- target: continuous next-cohort adverse rate / probability;
- unit: borough × target cohort;
- forecast horizon: **one cohort ahead**;
- nominal forecasting rows: up to 32 boroughs × six transitions = **192**;
- crucial time dimension: only **six forecast transitions / seven annual regimes**.

### Legitimate information set

Information from cohort `t` or earlier may potentially be used, including lagged headline outcomes, lagged outcome components, historical borough trajectories, cohort size and appropriately defined lagged composition variables.

The exact set is deliberately deferred until feature and validation design.

### Baseline requirement

Because borough outcomes are moderately persistent, a meaningful minimum baseline is:

> **next cohort's borough adverse rate ≈ current cohort's borough adverse rate.**

Any more elaborate method should demonstrate genuine improvement over simple historical baselines under chronological evaluation.

### Why this remains useful

This creates a real supervised-learning question without manufacturing an arbitrary classification task. It tests whether the historical data contain forward-looking information beyond persistence and common temporal structure.

It also prevents the project from assuming that complex ML is useful merely because supervised learning was suggested in the hackathon brief.

### Decision

**Accept as a required secondary modelling track — D7b.**

---

## 16.3 Leakage and target-reconstruction audit

### Structural risk

The source contains multiple overlapping slices of the same underlying cohort and exact destination-accounting identities. Several apparently rich variables therefore encode the target itself.

### Same-target-period variables that must not be used as independent predictors

For a borough-year headline adverse outcome, prohibit:

- `Not recorded as a sustained destination` for that same borough-year;
- `Activity not captured` for that same borough-year;
- sustained education, employment & apprenticeships for that same borough-year;
- same-year subgroup destination outcome rates/counts;
- same-year mainstream and special-school destination outcomes used to explain/predict their combined headline outcome;
- transformations that reconstruct the target through an accounting identity.

### Lagged outcomes

Lagged outcome information from `t` or earlier is not intrinsically leakage when forecasting `t+1`, provided it was genuinely available by the forecast origin and the later validation scheme preserves chronological order.

### Decision

**Accept D7c — explicit target-reconstruction / leakage prohibition.**

---

## 16.4 Cohort composition versus cohort outcomes

D7 distinguishes composition information from outcome information.

Potentially legitimate composition measures describe **who is in the cohort**, for example:

- cohort size;
- sex composition;
- broad ethnicity composition;
- FSM / disadvantage composition where valid under the disclosure rules;
- SEN composition following the D5d hierarchy;
- special-school cohort share.

These variables do not, by themselves, encode whether the same pupils subsequently achieved a sustained destination.

However, they must still be treated parsimoniously:

- disadvantage and FSM overlap conceptually and empirically;
- SEN labels are hierarchical;
- subgroup proportions are composition measures, not independent causal effects;
- disclosure-controlled disadvantage counts restrict what can be reconstructed exactly.

### Decision

**Accept D7d — composition features must be non-outcome quantities, and overlapping measures require parsimonious treatment.**

---

## 16.5 Policy and geographic usefulness

The modelling question must preserve the D1 interpretation of geography.

The LA dimension is associated with the pupil's **school/institution**, not necessarily residential borough. Therefore the model can support statements about:

- persistent borough education-system patterns;
- common versus borough-specific temporal movement;
- observable cohort composition associated with outcomes;
- whether historically available information improves next-cohort forecasting.

It cannot directly support a claim that it identifies which residential boroughs or resident young people should receive resources.

### Decision

**Accept D7e — preserve the school/institution-location interpretation in all modelling claims.**

---

## 16.6 External-data requirement

### Finding

External data are **not necessary** to answer the core D7 questions.

The supplied historical panel is sufficient for:
- the primary borough-year structural / associational analysis;
- an internal one-cohort-ahead forecasting benchmark.

External point-in-time predictors could later make the forecasting question more operationally rich—for example by providing information not already encoded in historical destination outcomes—but they would add new requirements around historical availability, comparability and leakage.

### Decision

**Accept D7f — external data are optional extensions rather than a core requirement.**

Do not expand scope until the internal analysis shows a specific reason to do so.

---

## 16.7 Candidate questions explicitly rejected

The following formulations are not supported as primary modelling questions:

| Candidate | D7 decision | Reason |
|---|---|---|
| Predict a binary “high-risk borough” label | Reject | Requires an arbitrary threshold and discards information from the continuous rate. |
| Individual pupil risk prediction | Reject | Source rows are aggregate statistical cells, not pupil-level records. |
| Intersectional subgroup prediction | Reject | LA data do not provide intersectional subgroup combinations. |
| Estimate which intervention causes better outcomes | Reject | No intervention / exposure identification strategy is available. |
| Predict AP borough outcomes as the main task | Reject | Small denominators make annual borough outcomes highly unstable; AP remains primarily a London-level secondary analysis. |
| Explain the headline outcome using same-year subgroup destination rates | Reject | Overlapping slices of the same underlying outcome create tautological explanation / leakage. |
| Explain combined outcome using same-year mainstream + special outcomes | Reject | The combined outcome is mechanically reconstructed from those components. |
| Make adverse count the primary comparative prediction target | Do not use as primary | Counts are strongly dependent on cohort size; retain them for scale / support-demand context under D6a. |
| Predict year-on-year deterioration as the main target | Do not use as primary | Differencing discards persistent structure and can amplify noise in a short panel. |

---

## 16.8 Career / project-design implication

The strongest methodological story is not to force complex ML onto a small aggregate panel. The project instead demonstrates:

1. rigorous raw-data and disclosure auditing;
2. explicit outcome and population definition;
3. EDA-driven question formulation;
4. panel / temporal reasoning;
5. leakage prevention;
6. comparison against simple forecasting baselines;
7. interpretable statistical modelling and uncertainty;
8. a supervised-learning track whose value must be demonstrated rather than assumed.

This keeps the project technically defensible while preserving a genuine predictive component for later evaluation.

---

# 17. D7 conclusion and decisions supported

D7 found **no evidence requiring D1–D6 to be reopened**.

The following decisions are accepted in `DECISIONS.md`:

- **D7a:** primary borough-year structural / associational modelling question;
- **D7b:** required one-cohort-ahead predictive track with simple historical baselines;
- **D7c:** explicit target-reconstruction and leakage prohibition;
- **D7d:** cohort-composition admissibility and overlap rule;
- **D7e:** school/institution-location interpretation for modelling outputs;
- **D7f:** external data optional, not required for the core project.

No model or algorithm has been selected.

---

# 18. D8 — Validation Design

D8 froze the evaluation framework before model selection. The purpose is to make later model comparison auditable and to prevent the small panel from creating a false impression of validation strength.

## 18.1 Predictive sample structure

The primary panel contains 32 boroughs across seven cohorts, but a one-cohort-ahead task provides only six chronological transitions:

`2016/17->2017/18`, `2017/18->2018/19`, ..., `2021/22->2022/23`.

The borough dimension therefore does not create six independent copies of the time problem. All boroughs in a target year share the same broad annual regime.

### Decision implication

Use expanding-window / rolling-origin evaluation with boroughs retained across periods. Randomly shuffled borough-year cross-validation is not an appropriate core design because it would mix later and earlier annual regimes.

The evaluation roles are:

| Target cohort | Earlier transition rows available to a learned one-step model | D8 role |
|---|---:|---|
| 2017/18 | 0 | baseline-only reference |
| 2018/19 | 32 | development fold 1 |
| 2019/20 | 64 | development fold 2 |
| 2020/21 | 96 | development fold 3 |
| 2021/22 | 128 | development fold 4 |
| 2022/23 | 160 | locked final temporal evaluation |

The 2018/19 fold is intentionally data-poor. Excluding it simply because it is difficult would hide the actual limitation of the available panel.

---

## 18.2 Fold-local fitting and tuning

For every outer target cohort:

- the target cohort is excluded from model fitting and learned preprocessing;
- scaling, imputation, transformations and history-derived features are fitted/recomputed only from the earlier training history;
- hyperparameters must not be selected using the outer target;
- model families requiring extensive tuning are poorly matched to this dataset.

Formal elaborate nested cross-validation would create complexity without creating additional independent years. The design therefore prefers fixed or lightly tuned models. Where tuning is unavoidable, it must use a small predeclared search and earlier chronological splits inside the training history when feasible. An early fold without enough inner history uses a predeclared fixed/default setting rather than outer-fold tuning.

A borough-held-out predictive test is not part of the core question, because the intended task is forward prediction for the same stable 32-borough London system. It remains an optional separate robustness question if later interpretation requires unseen-borough generalisation.

---

## 18.3 Predictive baselines

D6 found both substantial borough persistence and common London-wide temporal movement. The predictive baseline set therefore tests these simple structures directly.

### Baseline 1 — borough persistence

`prediction(b,t+1) = adverse_rate(b,t)`

This is the principal baseline.

### Baseline 2 — London-level persistence

`prediction(b,t+1) = London_adverse_rate(t)`

Every borough receives the current London-wide rate. This asks whether borough-specific history adds value beyond the common London level.

### Baseline 3 — London level plus historical borough offset

`prediction(b,t+1) = London_adverse_rate(t) + mean_{s<=t}[adverse_rate(b,s) - London_adverse_rate(s)]`

This uses the latest London level plus the borough's average historical deviation from London. It is a simple benchmark for the two strongest structures identified in EDA without introducing a large baseline library.

---

## 18.4 Predictive evaluation metrics

The target is a continuous borough adverse rate, so the primary metric should remain directly interpretable in rate units.

### Primary

**MAE in percentage points.**

For borough `b`, absolute error is:

`abs(predicted adverse rate - observed adverse rate)`.

MAE averages this quantity across boroughs. It answers: how far off is the forecast for a typical borough?

### Secondary

**RMSE in percentage points.**

RMSE gives greater weight to occasional large misses and therefore complements MAE rather than replacing it.

### Policy-scale sensitivity

**Cohort-size-weighted MAE.**

This weights errors by the target-cohort denominator and answers a different question: how large are errors when boroughs with more pupils receive more weight? The target denominator is used only for ex-post evaluation in this sensitivity metric, not as a predictor in the core forecasting design.

### Reporting rule

Report metrics separately for every forecast target year as well as across the development folds. Because each year contains 32 boroughs, mean unweighted MAE across development years gives equal weight to each annual regime.

Report error differences versus the borough-persistence baseline. Do not use rank correlation as a core metric unless a later policy question explicitly requires ranking boroughs.

---

## 18.5 Point-in-time availability and retrospective forecasting interpretation

D7 correctly prohibited target reconstruction but left publication timing to D8.

### External DfE verification

Official DfE release histories show that destination outcomes are published substantially after the destination academic year. For example:

- the **2021/22** destination release was first published on **19 October 2023** and revised on **1 February 2024**;
- the **2022/23** destination release was first published on **24 October 2024** and revised on **27 February 2025**.

The 2022/23 release states that it follows pupils who left KS4 in 2021/22 and observes their destination activity during 2022/23.

Sources checked at D8:
- https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-destination-measures/2021-22/updates
- https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-destination-measures/2022-23/updates
- https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-destination-measures/2022-23

The supplied/current series also contains retrospective methodological revisions, already documented in §11.1 and §12.8.

### Finding

A model using the current published `y_t` to predict the next indexed outcome `y_(t+1)` is therefore a valid **retrospective chronological forecasting benchmark**, but not automatically a forecast that could literally have been issued before the `t+1` destination period occurred.

Reconstructing a genuinely real-time historical forecast would require archived release vintages and feature-specific publication dates, and would reduce the already limited information set.

### D8 protocol

For the core benchmark:

- allow outcomes and non-outcome composition indexed to `t` or earlier;
- prohibit target-period composition/denominator as predictors by default;
- prohibit all target-period outcomes and target-reconstructing variables;
- recompute history-dependent features within each training fold;
- describe the result explicitly as retrospective chronological evaluation on the harmonised series.

This is a clarification of D7b, not a reason to abandon the predictive track.

---

## 18.6 Validation of the primary explanatory track

The explanatory question is not a future-prediction task. A held-out year would therefore discard scarce information without matching the estimand. Use the full 224 borough-year panel and test whether the substantive conclusions survive reasonable changes in specification.

### Progressive structural specifications

Compare the conclusions across:

1. common cohort-year structure;
2. persistent borough structure;
3. borough + cohort-year structure;
4. borough + cohort-year structure + a small predeclared set of admissible composition variables.

This progression tests how much apparent variation remains as each source of structure is accounted for; it does not yet choose the statistical estimator.

### Year structure

The D6 London trend is non-linear, so the main specification should allow each cohort year its own common effect rather than imposing one straight time trend. A linear trend can be used as a sensitivity check.

### Denominator / precision

Retain exact adverse counts and cohort denominators in the main analysis so that borough-years with different statistical precision are not treated as identical observations by construction. The eventual estimator must be denominator-aware. An equal-weight rate specification is a useful sensitivity check because it answers whether substantive conclusions depend strongly on precision weighting.

### Composition overlap

Keep the composition set low-dimensional and predeclared. Do not use automated stepwise selection.

- disadvantage and FSM should not be treated as independent socioeconomic effects in the same primary specification;
- one can be used in the primary specification and the other as a replacement sensitivity if technically constructible;
- SEN must follow the accepted hierarchy;
- within any compositional family whose shares sum to one, use a non-redundant representation rather than entering every share unchanged.

### Influence and regime sensitivity

Required checks:

- leave one borough out at a time and assess whether the main structural/composition conclusions materially change;
- leave one cohort out at a time;
- jointly exclude **2019/20–2020/21**, the unusual low-rate period identified in D6, as a regime sensitivity.

The joint exclusion is not a causal COVID test. It asks only whether the conclusions depend heavily on that unusual period.

### Residual diagnostics

Inspect residuals by borough, cohort, fitted value and denominator, and inspect obvious within-borough temporal pattern and influential observations. Diagnostics should identify model inadequacy rather than become a licence for repeated specification searching.

---

## 18.7 Uncertainty and small-sample limits

### Explanatory track

The eventual analysis should report **95% uncertainty intervals** for important model quantities where supported by the chosen estimator.

The interval method must respect:

- repeated observations within boroughs;
- different cohort denominators;
- the fact that only seven common cohort-year regimes are observed.

Naive iid row-level standard errors would overstate the independence in the data. The exact estimator and interval construction remain for model selection rather than D8.

### Predictive track

There are only a handful of independent target years. Formal resampling cannot create new annual regimes.

Accordingly:

- show performance by forecast year;
- treat variation across years as substantive evidence about stability;
- do not report a narrow confidence interval that implies much more time information than exists;
- do not claim robust ML superiority from a tiny pooled gain or one favourable year;
- keep feature count and researcher/tuning degrees of freedom small.

The strongest evidence for incremental predictive value would be improvement over persistence that is not concentrated in only one development year and that survives the final locked evaluation. Mixed results should be reported as mixed rather than converted into a binary success claim.

---

## 18.8 Final holdout discipline

A fully pristine holdout no longer exists because 2022/23 was already examined descriptively in D6. Nevertheless, the latest cohort remains a **prospectively locked final temporal evaluation from D8 onward**.

### Rule

Reserve **2022/23** for final predictive evaluation.

Before its predictive performance is calculated, freeze:

- predictive feature definitions;
- preprocessing;
- historical benchmark definitions;
- learned-model specification;
- hyperparameter/tuning procedure;
- development/final reporting rules.

The 2018/19–2021/22 targets are the development rolling-origin folds. The final 2022/23 learned-model forecast can train on the five earlier transitions, giving 160 transition rows.

### D9a refinement

D8 originally used the phrase **model-selection holdout** because the exact predictive candidate set was still open. D9a ultimately selected one predeclared learned model plus the three already-frozen historical baselines and rejected development-stage model-family searching. The role of 2022/23 is therefore more accurately described as a **locked final temporal evaluation** of the predeclared methods. The underlying leakage-control principle is unchanged.

After the final evaluation is opened, report all predeclared results regardless of performance. Any later redesign becomes a separately labelled experiment; the original result remains in the audit trail.

---

## 18.9 D8 conclusion

D8 accepts the following decisions in `DECISIONS.md`:

- **D8a:** expanding-window chronological predictive evaluation;
- **D8b:** three simple historical predictive baselines;
- **D8c:** MAE primary, RMSE secondary, cohort-weighted MAE sensitivity;
- **D8d:** fold-local feature availability/leakage protocol and retrospective forecasting interpretation;
- **D8e:** robustness framework for the primary explanatory track;
- **D8f:** uncertainty and small-sample discipline;
- **D8g:** 2022/23 as a locked model-selection holdout from D8 onward.

D8 found no reason to reopen D1–D6 or D7a/D7c–D7f. **D7b is clarified**: the core one-step forecasting task is retrospective chronological evaluation on the harmonised series, not an operational real-time historical forecast unless publication vintages are later reconstructed.

No statistical model or algorithm has been selected.

---

# 19. D9a — Primary explanatory model selection

D9a selected the primary explanatory framework before implementation. The review followed the frozen D7/D8 question and validation design: use the exact count/denominator information, represent persistent borough and flexible cohort-year structure, keep composition parsimonious, respect repeated borough observations, and avoid complexity unsupported by seven cohorts.

## 19.1 Verified construction and remaining variation of candidate composition shares

### Check

The new D9a composition diagnostics were recomputed directly from the supplied raw CSV rather than inferred from D6 subgroup outcomes.

For the **32-LA × seven-cohort** combined mainstream + special panel, cohort-composition shares were constructed from one common destination row (`Sustained education, employment & apprenticeships`) because `cohort_count` is repeated across destination measures within a given subgroup slice. Using one destination avoids duplicate representations of the same subgroup denominator.

Primary candidate constructions:

```text
FSM share = FSM-eligible cohort_count / exact headline cohort_count
Identified-SEN share = Identified-SEN cohort_count / exact headline cohort_count
Special-school share = standalone-special headline cohort_count / combined headline cohort_count
```

For diagnostics only, male share and disadvantaged share were constructed analogously. The disadvantaged share remains approximate because the public disadvantage counts are disclosure-rounded under D5c.

To measure the variation that remains available once the intended fixed effects are included, each share `x_bt` was two-way residualised:

```text
r_bt = x_bt - mean_b(x) - mean_t(x) + overall_mean(x)
```

Because the panel is balanced, this removes each borough's persistent mean and each cohort year's common mean. The standard deviation of `r_bt` measures the scale of composition movement left to identify a composition association after borough and cohort-year fixed effects.

### Finding

| Candidate share | SD of remaining variation after borough + cohort-year removal |
|---|---:|
| FSM eligible | **1.65 pp** |
| Identified SEN | **1.62 pp** |
| Special-school share | **0.27 pp** |
| Male | **0.95 pp** |
| Disadvantaged | **2.17 pp** |

For the three proposed primary variables, pairwise correlations after the same borough/year residualisation are low:

| Pair | Correlation |
|---|---:|
| FSM vs Identified SEN | **0.14** |
| FSM vs special-school share | **0.05** |
| Identified SEN vs special-school share | **0.24** |

The six major-ethnicity shares retain residual SDs of approximately **0.72–1.76 pp** individually, but a non-redundant representation of the full composition would require roughly five share parameters because the category shares sum to one.

### Interpretation

FSM and Identified SEN retain meaningful borough-year movement after the two dominant panel structures are removed, so their coefficients are not being asked to rely only on persistent cross-borough differences. The special-school share moves less, but it has a specific structural role because the target population is the exact combination of mainstream and standalone special-school cohorts.

The low residual correlations among the three proposed primary variables do not suggest an obvious collinearity problem.

These checks establish **constructibility and available variation**, not evidence that any composition variable predicts or explains the outcome. No target outcome or 2022/23 predictive performance was used to select the composition block.

---

## 19.2 Why a grouped-binomial logistic model is the primary estimator

Each borough-year supplies an exact adverse count `Y_bt` out of an exact cohort denominator `n_bt`. The natural starting sampling model is therefore:

```text
Y_bt ~ Binomial(n_bt, p_bt)
```

where `p_bt` is the borough-year adverse probability / rate of substantive interest.

This does **not** assert that pupils are literally sampled with replacement or that real pupil outcomes are perfectly independent and identically distributed. It is a denominator-aware starting model for counts out of a known population size. Potential departures from the simple binomial variance are handled explicitly in §19.5.

The model then needs a rule for how `p_bt` depends on borough, cohort year and composition. A direct linear probability model can produce values below zero or above one, so the main model uses the logit link:

```text
logit(p_bt) = log[p_bt / (1 - p_bt)] = linear predictor
```

The logit maps probabilities in `(0,1)` to an unrestricted real-valued scale. It is the standard simple symmetric link for binomial regression and has no project-specific evidence against it. Probit would usually give similar fitted probabilities but adds no clear interpretive advantage here; complementary log-log introduces asymmetry for which the present question provides no substantive reason.

The logit is therefore a modelling device, not a claim that the physical data-generating mechanism is literally linear in log-odds. Substantive results should be transformed back to probabilities / percentage points.

---

## 19.3 Borough and cohort-year structure

### Cohort year

D6 established a non-linear London-wide pattern: broadly stable through 2018/19, lower in 2019/20–2020/21 and higher thereafter. The main model therefore gives each cohort its own categorical fixed effect instead of imposing one straight trend.

### Borough

D6 also established substantial, moderately persistent borough differences. The primary model gives each of the 32 observed boroughs its own fixed intercept.

A conventional random-intercept model would partially pool borough effects but would also impose an additional model for the borough-effect distribution and, in its standard form, assume that the latent borough effect is independent of the composition regressors. Persistent unobserved borough characteristics are plausibly related to FSM/SEN composition, so that assumption is unnecessarily strong for the core associational question.

Borough fixed effects instead absorb arbitrary persistent borough-level differences. Consequently, composition associations are identified largely from within-borough changes through time after common cohort-year movement is also removed.

This is deliberately conservative: a composition variable that differs mainly between boroughs but hardly changes within boroughs will be estimated imprecisely rather than borrowing the persistent between-borough contrast and attributing it to composition.

With only seven cohorts, no borough-specific trends, borough × year interactions, spline time effects or formal breakpoints are justified in the core specification.

---

## 19.4 Selected primary composition block

The selected primary explanatory composition block is:

1. **FSM-eligible cohort share**;
2. **Identified-SEN cohort share**;
3. **standalone special-school cohort share** within the combined population.

FSM is preferred to disadvantage in the primary regression for a technical data-quality reason: FSM cohort counts reconcile exactly to the headline cohort, while disadvantage counts are disclosure-rounded. This does not make FSM substantively more important. Disadvantage remains the leading socioeconomic descriptive measure under D6b and becomes a predeclared replacement sensitivity in the model.

Identified SEN uses the accepted top-level split and therefore avoids entering the parent `Identified SEN` category together with its nested `SEN support` / `EHC plan or statement` children.

Special-school share is retained as a structural adjustment because the combined target is exactly mainstream + standalone special. D6 showed that mainstream outcomes dominate the combined borough pattern, so the special-school-share coefficient should not be overinterpreted as a principal substantive effect.

Sex composition is omitted from the primary block: its subgroup outcome gap exists, but borough-year sex shares are comparatively close to balance and provide limited plausible scope to explain headline borough-year movements. Major ethnicity remains an important descriptive analysis, but entering a full non-redundant ethnicity composition would add roughly five parameters to a seven-cohort panel. It is therefore excluded from the primary low-dimensional block unless a later, explicitly labelled expanded-composition sensitivity is justified.

Cohort size is used as the binomial denominator, not automatically as a predictor. Adding it as a regressor would make the separate substantive assumption that larger cohorts have systematically different adverse probabilities; no such assumption is needed for the core model.

All three primary composition terms enter linearly on the logit scale. No interactions, thresholds, splines or automated nonlinear searches are included in the primary model.

---

## 19.5 Overdispersion, repeated boroughs and uncertainty

Two uncertainty problems must be distinguished.

First, the textbook binomial variance

```text
Var(Y_bt) = n_bt * p_bt * (1 - p_bt)
```

may be too small because pupils within a borough-year share schools, local conditions and unmeasured characteristics. Extra residual variation beyond this formula is **overdispersion**.

Second, the seven observations belonging to the same borough may remain correlated through time even after a borough fixed effect is included.

The main mean model remains the grouped-binomial GLM, but naive iid / model-based binomial standard errors are not sufficient for inference.

### Primary uncertainty method

Use a **borough-level block bootstrap** for common model quantities:

1. sample borough trajectories with replacement;
2. retain all seven cohort observations whenever a borough is sampled;
3. refit the full specification;
4. repeat approximately **2,000 times**, subject to convergence / numerical-stability checks;
5. construct uncertainty intervals from the bootstrap distribution using a predeclared interval rule during implementation.

Resampling whole borough trajectories preserves within-borough dependence in the resampling unit. This use of sampling with replacement is a bootstrap procedure and is unrelated to the assumptions of the binomial outcome model.

Borough-clustered robust covariance will be retained as a secondary inferential cross-check, with an appropriate finite-cluster correction, rather than as the sole uncertainty procedure with only 32 borough clusters.

### Diagnostics

Inspect:
- Pearson dispersion statistic;
- residuals against fitted probability;
- residuals against denominator;
- residual patterns by borough and cohort year;
- obvious within-borough temporal structure;
- influential observations.

A Pearson dispersion statistic materially above one suggests the simple binomial variance is too small. It does not automatically imply that the mean structure should be changed; systematic residual patterns must first be checked for mean-model misspecification.

The seven common cohort regimes remain an irreducible limitation. The block bootstrap addresses repeated borough observations but does not create additional independent years or justify broad inference to arbitrary future regimes.

---

## 19.6 How the explanatory model will answer D7a

Use the already frozen progressive structure:

```text
E1: cohort-year effects
E2: borough effects
E3: borough + cohort-year effects
E4: borough + cohort-year effects + composition
```

For the binomial models, compare **deviance reductions** when predeclared structure is added:

- `E1 -> E3`: contribution of persistent borough structure after common cohort-year structure;
- `E2 -> E3`: contribution of common cohort-year structure after persistent borough structure;
- `E3 -> E4`: additional fit from the observable composition block.

These are model-fit comparisons, not a unique additive decomposition of a total variance. Do not report statements such as “borough explains X% and year explains Y%” unless a separately defined measure later justifies that exact interpretation.

To keep the magnitude interpretable, also summarise rate-scale residuals:

```text
residual_bt = observed adverse rate_bt - fitted adverse rate_bt
```

and report in-sample explanatory MAE / RMSE in percentage points for the predeclared structural sequence. These describe fit to the observed panel; they are not predictive validation metrics.

Composition coefficients should be converted to probability-scale marginal effects for meaningful changes in a share, such as a 5-percentage-point increase, with associational wording only.

Cohort-year effects should likewise be presented using adjusted predicted probabilities / contrasts rather than raw log-odds coefficients.

If persistent borough effects are presented as adjusted borough rates, all boroughs must be evaluated under the same year/composition reference distribution. One possible model-based standardisation averages each borough's predictions over a common set of reference profiles, but the exact weighting/reference formula is a reporting decision that must be frozen before those values are calculated. No identical naturally observed composition profile is required to exist in every borough.

Residual variation is variation **not accounted for by the fitted model**. It may contain omitted structure, random variation, measurement issues or model misspecification and must not be interpreted as a measured causal effect of unobserved factors.

---

## 19.7 Predeclared explanatory robustness set

The core robustness set remains deliberately small:

1. **equal-weight rate model** with the same structural terms, testing whether conclusions depend strongly on the denominator-aware binomial treatment;
2. **disadvantage replacing FSM** as the socioeconomic composition representation;
3. **leave-one-borough-out** influence checks;
4. **leave-one-cohort-out** influence checks;
5. joint exclusion of **2019/20–2020/21** as the predeclared unusual-regime sensitivity;
6. a **single linear cohort trend** as a sensitivity to categorical year effects.

These are stability checks, not opportunities to select whichever specification gives the strongest association. Random effects, beta-binomial models, additional interactions, nonlinear composition terms or expanded ethnicity composition are not part of the core set and require a specific diagnostic or substantive reason before being added.

---

## 19.8 D9a explanatory-model conclusion

The selected primary explanatory model is:

```text
Y_bt ~ Binomial(n_bt, p_bt)

logit(p_bt)
    = alpha
    + borough fixed effect_b
    + categorical cohort-year fixed effect_t
    + beta_FSM * FSM_share_bt
    + beta_SEN * Identified_SEN_share_bt
    + beta_special * special_school_share_bt
```

Primary inference uses borough-level block-bootstrap uncertainty for common quantities; naive iid binomial uncertainty is not used as the main basis for conclusions.

The explanatory specification now answers the frozen D7a question without requiring causal interpretation, elaborate temporal structure or a model zoo. No evidence from D9a requires reopening D1–D8.

The exact standardisation formula for optional adjusted borough reporting remains a reporting detail to freeze before such summaries are calculated; it does not affect estimation of the primary model.

No 2022/23 predictive performance has been inspected or used during this selection work.

---

# 20. D9a — Predictive feature and model selection

D9a completed the predictive design without inspecting 2022/23 predictive performance. The objective was to define the smallest defensible information set and learned model under the D8 chronological-validation discipline, then remove avoidable researcher degrees of freedom before implementation.

## 20.1 Transition construction and one-cohort feature horizon

### Distinguishing feature history from training history

The predictive task uses **one-cohort-ahead transition rows**. For borough `b`:

```text
features from cohort t -> adverse-rate target in cohort t+1
```

The **feature horizon is one cohort**: for example, the forecast of 2020/21 uses the borough's 2019/20 adverse rate, FSM share and SEN share as its input features.

The **training window is expanding**: the model producing that 2020/21 forecast is fitted on all earlier observed one-step transitions:

```text
2016/17 -> 2017/18
2017/18 -> 2018/19
2018/19 -> 2019/20
```

This distinction is important. Older cohorts teach the model's coefficients; they are not supplied as additional lags for the individual 2020/21 prediction.

The four development target years therefore have learned-model training sizes of 32, 64, 96 and 128 borough-transition rows. The locked 2022/23 learned-model forecast will use the five earlier transitions, or 160 rows, once the final evaluation is opened.

## 20.2 Frozen predictive feature set

The selected learned-model inputs at forecast origin `t` are:

```text
latest adverse rate_(b,t)
FSM-eligible cohort share_(b,t)
Identified-SEN cohort share_(b,t)
```

Exact constructions:

```text
adverse_rate_(b,t)
    = adverse_count_(b,t) / exact_headline_cohort_(b,t)

FSM_share_(b,t)
    = FSM_eligible_cohort_count_(b,t) / exact_headline_cohort_(b,t)

SEN_share_(b,t)
    = Identified_SEN_cohort_count_(b,t) / exact_headline_cohort_(b,t)
```

All three variables are available from the earliest 2016/17 origin for all 32 boroughs. FSM and top-level Identified-SEN counts reconcile exactly to the headline cohort under the D5 audit rules.

### Why these three

- **Latest adverse rate** carries the strongest direct borough-persistence signal identified in D6.
- **FSM share** adds recent socioeconomic composition using exact rather than disclosure-rounded counts.
- **Identified-SEN share** adds a substantively distinct composition dimension using the accepted top-level SEN hierarchy.

### Excluded predictive features

The core learned model excludes:

- target-cohort composition, denominator or outcome information;
- additional adverse-rate lags, year-on-year changes, slopes and rolling averages;
- the two adverse components as separate lagged predictors;
- borough and cohort-year dummy variables;
- current London level and historical borough offset as additional learned regressors;
- cohort size as a predictor;
- disadvantage in addition to / instead of FSM;
- special-school share;
- sex and ethnicity composition.

The exclusions are mainly about degrees of freedom and interpretation, not claims that these variables can never predict anything. Extra lags/trends are unavailable or poorly supported in the earliest histories; borough dummies would consume almost the entire 32-row first training fold; a future cohort-year fixed effect is unknowable; London/history structure is already tested directly by B2/B3; cohort size would mainly encode borough scale; and broader composition would add parameters without enough independent target years.

No core-feature imputation is planned. Missing expected headline/FSM/SEN inputs will be treated as a preprocessing / QA failure rather than silently filled.

### Predictor-geometry check

Using predictor information only through 2021/22, pooled pairwise correlations were approximately:

| Pair | Correlation |
|---|---:|
| Adverse rate vs FSM share | **0.37** |
| Adverse rate vs Identified-SEN share | **0.29** |
| FSM share vs Identified-SEN share | **0.55** |

For the four expanding development training matrices, the intercept-plus-three-feature design was full rank throughout. Standardised condition numbers were approximately **2.09–2.30**.

**Finding:** the three predictors are related but do not show a serious numerical redundancy / multicollinearity problem. This does not prove regularisation could never help; it removes one major reason that regularisation would be required.

## 20.3 Learned estimator: median / LAD linear regression

The selected learned model is:

```text
predicted adverse_rate_(b,t+1)
    = beta_0
    + beta_1 * adverse_rate_(b,t)
    + beta_2 * FSM_share_(b,t)
    + beta_3 * Identified_SEN_share_(b,t)
```

The coefficients are fitted by **least absolute deviations**, equivalently median regression / quantile regression at `q = 0.5`.

A direct implementation is:

```text
QuantileRegressor(quantile=0.5, alpha=0, solver="highs")
```

with:

- equal weight for each borough-transition row;
- intercept included;
- no regularisation;
- no scaling;
- no imputation;
- no hyperparameter tuning;
- no prediction clipping.

### Why absolute-error regression

D8 made **unweighted borough MAE** the primary forecasting metric. Least-absolute-deviations regression uses the same absolute-error loss during fitting and gives each borough-transition equal weight. The fitted point prediction is therefore naturally aligned with the conditional-median target associated with MAE.

OLS was considered but optimises squared error instead. Ridge was also considered because regularisation can reduce small-sample variance even without severe collinearity. However, Ridge introduces a penalty-strength parameter `alpha`; the earliest chronological fold contains no earlier target year on which to tune that parameter, and later folds still contain very few independent annual regimes. A fixed `alpha` would therefore be largely conventional rather than evidence-based. Lasso / Elastic Net would add unnecessary feature-selection/tuning freedom to an already preselected three-feature model.

No nonlinear comparator is included. Trees / forests / boosting would introduce thresholds, interactions and several tuning choices without a specific diagnostic or substantive reason, while the panel contains only four development target years.

### Why this differs from the explanatory grouped-binomial GLM

The two tracks answer different questions.

For explanation, an observation such as `240 adverse pupils out of 4,000` carries more statistical precision about its borough-year probability than `48 out of 800`, even though both rates are 6%. The grouped-binomial GLM therefore uses the exact count and denominator when estimating historical associations.

For prediction, the primary evaluation question is: **how far wrong is the forecast for a typical borough?** Unweighted MAE gives each borough equal weight. An equal-weight rate regression therefore matches the primary predictive target more directly, while target-cohort-size-weighted MAE remains the predeclared policy-scale sensitivity.

## 20.4 Development stability checks before freezing the estimator

These checks used development-period information only and did not inspect 2022/23 predictive performance.

### Numerical identification

Across the four expanding training sets:

- all intercept-plus-feature design matrices had full rank;
- standardised condition numbers were approximately **2.09–2.30**.

### Independent implementation agreement

The unregularised median regression was fitted independently with scikit-learn linear-programming quantile regression and statsmodels quantile regression. Across all four development training sets, the largest absolute coefficient difference was approximately **6.3 × 10^-5**.

**Finding:** there is no evidence of an ill-defined numerical solution.

### Prediction-range check

Across the four development forecast folds, learned-model predictions ranged approximately from **3.20% to 8.31%**. No prediction fell below 0% or above 100%.

The no-clipping rule is therefore retained. If invalid probabilities later appear, they remain visible as a diagnostic rather than being silently repaired.

### Earliest-fold leave-one-borough stability check

The first learned training fold has only 32 rows, so it is the most vulnerable to individual observations. Refit the 2016/17->2017/18 training model after omitting each borough in turn and compare the resulting 2018/19 forecasts with the full-fit forecasts.

Results:

- median of the maximum forecast change produced by each omission: approximately **0.037 pp**;
- 95% of individual forecast changes: below approximately **0.160 pp**;
- largest observed change from any one omission: approximately **0.465 pp**.

This shows genuine small-sample sensitivity, but not general numerical failure. Coefficients also move as the expanding window adds new annual regimes; such movement is expected and is not interpreted as a timeless structural parameter change.

### Diagnostic-trigger rule

Before 2022/23 is opened, reopen the learned estimator only if an objective failure appears, such as:

- loss of full rank;
- solver failure or materially inconsistent solutions across implementations;
- non-finite coefficients / predictions;
- materially invalid probability predictions outside 0–100%;
- preprocessing / QA failure;
- another specific structural diagnostic that makes the frozen linear specification untenable.

Ordinary coefficient movement as training history expands is not, by itself, a licence to redesign the model.

## 20.5 Baseline comparison and development/final evaluation role

The predictive experiment retains the three D8 baselines:

```text
B1: borough persistence
B2: London-level persistence
B3: London level + expanding historical borough offset
```

and adds one learned model:

```text
M1: median/LAD regression on latest adverse rate + FSM share + Identified-SEN share
```

These methods intentionally represent different forecasting hypotheses rather than an algorithm library.

### Development role

For targets **2018/19–2021/22**, report for every method:

- MAE by target year and mean MAE across years;
- RMSE by target year and mean RMSE across years;
- target-cohort-size-weighted MAE as sensitivity.

Development results are used to understand temporal stability and to expose objective diagnostic failures. They are **not** used to search for whichever model family happens to win across four years. No practical-effect threshold, `2/4`-years rule, MAE/RMSE tie-break or simplicity ranking is used for model selection.

### Final 2022/23 role

Once implementation has reproduced the frozen definitions, carry the same four methods unchanged into **2022/23**:

- M1 is fitted using all five earlier one-cohort transitions permitted through 2021/22;
- B1–B3 are constructed mechanically using information through 2021/22;
- report primary MAE, secondary RMSE and weighted-MAE sensitivity for all four.

The final comparison directly answers whether the predeclared learned method improves on simple historical benchmarks in the locked later cohort. If a baseline performs better, report that result rather than redesigning M1.

### Interpretation boundaries

- A small average advantage or one-year improvement is not evidence of broad/robust superiority with so few annual regimes.
- If M1 beats B3, do not claim that FSM/SEN provide incremental predictive value **conditional on B3**. M1 and B3 use different historical information sets.
- Composition coefficients are forecasting parameters, not causal effects.
- No method can know an unobserved future London-wide shock; retrospective explanatory year effects cannot be treated as forecast-time inputs.
- The current benchmark remains retrospective on a harmonised/revised series rather than a reconstructed real-time historical forecast.

## 20.6 D9a predictive conclusion

The predictive specification is now frozen as:

```text
feature horizon: one cohort
training window: expanding earlier one-cohort transitions

features at t:
    latest borough adverse rate
    FSM-eligible share
    Identified-SEN share

target:
    borough adverse rate at t+1

learned model:
    unregularised median / LAD linear regression

preprocessing:
    no imputation
    no scaling
    no tuning
    no clipping

comparators:
    B1 borough persistence
    B2 London persistence
    B3 London + historical borough offset
    M1 learned LAD model
```

No evidence from the predictive D9a review requires reopening the explanatory D9a specification or D1–D8's substantive analytical choices. The only refinement to D8 is terminological/procedural: because D9a selected one predeclared learned model rather than a model family to choose from, 2022/23 is now described as a **locked final temporal evaluation** rather than a model-selection holdout. The anti-leakage / no-retuning rule is unchanged.

No 2022/23 predictive performance was calculated or used during D9a selection.

---

# 21. D9b implementation checkpoint — modelling tables, baselines and M1

## 21.1 Implementation scope completed

The D9b predictive implementation checkpoint has been completed under the frozen D1–D9a definitions.

Implemented components:

- London Local Authority source extraction for the seven analysis cohorts;
- exact headline borough-year outcome construction;
- FSM and Identified-SEN composition variables;
- standalone special-school cohort share;
- approximate disadvantaged cohort share sensitivity variable;
- complete explanatory modelling table;
- one-cohort-ahead predictive transition table for development;
- predictive baselines B1–B3;
- frozen learned predictive model M1 and its four expanding-window development folds;
- reusable QA checks and a single `src/run_pipeline.py` entry point;
- reproducible development prediction and model-diagnostic CSV outputs.

The implementation remains deliberately simple and function-based. No predictive accuracy or model-comparison metric has yet been calculated during this D9b implementation checkpoint.

## 21.2 Explanatory modelling table

The explanatory table contains the frozen 32-LA × 7-cohort panel:

- **224 borough-year rows**;
- cohorts **2016/17–2022/23**;
- one row per Local Authority × cohort;
- exact headline cohort denominator;
- exact adverse count and adverse rate;
- FSM-eligible cohort share;
- Identified-SEN cohort share;
- standalone special-school cohort share;
- approximate disadvantaged cohort share sensitivity variable.

Hard QA confirms:

- expected row count and all seven cohort years;
- exactly 32 boroughs per cohort;
- unique borough-year grain;
- stable one-to-one LA-code / LA-name mapping;
- no missing required modelling fields;
- valid count and rate bounds;
- exact headline destination accounting;
- exact FSM and top-level SEN source accounting;
- exact combined-population = mainstream + standalone-special accounting.

The disadvantaged cohort share remains explicitly approximate because its displayed cohort counts are disclosure-rounded.

## 21.3 Development predictive transition table

A separate one-cohort-ahead transition table was constructed for predictive development.

Each row represents:

```text
borough b at cohort t
    ↓
features known at t
    ↓
adverse-rate target at t+1
```

Development transitions are restricted to:

```text
2016/17 → 2017/18
2017/18 → 2018/19
2018/19 → 2019/20
2019/20 → 2020/21
2020/21 → 2021/22
```

This produces:

- **160 transition rows**;
- 5 transitions × 32 boroughs;
- feature variables from cohort `t` only:
  - borough adverse rate;
  - FSM-eligible share;
  - Identified-SEN share;
- target adverse rate from cohort `t+1`;
- target cohort denominator retained only for later weighted-MAE evaluation.

The locked **2022/23 target is not materialised in the development transition table**.

QA confirms:

- exactly the five permitted transition pairs;
- exactly 32 boroughs in each transition;
- unique borough-transition grain;
- no missing predictive fields;
- valid rate and denominator ranges;
- 2022/23 absent from development feature and target years.

An independent source-alignment check also verifies that, for every transition:

- feature values match the same borough's original cohort-`t` row;
- target adverse rate and target denominator match the same borough's original cohort-`t+1` row.

This check does not reproduce the original `shift()` transformation. Instead it independently looks up the explicitly stored `feature_year` and `target_year` in the verified borough-year table.

## 21.4 Baseline implementation

The three frozen predictive baselines have been implemented.

### B1 — borough persistence

```text
prediction(b, t+1) = adverse_rate(b, t)
```

### B2 — London-level persistence

```text
prediction(b, t+1) = London_adverse_rate(t)
```

The London rate is calculated from aggregate exact counts:

```text
sum_b adverse_count(b,t)
--------------------------
sum_b cohort_count(b,t)
```

rather than as an unweighted mean of borough rates.

### B3 — London level + historical borough offset

```text
prediction(b, t+1)
    =
London_adverse_rate(t)
    +
mean_{s <= t}[
    adverse_rate(b,s) - London_adverse_rate(s)
]
```

The borough offset is therefore expanding-history only: information from cohorts after the feature year cannot enter the prediction.

## 21.5 Baseline QA

Baseline QA was implemented separately from the prediction construction where practical.

For B1:

- prediction is checked directly against the feature-year borough adverse rate.

For B2:

- the implementation constructs the London rate from aggregate counts;
- QA reconstructs the same quantity independently as a cohort-size-weighted average of borough adverse rates;
- all 32 boroughs within a feature year are checked to receive one common London prediction.

For B3:

- implementation uses grouped expanding historical borough offsets;
- QA does **not** repeat the expanding calculation;
- instead, each transition is checked row-by-row by explicitly selecting that borough's history satisfying `year <= feature_year`;
- annual borough-minus-London offsets are reconstructed and averaged;
- later cohorts are therefore explicitly excluded from the expected prediction.

All baseline QA checks pass.

## 21.6 M1 development implementation

The frozen M1 learned model is implemented in `src/youth_offer/predictive.py` as an equal-row-weight median/least-absolute-deviations regression using `QuantileRegressor(quantile=0.5, alpha=0.0, fit_intercept=True, solver="highs")`.

It fits exactly three cohort-`t` predictors: `feature_adverse_rate`, `feature_fsm_share`, and `feature_identified_sen_share`. No additional predictors, borough/year effects, feature scaling, regularisation, imputation, hyperparameter tuning or prediction clipping are used.

The expanding-window development target years are **2018/19–2021/22**. The first available 2017/18 target is baseline-only and is used as M1 training history, not as an M1 development test fold.

| M1 test target | Training rows | Test rows | Latest training target | Minimum prediction | Maximum prediction | Predictions outside [0,1] |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| 2018/19 | 32 | 32 | 2017/18 | 3.51% | 8.13% | 0 |
| 2019/20 | 64 | 32 | 2018/19 | 3.83% | 8.31% | 0 |
| 2020/21 | 96 | 32 | 2019/20 | 3.20% | 7.31% | 0 |
| 2021/22 | 128 | 32 | 2020/21 | 3.21% | 6.90% | 0 |

The recorded fitted parameters, rounded to six decimals, are:

| M1 test target | Intercept | Adverse-rate coefficient | FSM coefficient | SEN coefficient |
| --- | ---: | ---: | ---: | ---: |
| 2018/19 | -0.001125 | 0.853775 | -0.028066 | 0.096487 |
| 2019/20 | 0.000723 | 0.842362 | -0.011635 | 0.071175 |
| 2020/21 | 0.003459 | 0.811817 | -0.006020 | 0.041219 |
| 2021/22 | 0.010002 | 0.750481 | 0.005451 | 0.010136 |

These parameter changes are descriptive fit diagnostics, not causal effect estimates and not grounds by themselves for reopening the frozen model family. Ranges shown above are rounded for display; unrounded diagnostics are generated by the pipeline.

## 21.7 M1 QA and assembled development predictions

The reusable validation rules live in `src/youth_offer/qa.py`. The `src/run_pipeline.py` entry point runs those checks at the point where each table, fold or prediction set is produced; the pipeline does not duplicate their substantive definitions.

The implemented checks passed for all four development M1 folds, including:

- exact predeclared three-feature list, with non-missing training and test inputs;
- chronological separation of training and held-out target cohorts;
- expected training sizes of 32, 64, 96 and 128 and exactly 32 test rows per fold;
- three finite fitted coefficients and a finite intercept;
- full rank **4** for the training design matrix, including the intercept column;
- exactly 32 finite predictions per held-out target year;
- prediction-range diagnostics with zero observations outside [0,1], **without clipping**.

The four held-out M1 test folds are assembled into **128 borough × target-year prediction rows**. Additional assembled-output QA passed: correct year-specific counts, no duplicate borough–target-year keys, finite predictions and equality of all original transition fields against the corresponding 128 source transition records. This checks source-row preservation, while the separate fold checks address model fitting and chronology.

## 21.8 Reproducible outputs, leakage status and next step

The refactored runner `src/run_pipeline.py` completed successfully from the repository root and produced:

- `outputs/development/m1_predictions.csv` — 128 held-out development prediction rows;
- `outputs/development/m1_diagnostics.csv` — four fold-level fit and prediction-range diagnostic rows.

The `outputs/` directory is excluded by `.gitignore`, since these are regenerable intermediate artefacts; the implementation and this checkpoint log preserve how to reproduce them. Baseline predictions B1–B3 are implemented and separately QA-verified.

**No development predictive performance metric has yet been calculated as part of D9b implementation.** In particular, no M1-versus-baseline development MAE, RMSE or weighted-MAE comparison has been performed here. The next step is the predeclared development evaluation of B1–B3 and M1, using the frozen metric definitions and the four development target years; results are diagnostic, not a licence to retune or select a model family.

The **2022/23 final temporal evaluation remains locked**: no 2022/23 target appears in development transitions, and no final-year predictive error has been calculated or inspected. The explanatory borough-year source table may still contain 2022/23 for its separate descriptive/explanatory purpose. Reopening any frozen predictive specification requires a specific documented objective diagnostic failure before final evaluation.

---

# 22. D9c — Development Performance Evaluation evidence

## 22.1 Inputs, alignment and metric definitions

The predictive development evaluation uses four expanding-window M1 test cohorts, 2018/19–2021/22, each containing the same 32 London boroughs. It combines the 128 held-out M1 forecasts with B1–B3 forecasts using unique `new_la_code × feature_year × target_year` keys, preserving both input copies of the target adverse rate and target-cohort denominator for source agreement checks.

For each *target year* and each method, calculate unweighted borough MAE and RMSE and target-cohort-denominator-weighted MAE from the 32 observed rates and predictions. Multiply rate-unit errors by 100 to report percentage points. Report the **arithmetic average of four annual values** for every metric; in particular, mean annual RMSE is *not* pooled 128-row RMSE, and mean annual weighted MAE is *not* a pooled-across-years weighted MAE. Target-cohort count is used as an ex-post evaluation weight and never as an M1 predictor.

Produced outputs under ignored `outputs/development/`: `evaluation_table.csv` (128 rows), `annual_metrics.csv` (16 year–method rows), `summary_metrics.csv` (four method rows), alongside D9b `m1_predictions.csv` and `m1_diagnostics.csv`.

## 22.2 Observed development metrics

All values below are percentage points. A negative MAE difference from B1 indicates lower MAE.

| Target | Method | MAE | RMSE | Weighted MAE | MAE − B1 |
|---|---|---:|---:|---:|---:|
| 2018/19 | B1 | 0.638654 | 0.838228 | 0.614254 | 0.000000 |
| 2018/19 | B2 | 1.063366 | 1.345478 | 1.046259 | +0.424712 |
| 2018/19 | B3 | 0.552739 | 0.713571 | 0.545086 | −0.085915 |
| 2018/19 | M1 | 0.684038 | 0.933547 | 0.647226 | +0.045385 |
| 2019/20 | B1 | 0.856626 | 1.108953 | 0.748049 | 0.000000 |
| 2019/20 | B2 | 0.965666 | 1.187146 | 0.955942 | +0.109040 |
| 2019/20 | B3 | 0.800608 | 0.997435 | 0.744405 | −0.056017 |
| 2019/20 | M1 | 0.808823 | 1.039947 | 0.710365 | −0.047803 |
| 2020/21 | B1 | 0.581264 | 0.723614 | 0.534507 | 0.000000 |
| 2020/21 | B2 | 0.733420 | 0.964057 | 0.733057 | +0.152156 |
| 2020/21 | B3 | 0.494217 | 0.606209 | 0.464696 | −0.087047 |
| 2020/21 | M1 | 0.524858 | 0.653492 | 0.481461 | −0.056406 |
| 2021/22 | B1 | 0.787596 | 0.972902 | 0.771081 | 0.000000 |
| 2021/22 | B2 | 1.057107 | 1.300378 | 1.050812 | +0.269511 |
| 2021/22 | B3 | 0.705403 | 0.848497 | 0.707364 | −0.082193 |
| 2021/22 | M1 | 0.805188 | 0.989690 | 0.793886 | +0.017592 |

| Method | Mean annual MAE | Mean annual RMSE | Mean annual weighted MAE | Mean MAE − B1 |
|---|---:|---:|---:|---:|
| B1 | 0.716035 | 0.910924 | 0.666973 | 0.000000 |
| B2 | 0.954890 | 1.199265 | 0.946517 | +0.238855 |
| B3 | 0.638242 | 0.791428 | 0.615388 | −0.077793 |
| M1 | 0.705727 | 0.904169 | 0.658234 | −0.010308 |

## 22.3 Paired M1–B3 error diagnostics

Define per-observation difference as `abs(M1 prediction − observed) − abs(B3 prediction − observed)` in percentage points. Positive favours B3. These are descriptive diagnostics, not model-selection thresholds or independent inferential trials.

| Target | Mean difference (pp) | Median (pp) | B3 smaller error | M1 smaller error |
|---|---:|---:|---:|---:|
| 2018/19 | +0.131299 | +0.046865 | 19 | 13 |
| 2019/20 | +0.008215 | −0.059473 | 12 | 20 |
| 2020/21 | +0.030641 | +0.024595 | 17 | 15 |
| 2021/22 | +0.099784 | +0.040823 | 21 | 11 |
| Total/mean | +0.067485 | — | 69 | 59 |

B3 has lower annual MAE than M1 in all four years but smaller error in only 69/128 individual borough-year observations. In 2019/20 M1 has the smaller error in 20/32 boroughs while B3 has slightly lower mean MAE, showing that the magnitude and frequency of wins are different questions. Some individual M1 disadvantages relative to B3 exceed one percentage point. This does not establish a stable future advantage.

## 22.4 Validation evidence and limitations

- The common evaluation table is checked for exact expected key coverage, uniqueness and equality to source M1/B1–B3 keys; independent key-indexed comparison checks every merged target, denominator and prediction against its source.
- Annual QA validates exactly four years × four methods, independently recomputes MAE, RMSE and weighted MAE using scikit-learn, and checks B1-relative differences. Summary QA checks four method rows, arithmetic averaging across four years and signed differences.
- Synthetic known-answer checks cover all four methods, weighting and B1 differences. Deliberately altered prediction/target and metric values are rejected by the corresponding QA checks. The source/pipeline QA passed after adding source-value preservation.
- All method definitions, cohort windows and model parameters remain frozen. The effective temporal evidence is four distinct target-year regimes, not 128 independent experiments. No narrow model-superiority confidence interval, significance claim or causal explanation is warranted.
- B3 and M1 use different historical information sets. Their comparison does not identify the incremental contribution of FSM or SEN conditional on B3. The benchmark is retrospective on the harmonised published series; data-release timing does not support claims about real-time operational forecasts.
- The 2022/23 predictive evaluation remains locked. It was **not** constructed, scored or inspected during D9c. Presence of the cohort in separate explanatory/EDA tables does not release the predictive lock.

**Reproduction:** From the repository root, run `python -m unittest discover -s tests -p 'test_development_evaluation.py' -v` for self-contained synthetic QA, followed by `python src/run_pipeline.py` to regenerate ignored development outputs and `python scripts/development_error_diagnostics.py` to recreate the M1–B3 borough-error comparisons in §22.3. Compare the generated development metric tables with the recorded values above. Source-code and documentation commit/push status is tracked by Git, not implied by this evidence log.

---

# 23. D9d — Explanatory E1–E4 implementation, QA and first-pass diagnostics

## 23.1 Scope and model specification

`src/youth_offer/explanatory.py` implements the four D9a5 grouped-binomial logistic GLMs using the exact borough-year adverse count `Y_bt` and denominator `n_bt` as a two-column response `[Y_bt, n_bt − Y_bt]`. The response means **not in a recorded sustained destination**, including activity not captured; it is **not a directly measured NEET rate**. The explanatory analysis includes all seven cohorts, 2016/17–2022/23, across 32 boroughs (224 rows).

- **E1:** intercept plus six cohort-year indicators; 2016/17 is the reference.
- **E2:** intercept plus 31 borough indicators; the lexicographically first `new_la_code` is the reference.
- **E3:** intercept, 31 borough indicators and six year indicators.
- **E4:** E3 plus three untransformed 0–1 shares: `fsm_share`, `identified_sen_share` and `special_school_share`. The composition columns are explicitly cast to NumPy-compatible `float64` before fitting.

The models have no borough-by-year interactions or borough-specific trends. E4 remains associational, with borough and categorical year fixed effects. No change to the frozen D9a model or feature set was made.

## 23.2 Fitting and structural evidence

The locally reported fits converged and the model matrix was confirmed full-column-rank. The implemented shared `assert_explanatory_glm_structure()` checks shape, convergence, model and residual degrees of freedom, and that `matrix_rank(X) == number_of_columns`; the equality is essential because merely asserting a nonzero rank would fail to detect collinearity.

| Model | Matrix rows × columns | Rank | Model df | Residual df | Pearson chi-square / residual df |
|---|---:|---:|---:|---:|---:|
| E1 | 224 × 7 | 7 | 6 | 217 | approximately 6.5 |
| E2 | 224 × 32 | 32 | 31 | 192 | 2.411062 |
| E3 | 224 × 38 | 38 | 37 | 186 | 1.583911 |
| E4 | 224 × 41 | 41 | 40 | 183 | 1.596351 |

The relatively high ratios motivate later overdispersion and residual diagnostics; they do **not** validate naive iid-binomial uncertainty or establish comparative model superiority. E4's marginally higher ratio than E3 is not, on its own, a verdict on its incremental fit: the statistic is divided by differing residual degrees of freedom. Deviance reductions and rate-scale residuals were not part of the initial fitting checkpoint; subsequent evidence is in §23.5.

## 23.3 Independent numerical verification

Separate `src/youth_offer/qa.py` checks compare fitted outputs with properties expected of the frozen binomial likelihood:

| Model | Check | Maximum absolute discrepancy reported |
|---|---|---:|
| E1 | Predicted probabilities versus exact cohort-size-pooled annual rates (seven years) | `1.249 × 10^-16` in rate units |
| E2 | Predicted probabilities versus exact cohort-size-pooled borough rates (32 boroughs) | `4.137 × 10^-14` in rate units |
| E3 | Summed observed versus fitted adverse counts by borough | `9.013 × 10^-10` pupils |
| E3 | Summed observed versus fitted adverse counts by cohort year | `2.237 × 10^-10` pupils |
| E4 | Largest absolute score component across 41 columns, `X.T @ (Y − n * fitted_probability)` | `1.306 × 10^-9` count-weighted predictor units |

E1/E2 pooled-rate identities and the E3 count-margin identities use directly aggregated observed totals; E4's score test verifies the first-order likelihood conditions, including the intercept, borough, year and composition columns. These are strong numerical checks but not evidence that the grouping, outcome interpretation, model assumptions or standard errors are automatically correct. Structural convergence/full rank and independent source-table QA are retained as separate checks.

`tests/test_explanatory.py` contains four deterministic, raw-data-independent `unittest` tests: model fitting and numerical identities; frozen design-matrix columns, reference categories and row alignment (including shuffled rows, non-default index and a nullable `Float64` input); deliberate adverse-count corruption rejected by all four numerical QA functions; and a duplicated E4 predictor rejected by the full-rank QA. The user reported the four new tests and the existing test suite passing locally. A subsequent full end-to-end pipeline run should be confirmed separately before committing; its success is not asserted by the test results alone.

## 23.4 Reproduction, limits and next work

From the repository root:

```bash
python -m unittest discover -s tests -p 'test_explanatory.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
python src/run_pipeline.py
```

The pipeline builds and checks the common explanatory model table, then fits and structurally/numerically verifies E1–E4 before performing the separate, development-only predictive workflow. Existing development prediction and evaluation definitions are unchanged. The last command checks the integrated pipeline. The project author subsequently reported that the final local pipeline and test suite passed after diagnostic QA additions; this review did not independently rerun the complete raw-data pipeline.

**Outstanding frozen analyses:** §23.5 records the completed descriptive comparisons and first-pass diagnostics. Next, define probability-scale effects/contrasts and any optional reference distribution, implement whole-borough block-bootstrap inference (approximately 2,000 refits subject to stability), the borough-clustered covariance cross-check and the full D9a6 sensitivity set. Do not make causal or naive-binomial inference claims.

**Boundary:** The seven-cohort 2022/23 observation is permitted in the *explanatory* track. This does **not** release the 2022/23 *predictive* final temporal evaluation. No final-cohort predictive error, method comparison or performance claim is part of D9d. Git commit/push status is independent of the analytical evidence recorded here.


## 23.5 Subsequent D9d fit comparison, residual and influence diagnostics — locally verified

**Scope and provenance.** All four frozen grouped-binomial explanatory fits use the same 224 borough × KS4-cohort records. The numerical results below were reported from the local pipeline by the project author after QA and are **in-sample**, not predictive evaluations. Six synthetic diagnostic tests, the full local test suite and the integrated pipeline were reported passing; this documentation update does not claim an independent remote execution of the raw-data pipeline.

### Fit comparison

| Model | Number of parameters | Binomial deviance | Equal-borough-year MAE (pp) | Equal-borough-year RMSE (pp) |
|---|---:|---:|---:|---:|
| E1 — cohort-year FE | 7 | 1462.731158 | 0.937282 | 1.200378 |
| E2 — borough FE | 32 | 463.408094 | 0.567593 | 0.716440 |
| E3 — borough + cohort-year FE | 38 | 295.864622 | 0.447924 | 0.566222 |
| E4 — E3 + composition | 41 | 293.374646 | 0.447420 | 0.564119 |

| Nested comparison | Deviance reduction | Added parameters | Meaning |
|---|---:|---:|---|
| E1 → E3 | 1166.866536 | 31 | Borough structure improves fit conditional on common cohort years |
| E2 → E3 | 167.543472 | 6 | Common cohort-year structure improves fit conditional on borough |
| E3 → E4 | 2.489976 | 3 | Composition adds little further in-sample fit conditional on both FE sets |

Deviance reduction is the **reduced-model deviance minus full-model deviance**, with all 224 rows held constant. These are **conditional, nested fit comparisons**, not an additive partition of explained variance or a likelihood-ratio inference under valid independent-binomial variance. No naive p-values are interpreted. The composition block's modest fit increment alone neither proves absence of association nor justifies its post-hoc removal.

MAE/RMSE are computed from observed adverse rate minus fitted probability, multiplied by 100 to obtain **percentage points**; borough-years receive equal weight **in these error summaries**. The fitted grouped-binomial likelihood continues to use the exact adverse counts and denominators. These are not out-of-sample predictive scores.

### E4 residual distribution and dependence screening

- **Pearson dispersion:** `sum(Pearson residual²) / 183 = 1.596351`, above the simple independent grouped-binomial benchmark. This is extra-binomial variation, not by itself proof of an incorrectly specified mean.
- **Residual versus fitted probability / denominator plots:** no conspicuous overall curvature or denominator-related pattern on visual inspection. This does not rule out subtler misspecification or heterogeneous variance.
- **Borough × year heatmap:** some runs of same-signed residuals, reversals and isolated extreme borough-years. Because the borough/year fixed-effect score equations constrain aggregated **observed-minus-fitted counts**, such residual sign patterns are not independently identified changes in borough trajectories.
- **Within-borough descriptive lag-1 correlation:** `-0.035173` for `32 × 6 = 192` overlapping adjacent-cohort Pearson-residual pairs. There is little **pooled linear** persistence, but this does not establish residual independence or rule out borough-specific temporal effects. The seven observations per borough, overlapping pairs and FE fitting constraints limit interpretation.

### E4 single-row influence screening

`result.get_influence().summary_frame()` supplied GLM leverage (`hat_diag`) and approximate Cook's distance (`cooks_d`). QA checked index alignment, 224 rows, finite non-negative Cook's distances, leverage within [0, 1], and leverage sum = **41** fitted parameters (average leverage ≈ 0.1830).

| Borough | Cohort | Pearson residual | Leverage | Cook's distance |
|---|---|---:|---:|---:|
| Enfield | 2016/17 | -3.570312 | 0.212428 | 0.106478 |
| Tower Hamlets | 2019/20 | +3.320950 | 0.184279 | 0.074496 |
| Southwark | 2017/18 | +3.274995 | 0.171102 | 0.065146 |
| Havering | 2018/19 | -2.921832 | 0.180027 | 0.055752 |
| Camden | 2021/22 | -2.910220 | 0.177701 | 0.054287 |
| Harrow | 2019/20 | +2.912018 | 0.156377 | 0.045444 |
| Hackney | 2022/23 | +2.262182 | 0.211837 | 0.042564 |
| Enfield | 2022/23 | -2.114882 | 0.226861 | 0.041403 |
| Havering | 2022/23 | +2.199439 | 0.202322 | 0.037517 |
| Brent | 2020/21 | -2.457722 | 0.166723 | 0.035375 |

These are the **ten highest** local Cook's distances. Their leverage is not exceptionally high relative to the model average, while many have large residuals. Influence is an approximate **one-observation deletion** measure; it is **not** a substitute for deleting whole borough trajectories or cohort years. Repeated observations, overdispersion and common-year shocks limit simplistic Cook's-distance thresholds. No observations were deleted and the E4 mean specification was not changed.

### Verification, reproducibility and remaining analysis

- `src/youth_offer/explanatory_diagnostics.py` contains the fit comparisons, rate-scale errors, Pearson residuals/dispersion, residual table, lagged-residual pairs/correlation and influence table. `src/youth_offer/explanatory_plots.py` contains the two-panel scatterplot and borough × year heatmap. `src/run_pipeline.py` calls these after fitting E1–E4.
- The `qa.py` checks compare individual Pearson residuals and Pearson chi-square with `statsmodels`, check row alignment and reconstruct MAE/RMSE, and check leverage trace/ranges and finite Cook's distances. The **six** raw-data-independent tests in `tests/test_explanatory_diagnostics.py` cover known rate-error and deviance values, source and prediction-index mismatches, Pearson residual/dispersion known answers and invalid inputs, and lag-pair construction on a shuffled complete panel.
- **Locally reported validation:** all six diagnostic tests passed, as did the full test suite and `python src/run_pipeline.py` after final input-validation fixes. To reproduce, provide `data/raw/key-stage-4-destination-measures_2023-24.zip` and run `python -m unittest discover -s tests -p 'test_*.py' -v` and `python src/run_pipeline.py` from the repository root. Generated plots under `outputs/explanatory/` are git-ignored; numeric summaries currently print to standard output and are recorded here rather than exported as a separate diagnostic results file.
- **Conclusion / checkpoint:** E3's borough/year structure improves in-sample fit substantially; the E4 composition block yields only a small extra deviance reduction. Dispersion above one and several influential borough-years require planned inferential and group-deletion sensitivity checks. No evidence currently warrants reopening the frozen E4 mean specification, but full adequacy, effect significance, independent errors, causality and predictive utility have **not** been established.
- **Pending frozen work:** define probability-scale associations and adjusted cohort-year contrasts; implement approximately 2,000 whole-borough-trajectory bootstrap refits subject to stability, a borough-clustered covariance cross-check, and all six D9a6 sensitivity checks (equal-weight rate regression, disadvantage replacing FSM, leave-one-borough, leave-one-cohort, joint 2019/20–2020/21 regime exclusion and linear cohort trend). Resampling boroughs does not create new independent common-year regimes. Freeze a common reference distribution before optional adjusted borough summaries.
- **Predictive holdout boundary:** using 2022/23 outcomes in all-seven-cohort **explanatory** fits and their diagnostics is explicitly permitted. No 2022/23 **predictive** score, forecast-method comparison or final evaluation was constructed or examined. That boundary remains locked until the separate pre-final audit and formal release.

---

# 24. D9e — Explanatory estimands, inference and empirical checkpoint (accepted methodology; exported results verified)

## 24.1 Purpose, provenance and scope

This design review follows the verified E1–E4 explanatory fits, D9d2 diagnostics and the frozen D7a/D8e–D8f/D9a rules. It defines **what** model quantities would mean before estimating uncertainty or running robustness checks. Source inspection used GitHub branch `d9-implementation` at commit `28289ecd0a2602e32026df75516a3ed31336b845`; the raw ZIP was independently read for the 224 target borough–cohort **composition** profiles only. **At this original design-review stage**, no D9e fitted effects, inferential intervals or robustness results were computed, and no 2022/23 predictive evaluation was opened. **The subsequent completed empirical checkpoint is documented in §24.6–§24.10.**

Two reportable questions follow: (i) How did the **model-adjusted adverse probability** differ across the seven observed cohorts for a common borough/composition reference? (ii) What **modelled percentage-point probability difference** accompanies a predeclared, plausible change in one composition share, conditional on borough/year fixed effects and the other shares? These are associations, not causal, individual-level or forecasting claims.

## 24.2 Common standardisation and probability-scale definitions

Let the 224 original explanatory rows index reference profiles `i=(b,t)` with composition vector `x_i=(fsm_share, identified_sen_share, special_school_share)` and fixed borough ID `b(i)`; give every reference profile weight `1/224` (hence every borough is weighted equally across its seven profiles). Let `g(z)=1/(1+exp(-z))`, and `eta(b,s,x)` be E4's fitted linear predictor for borough `b`, evaluated at cohort year `s` and composition `x`.

**Adjusted year probability:** `P_s = (1/224) * sum_i g(eta(b(i),s,x_i))`. Report `100*P_s` (%) for all seven years; report `100*(P_s-P_201617)` (pp) for each later year and `100*(P_s-P_previous)` (pp) for each adjacent pair. The endpoint `2022/23 − 2016/17` is the headline contrast. Evaluating the **same** borough/composition multiset for each `s` isolates the year fixed-effect contrast *within E4*, rather than changing population composition. It is not an observed London-wide pupil-weighted rate. Different valid references change percentage-point magnitudes because logit is nonlinear, although no-interaction E4 implies each profile's year contrast shares the same sign.

**Composition difference for variable `k` and increment `d_k`:** `M_k(d_k) = (100/224) * sum_i [g(eta(b(i),t(i),x_i + d_k*e_k)) - g(eta(b(i),t(i),x_i))]` (pp). The comparison changes one share, holding its borough/year and other shares fixed. The mean is the average of *paired probability differences*, not a difference in log-odds. E4's constant logit slope implies no genuinely heterogeneous coefficient signs across profiles; nonlinearity creates different probability-point sizes.

A fixed profile such as Camden in 2016/17 is mathematically valid but answers a Camden-profile question. The 224 equally weighted profiles are more suitable for the predeclared **average-borough** structural question. Pupil-weighted standardisation would answer a different policy question and is not primary. Optional *adjusted borough rankings* would require an additional separate common year/composition reference and are **not selected** by this specification.

## 24.3 Independent composition-size check against the raw ZIP

An audit-only read selected the seven target cohorts, London Local Authority rows, the frozen combined population, one sustained-destination row per relevant breakdown to avoid duplicated denominators, and the exact standalone-special population. It reconstructed the 224 original composition profiles from exact group `cohort_count` values. The comparisons below are input support checks, **not model effects**:

| Covariate | Min share | Max share | SD after two-way borough/year demeaning | D9e increment |
|---|---:|---:|---:|---:|
| FSM eligible | 0.062046 | 0.477124 | 0.01646 | +0.0200 |
| Identified SEN | 0.047960 | 0.243697 | 0.01624 | +0.0200 |
| standalone special-school share | 0.003677 | 0.055556 | 0.00272 | +0.0025 |

All three adjusted-share comparisons keep each of the 224 values within `[0,1]`. The residual SDs reproduce D9a's rounded figures (1.65, 1.62 and 0.27 percentage points respectively). These simple bounds do **not** prove that every hypothetical joint composition is frequently observed; evaluate practical support during QA and interpret the resulting modelled comparisons as conditional, not interventions. The special-school association is a structural adjustment rather than a principal policy conclusion.

## 24.4 Borough-bootstrap target, repeated fixed effects and interpretation

D9a4 freezes whole-borough resampling, approximately 2,000 refits, with borough-clustered covariance as a cross-check. With E4 **borough fixed effects**, resampling rows independently is invalid, and evaluating the original 224 fixed borough profiles in a replicate omitting some boroughs requests **unestimated FE**. The coherent *pairs-cluster-bootstrap* procedure is:

1. Draw 32 complete borough trajectories with replacement; keep every selected borough's **seven cohort observations**, original counts and denominators, and shares. Create **unique temporary FE IDs for duplicated draws** so each draw is an independent bootstrap copy of a seven-year trajectory; do not sum or otherwise alter its observed outcome counts.
2. Refit the unchanged grouped-binomial E4 to the 224 sampled rows, check rank/convergence and model diagnostics. Because draws are whole seven-cohort trajectories, every sample retains the seven year levels.
3. Use the **sampled profile multiset** as the reference for that replicate, including duplicate draws with multiplicity, and keep that set fixed between predictions on either side of *each* year/composition contrast. Save the resulting scalar contrasts and, as appropriate, adjusted rates.
4. Use a reproducible RNG seed and a predeclared target of approximately 2,000 attempted replicates, with the 2.5th/97.5th percentiles of valid **replicate contrasts themselves** as proposed 95% percentile intervals. Report attempted/successful/failed counts, failure reasons and distributional anomalies; do not conceal failures or automatically replace them to achieve a cosmetically clean success count. Serious failure, singularity or instability triggers review before intervals are interpreted.

The original `224`-profile point estimate standardises to the **empirical London borough/composition distribution**. The bootstrap's changing profile distribution estimates repeated-sampling variability of a **sample-standardised statistic**, not the variance of the original fixed-reference estimand holding those 224 profiles literally fixed. This distinction must be explicit in reporting. The procedure also relies on borough trajectories being sufficiently independent **conditional on modelled cohort-year structure**; all 32 boroughs are observed, not a probability sample. The resulting percentiles are therefore conditional **borough-resampling uncertainty summaries**, not design-based confidence bounds for the complete London population and not guarantees about new cohort regimes.

Borough clustering does **not** generate new independent historical years. Only seven common cohort-year regimes exist; residual common-year dependence, year-regime uncertainty and nonlinear FE estimation remain limits. The year fixed effects absorb a shared *mean* time profile but cannot prove absence of residual common shocks. Avoid pretending two-way clustering on **seven** year groups would automatically solve this. The D9a6 leave-one-cohort, joint-regime exclusion and linear-trend checks are important complementary stress tests.

For the frozen secondary covariance cross-check, use a finite-cluster correction and transform common-coefficient uncertainty to the **same probability-scale contrasts** where computationally stable. Do not use naive binomial standard errors. With 32 clusters and many borough FE, treat apparent precision or sandwich/percentile disagreement as a diagnostic, not an invitation to switch to more favourable intervals. Relevant background: Cameron & Miller (2015), *A Practitioner's Guide to Cluster-Robust Inference*, https://doi.org/10.3368/jhr.50.2.317; MacKinnon, Nielsen & Webb (2023), *Cluster-robust inference: A guide to empirical practice*, https://doi.org/10.1016/j.jeconom.2022.04.001.

## 24.5 Comparable robustness targets and reporting discipline

Preserve **all six** D9a6 analyses, with no post-hoc selection. For leave-one-borough/year or joint-regime exclusions, recalculate **both full-fit and reduced-fit contrasts over the same retained reference profiles**. A categorical-year contrast containing an omitted cohort is not defined in that reduced fit; mark **not estimable** rather than extrapolating. The linear-trend check can still evaluate an endpoint contrast but forces a different year structure, so a changed result reflects that constraint. With disadvantage replacing FSM, do not compare the two socioeconomic effects as though they were the exact same covariate or estimand; examine whether broader conclusions change. Equal-weight OLS tests a distinct rate-model/weighting combination rather than just one assumption at a time.

Report E1–E4 *in-sample model-fit reductions* separately from adjusted probability contrasts and effect/uncertainty tables. Show the interval, effect magnitude, direction and changes under every predeclared sensitivity without a model-selection tournament, uncorrected multiple-testing claims or causal phrasing. A small association with a narrow model-conditional interval need not imply substantial policy usefulness. Grouped composition is not an individual pupil effect. The measured outcome includes **activity not captured** and is **not directly NEET**. 2022/23 explanatory use remains legitimate; the separate 2022/23 **predictive final evaluation remains locked**.

**Subsequent status (31 October 2026):** The predeclared D9e design has been implemented. The author reported local tests and a complete production run; all nine D9e exports were supplied and independently checked for numerical consistency (see §24.6–§24.10). This is an export-level audit, not an independent rerun of the original raw-data pipeline. The separate 2022/23 predictive final evaluation remains locked.

## 24.6 D9e implementation, output provenance and reproducibility

**Evidence level.** The author reported a successful local production run and supplied the nine exported D9e files for independent **output-level** verification on **31 October 2026**. This checkpoint independently recalculated summary statistics from the supplied 2,000 bootstrap replicate rows and checked the internal consistency of the exported point estimates, intervals and sensitivity results; it **did not independently rerun the full raw-data pipeline or access the locked predictive final evaluation**. D9e methodological decisions in §24.1–§24.5 remain unchanged. Historical "pending" statements under D9d/early §24 describe the earlier stage.

**Implementation:** `src/youth_offer/explanatory_estimands.py` contains paired year and composition predictions; `explanatory_inference.py` contains the complete-borough bootstrap and finite-cluster/delta cross-check; `explanatory_robustness.py` contains all six fixed sensitivities; `explanatory_reporting.py` writes outputs; `src/run_pipeline.py` calls this reporting step after E4 fitting and QA. The author reported the D9e module tests passing locally. Full-suite execution is not independently asserted in this export review. The model remains the **224-row grouped-binomial E4** with borough and categorical-year fixed effects and the three original composition shares.

**Nine local output files:** `outputs/explanatory/d9e/d9e_adjusted_years.csv`, `d9e_composition_associations.csv`, `d9e_point_estimates.csv`, `d9e_bootstrap_intervals.csv`, `d9e_bootstrap_replicates.csv`, `d9e_bootstrap_failures.csv`, `d9e_bootstrap_run.json`, `d9e_cluster_delta_intervals.csv` and `d9e_robustness.csv`. The complete numerical output (including all sensitivity cases) is retained in these machine-readable exports; a table below is the human-readable checkpoint, not a substitute for those files. All statements below concern **explanatory** outcomes, never predictive holdout scores.

**Bootstrap run:** fixed RNG seed **`20261030`**; **2,000 attempted, 2,000 successful, zero failed** fits; 32 whole borough histories sampled with replacement, each contributing its complete seven-cohort trajectory; sampled profiles provide the equal-weight paired reference for each replicate. `d9e_bootstrap_failures.csv` contains zero rows (with expected columns). **22 estimands × 2,000 finite replicate estimates** are present. Success of the numerical refits does not establish all modelling or independence assumptions.

## 24.7 Adjusted cohort-year rates and contrasts (D9e1)

The estimates standardise E4 to the **224 observed borough/composition profiles with equal weights**, predicting each observed cohort year on that same profile set. Rates are **percent**; differences are **percentage points (pp)**. Percentile intervals use **whole-borough resampling**, not naive grouped-binomial standard errors. Displayed values are rounded to three decimals; calculations and exported values retain greater precision.

| Cohort | Adjusted adverse rate (%) | Borough-bootstrap 95% percentile interval (%) |
|---|---:|---:|
| 2016/17 | 6.040 | [5.621, 6.469] |
| 2017/18 | 6.031 | [5.615, 6.483] |
| 2018/19 | 5.954 | [5.536, 6.418] |
| 2019/20 | 5.461 | [5.081, 5.848] |
| 2020/21 | 5.352 | [5.008, 5.675] |
| 2021/22 | 5.927 | [5.481, 6.329] |
| 2022/23 | 6.627 | [6.075, 7.126] |

| Cohort contrast | Estimated change (pp) | Borough-bootstrap 95% percentile interval (pp) |
|---|---:|---:|
| 2017/18 vs 2016/17 | -0.010 | [-0.286, +0.298] |
| 2017/18 vs previous cohort | -0.010 | [-0.286, +0.298] |
| 2018/19 vs 2016/17 | -0.087 | [-0.364, +0.234] |
| 2018/19 vs previous cohort | -0.077 | [-0.339, +0.195] |
| 2019/20 vs 2016/17 | -0.579 | [-0.938, -0.199] |
| 2019/20 vs previous cohort | -0.493 | [-0.787, -0.236] |
| 2020/21 vs 2016/17 | -0.688 | [-1.036, -0.353] |
| 2020/21 vs previous cohort | -0.109 | [-0.381, +0.128] |
| 2021/22 vs 2016/17 | -0.114 | [-0.545, +0.283] |
| 2021/22 vs previous cohort | +0.575 | [+0.296, +0.813] |
| 2022/23 vs 2016/17 | +0.586 | [+0.094, +1.027] |
| 2022/23 vs previous cohort | +0.700 | [+0.418, +0.998] |

**Summary:** The adjusted rate reached **5.352% in 2020/21**, after **6.040% in 2016/17**, then increased to **6.627% in 2022/23**. The predeclared headline **2022/23 − 2016/17** estimate is **+0.586 pp**, 95% borough-bootstrap interval **[+0.094, +1.027] pp**; the most recent adjacent-year difference is **+0.700 pp** [**+0.418, +0.998**]. The intervals for several contrasts exclude zero under the borough-resampling procedure; these are **not multiplicity-adjusted claims** and do not identify causal cohort-year effects or uncertainty over future common-year shocks. There is no adjacent contrast for 2016/17.

## 24.8 Composition associations and independent uncertainty cross-check (D9e2–D9e3)

Each number is the **equal-profile mean of a paired change in E4 predicted probability** when one composition share increases by its frozen increment. Borough, observed year and other shares remain unchanged. These are **hypothetical model comparisons**, not physically reallocating students or estimating programme effects.

| Frozen composition perturbation | Association (pp) | Bootstrap 95% interval (pp) | Clustered/delta 95% interval (pp) |
|---|---:|---:|---:|
| FSM-eligible share +2 pp | +0.030 | [-0.026, +0.137] | [-0.050, +0.109] |
| Identified-SEN share +2 pp | -0.025 | [-0.159, +0.087] | [-0.164, +0.114] |
| Standalone special-school share +0.25 pp (secondary) | -0.033 | [-0.111, +0.052] | [-0.124, +0.058] |

All **three** bootstrap intervals and all **three** clustered/delta intervals include zero; the estimates are small, directionally uncertain and not individual-level associations. Changing one share while holding the other shares constant does not demonstrate that every resulting joint composition is common in the data. The standalone special-school perturbation remains a **secondary structural** sensitivity.

The separate borough-clustered covariance/delta method uses a **finite-cluster correction** and evaluates the same 22 probability-scale quantities. The headline **2022/23 − 2016/17** clustered/delta interval is **[+0.121, +1.051] pp**, compared with the primary bootstrap **[+0.094, +1.027] pp**. Across the 12 reported year contrasts and three composition associations, both methods agree on whether their nominal 95% intervals straddle zero. For adjusted **rate levels**, the clustered/delta intervals are materially narrower than the borough-bootstrap intervals. Agreement on interval signs is not independent confirmation of coverage, model validity or future-year extrapolation. Rate-level interval widths differ partly because the bootstrap resamples the **reference-profile multiset**, while the clustered/delta calculation uses the original reference conditional on the fitted model; dependence assumptions also differ.

## 24.9 Full frozen robustness set (D9e4)

All six planned families were executed, totalling **43 alternative fits** (1 OLS + 1 disadvantage proxy + 32 borough deletions + 7 cohort deletions + 1 joint two-year exclusion + 1 trend) and **947** case/estimand rows: **907 comparable**, **38 not estimable**, **2 different-proxy** entries. These are sensitivity **point estimates**, not independently bootstrap-refitted intervals or formal hypothesis tests. Each group-deletion comparison uses the **same retained reference rows** for its full E4 and alternative-model evaluations; omit-year contrasts that require a missing category are labelled **not estimable**, never filled by extrapolation.

| Robustness specification | Alternative 2022/23 − 2016/17 contrast (pp) |
|---|---:|
| Equal-weight adverse-rate OLS | +0.475 |
| Approximate disadvantage replaces FSM | +0.991 |
| Leave one borough out (32 refits) | +0.501 to +0.651 |
| Leave one cohort out (seven refits) | +0.337 to +0.634 (five estimable) |
| Remove 2019/20–2020/21 jointly | +0.537 |
| Linear cohort-year log-odds trend | -0.331 |

The original full-E4 endpoint estimate is **+0.586 pp**. The **32** borough-deletion alternatives remain positive, ranging **+0.501 to +0.651 pp**; omission of 2016/17 or 2022/23 makes the endpoint unidentifiable, leaving **five** estimable one-cohort-deletion alternatives (**+0.337 to +0.634 pp**). Joint exclusion of 2019/20–2020/21 yields **+0.537 pp**, still positive. Equal-weight OLS changes **both** the outcome model/link and observation weighting; it does not isolate a single assumption. The disadvantage-proxy model yields an alternative socioeconomic association of **+0.064 pp per +2 pp approximate disadvantage share**, **not** a directly interchangeable replacement for the FSM-specific effect.

**Material limitation: the linear-trend alternative estimates −0.331 pp for the endpoint**, a sign reversal versus the categorical-year E4. It replaces six freely estimated cohort-year indicators with **one numerical 0–6 cohort trend on the log-odds scale**, while retaining borough FE and composition predictors. Thus the endpoint conclusion **depends on the allowed temporal pattern**; do **not** describe it as robust to all six checks, select the favourable temporal specification after inspecting results, or interpret the trend-constrained contrast as the same structural assumption. Other composition sensitivity results are also specification-sensitive (e.g. FSM +2 pp is **+0.119 pp** under the linear-trend alternative and can change sign in one-cohort deletions); their small original point estimates and wide intervals limit substantive claims.

## 24.10 Output-level numerical QA, inference limits and checkpoint decision

**Independent checks on the supplied exports:** (1) 2,000 unique numbered bootstrap attempts, 2,000 finite rows of all 22 estimands, and failure count zero; (2) recomputed 2.5th/97.5th replicate percentiles and sample SDs matching **all 22** exported bootstrap interval rows to floating-point tolerance; (3) the seven exported year rates and 12 reported differences agree with independently reconstructed point estimates; (4) the 22 clustered/delta point estimates equal the 22 primary point estimates; (5) all 43 robustness cases are present, with 947 statuses as reported; (6) the original year/composition estimate keys are complete, and no missing cohort-year contrast is represented by a fabricated prediction. These checks establish **export arithmetic/structure**, not an independent validation of upstream raw-data transformations or model fitting on the local machine.

**Interpretation and limits:** The outcome is **not in a recorded sustained destination** (including activity not captured), **not a direct NEET rate**. Equal-weight standardized profile averages are **not** pupil-weighted London rates. Associations are borough/cohort-level and **not causal**, individual-pupil effects or forecasts. The 32 London boroughs form the observed borough system, not an independent random population sample; bootstrap intervals describe an assumed borough-resampling process conditional on model structure. Seven **common year regimes** cannot be made into thousands of independent time shocks by resampling boroughs. Shared shocks, nonlinear FE estimation, modest cluster counts, approximation of sandwich/delta inference, multiple reported contrasts and absent formal sensitivity intervals all restrict certainty. Differences in confidence-interval inclusion of zero do not constitute an adjusted multiple-testing decision.

**Checkpoint decision:** D9e's predeclared explanatory estimands, uncertainty methods and six robustness families have been implemented and numerically reviewed at the **export level** with **no material internal inconsistency identified**. Preserve frozen E4 and the full sensitivity results, prominently retain the linear-trend sign reversal and modest uncertain composition effects, and proceed to the **separate predictive pre-final audit**. **Do not calculate, inspect or release the locked 2022/23 predictive final evaluation** without explicit subsequent approval. No additional adjusted borough-ranking estimand has been selected.

---

# 25. Current open questions

1. What exact common reference distribution / formula should be used if standardised adjusted borough summaries are included in final explanatory reporting?
2. What exact public-facing label, if any, should refine “Outside recorded sustained destinations” without changing its frozen definition?
3. If borough-level special-school or AP comparisons remain in the final output, what explicit uncertainty/stability treatment is most useful?

---

# 26. Workflow rule

Proceed in the order:

**problem understanding → raw-data understanding → population/outcome decisions → data-quality audit → EDA → modelling question → validation design → implementation → final audit**

**D9c predictive development metrics and D9d explanatory E1–E4 fitting, numerical QA, fit comparisons and first-pass diagnostics are locally verified.** D9e probability-scale estimates, 2,000 successful borough-bootstrap draws, clustered-covariance cross-check and all six robustness families have now been produced and numerically audited from the supplied exports (§24.6–§24.10). Preserve frozen explanatory and predictive specifications; proceed to the **separate predictive pre-final audit**. The **2022/23 predictive final evaluation remains locked** until explicitly released.

---

# 27. D9f — Predictive pre-final audit and implementation checkpoint (proposed)

Read-only inspection of commit `2123cbaa1272cf8d008935bb709558b0e7164fc2` confirmed that the existing development implementation follows the frozen D8/D9a target, three features, baselines and M1 specification. `build_development_transition_table` excludes the 2022/23 target **before** next-cohort shifts; source-alignment QA verifies the correct borough and cohort; B3 expands only through each feature origin; M1 fits strictly earlier target years; key-preservation and known-answer tests support all D9c metrics. The current branch had no GitHub Actions runs/status checks at this review. These are source-review and previously documented local-QA findings, not a new independent full-pipeline execution.

**Development evidence remains unchanged:** Mean annual MAE (pp): B1 0.716035, B2 0.954890, B3 0.638242, M1 0.705727. B3 is lower than M1 in all four annual folds, but these four regimes do not demonstrate statistical superiority. No score-based method selection or D9e reopening is justified.

**Identified implementation gap:** Prior to D9f there was no separate, explicitly permission-gated final forecast/scoring command or final-specific regression tests. The proposed additive implementation comprises `src/youth_offer/final_gate.py`, `src/run_final_predictive.py` and synthetic-only `tests/test_final_gate.py`. It reuses the existing model-table, baseline, predictive, evaluation and QA functions, provides the historical-only preflight report, and makes the locked target construction reachable only by a manually specified release flag. Six synthetic-only tests exercise source-table reconstruction, the five-transition history boundary, six-year B3 origin, missing/modified history rejection, known-answer metric arithmetic, mismatch rejection and default-run lock.

**Verification boundary:** New code compiled, and six synthetic tests passed in an isolated local *representative module mirror*, not against the actual checked-out GitHub repository. A historical-only preflight using the supplied raw ZIP and that mirror also passed: 160 training transitions, latest target 2021/22, 32 forecast origins, matrix rank four, finite M1 values and zero out-of-range forecasts. The patch has not yet been applied or run in the user's checked-out repository; therefore full GitHub-source integration, user-side raw-ZIP preflight and reproducibility are still **unverified**. No real 2022/23 predictive performance was constructed or inspected. User-side `git apply --check`, full test suite and historical-only preflight are required before readiness can be marked verified. Only subsequent, explicit authorisation can release the final scoring boundary.
