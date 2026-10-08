from dv.fault_injection.run import run_all


def test_checkers_catch_representative_injected_faults(tmp_path):
    report = run_all(tmp_path / "fault-injection.json")

    assert report["status"] == "PASS"
    assert report["caught"] == 4
    assert all(injection["caught"] for injection in report["injections"])
