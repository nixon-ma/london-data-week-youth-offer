# London Data Week 2026 — Youth Offer for London
## Decision Log

This file is the authoritative record of accepted project decisions for the post-hackathon rebuild.

Accepted decisions should only be reopened if new evidence gives a specific reason to do so.

---

## D1 — Geography

**Evidence:** `DATA_AUDIT.md` §§2.1, 9.2, 12.2

**Status:** Accepted

**Decision:**
Use **London Local Authority** as the primary geography.

Interpret Local Authority according to the administrative LA of the pupil's school/institution rather than pupil residence.

**Rationale:**
This is the most useful borough-level geography available for the London policy question.

**Implications / limitations:**
- Results should not be described as outcomes for all young people *living* in a borough.
- Cross-borough school attendance may affect borough-level interpretation.
- The primary analytical panel contains a stable **32 London LAs** across 2016/17–2022/23.

---

## D2 — Period

**Evidence:** `DATA_AUDIT.md` §§2.2, 11, 12.8

**Status:** Accepted

**Decision:**
Use **2016/17–2022/23** as the primary borough-level time series.

**Rationale:**
This is the complete Local Authority history for the chosen primary population in the supplied file. The supplied guidance explicitly flags methodological changes from the 2016/17 cohort onwards and cautions against comparison with earlier cohorts; the chosen period therefore starts at the relevant boundary.

D5 also found stable destination categories and stable availability of the five target subgroup families throughout all seven cohorts. Current DfE methodology additionally states that the latest employment-source change was retrospectively applied to 2016/17–2022/23 to keep that published series on a consistent basis.

**Implications / limitations:**
- Do not splice values from older publication vintages into the current supplied series without checking methodology compatibility.
- The COVID-affected cohorts are a substantive regime/event issue rather than, by themselves, evidence of a definition break. Later trend analysis and validation should therefore be time-aware and include pandemic sensitivity checks where relevant.
- Prior-attainment methodology changed from 2020/21, but prior-attainment breakdowns are not available in the chosen primary London LA slice. If prior attainment is used in another analytical slice later, its comparability must be handled separately.

---

## D3 — Analytical population

**Evidence:** `DATA_AUDIT.md` §§5, 9.3, 12.3

**Status:** Accepted

**Decision:**
Use **state-funded mainstream + special** as the primary population.

Also:
- analyse **mainstream** and **special schools** separately at aggregate borough/year level to identify composition effects;
- treat **alternative provision** as a separate secondary population.

**Rationale:**
The combined population is the broadest coherent borough-level population for which the main subgroup breakdowns are available.

Separate mainstream/special analysis is needed because borough differences in the combined outcome may partly reflect:
- different proportions of special-school pupils;
- different outcomes within special schools;
- different mainstream-school outcomes.

D5 confirmed that `State-funded mainstream and special = mainstream + standalone special` exactly for all tested borough/year/destination count cells in the analytical period.

**Implications / limitations:**
- Subgroup analysis is available for the combined mainstream + special population.
- Standalone special schools do not have equivalent subgroup breakdowns at LA level.
- Alternative provision does not have equivalent subgroup breakdowns at LA level and should not be merged into the primary population.

---

## D4 — Primary analytical outcome

**Evidence:** `DATA_AUDIT.md` §§6–7, 9.4, 12.4–12.7

**Status:** Accepted

**Decision:**
Use the **rate and count outside recorded sustained destinations** as the primary adverse outcome.

Define it from pupil counts as:

**Outside recorded sustained destinations**
= **Not recorded as a sustained destination**
+ **Activity not captured**

Equivalently:

**Outside recorded sustained destinations**
= **KS4 cohort**
− **Sustained education, employment & apprenticeships**

**Rationale:**
The derived outcome captures the full complement of pupils not appearing in the published sustained-destination measure, while preserving the two distinct official DfE components.

**Implementation rule:**
For headline borough totals and subgroup families whose counts are exact in the supplied LA data, calculate the derived count and rate from pupil counts rather than by adding rounded percentages.

**Disadvantage exception:**
Displayed disadvantage cohort and pupil counts are disclosure-controlled/rounded and must not be treated as exact. For disadvantage subgroup analysis:
- use the published destination percentages as the rate source;
- derive the adverse rate as `100 − published Sustained education, employment & apprenticeships %`;
- retain the published `Not recorded as a sustained destination` and `Activity not captured` percentages separately;
- do **not** report a derived disadvantage adverse pupil count as exact.

**Interpretation rules:**
- Always retain and examine the two official components separately:
  - `Not recorded as a sustained destination`
  - `Activity not captured`
- Do **not** call the derived measure a NEET rate.
- Do not imply that all pupils outside recorded sustained destinations were NEET.
- The exact public-facing display label can be refined later if a clearer term is found, but the underlying definition is frozen.

---

## D5a — Analytical table grains

**Evidence:** `DATA_AUDIT.md` §12.1

**Status:** Accepted

**Decision:**
Freeze explicit analytical grains before implementation.

Expected unique keys:

| Analytical table | Expected unique key |
|---|---|
| Headline destinations, long | `year × LA code × establishment population × destination` |
| Headline borough outcomes, wide | `year × LA code × establishment population` |
| Normalised subgroup destinations | `year × LA code × establishment population × subgroup family × subgroup value × destination` |
| Mainstream/special composition | `year × LA code` after population measures are pivoted |
| Alternative-provision headline | `year × LA code × destination` |

**Rationale:**
The source is aggregated and contains overlapping characteristic slices of the same underlying pupil cohort. Duplicate-looking rows are usually distinct analytical slices, not duplicated pupils.

**Implementation implications:**
- Headline extraction must explicitly select all characteristic dimensions as `Total`.
- Do not use broad `drop_duplicates()` operations to collapse subgroup rows.
- Assert uniqueness at the intended table grain during preprocessing.

---

## D5b — Publication-code handling

**Evidence:** `DATA_AUDIT.md` §12.5

**Status:** Accepted

**Decision:**
Preserve publication codes semantically rather than converting them blindly to zero or ordinary missing values.

The supplied guidance defines:
- `(c)` = small number suppressed to preserve confidentiality or for accountability reasons;
- `(z)` = not applicable;
- `(x)` = not available;
- `(low)` = positive percentage less than 0.5.

The CSV stores these tokens without parentheses (`c`, `z`, `x`, `low`).

**Implementation implications:**
Represent at least the following states distinctly:

`numeric / suppressed_c / not_applicable_z / unavailable_x / low`

Do not numerically impute suppressed values in the main analysis. Do not treat `low` as zero.

---

## D5c — Disadvantage disclosure treatment

**Evidence:** `DATA_AUDIT.md` §§12.5–12.7

**Status:** Accepted

**Decision:**
Treat displayed disadvantage counts as disclosure-controlled/rounded rather than exact analytical counts.

Use published percentages for disadvantage rate analysis. Do not require disadvantage category counts to sum exactly to headline counts, and do not reconstruct exact subgroup counts from the displayed rounded values.

**Rationale:**
Across the supplied London LA data, every ordinary numeric disadvantage `cohort_count` and `pupil_count` is a multiple of five. The category sums differ from exact headline counts by at most four pupils, and count-derived rates can differ materially from the published percentages. Authoritative DfE documentation for a closely related LA destinations dataset explicitly states that disadvantage counts are rounded to the nearest five and values of 1 or 2 may be represented by `low`; this is consistent with the observed pattern, although the supplied KS4 guidance does not state that nearest-five rule explicitly.

**Limitation:**
The exact unrounded disadvantage subgroup counts are not recoverable from the public file.

---

## D5d — SEN hierarchy

**Evidence:** `DATA_AUDIT.md` §§12.6, 12.9

**Status:** Accepted

**Decision:**
Do not treat all four published SEN labels as mutually exclusive peer categories.

Use either:
- top-level split: `Identified SEN` vs `No identified SEN`; or
- within-SEN split: `SEN support` vs `SEN with EHC plan or statement`.

**Rationale:**
For every tested borough/year/destination cell:

`Identified SEN = SEN support + SEN with EHC plan or statement`

The two detailed SEN categories therefore sit inside the aggregate `Identified SEN` category.

---

## D5e — Alternative-provision geography panel

**Evidence:** `DATA_AUDIT.md` §12.2

**Status:** Accepted

**Decision:**
Use the same stable **32-borough panel** for ordinary alternative-provision borough comparisons and longitudinal summaries.

Retain the two City of London AP observations in the raw/audit layer but exclude them from ordinary comparative AP analysis unless the anomaly itself is being discussed.

**Rationale:**
City of London appears only in AP in 2017/18 and 2018/19, with a cohort of exactly one pupil in each year. Including those two observations would create inconsistent panel coverage and extremely unstable rates without adding useful comparative information.

---

## D5f — Small-population interpretation for special schools and AP

**Evidence:** `DATA_AUDIT.md` §12.10

**Status:** Accepted

**Decision:**
Treat standalone special-school and alternative-provision borough rates as high-variance diagnostics rather than directly comparable performance rankings.

**Implementation / reporting rules:**
- always retain and display cohort denominator alongside rates;
- do not present unqualified borough rankings based on raw special-school or AP rates;
- consider multi-year pooling, uncertainty intervals, shrinkage or another explicit uncertainty treatment later if the EDA shows it is useful.

**Rationale:**
Borough-year denominators are often small: the special-school cohort has a minimum of 9 and median of 45.5; AP has a minimum of 1 and median of 52. A one-pupil change can therefore move a raw rate substantially.

---

## D6a — Rates and counts answer different questions

**Evidence:** `DATA_AUDIT.md` §§14.1–14.2

**Status:** Accepted

**Decision:**
Use the **adverse rate** for comparative prevalence across boroughs and groups, and the **adverse count** for scale / potential support-demand context. Report both where the policy interpretation needs both.

**Rationale:**
Borough cohort size strongly affects adverse counts, so the borough with the largest number of pupils outside recorded sustained destinations is not necessarily the borough with the highest rate. In 2022/23, for example, Newham had a larger adverse count than Islington, while Islington had the higher adverse rate.

**Implications / limitations:**
- Do not interpret a high count as a high prevalence rate, or vice versa.
- Do not prioritise boroughs using one metric without stating which policy question it answers.
- London-wide counts remain useful for understanding the scale of the issue even when rates are the main comparative measure.

---

## D6b — Subgroup reporting hierarchy

**Evidence:** `DATA_AUDIT.md` §14.4

**Status:** Accepted

**Decision:**
For the primary subgroup narrative:
- lead the socioeconomic analysis with **disadvantage**;
- use **FSM** as a corroborating measure rather than independent evidence;
- use **Identified SEN vs No identified SEN** as the principal SEN comparison;
- use **SEN support vs SEN with EHC plan or statement** only as a secondary within-SEN drill-down;
- retain **sex** and **major ethnicity** as separate descriptive analyses.

Do not combine overlapping subgroup families as though they were independent populations.

**Rationale:**
The largest and most geographically widespread disparities are observed for disadvantage/FSM and SEN. Disadvantage and FSM overlap conceptually and show very similar patterns, while the SEN labels are hierarchical under D5d. Sex differences are smaller, and ethnicity shows a distinct, more nuanced pattern that should be reported directly rather than forced into the wider youth-unemployment narrative.

**Implementation implications:**
- Continue to apply D5c: disadvantage rates use published percentages rather than reconstructed rates from rounded counts.
- Continue to apply D5d: do not treat all four SEN labels as peer categories.
- `Unknown` ethnicity remains part of accounting checks but should not be interpreted as a substantive ethnic group.

---

## D6c — Alternative provision analytical emphasis

**Evidence:** `DATA_AUDIT.md` §14.5

**Status:** Accepted

**Decision:**
Include **alternative provision (AP)** as a dedicated **secondary analysis**, primarily at London level.

Do not use raw annual AP borough rates as performance rankings. Any later borough-level AP comparison must retain denominators and use an explicit stability/uncertainty treatment if interpretation goes beyond simple description.

**Rationale:**
AP is small in cohort size but substantively important. In 2022/23 its adverse rate was about **35.0%**, compared with **6.58%** in the primary mainstream + special population, and AP recorded **607** pupils outside recorded sustained destinations. At borough level, AP denominators are often small: the 2022/23 median was 44.5 pupils and 17 of 32 boroughs had fewer than 50 pupils.

**Implications / limitations:**
- AP should not be merged into the primary population.
- Equivalent LA subgroup breakdowns are unavailable for AP.
- The two City of London `n=1` observations remain governed by D5e.

---

## D6d — Preserve temporal structure

**Evidence:** `DATA_AUDIT.md` §§14.1, 14.2, 14.6

**Status:** Accepted

**Decision:**
Treat **cohort year as genuine analytical structure**. Later validation must test generalisation through time rather than randomly shuffling borough-year observations in a way that removes temporal ordering.

**Rationale:**
The London-wide adverse rate is non-linear across the seven cohorts: broadly stable through 2018/19, lower in 2019/20–2020/21, then rising to a series high in 2022/23. Most boroughs moved in the same direction during the major shifts, while borough rankings remained moderately persistent. The 2019/20 and 2020/21 cohorts also have different mixes of the two adverse components.

**Implications / limitations:**
- Do not assume a single smooth linear time trend adequately describes the period.
- Retain the two adverse components separately in time analysis.
- Pandemic-era patterns are descriptive regime/event structure, not proof that COVID caused the observed changes.
- The exact time-aware validation design belongs to the later validation stage.

---

## D7a — Primary modelling question

**Evidence:** `DATA_AUDIT.md` §§14.2, 14.3, 14.4, 14.6, 18.1

**Status:** Accepted

**Decision:**
Use the following as the **primary modelling question**:

> **How much of the observed variation in London borough rates outside recorded sustained destinations is associated with persistent borough differences, common cohort-year effects and observable cohort composition, and how much borough-specific variation remains after accounting for those structures?**

The unit of analysis is **borough × cohort** for the frozen 32-LA, seven-cohort primary panel.

The estimand is the borough-year adverse **rate / probability**, while retaining the exact adverse count and cohort denominator so that later modelling can respect differing statistical precision across borough-years.

**Rationale:**
D6 found substantial and moderately persistent borough differences alongside strong common London-wide temporal movement. This question quantifies that structure directly and adds information beyond descriptive EDA without requiring a causal interpretation.

**Interpretation / limitations:**
- This is an **associational**, not causal, modelling question.
- With only seven annual cohorts, do not assume that elaborate borough-specific trends or structural breaks can be estimated reliably.
- “Borough-specific temporal movement” should be interpreted as borough-specific **deviation from the common London time pattern**, not as evidence of a stable borough-specific trend process.
- The exact statistical model is deliberately not selected at D7.

---

## D7b — Required secondary predictive question

**Evidence:** `DATA_AUDIT.md` §§14.2, 14.6, 14.8, 18.2

**Status:** Accepted

**Decision:**
Retain a **required secondary predictive track**:

> **Using only information genuinely available through cohort `t`, can we predict borough adverse rates in cohort `t+1` better than simple historical baselines?**

Use a **one-cohort-ahead** horizon and a continuous adverse-rate / probability target.

**Rationale:**
The prediction task provides a genuine supervised-learning test while respecting the small panel and the strong persistence already visible in EDA. The central question is whether any additional information improves on simple persistence, not whether a complex ML algorithm can achieve a high in-sample score.

**Baseline principle:**
At minimum, later evaluation must compare against a persistence baseline such as:

> next cohort's borough adverse rate ≈ current cohort's borough adverse rate.

The exact validation design and additional baselines belong to D8.

**Limitations:**
- The panel supplies only six one-year transitions and seven distinct annual regimes.
- Complex ML is not justified by nominal row count alone.
- Operational claims about when a forecast could have been produced require verification of publication / feature availability timing.

**D8 clarification:**
The core predictive track is a **retrospective chronological forecasting benchmark on the current harmonised series**, not a claim that the cohort-`t` destination outcome was historically published before cohort `t+1` occurred. DfE destination measures are published with a substantial lag and the current series includes retrospective revisions. Real-time operational forecasting would require archived publication vintages and feature-specific release dates.

---

## D7c — Target-reconstruction and leakage prohibition

**Evidence:** `DATA_AUDIT.md` §§3, 6, 12.3–12.4, 14.8, 18.3

**Status:** Accepted

**Decision:**
Do not use information from the target cohort that directly or indirectly reconstructs the target destination outcome.

For the same target borough-year, prohibited explanatory or predictive features include:
- `Not recorded as a sustained destination` outcome;
- `Activity not captured` outcome;
- sustained education, employment & apprenticeships outcome;
- contemporaneous subgroup destination outcomes;
- contemporaneous mainstream or special-school destination outcomes when predicting/explaining the combined headline outcome;
- any arithmetic transformation that mechanically encodes the target.

Lagged outcome information from cohort `t` or earlier may be considered for forecasting cohort `t+1`, subject to D8 validation and availability rules.

**Rationale:**
The source contains overlapping views of the same underlying pupil cohort, and the headline destination outcome has exact accounting identities. Treating contemporaneous outcome slices as independent predictors would create leakage or tautological target reconstruction rather than genuine explanation or prediction.

---

## D7d — Cohort-composition feature rule

**Evidence:** `DATA_AUDIT.md` §§4, 12.6, 14.3–14.4, 18.4

**Status:** Accepted

**Decision:**
Potential explanatory composition variables must describe **who is in the cohort**, not how that same cohort performed on the destination outcome.

Examples of potentially legitimate composition information include:
- cohort size;
- sex composition;
- major-ethnicity composition;
- FSM / disadvantage composition where disclosure rules permit valid construction;
- SEN composition following the D5d hierarchy;
- special-school share.

Do not automatically include all available composition measures together. Overlapping variables, especially disadvantage and FSM, require parsimonious treatment and must not be interpreted as independent effects by default.

**Rationale:**
Composition variables can help distinguish observable cohort structure from persistent borough and common year effects without reusing the target outcome itself. D6 also showed that some subgroup families overlap conceptually and empirically.

**Implementation limitation:**
The exact feature set and encoding remain open until model / validation design; D7 freezes only the admissibility principle.

---

## D7e — Geographic interpretation of modelling results

**Evidence:** `DATA_AUDIT.md` §§2.1, 12.11

**Status:** Accepted

**Decision:**
Interpret modelling results at the **Local Authority associated with the pupil's school/institution**, not automatically as the borough of pupil residence.

**Implications:**
- Do not describe the model as directly identifying which resident young people or residential boroughs should receive Youth Offer resources.
- The analysis can support understanding of borough-level education-system patterns, persistent differences and temporal deviations within the available geography.
- A direct residence-based allocation model would require appropriate residence-based data.

---

## D7f — External-data requirement

**Evidence:** `DATA_AUDIT.md` §§12.9, 14.8, 18.5

**Status:** Accepted

**Decision:**
External data are **not required for the core project**.

The supplied data are sufficient for:
- the primary borough-year variation / association question; and
- a rigorous internal one-cohort-ahead forecasting benchmark.

External point-in-time predictors are an **optional later extension**, not a prerequisite. They should be added only if they address a specific limitation or materially improve the policy usefulness of the predictive question, and only after their historical availability is verified.

**Rationale:**
This keeps the core project defensible and scoped to information that has already been audited, while leaving room for a richer operational forecasting extension if justified later.

---

# D8 — Validation design

## D8a — Predictive chronological evaluation

**Evidence:** `DATA_AUDIT.md` §§14.6, 16.2, 18.1–18.2

**Status:** Accepted

**Decision:**
Use **expanding-window / rolling-origin evaluation** for the one-cohort-ahead predictive track. Keep all 32 boroughs in each chronological train/test period; do not randomly split borough-year rows.

Evaluation roles:

| Target cohort | Role |
|---|---|
| 2017/18 | Baseline-only reference; no earlier transition exists for training a learned one-step model |
| 2018/19–2021/22 | Development rolling-origin folds |
| 2022/23 | Locked final temporal evaluation |

For every target cohort, train only on earlier target cohorts. The first development fold is intentionally data-poor; this is evidence about the real small-sample problem rather than a reason to discard it.

All learned preprocessing, feature construction, imputation, scaling and tuning must occur **inside the training history of that fold**. The outer target cohort must not influence those choices.

A borough-held-out test is **not part of the core predictive evaluation**, because the target use case is forecasting the same 32-LA London system through time. It may be added only as a separately labelled robustness question if later model interpretation makes unseen-borough generalisation relevant.

**Hyperparameter rule:**
Prefer methods with no or very few tuning parameters. Do not use elaborate nested resampling to manufacture apparent sample size. If tuning is unavoidable, use only earlier chronological splits within the training history and a small predeclared search; if an early fold has insufficient history, use a predeclared fixed/default setting rather than tuning on the outer target.

---

## D8b — Predictive baseline set

**Evidence:** `DATA_AUDIT.md` §§14.2, 16.2, 18.3

**Status:** Accepted

**Decision:**
Use three core baselines:

1. **Borough persistence**

   `prediction(b, t+1) = adverse_rate(b, t)`

2. **London-level persistence**

   `prediction(b, t+1) = London_adverse_rate(t)`

3. **London level + historical borough offset**

   `prediction(b, t+1) = London_adverse_rate(t) + mean_{s<=t}[adverse_rate(b,s) - London_adverse_rate(s)]`

The third baseline represents the two strongest structures found in D6: a common London level plus a persistent borough tendency.

Do not create a large baseline library. More complex methods must demonstrate value beyond these simple historical structures.

---

## D8c — Predictive evaluation metrics

**Evidence:** `DATA_AUDIT.md` §§16.2, 18.4

**Status:** Accepted

**Decision:**
Use:

- **primary:** unweighted **MAE**, reported in percentage points;
- **secondary:** **RMSE**, also in percentage points;
- **sensitivity:** cohort-size-weighted MAE, using the target-cohort denominator as an **evaluation weight only**, never as a predictor unless separately verified as available at forecast time.

Report performance **for each target cohort** as well as the development-period aggregate. For model comparison, the main summary is mean MAE across the development forecast years; because every year contains the same 32 boroughs, this gives equal weight to the distinct annual regimes.

Also report improvement/deterioration relative to borough persistence, for example `model MAE - persistence MAE`.

Do not make rank correlation a core metric unless a later policy use case specifically requires ranking boroughs.

---

## D8d — Predictive feature availability and leakage protocol

**Evidence:** `DATA_AUDIT.md` §§12.8, 16.2–16.4, 18.5

**Status:** Accepted

**Decision:**
For the core retrospective predictive benchmark:

- lagged outcomes indexed to cohort `t` or earlier may be used;
- lagged non-outcome composition and cohort information indexed to `t` or earlier may be used, subject to D5/D7 admissibility rules;
- target-cohort (`t+1`) composition, denominator or other information is **not** a predictor by default;
- target-cohort outcomes, contemporaneous subgroup destination outcomes and any target-reconstructing quantities remain prohibited;
- every historical aggregate, transformation and preprocessing parameter must be recomputed from the training history available to that fold.

**Point-in-time interpretation:**
The current supplied series is a harmonised retrospective dataset. DfE destination outcomes are published after the destination year and can later be revised. Therefore `t -> t+1` in the core project means **chronological index order in the current series**, not an operational claim that `y_t` was available before the `t+1` destination period occurred.

A genuinely real-time forecasting extension would require archived release vintages and verified publication dates for every feature. It is not required for the core project.

---

## D8e — Validation of the primary explanatory track

**Evidence:** `DATA_AUDIT.md` §§14.2–14.6, 16.1, 16.4, 18.6

**Status:** Accepted

**Decision:**
Use the full 32-LA × seven-cohort panel for the explanatory track; do **not** create an artificial predictive train/test split.

Assess robustness through progressively richer structural specifications:

1. common cohort-year structure;
2. persistent borough structure;
3. borough + cohort-year structure;
4. borough + cohort-year structure + a **small, predeclared** set of admissible composition variables.

Validation requirements:

- represent cohort year flexibly in the main specification rather than assuming a single linear trend; a linear trend may be a sensitivity check;
- use a denominator-aware main analysis based on the exact adverse count and cohort denominator; compare with an equal-weight rate analysis as a sensitivity check;
- do not use automated stepwise feature selection;
- do not treat disadvantage and FSM as independent socioeconomic effects in the same primary specification; use one as the main representation and the other as a replacement sensitivity if both are technically constructible;
- respect the SEN hierarchy and avoid redundant sum-to-one composition encodings;
- perform leave-one-borough-out and leave-one-cohort-out influence checks on the substantive conclusions;
- perform a joint **2019/20–2020/21 regime sensitivity**, because D6 identified these as the unusual low-rate period; interpret this only as sensitivity to that period, not as a causal estimate of COVID effects;
- inspect residual structure by borough, cohort, fitted value and denominator, including obvious within-borough temporal pattern or influential observations.

These checks test whether the substantive conclusions are stable; they are not a search for whichever specification produces the preferred result.

---

## D8f — Uncertainty and small-sample discipline

**Evidence:** `DATA_AUDIT.md` §§16.1–16.2, 18.7

**Status:** Accepted

**Decision:**
Treat the seven cohorts as the critical sample-size limitation. The 224 borough-years are repeated observations from only 32 boroughs across seven common time regimes, not 224 independent forecasting experiments.

For the explanatory track:
- report effect/structure estimates with **95% uncertainty intervals** where the eventual estimator supports them;
- the uncertainty method must respect repeated observations within boroughs and differing cohort denominators;
- do not rely on naive row-level iid uncertainty;
- the exact estimator and interval construction remain model-selection decisions.

For the predictive track:
- show fold-by-fold performance explicitly;
- do not present a narrow confidence interval that implies more independent time information than the panel contains;
- do not claim robust ML superiority from a marginal pooled improvement or a single successful year;
- keep feature count and tuning degrees of freedom small and record development choices before the final evaluation is opened.

---

## D8g — Final predictive evaluation discipline

**Evidence:** `DATA_AUDIT.md` §18.8

**Status:** Accepted; terminology refined by D9a

**Decision:**
Reserve **2022/23** from D8 onward as the final **locked temporal evaluation** for the predictive track.

It is **not** described as a pristine untouched holdout because its outcome was already examined during D6 EDA. Its purpose is narrower: predictive feature definitions, preprocessing, benchmark methods, the learned-model specification, tuning rules and reporting rules must be frozen before 2022/23 predictive performance is calculated.

D9a ultimately predeclares **one learned model plus three historical baselines**, so there is no development-stage search for a winning model family. The 2018/19–2021/22 targets are used for chronological development diagnostics and stability assessment, while the same four predeclared methods are carried unchanged into 2022/23.

After the final evaluation is opened:
- report all predeclared results whether favourable or unfavourable;
- do not retroactively tune or redesign the learned method to improve 2022/23;
- any later redesign is a separately labelled experiment and the original 2022/23 result remains recorded.

This leaves five earlier transitions for fitting the final learned-model forecast, while the four targets 2018/19–2021/22 provide chronological development evaluation.

---


# D9a — Primary explanatory model selection

## D9a1 — Primary outcome model and link

**Evidence:** `DATA_AUDIT.md` §§19.1–19.2

**Status:** Accepted

**Decision:**
Use a **grouped-binomial logistic GLM** as the primary explanatory estimator for the headline borough-year outcome:

```text
Y_bt ~ Binomial(n_bt, p_bt)
logit(p_bt) = linear predictor
```

where `Y_bt` is the exact adverse count and `n_bt` is the exact KS4 cohort denominator for borough `b`, cohort `t`.

**Rationale:**
The observed data are exact counts out of known denominators. A grouped-binomial model therefore uses the available count/denominator information directly instead of treating every borough-year percentage as equally precise. The logit link maps an unrestricted additive predictor to a valid probability in `(0, 1)` without requiring the adverse probability itself to vary linearly.

**Interpretation / limitation:**
- The binomial model is a starting sampling model, not a claim that pupils are literally independent identical draws.
- Extra-binomial variation and within-borough dependence must be diagnosed and reflected in uncertainty treatment under D9a4.
- Report substantive results on the probability / percentage-point scale rather than relying on raw log-odds coefficients.

---

## D9a2 — Borough and cohort-year structure

**Evidence:** `DATA_AUDIT.md` §19.3

**Status:** Accepted

**Decision:**
Use **borough fixed effects** and **categorical cohort-year fixed effects** in the primary explanatory model:

```text
logit(p_bt) = alpha + borough_b + cohort_year_t + composition_bt
```

Do not use borough-specific trends, borough × year interactions, splines or formal breakpoint terms in the primary specification.

**Rationale:**
- D6 identified both persistent borough differences and non-linear common London-wide cohort movement.
- Categorical year effects allow each of the seven observed cohorts its own common adjustment rather than imposing a straight trend.
- Borough fixed effects allow persistent unobserved borough differences to be correlated with observed composition variables; a conventional random-intercept model would require stronger assumptions about that relationship.
- Only seven cohorts are available, so richer borough-specific temporal structures would add substantial flexibility without enough independent time information.

**Implication for composition coefficients:**
With borough and cohort-year fixed effects present, composition associations are identified primarily from borough-year composition changes remaining after persistent borough differences and common London-wide year movement have been accounted for. They must not be interpreted as causal effects.

---

## D9a3 — Primary explanatory composition block

**Evidence:** `DATA_AUDIT.md` §§19.1, 19.4

**Status:** Accepted

**Decision:**
Use the following small primary composition block:

1. **FSM-eligible cohort share** — primary socioeconomic representation;
2. **Identified-SEN cohort share** — top-level SEN representation;
3. **standalone special-school cohort share** within the combined mainstream + special population — structural population-composition adjustment.

Enter these as continuous linear main effects on the logit scale in the primary specification.

Do not include in the primary specification:
- disadvantage alongside FSM;
- all four SEN labels;
- sex composition;
- the full major-ethnicity share vector;
- cohort size as an explanatory predictor;
- automated interactions or nonlinear transformations.

**Predeclared sensitivity:**
Replace FSM share with an approximate **disadvantaged cohort share** and check whether substantive conclusions change. Do not include FSM and disadvantage together. The disadvantage share is approximate because its displayed public counts are disclosure-rounded.

**Rationale:**
- FSM and Identified SEN are substantively important in D6, are constructible from exact cohort counts, and retain meaningful borough-year variation after borough and cohort-year structure is removed.
- The special-school share addresses a known structural feature of the combined analytical population; it is retained as an adjustment rather than a primary substantive effect.
- The three primary composition variables show low pairwise correlation after removing borough and cohort-year structure, so there is no obvious redundancy problem.
- Sex composition has limited plausible ability to explain the headline borough-year variation; full ethnicity composition would require multiple additional share parameters in a seven-cohort panel and remains better suited to the descriptive analysis / an explicitly labelled expanded sensitivity if later justified.

---

## D9a4 — Overdispersion, dependence and uncertainty

**Evidence:** `DATA_AUDIT.md` §19.5

**Status:** Accepted

**Decision:**
Use the grouped-binomial model for the primary mean structure, but do **not** rely on naive iid/binomial model-based standard errors.

Primary uncertainty for common model quantities will use a **borough-level block bootstrap**, resampling whole seven-cohort borough trajectories with replacement and refitting the model. Use approximately **2,000 replicates** subject to numerical-stability checks during implementation.

Use borough-clustered robust covariance as a secondary cross-check rather than the sole inferential method.

**Diagnostics:**
- Pearson dispersion statistic;
- residuals by fitted value;
- residuals by denominator;
- residuals by borough;
- residuals by cohort year;
- obvious within-borough residual temporal pattern and influential observations.

**Interpretation:**
A dispersion statistic materially above one is evidence that the simple binomial variance is too small, but it is not by itself a reason to change the mean specification. First inspect whether systematic residual patterns indicate misspecification of the mean model.

**Scope of bootstrap inference:**
Use bootstrap intervals mainly for common quantities such as composition associations, adjusted year contrasts and structural summaries. Do not turn the analysis into 32 separate borough fixed-effect significance tests.

---

## D9a5 — Structural model sequence and reporting

**Evidence:** `DATA_AUDIT.md` §19.6

**Status:** Accepted

**Decision:**
Implement the D8 progressive explanatory sequence as:

1. **E1:** cohort-year fixed effects;
2. **E2:** borough fixed effects;
3. **E3:** borough + cohort-year fixed effects;
4. **E4:** borough + cohort-year fixed effects + the D9a3 composition block.

Assess how model fit changes when the predeclared structures are added using **binomial deviance reductions**, but do not describe these reductions as a unique additive percentage of variance explained.

Also report residual error on the original rate scale, including **in-sample explanatory MAE / RMSE in percentage points**, so the magnitude of remaining borough-year discrepancy is interpretable.

For substantive effects:
- express composition associations as probability-scale / percentage-point marginal effects for meaningful changes in composition rather than raw log-odds alone;
- present cohort-year structure using adjusted predicted rates / contrasts on the probability scale;
- if adjusted borough summaries are shown, place boroughs on a common year/composition reference distribution. The exact standardisation formula is a reporting specification to be frozen before those summaries are calculated.

**Interpretation boundary:**
Residual variation means variation **not accounted for by the fitted model**. It must not be described as a measured causal contribution of omitted factors.

---

## D9a6 — Predeclared explanatory robustness set

**Evidence:** `DATA_AUDIT.md` §19.7

**Status:** Accepted

**Decision:**
Keep the core robustness set small and predeclared:

- equal-weight linear regression on borough-year adverse rates using the same structural terms;
- disadvantage share replacing FSM share;
- leave-one-borough-out influence checks;
- leave-one-cohort-out influence checks;
- joint exclusion of 2019/20–2020/21 as the D8 regime sensitivity;
- a single linear cohort trend as a sensitivity to the main categorical-year specification.

Do not use these checks to search for a preferred result. Additional model families, interactions, nonlinear composition terms or random-effects specifications require a specific diagnostic or substantive reason before being added.

---

## D9a7 — Predictive transition construction and frozen feature set

**Evidence:** `DATA_AUDIT.md` §§20.1–20.2

**Status:** Accepted

**Decision:**
Represent the learned forecasting data as one-cohort transitions:

```text
borough information at cohort t -> borough adverse rate at cohort t+1
```

The **feature horizon is one cohort**: each forecast uses only the immediately preceding cohort's predictors. The **training window is expanding**: when forecasting a later cohort, fit the learned model on all earlier one-cohort transitions available at that forecast origin.

Use exactly three core predictive features, all measured at cohort `t`:

1. **latest borough adverse rate**, constructed from the exact adverse count and exact headline cohort denominator;
2. **FSM-eligible cohort share**, from exact FSM cohort counts;
3. **Identified-SEN cohort share**, using the accepted top-level SEN hierarchy.

For forecasting `t+1`, do not use target-cohort composition, denominator or outcomes as predictors.

Do not add to the core learned model:
- borough or cohort-year dummy variables;
- additional outcome lags, year-on-year changes, slopes or rolling averages;
- the two adverse outcome components separately;
- London level or historical borough offset as additional learned regressors;
- cohort size as a predictor;
- disadvantage in addition to / instead of FSM for the core predictive model;
- special-school share, sex composition or ethnicity composition.

**Rationale:**
The three retained features represent distinct, interpretable information available from the immediately preceding cohort and are constructible from the earliest transition. Extra historical or composition features would add degrees of freedom unsupported by only four development target years. London-level and longer-run borough-history structure remain explicitly represented by the frozen historical baselines rather than being duplicated inside the learned model.

**QA rule:**
No core-feature imputation is used. Missing expected headline/FSM/SEN inputs are treated as a preprocessing or data-quality failure to investigate.

---

## D9a8 — Predictive learned model and preprocessing

**Evidence:** `DATA_AUDIT.md` §§20.2–20.4

**Status:** Accepted

**Decision:**
Use one learned predictive model: an **unregularised median / least-absolute-deviations linear regression**:

```text
predicted adverse_rate_(b,t+1)
    = beta_0
    + beta_1 * adverse_rate_(b,t)
    + beta_2 * FSM_share_(b,t)
    + beta_3 * Identified_SEN_share_(b,t)
```

Fit the coefficients by minimising **absolute error**, equivalently quantile regression at the 0.5 quantile.

Implementation specification:
- equal weight for each borough-transition row;
- intercept included;
- no regularisation;
- no feature scaling;
- no imputation;
- no hyperparameter tuning;
- no prediction clipping.

A suitable implementation is `QuantileRegressor(quantile=0.5, alpha=0, solver="highs")`.

**Rationale:**
The primary predictive metric is unweighted borough MAE, so an equal-weight absolute-error regression directly aligns the fitting objective with the primary evaluation objective. The three-predictor design does not show a serious numerical redundancy problem. Ridge could still reduce small-sample variance in principle, but it would introduce a penalty-strength choice that the very short chronological history cannot tune convincingly. OLS instead optimises squared error and is therefore less directly aligned with the frozen primary metric.

The predictive estimator deliberately differs from the grouped-binomial explanatory model. The explanatory question uses counts and denominators to estimate historical probability structure while respecting different statistical precision; the predictive question asks how accurately the next rate can be forecast for a **typical borough**, for which unweighted MAE gives each borough equal evaluation weight.

---

## D9a9 — Predictive benchmark comparison and reporting rule

**Evidence:** `DATA_AUDIT.md` §20.5

**Status:** Accepted

**Decision:**
Carry four predeclared forecasting methods through the chronological evaluation:

1. **B1:** borough persistence;
2. **B2:** London-level persistence;
3. **B3:** London level + historical borough offset;
4. **M1:** the D9a8 median/LAD learned model.

Do **not** use 2018/19–2021/22 to search across model families or select whichever of B1–B3/M1 happens to score best. These years are the development evaluation for diagnosing stability and understanding relative performance of the already-frozen methods.

For every development target year, report:
- unweighted MAE in percentage points as primary;
- RMSE in percentage points as secondary;
- target-cohort-size-weighted MAE as sensitivity.

Also report the mean of each metric across the four development target years, with the principal emphasis remaining on mean unweighted MAE plus the year-by-year pattern.

After D9a is documented, carry the **same four methods unchanged** into the locked 2022/23 temporal evaluation. Fit M1 on all five earlier transitions permitted through 2021/22; calculate B1–B3 mechanically from information through 2021/22. Report the final results regardless of which method performs best.

**Interpretation rule:**
A small average advantage or an advantage concentrated in one development/final year is not evidence of robust superiority. If M1 beats B3, do not claim that FSM/SEN add value *conditional on B3*, because M1 and B3 use different historical information sets.

No practical-equivalence threshold, `2/4`-year winning rule or score-based tie-break hierarchy is used.

---

## D9a10 — Predictive diagnostic / reopening rule

**Evidence:** `DATA_AUDIT.md` §20.4

**Status:** Accepted

**Decision:**
Do not reopen the learned-model family because coefficients move normally as the expanding training history changes.

Before the 2022/23 evaluation is opened, reopen the predictive estimator only if an objective diagnostic reveals a specific failure, such as:
- loss of full design-matrix rank;
- solver failure or materially inconsistent solutions across independent implementations;
- non-finite coefficients or predictions;
- materially invalid probability predictions outside the 0–100% range;
- a preprocessing / QA failure;
- another specific structural diagnostic showing that the frozen linear specification is untenable.

Any such reopening must be documented before 2022/23 predictive performance is calculated.

---

# D9c — Development Performance Evaluation

**Status:** Accepted; D9c implementation and QA completed.

**Evidence:** `DATA_AUDIT.md` §22 and the reproducible D9c evaluation code/tests.

**Decision:** Preserve the four D9a9 methods (B1, B2, B3, M1) unchanged. Evaluate each on the same 128 held-out borough–target-year observations from the four expanding-window development targets, 2018/19–2021/22. Report within-year MAE, RMSE and target-cohort-weighted MAE (all in percentage points) and arithmetic means of the four annual scores. Target-cohort denominators are evaluation weights only. Negative `MAE − B1 MAE` denotes an improvement over B1.

| Method | Mean annual MAE (pp) | Mean annual RMSE (pp) | Mean annual weighted MAE (pp) | MAE − B1 (pp) |
|---|---:|---:|---:|---:|
| B1: borough persistence | 0.716035 | 0.910924 | 0.666973 | 0.000000 |
| B2: London persistence | 0.954890 | 1.199265 | 0.946517 | +0.238855 |
| B3: London + expanding borough offset | 0.638242 | 0.791428 | 0.615388 | −0.077793 |
| M1: frozen median/LAD regression | 0.705727 | 0.904169 | 0.658234 | −0.010308 |

**Interpretation:** B3 has the lowest mean annual error on all three predeclared metrics and a lower annual MAE than M1 in each of the four development years. However, B3's individual absolute error is smaller in only 69/128 borough-year comparisons versus 59/128 for M1. M1 beats B1 on annual MAE in two of four development years; its mean B1 improvement (0.010308 pp) is small. These are descriptive comparisons, **not statistically established superiority**: just four common target-year regimes are observed, and borough errors share annual shocks.

The results do not demonstrate that FSM/SEN add or lack incremental predictive value *conditional on B3*, because B3 and M1 use different information sets. No score-driven tuning, model selection or replacement is permitted. The current series is retrospective and harmonised, not point-in-time operational forecasts. The adverse outcome is **not** a direct NEET measure.

**Validation:** Common keys and merged source values were checked; 16 year–method records and four method summaries were independently recalculated and validated; two-cohort known-answer synthetic and deliberate-corruption tests passed. No 2022/23 predictive target was constructed, scored or inspected in D9c. That final evaluation remains locked until the pre-final audit and formal release of the evaluation boundary.

---

# D9d — Explanatory GLM implementation and numerical QA checkpoint

**Status:** E1–E4 fitting and structural/numerical QA implemented and locally verified. This is an implementation checkpoint, **not** completion of explanatory evaluation or inference.

**Evidence:** `DATA_AUDIT.md` §23; `src/youth_offer/explanatory.py`, `src/youth_offer/qa.py`, `src/run_pipeline.py` and `tests/test_explanatory.py`.

**Implementation:** Retain the frozen D9a1–D9a5 grouped-binomial logit specifications on the 224 borough × cohort records (32 boroughs × seven cohorts, 2016/17–2022/23):

- **E1:** categorical cohort-year effects (2016/17 reference; seven coefficients including intercept);
- **E2:** borough fixed effects (lowest sorted borough code as reference; 32 coefficients);
- **E3:** borough and categorical cohort-year fixed effects (38 coefficients);
- **E4:** E3 plus FSM-eligible, Identified-SEN and standalone special-school cohort shares, entered on the 0–1 scale (41 coefficients).

**Verification:** All four fits converged and passed dimension, degrees-of-freedom, full-rank and independent numerical QA. E1/E2 fitted rates match independently pooled counts; E3 borough and year fitted-count margins match observed margins; E4 satisfies all 41 grouped-binomial score equations to numerical tolerance. The permanent synthetic `unittest` module covers specification/row alignment, these identities, corrupted-count rejection and rank-deficiency rejection. See §23 for measured discrepancies, dispersion diagnostics and reproducibility commands.

**Interpretation and scope:** These checks establish implementation consistency, not substantive effects, causal relationships or valid naive-binomial standard errors. Remaining under the **unchanged** D9a/D8 plan are deviance and rate-error comparisons, residual/influence/overdispersion diagnostics, borough-block-bootstrap inference and clustered-covariance cross-check, predeclared robustness, and probability-scale reporting. Do not select or drop the E4 composition variables based on initial dispersion or significance.

**Predictive boundary:** Including 2022/23 in the seven-cohort *explanatory* fits is permitted. The separate 2022/23 *predictive* evaluation remains locked, with no final-year predictive performance calculated or inspected. Code/documentation commit status is not implied by this checkpoint.

---

# Open Questions

These are not yet accepted decisions.

- What exact public-facing label, if any, should refine “Outside recorded sustained destinations” without changing its frozen definition?
- If borough-level special-school or AP comparisons are retained in the final presentation, what explicit uncertainty/stability treatment is most useful?
- What exact common reference distribution / formula should be used if standardised adjusted borough summaries are included in final reporting?

---

## Working rule

Proceed in the order:

**problem understanding → raw-data understanding → population/outcome decisions → data-quality audit → EDA → modelling question → validation design → implementation → final audit**

**D9c predictive development evaluation and D9d E1–E4 fitting/numerical QA are implemented and locally verified.** Next, complete the explanatory fit comparisons, diagnostics, inference and robustness under frozen D9a, alongside the pre-final predictive audit. Do not calculate or inspect 2022/23 predictive performance until the final boundary is explicitly released after all pre-final checks.
