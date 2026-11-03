"""Reproduce descriptive M1-versus-B3 development diagnostics.

Run from the repository root after `python scripts/run_pipeline.py`:
    python scripts/development_error_diagnostics.py

Only the four unlocked development target years are examined.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path('outputs/development')
YEARS = {'201819', '201920', '202021', '202122'}

evaluation = pd.read_csv(
    OUTPUT_DIR / 'evaluation_table.csv',
    dtype={'new_la_code': str, 'feature_year': str, 'target_year': str},
)
annual = pd.read_csv(
    OUTPUT_DIR / 'annual_metrics.csv',
    dtype={'target_year': str},
)

assert len(evaluation) == 128
assert set(evaluation['target_year']) == YEARS
assert evaluation.groupby('target_year').size().eq(32).all()

comparison = evaluation[[
    'new_la_code',
    'target_year',
    'target_adverse_rate_baseline',
    'b3_london_plus_borough_offset',
    'm1_prediction',
]].copy()
actual = comparison['target_adverse_rate_baseline']
comparison['b3_abs_error_pp'] = 100 * (
    comparison['b3_london_plus_borough_offset'] - actual
).abs()
comparison['m1_abs_error_pp'] = 100 * (
    comparison['m1_prediction'] - actual
).abs()
comparison['m1_minus_b3_error_pp'] = (
    comparison['m1_abs_error_pp'] - comparison['b3_abs_error_pp']
)

by_year = comparison.groupby('target_year').agg(
    mean_difference_pp=('m1_minus_b3_error_pp', 'mean'),
    largest_disadvantage_pp=('m1_minus_b3_error_pp', 'max'),
    largest_advantage_pp=('m1_minus_b3_error_pp', 'min'),
    median_difference_pp=('m1_minus_b3_error_pp', 'median'),
    b3_better_count=('m1_minus_b3_error_pp', lambda x: (x > 0).sum()),
    m1_better_count=('m1_minus_b3_error_pp', lambda x: (x < 0).sum()),
)

# Identity: the mean of per-borough MAE differences equals the
# difference of independently produced annual mean absolute errors.
annual_mae = annual.pivot(index='target_year', columns='method', values='mae_pp')
assert set(annual_mae.index) == YEARS
np.testing.assert_allclose(
    by_year['mean_difference_pp'].sort_index().to_numpy(),
    (annual_mae['M1'] - annual_mae['B3']).sort_index().to_numpy(),
    atol=1e-10,
    rtol=1e-10,
)

print('M1 versus B3 by development target year:')
print(by_year.to_string())
print('\nLargest M1 disadvantages:')
print(comparison.nlargest(8, 'm1_minus_b3_error_pp').to_string(index=False))
