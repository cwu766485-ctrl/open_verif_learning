from dv.coverage.coverage_triage import classify


def test_only_exact_proved_block_bits_are_candidates():
    p=dict(dataset_id='directory_controller', metric='toggle', identity='103|16|line_addr_q[0]:0->1|page|',source='',source_line=103)
    assert classify(p,None)[0]=='2_WAIVER_CANDIDATE'
    p['dataset_id']='main_subsystem'
    assert classify(p,None)[0]=='REVIEW_REQUIRED'


def test_default_is_not_deletable_and_hit_requires_execution():
    p=dict(dataset_id='shared_line_engine',metric='line',source='rtl/coherence/SharedLineEngine.sv',source_line=367)
    assert classify(p,None)[0]=='REVIEW_REQUIRED'
    assert classify(p,{'count':1})[0]=='1_TESTABLE'
