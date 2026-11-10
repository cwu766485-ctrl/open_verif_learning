from dv.coverage.risk_closure_review import toggle_axes


def test_toggle_retains_signal_array_bit_and_direction():
    assert toggle_axes({'identity':'12|2|ctx_addr[3][17]:1->0|v_toggle/Top|'} ) == ('ctx_addr[3]', '17', '1->0')


def test_unknown_toggle_format_stays_unresolved():
    assert toggle_axes({'identity':'12|2|unexpected|page|'}) == ('unexpected', '', 'UNRESOLVED')
