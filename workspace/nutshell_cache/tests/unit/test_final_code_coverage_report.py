import pytest
from dv.coverage.final_code_coverage_report import line_ranges, summarize


def test_ranges_preserve_gaps_and_remove_duplicates():
    assert line_ranges([9, 3, 2, 3, 4, 7]) == '2-4, 7, 9'
    assert line_ranges([]) == ''


def test_other_top_hit_cannot_close_zero_or_hide_denominator():
    points = [dict(point_id='a', dataset_id='main', source='x.sv', metric='line', count=0),
              dict(point_id='b', dataset_id='block', source='x.sv', metric='line', count=1)]
    groups = summarize(points)
    assert groups[('main', 'x.sv', 'line')] == dict(total=1, hit=0, zero=1)
    assert groups[('block', 'x.sv', 'line')] == dict(total=1, hit=1, zero=0)
    with pytest.raises(ValueError, match='duplicate Point ID'):
        summarize(points + points[:1])
