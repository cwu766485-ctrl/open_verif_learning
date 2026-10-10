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

.PHONY: wave test coverage rtl_coverage functional_coverage formal fault_injection report gen_dut doctor clean

wave:
	@source $(ENV_SCRIPT); $(GTKWAVE) -r .gtkwaverc $(NAME_L).$(WAVE_FORMAT)
# Test
test:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv

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
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m pytest -sv --toffee-report --report-dir reports --report-name cache
	$(MAKE) rtl_coverage
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.closure reports/cache.info
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.coverage.functional_closure reports/functional_coverage.json
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -c "from dv.coverage.report import render_html; render_html('reports/functional_coverage.json', 'reports/functional_coverage.html')"
	$(MAKE) fault_injection

functional_coverage: test
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -c "from dv.coverage.report import render_html; render_html('reports/functional_coverage.json', 'reports/functional_coverage.html')"

formal:
	@source $(ENV_SCRIPT); export PATH="$(abspath ../../.tooling/sby-install/bin):$$PATH"; \
	 mkdir -p reports/formal; \
	 sby -f -d reports/formal/replacement_selector formal/replacement_selector.sby && \
	 sby -f -d reports/formal/cache_way_selector formal/cache_way_selector.sby && \
	 sby -f -d reports/formal/cache_stage2_stability formal/cache_stage2_stability.sby && \
	 yosys -Q -l reports/formal/cache_stage3_response_lifecycle_sat.log -s formal/cache_stage3_response_lifecycle.ys

fault_injection:
	@source $(ENV_SCRIPT); PYTHONPATH=.:./dv:./Cache:./tests python3 -m dv.fault_injection.run

doctor:
	@source $(ENV_SCRIPT); echo "python: $$(command -v python3)"; python3 --version; \
	 echo "pytest: $$(command -v pytest || true)"; python3 -m pytest --version; \
	 python3 -c "import toffee, toffee_test; print('toffee: OK')"; \
	 echo "picker: $$(command -v picker)"; picker --version || true; \
	 echo "sby: $$(command -v sby)"; sby --version; \
	 echo "verilator: $$(command -v verilator)"; verilator --version

# Remove all generated DUT, simulator, waveform, coverage and Python cache
# artifacts.  Source RTL, tests, documentation and report source remain.
clean:
	rm -rf Cache Cache_* picker_out reports .pytest_cache
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
	rm -f *.dat *.fst *.vcd *.log *.tmp *.so *.a *.o
	rm -f VCache_coverage.dat cache.fst cache.vcd
	rm -f reports/*.info reports/**/*.info
