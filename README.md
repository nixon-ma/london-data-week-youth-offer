# London Data Week 2026 — Youth Offer for London

A reproducible data-science rebuild of a London Data Week 2026 hackathon project. It examines variation in Key Stage 4 (KS4) destinations across London boroughs and evaluates whether next-cohort adverse destination rates can be forecast from historical information.

> **Project status:** D1–D9g completed, including the authorised 2022/23 predictive final evaluation. D9e explanatory inference and robustness were audited at export level; D9f local tests and historical-only preflight passed (user-reported). B3 had the lowest final error across all three predeclared metrics. This is not an operational council forecasting or intervention-allocation tool.

## What are we measuring?

The primary outcome is the number and proportion of pupils **not in a recorded sustained education, employment or apprenticeship destination**, combining the published *Not recorded as a sustained destination* and *Activity not captured* categories. The rate uses the exact KS4 cohort denominator.

**This is not a direct NEET measure.** An unrecorded destination does not establish that a young person is not in education, employment or training; recording quality can also affect the measured rate.

The main dataset has **224 borough–cohort observations**: 32 London Local Authorities across seven cohorts (2016/17–2022/23), for the combined state-funded mainstream and special-school population. Local Authority refers to the **school/institution's geography**, not necessarily the pupil's borough of residence.

## Three different questions

| Analysis | Question | What it can support |
| --- | --- | --- |
| **Descriptive** | Where, when and for which groups are adverse rates and counts high? | Identifying patterns and places or groups for further investigation |
| **Explanatory (E1–E4)** | How are observed rates associated with persistent borough differences, common cohort-year patterns and cohort composition? | Understanding *historical conditional associations* and residual discrepancies |
| **Predictive (B1–B3, M1)** | Using prior-cohort information, how well can we estimate the *next* cohort's rate? | Testing forecasting accuracy against simple historical benchmarks |

None of these, on its own, estimates the causal impact of a council intervention.

### Explanatory models: E1–E4

All four models use the full seven-cohort panel, including 2022/23, and fit the observed adverse counts against exact cohort denominators with a grouped-binomial logistic model:

- **E1:** Cohort-year effects.
- **E2:** Borough effects.
- **E3:** Borough + cohort-year effects.
- **E4:** Borough + cohort-year effects + *same-cohort* FSM-eligible share, Identified-SEN share and standalone special-school share.

These are **in-sample explanatory fits**, not next-year forecasts. E4 uses composition observed in the cohort being explained, and its categorical year effects are estimated using outcomes from those observed years. It can examine associations with changes in composition **within boroughs over time**, after common year patterns are accounted for, but **does not forecast how composition itself changes**.

The special-school share is a **structural population-composition adjustment**, not an intervention target. An association with that share, if found, would not imply that changing special-school provision reduces adverse outcomes.

Initial explanatory results show substantially improved in-sample fit from borough and cohort-year effects; E4's composition block adds little further deviance reduction after those effects. E4's in-sample MAE/RMSE are approximately **0.447/0.564 percentage points**, with Pearson dispersion approximately **1.60**. These are **fit diagnostics, not inference-qualified effects or forecasts**; see [DATA_AUDIT.md §23.5](DATA_AUDIT.md#235-subsequent-d9d-fit-comparison-residual-and-influence-diagnostics--locally-verified).

D9e completed 2,000 successful borough-bootstrap refits and six predeclared robustness families, checked numerically at the export level. The adjusted 2022/23–2016/17 contrast is +0.586 pp in E4 but reverses under a linear-trend alternative (−0.331 pp). These are historical associations, not causal effects or predictions; see [DATA_AUDIT.md §24](DATA_AUDIT.md).

### Predictive models: B1–B3 and M1

For a forecast of cohort `t+1`, the inputs must come from cohort `t` or earlier. The four frozen methods are:

- **B1:** Borough persistence.
- **B2:** London-level persistence.
- **B3:** London level plus historical borough offset.
- **M1:** A median/least-absolute-deviations linear model using the **previous cohort's** adverse rate, FSM share and Identified-SEN share.

Unlike E4, M1 does **not** include borough or cohort-year dummy variables or special-school share. This is a predeclared **parsimony choice given only seven cohorts**, **not evidence** that those factors are unimportant or cannot improve a future forecast. B3 separately represents historical borough structure. M1 also does **not** forecast next year's FSM or SEN shares; it predicts the next adverse rate directly from prior information.

The 2018/19–2021/22 development target years were evaluated chronologically; B3 had lower mean development MAE than M1. Following explicit release authorisation, the **2022/23 final predictive evaluation was completed** without retuning: B3 had the lowest MAE (0.878 pp), RMSE (1.087 pp) and target-cohort-weighted MAE (0.776 pp). M1 did not improve on B1 in primary MAE. This one final cohort is not evidence of stable future superiority, and B3 versus M1 does not identify the incremental effect of FSM/SEN conditional on B3; see `DATA_AUDIT.md` §28.

Forecasting is a **retrospective benchmark on a harmonised published dataset**, not a demonstrated real-time historical forecasting system: publication delays and revisions would need separate point-in-time verification.

## What can councils use this for?

This project may help councils or analysts **prioritise questions**: where recorded adverse outcomes are concentrated, which historical disparities persist after statistical adjustments, and whether historical patterns offer useful forecasting benchmarks.

It **cannot establish which intervention will reduce adverse destinations**. Associations with FSM, SEN or special-school share do not show causal effects, and a change in the measured adverse rate could reflect better destination recording rather than improved destinations. Evaluating an intervention would require suitable causal evidence and attention to actual sustained outcomes.

## Methodology and evidence

- [DECISIONS.md](DECISIONS.md) — accepted definitions, frozen modelling designs, validation and interpretation rules (especially D7, D8 and D9a).
- [DATA_AUDIT.md](DATA_AUDIT.md) — source-data audit, construction checks, modelling evidence and implementation checkpoints.
- [src/run_pipeline.py](src/run_pipeline.py) — current reproducible pipeline entry point.
- [src/youth_offer/](src/youth_offer/) and [tests/](tests/) — implementation and tests.

To reproduce locally, place the source ZIP at `data/raw/key-stage-4-destination-measures_2023-24.zip` and run `python -m unittest discover -s tests -p 'test_*.py' -v`, then `python src/run_pipeline.py` from the repository root. Generated files under `outputs/` are git-ignored; diagnostic results are documented in `DATA_AUDIT.md` §23.5. Environment/dependency packaging is still pending.

The current rebuild is deliberately distinct from the original time-limited hackathon implementation.
