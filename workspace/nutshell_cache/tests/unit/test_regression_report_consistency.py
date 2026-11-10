import hashlib
import json
from dv.coverage import rtl_coverage_closure as report
from dv.coverage import rtl_release_gate as gate
from dv.coverage import rtl_coverage_dataset_manifest as manifest


def test_report_requires_current_source_and_intact_logs(tmp_path, monkeypatch):
    log = tmp_path / 'test.log'
    log.write_text('PASS\n')
    status = tmp_path / 'runs.json'
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    monkeypatch.setattr(gate, 'RUN_STATUS', status)
    monkeypatch.setattr(gate, 'REQUIRED_GATES', ['test'])
    monkeypatch.setattr(manifest, 'source_fingerprint', lambda: ('current', {}))
    run = dict(result='PASS', returncode=0, log='test.log',
               log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
               source_fingerprint_before='current', source_fingerprint_after='current')
    data = dict(source_fingerprint='current', runs={'test': run})
    status.write_text(json.dumps(data))
    assert report.full_regression_status()[0] == 'PASS'
    log.write_text('tampered')
    assert report.full_regression_status()[0] == 'OPEN'
    log.write_text('PASS\n')
    data['source_fingerprint'] = 'old'
    status.write_text(json.dumps(data))
    assert report.full_regression_status()[0] == 'OPEN'
    status.unlink()
    assert report.full_regression_status()[0] == 'OPEN'
