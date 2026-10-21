SHELL       := /bin/bash
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
TOP_ENTRY = ./rtl/CacheTop.v
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

.PHONY: wave test test_slow mega_random benchmark coverage rtl_coverage functional_coverage formal fault_injection report gen_dut doctor coherence_build coherence_smoke coherence_random coherence_formal clean

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
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv tests/test_random.py::test_mega_randomized_cache_mmio_traffic

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
	@PATH="$(abspath .tooling/sby-install/bin):$$PATH" sby -f -d reports/formal/coherence_request_arbiter formal/coherence_request_arbiter.sby

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
	@cd rtl && verilator --binary --timing --assert -j 8 -Wall -Wno-fatal -Wno-BLKSEQ \
	  --unroll-count 10000 --top-module CoherentCacheSubsystem_tb \
	  --Mdir ../reports/coherence/obj_dir -f Coherence.files.f \
	  coherence/tb/CoherentCacheSubsystem_tb.sv

coherence_smoke: coherence_build
	@reports/coherence/obj_dir/VCoherentCacheSubsystem_tb

coherence_random: coherence_build
	@for seed in 00000001 00001234 5EEDC0DE DEADBEEF 2468ACE0; do \
	  echo "=== coherence regression seed=$$seed ==="; \
	  reports/coherence/obj_dir/VCoherentCacheSubsystem_tb +seed=$$seed || exit $$?; \
	done

# Remove transient build and per-test trace artifacts. Keep consolidated
# coverage reports, formal proof logs, and experimental formal records.
clean:
	rm -rf Cache picker_out .pytest_cache reports/coherence/obj_dir
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
	rm -f *.dat *.fst *.vcd *.log *.tmp *.so *.a *.o
	rm -f reports/DUTCache_test_*.dat reports/DUTCache_test_*.fst
