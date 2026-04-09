from __future__ import annotations

import numpy as np
import pandas as pd

from metrics.percentile import percentile_rank_0_100


def test_percentile_monotone_non_decreasing():
    s = pd.Series([0.0, 1.0, 2.0, 3.0], index=[10, 11, 12, 13])
    p = percentile_rank_0_100(s)
    assert list(p.index) == [10, 11, 12, 13]
    assert np.all(np.diff(p.to_numpy()) >= 0)
    assert p.iloc[-1] == 100.0


def test_percentile_small_set_with_ties_max_rule():
    # Values: [0, 0, 2, 10] with method="max" ranks -> [2, 2, 3, 4] out of 4.
    s = pd.Series([0.0, 0.0, 2.0, 10.0], index=[1, 2, 3, 4])
    p = percentile_rank_0_100(s)
    expected = pd.Series([50.0, 50.0, 75.0, 100.0], index=[1, 2, 3, 4])
    np.testing.assert_allclose(p.to_numpy(), expected.to_numpy(), rtol=0, atol=1e-12)

