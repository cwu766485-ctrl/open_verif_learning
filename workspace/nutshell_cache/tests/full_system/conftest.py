"""Picker fixture for the full AXI-integrated MESI cache top."""

import json
import importlib.metadata
import os
import platform
import shutil
import subprocess
from pathlib import Path

import pytest
from toffee import ClockCycles, Executor, start_clock
from toffee_test import ToffeeRequest, fixture

from dv.env.full_system_env import FullSystemEnv

try:
    from coherent_axi_python import DUTCoherentCacheAxiPythonWrapper
except ImportError:
    DUTCoherentCacheAxiPythonWrapper = None


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted((_json_safe(item) for item in value), key=str)
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _tool_versions():
    """Capture versions that affect a saved full-system result."""
    versions = {"python": platform.python_version()}
    for distribution in ("pytest", "toffee", "picker-py", "verilator"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = "not-installed-as-python-package"
    for executable, args in (("verilator", ["--version"]),
                             ("picker", ["--version"])):
        path = shutil.which(executable)
        if not path:
            versions[executable] = "not-found-in-PATH"
            continue
        result = subprocess.run([path, *args], check=False, capture_output=True,
                                text=True, timeout=5)
        output = (result.stdout or result.stderr).strip().splitlines()
        versions[executable] = output[0] if output else f"exit-{result.returncode}"
    return versions


def pytest_configure(config):
    config._full_system_envs = []


def pytest_sessionfinish(session, exitstatus):
    envs = getattr(session.config, "_full_system_envs", [])
    if not envs:
        return
    output = Path(os.environ.get(
        "FULL_SYSTEM_COVERAGE_OUTPUT",
        "reports/full_system/full_system_coverage.json",
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "dut": "CoherentCacheAxiSubsystem",
        "pytest_exit_status": exitstatus,
        "test_environment_count": len(envs),
        "runs": [{
            "test_id": env.trace_test_id,
            "scenario_id": env.trace_scenario_id,
            "seed": env.trace_seed,
            "test_status": env.trace_test_status,
            "configuration": env.trace_config,
            "failure_context": env.trace_failure_context,
            "generated_operations": env.trace_operations,
            "initial_backing_memory": {
                f"0x{address:08x}": f"0x{value:016x}"
                for address, value in sorted(env.axi.seeded_words.items())
            },
            "coverage": env.coverage_report(),
            # Every FullSystemEnv is scoped to one pytest testcase/seed, so
            # its checked counters are that run's coverage delta from zero.
            "coverage_delta": env.coverage_report(),
            "monitor": {
                "event_counts": dict(env.monitor.counts),
                "stall_cycles": dict(env.monitor.stall_cycles),
                "mshr_occupancy_histogram": dict(
                    env.monitor.mshr_occupancy_histogram
                ),
                "directory_context_histogram": dict(
                    env.monitor.directory_context_histogram
                ),
                "max_mshr_occupancy": env.monitor.max_mshr_occupancy,
                "max_directory_contexts": env.monitor.max_directory_contexts,
                "reset_epoch": env.monitor.reset_epoch,
                "axi_peak_reads": env.axi.peak_reads,
                "axi_peak_writes": env.axi.peak_writes,
                "cpu_request_accepts": sum(
                    1 for event in env.monitor.events
                    if event["source"] == "cpu" and
                    event["event_type"] == "request_accept"
                ),
                "cpu_response_completions": sum(
                    1 for event in env.monitor.events
                    if event["source"] == "cpu" and
                    event["event_type"] == "response_complete"
                ),
                "replay_records": sum(
                    1 for item in env.trace_operations
                    if item.get("kind") == "replay"
                ),
                "protocol_error": env.trace_protocol_error,
                "fatal_error": env.trace_fatal_error,
                "axi_error_count": len(env.axi.errors),
            },
        } for env in envs],
    }
    repo = Path(__file__).resolve().parents[3]
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False, capture_output=True, text=True,
    ).stdout.strip() or "unknown"
    versions = _tool_versions()
    payload["git_sha"] = revision
    payload["tool_versions"] = versions
    output.write_text(json.dumps(_json_safe(payload), indent=2) + "\n",
                      encoding="utf-8")
    trace = Path(os.environ.get(
        "FULL_SYSTEM_TRACE_OUTPUT",
        "reports/full_system/full_system_trace.jsonl",
    ))
    with trace.open("w", encoding="utf-8") as stream:
        for env in envs:
            metadata = {
                "record_type": "run", "git_sha": revision,
                "tool_versions": versions,
                "test_id": env.trace_test_id,
                "scenario_id": env.trace_scenario_id,
                "seed": env.trace_seed,
                "configuration": env.trace_config,
                "coverage_delta": env.coverage_report(),
                "transaction_count": sum(
                    1 for event in env.monitor.events
                    if event["source"] == "cpu" and
                    event["event_type"] == "request_accept"
                ),
                "replay_count": sum(
                    1 for item in env.trace_operations
                    if item.get("kind") == "replay"
                ),
                "test_status": env.trace_test_status,
                "failure_context": env.trace_failure_context,
                "generated_operations": env.trace_operations,
                "initial_backing_memory": {
                    f"0x{address:08x}": f"0x{value:016x}"
                    for address, value in sorted(env.axi.seeded_words.items())
                },
                "pytest_exit_status": exitstatus,
            }
            stream.write(json.dumps(_json_safe(metadata), sort_keys=True) + "\n")
            for event in env.trace_records():
                record = {"record_type": "event", **event,
                          "git_sha": revision, "test_id": env.trace_test_id,
                          "scenario_id": env.trace_scenario_id,
                          "seed": env.trace_seed}
                stream.write(json.dumps(_json_safe(record), sort_keys=True) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach the exact pytest outcome/failure to the trace for that test."""
    outcome = yield
    report = outcome.get_result()
    if report.when not in ("call", "setup"):
        return
    for env in getattr(item.config, "_full_system_envs", []):
        if env.trace_test_id != item.nodeid:
            continue
        if report.when == "call":
            env.trace_test_status = "failed" if report.failed else "passed"
            # Snapshot scalar RTL status while the Toffee DUT handle is alive.
            # Reading these live XData pins from pytest_sessionfinish can hit
            # stale simulator backing storage after reset-heavy tests.
            env.trace_protocol_error = int(env.dut.protocol_error.value)
            env.trace_fatal_error = int(env.dut.fatal_error.value)
        if report.failed:
            env.trace_failure_context = report.longreprtext


@fixture
async def full_system_env(toffee_request: ToffeeRequest, pytestconfig, request):
    if DUTCoherentCacheAxiPythonWrapper is None:
        pytest.skip("run make coherence_full_system_build first")

    async def start(*, axi_options=None, mmio_options=None, seed=None):
        dut = toffee_request.create_dut(
            DUTCoherentCacheAxiPythonWrapper, "clock")
        for name in (
            "cpu_req_valid", "cpu_req_addr", "cpu_req_write", "cpu_req_wmask",
            "cpu_req_wdata", "cpu_resp_ready", "reset", "mmio_req_ready",
            "mmio_resp_valid", "mmio_resp_rdata", "apb_psel", "apb_penable",
            "apb_pwrite", "apb_paddr", "axi_arready", "axi_rid", "axi_rdata",
            "axi_rresp", "axi_rlast", "axi_rvalid", "axi_awready", "axi_wready",
            "axi_bid", "axi_bresp", "axi_bvalid",
        ):
            getattr(dut, name).value = 0
        dut.reset.AsImmWrite()
        dut.reset.value = 1
        dut.reset.AsRiseWrite()
        start_clock(dut)
        env = FullSystemEnv(dut, axi_options=axi_options,
                            mmio_options=mmio_options)
        env.trace_test_id = request.node.nodeid
        env.coverage.set_testcase(request.node.nodeid)
        env.trace_seed = seed
        env.trace_scenario_id = request.node.name.split("[", 1)[0]
        env.trace_config = {
            "agents": {"axi": dict(axi_options or {}),
                       "mmio": dict(mmio_options or {})}
        }
        pytestconfig._full_system_envs.append(env)
        async with Executor(exit="none") as executor:
            executor(env.axi.run(), sche_group="axi_memory_slave")
            executor(env.mmio.run(), sche_group="mmio_slave")
            executor(env.monitor.run(), sche_group="graybox_monitor")
            await ClockCycles(dut, 4)
            dut.reset.value = 0
        return env

    return start
