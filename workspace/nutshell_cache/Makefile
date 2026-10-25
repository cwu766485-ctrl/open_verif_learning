SHELL       := /bin/bash
COHERENCE_JOBS ?= 2
ENV_SCRIPT  := ./scripts/env.sh
VSRC_DIR    = ./rtl
PICKER      = picker
NAME        = Cache
NAME_L      = cache
SIM         = verilator
WAVE_FORMAT = fst
TARGET_LANG = python
GTKWAVE 	= gtkwave

# Generate DUT
TOP_ENTRY = ./rtl/legacy_l1/CacheTop.v
RTL_FILELIST = ./rtl/Cache.files.f
TL = python
WAVEFORM = -w cache.fst

gen_dut:
	@rm -rf $(NAME)
	@source $(ENV_SCRIPT); $(PICKER) export --autobuild=true $(TOP_ENTRY) --fs $(RTL_FILELIST) \
		-w $(NAME).$(WAVE_FORMAT) \
		--sname $(NAME) \
		--tdir $(NAME) \
		--lang $(TARGET_LANG) \
		--sim $(SIM) \
		-e -c

.PHONY: wave test test_slow mega_random benchmark coverage rtl_coverage functional_coverage formal fault_injection report gen_dut doctor coherence_build coherence_smoke coherence_random coherence_regression coherence_formal coherence_l1_array coherence_l2_array coherence_l1_controller coherence_directory coherence_request_arbiter coherence_snoop_arbiter coherence_cluster coherence_bus_blocks coherence_axi_lint coherence_axi_e2e coherence_multisnoop coherence_modules coherence_verify coherence_python_build coherence_python_test coherence_benchmark_v2 coherence_python_verify coherence_axi_python_build coherence_axi_python_test coherence_python_coverage_close clean

wave:
	@source $(ENV_SCRIPT); $(GTKWAVE) -r .gtkwaverc $(NAME_L).$(WAVE_FORMAT)
# Test
test:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv -m "not slow and not benchmark"

# Run deterministic DCache performance traces and write a JSON result.
benchmark:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv -m benchmark benchmarks/test_dcache_benchmark.py

# Long array and mixed-random sweeps are opt-in.
test_slow:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv -m slow

mega_random:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv tests/l1/test_random.py::test_mega_randomized_cache_mmio_traffic

coverage: report

rtl_coverage:
	@source $(ENV_SCRIPT); mkdir -p reports/rtl; \
	 shopt -s nullglob; coverage_files=(reports/DUTCache_test_*.dat); \
	 if [ -z "$${coverage_files[0]:-}" ]; then \
	   echo "No per-test Verilator data found; run 'make report' first." >&2; exit 2; \
	 fi; \
	 verilator_coverage --write-info reports/cache.info "$${coverage_files[@]}"; \
	 genhtml reports/cache.info --output-directory reports/rtl

report:
	@rm -f reports/DUTCache_test_*.dat
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv -m "not slow and not benchmark" --toffee-report --report-dir reports --report-name cache
	$(MAKE) rtl_coverage
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.closure reports/cache.info
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.functional_closure reports/functional_coverage.json
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -c "from dv.coverage.report import render_html; render_html('reports/functional_coverage.json', 'reports/functional_coverage.html')"
	$(MAKE) fault_injection

functional_coverage: test
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -c "from dv.coverage.report import render_html; render_html('reports/functional_coverage.json', 'reports/functional_coverage.html')"

formal: coherence_formal
	@source $(ENV_SCRIPT); export PATH="$(abspath ../../.tooling/sby-install/bin):$$PATH"; \
	 mkdir -p reports/formal; \
	 sby -f -d reports/formal/replacement_selector formal/replacement_selector.sby && \
	 sby -f -d reports/formal/cache_way_selector formal/cache_way_selector.sby && \
	 sby -f -d reports/formal/cache_stage2_stability formal/cache_stage2_stability.sby && \
	 yosys -Q -l reports/formal/cache_stage3_response_lifecycle_sat.log -s formal/cache_stage3_response_lifecycle.ys && \
	 sby -f -d reports/formal/cache_metadata_invariant formal/cache_metadata_invariant.sby && \
	 yosys -Q -l reports/formal/cache_metadata_stage3_sat.log -s formal/cache_metadata_stage3.ys && \
	 yosys -Q -l reports/formal/cache_stage3_array_sat.log -s formal/cache_stage3_array.ys && \
	 sby -f -d reports/formal/cache_metadata_reachability formal/cache_metadata_reachability.sby && \
	 sby -f -d reports/formal/cache_stage3_reset_cover formal/cache_stage3_reset_cover.sby && \
	 sby -f -d reports/formal/cache_stage3_stall_cover formal/cache_stage3_stall_cover.sby && \
	 sby -f -d reports/formal/cache_stage3_refill_cover formal/cache_stage3_refill_cover.sby && \
	 sby -f -d reports/formal/cache_stage3_dirty_writeback_cover formal/cache_stage3_dirty_writeback_cover.sby && \
	 PYTHONPATH=.:./dv:./Cache:./tests python3 formal/mutations/run.py

coherence_formal:
	@mkdir -p reports/formal
	@if [[ -f .tooling/oss-cad-suite/environment ]]; then source .tooling/oss-cad-suite/environment; fi; \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_request_arbiter formal/coherence_request_arbiter.sby && \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_snoop_arbiter formal/coherence_snoop_arbiter.sby && \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_directory formal/coherence_directory.sby && \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_directory_mshr_bank formal/coherence_directory_mshr_bank.sby && \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_directory_mshr_bank_cover formal/coherence_directory_mshr_bank_cover.sby && \
	 PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_l1_controller formal/coherence_l1_controller.sby

fault_injection:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.fault_injection.run

doctor:
	@source $(ENV_SCRIPT); echo "python: $$(command -v python3)"; python3 --version; \
	 echo "pytest: $$(command -v pytest || true)"; python3 -m pytest --version; \
	 python3 -c "import toffee, toffee_test; print('toffee: OK')"; \
	 echo "picker: $$(command -v picker)"; picker --version || true; \
	 echo "sby: $$(command -v sby)"; sby --version; \
	 echo "verilator: $$(command -v verilator)"; verilator --version

# Small subsystem-level directed MESI smoke test; does not run the legacy
# single-L1 Python regression.
coherence_build:
	@mkdir -p reports/coherence
	@rm -rf reports/coherence/obj_dir
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert --coverage-line --coverage-branch -j $(COHERENCE_JOBS) -CFLAGS -O0 -Wall -Wno-fatal -Wno-BLKSEQ \
	  --unroll-count 10000 --top-module CoherentCacheSubsystem_tb \
	  --Mdir ../reports/coherence/obj_dir -f Coherence.files.f \
	  ../tests/subsystem/rtl/CoherentCacheSubsystem_tb.sv

coherence_smoke: coherence_build
	@reports/coherence/obj_dir/VCoherentCacheSubsystem_tb

coherence_random: coherence_build
	@for seed in 00000001 00001234 5EEDC0DE DEADBEEF 2468ACE0; do \
	  echo "=== coherence regression seed=$$seed ==="; \
	  reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +seed=$$seed || exit $$?; \
	done

# Full dual-L1 regression with retained logs, merged Verilator coverage, and
# explicit Feature -> Testpoint -> Bin closure. Logs and reports are ignored
# generated outputs under reports/coherence/.
coherence_regression: coherence_build
	@rm -f reports/coherence/*.dat reports/coherence/*.log reports/coherence/coverage.info
	@set -o pipefail; reports/coherence/obj_dir/VCoherentCacheSubsystem_tb \
	  +verilator+coverage+file+reports/coherence/smoke.dat 2>&1 | tee reports/coherence/smoke.log
	@set -o pipefail; reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +l2_multisnoop_only \
	  +verilator+coverage+file+reports/coherence/multisnoop.dat 2>&1 | tee reports/coherence/multisnoop.log
	@for seed in 00000001 00001234 5EEDC0DE DEADBEEF 2468ACE0; do \
	  echo "=== coherence regression seed=$$seed ==="; \
	  set -o pipefail; reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +seed=$$seed \
	    +verilator+coverage+file+reports/coherence/seed_$$seed.dat 2>&1 | \
	    tee reports/coherence/seed_$$seed.log || exit $$?; \
	done
	@set -o pipefail; $(MAKE) coherence_directory_mshr_bank 2>&1 | tee reports/coherence/directory_mshr_bank.log
	@source $(ENV_SCRIPT); verilator_coverage --write reports/coherence/coverage.dat reports/coherence/*.dat
	@source $(ENV_SCRIPT); verilator_coverage --write-info reports/coherence/coverage.info reports/coherence/coverage.dat
	@source $(ENV_SCRIPT); cd rtl && genhtml ../reports/coherence/coverage.info --output-directory ../reports/coherence/code_html
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv python3 -m dv.coverage.coherence_closure \
	  --log reports/coherence/smoke.log --log reports/coherence/multisnoop.log \
	  --log reports/coherence/directory_mshr_bank.log \
	  --log reports/coherence/seed_00000001.log --log reports/coherence/seed_00001234.log \
	  --log reports/coherence/seed_5EEDC0DE.log --log reports/coherence/seed_DEADBEEF.log \
	  --log reports/coherence/seed_2468ACE0.log --lcov reports/coherence/coverage.info

# Fast array block tests use reduced geometries while preserving the RTL's
# indexing, metadata, replacement, full-line transfer, and backpressure rules.
coherence_l1_array:
	@mkdir -p reports/coherence/l1_array_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module MesiL1Array_tb --Mdir ../reports/coherence/l1_array_obj \
	  -f Coherence.files.f ../tests/l1/rtl/MesiL1Array_tb.sv
	@reports/coherence/l1_array_obj/VMesiL1Array_tb

coherence_l2_array:
	@mkdir -p reports/coherence/l2_array_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module SharedL2DirectoryArray_tb --Mdir ../reports/coherence/l2_array_obj \
	  -f Coherence.files.f ../tests/l2/rtl/SharedL2DirectoryArray_tb.sv
	@reports/coherence/l2_array_obj/VSharedL2DirectoryArray_tb

coherence_l1_controller:
	@mkdir -p reports/coherence/l1_controller_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module MesiL1Controller_tb --Mdir ../reports/coherence/l1_controller_obj \
	  -f Coherence.files.f ../tests/l1/rtl/MesiL1Controller_tb.sv
	@reports/coherence/l1_controller_obj/VMesiL1Controller_tb

coherence_directory:
	@mkdir -p reports/coherence/directory_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module DirectoryController_tb --Mdir ../reports/coherence/directory_obj \
	  -f Coherence.files.f ../tests/directory/rtl/DirectoryController_tb.sv
	@reports/coherence/directory_obj/VDirectoryController_tb

coherence_directory_mshr_bank:
	@mkdir -p reports/coherence/directory_mshr_bank_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module DirectoryMshrBank_tb --Mdir ../reports/coherence/directory_mshr_bank_obj \
	  -f Coherence.files.f ../tests/directory/rtl/DirectoryMshrBank_tb.sv
	@reports/coherence/directory_mshr_bank_obj/VDirectoryMshrBank_tb

coherence_request_arbiter:
	@mkdir -p reports/coherence/request_arbiter_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module CoherenceRequestArbiter_tb --Mdir ../reports/coherence/request_arbiter_obj \
	  common/CoherenceProtocol.sv interconnect/CoherenceRequestArbiterCore.sv \
	  interconnect/CoherenceRequestArbiter.sv ../tests/coherence/rtl/CoherenceRequestArbiter_tb.sv
	@reports/coherence/request_arbiter_obj/VCoherenceRequestArbiter_tb

coherence_snoop_arbiter:
	@mkdir -p reports/coherence/snoop_arbiter_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module MesiL1SnoopArbiter_tb --Mdir ../reports/coherence/snoop_arbiter_obj \
	  l1/MesiL1SnoopArbiter.sv ../tests/l1/rtl/MesiL1SnoopArbiter_tb.sv
	@reports/coherence/snoop_arbiter_obj/VMesiL1SnoopArbiter_tb

coherence_cluster:
	@mkdir -p reports/coherence/cluster_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --unroll-count 10000 --top-module DualL1MesiCluster_tb \
	  --Mdir ../reports/coherence/cluster_obj -f Coherence.files.f \
	  ../tests/subsystem/rtl/DualL1MesiCluster_tb.sv
	@reports/coherence/cluster_obj/VDualL1MesiCluster_tb

coherence_bus_blocks:
	@mkdir -p reports/coherence/bus_blocks_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module CacheBusBlocks_tb --Mdir ../reports/coherence/bus_blocks_obj \
	  -f Coherence.files.f ../tests/axi/rtl/CacheBusBlocks_tb.sv
	@reports/coherence/bus_blocks_obj/VCacheBusBlocks_tb

coherence_axi_lint:
	@source $(ENV_SCRIPT); cd rtl && verilator --lint-only --timing --assert -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module CoherentCacheAxiSubsystem -f Coherence.files.f

# End-to-end dual-L1 MESI simulation connected to a backpressured, burst-capable
# AXI RAM model with read/write accounting and an architectural data scoreboard.
coherence_axi_e2e:
	@mkdir -p reports/coherence/axi_e2e_obj
	@source $(ENV_SCRIPT); cd rtl && verilator --binary --timing --assert -j $(COHERENCE_JOBS) -Wall -Wno-fatal -Wno-BLKSEQ \
	  --top-module CoherentCacheAxiSubsystem_tb --Mdir ../reports/coherence/axi_e2e_obj \
	  -f Coherence.files.f ../tests/subsystem/rtl/CoherentCacheAxiSubsystem_tb.sv
	@reports/coherence/axi_e2e_obj/VCoherentCacheAxiSubsystem_tb

# Picker-exported packed-port DUT and the independent Python/Toffee dual-L1
# MESI regression (directed, reset, backpressure, seeded random, and benchmark).
coherence_python_build:
	@rm -rf .tooling/coherent_python
	@source $(ENV_SCRIPT); cd rtl && $(PICKER) export --autobuild=true \
	  --fs Coherence.files.f ../dv/rtl/CoherentCachePythonWrapper.sv \
	  --sname CoherentCachePythonWrapper --tdir ../.tooling/coherent_python \
	  --lang python --sim verilator -e -c

coherence_python_test: coherence_python_build
	@source $(ENV_SCRIPT); PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv -m "not benchmark" tests/coherence/test_subsystem_python.py && \
	 PYTHONPATH=.:./dv python3 -m dv.coverage.python_closure

coherence_benchmark_v2: coherence_python_build
	@source $(ENV_SCRIPT); PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv -m benchmark tests/coherence/test_subsystem_python.py

# One clean Picker export, then the Python functional DV and Benchmark v2.
coherence_python_verify: coherence_python_build
	@source $(ENV_SCRIPT); PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv tests/coherence/test_subsystem_python.py && \
	 PYTHONPATH=.:./dv python3 -m dv.coverage.python_closure

# Independent AXI5-channel Python agent against the line-to-AXI adapter.
coherence_axi_python_build:
	@rm -rf .tooling/line_axi_python
	@source $(ENV_SCRIPT); cd rtl && $(PICKER) export --autobuild=true \
	  --fs Coherence.files.f ../dv/rtl/LineMemoryAxi4PythonWrapper.sv \
	  --sname LineMemoryAxi4PythonWrapper --tdir ../.tooling/line_axi_python \
	  --lang python --sim verilator -e -c

coherence_axi_python_test: coherence_axi_python_build
	@source $(ENV_SCRIPT); PYTHONPATH=.tooling:.:./dv:./tests python3 -m pytest -sv tests/axi/test_axi4_adapter_python.py

coherence_python_coverage_close:
	@PYTHONPATH=.:./dv python3 -m dv.coverage.python_closure

coherence_multisnoop: coherence_build
	@reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +l2_multisnoop_only

coherence_modules: coherence_l1_array coherence_l2_array coherence_l1_controller coherence_directory coherence_directory_mshr_bank coherence_request_arbiter coherence_snoop_arbiter coherence_cluster

coherence_verify:
	$(MAKE) coherence_modules coherence_bus_blocks coherence_axi_lint coherence_axi_e2e && $(MAKE) coherence_formal && $(MAKE) coherence_regression && $(MAKE) coherence_python_verify coherence_axi_python_test

# Remove transient build and per-test trace artifacts. Keep consolidated
# coverage reports, formal proof logs, and experimental formal records.
clean:
	rm -rf Cache picker_out .pytest_cache reports/coherence/obj_dir
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
	rm -f *.dat *.fst *.vcd *.log *.tmp *.so *.a *.o
	rm -f reports/DUTCache_test_*.dat reports/DUTCache_test_*.fst
