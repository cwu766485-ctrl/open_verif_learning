# 课程 2 的统一入口。请在 Ubuntu WSL 的本目录执行 `make help`。
SHELL := /bin/bash
ENV_SCRIPT := ../../.tooling/env.sh
PICKER_EXPORT := picker export rtl/SyncFIFO.v --sname SyncFIFO --lang python --sim verilator --tdir generated/SyncFIFO --internal internal.yaml -w SyncFIFO.fst -c

.PHONY: help export test wave-smoke wave-reset-rise wave-reset-immediate clean distclean

help:
	@echo "Picker Course 2 commands:"
	@echo "  make export               Generate the Python DUT from RTL"
	@echo "  make test                 Generate the DUT if needed, then run all tests"
	@echo "  make wave-smoke           Open smoke.fst in GTKWave"
	@echo "  make wave-reset-rise      Open reset_rise.fst in GTKWave"
	@echo "  make wave-reset-immediate Open reset_immediate.fst in GTKWave"
	@echo "  make clean                Remove waves, coverage, and Python caches"
	@echo "  make distclean            Also remove generated/ Picker build output"

export: generated/SyncFIFO/__init__.py

generated/SyncFIFO/__init__.py: rtl/SyncFIFO.v internal.yaml
	@source $(ENV_SCRIPT); $(PICKER_EXPORT)

test: generated/SyncFIFO/__init__.py test_picker_fifo.py
	@source $(ENV_SCRIPT); python test_picker_fifo.py

wave-smoke:
	@test -f smoke.fst || (echo "smoke.fst not found. Run 'make test' first."; exit 1)
	@gtkwave smoke.fst

wave-reset-rise:
	@test -f reset_rise.fst || (echo "reset_rise.fst not found. Run 'make test' first."; exit 1)
	@gtkwave reset_rise.fst

wave-reset-immediate:
	@test -f reset_immediate.fst || (echo "reset_immediate.fst not found. Run 'make test' first."; exit 1)
	@gtkwave reset_immediate.fst

clean:
	@rm -f -- *.fst VSyncFIFO_coverage.dat
	@rm -rf -- __pycache__
	@find generated -type f -name '*_coverage.dat' -delete 2>/dev/null || true
	@find generated -type d -name __pycache__ -prune -exec rm -rf -- {} + 2>/dev/null || true
	@echo "Cleaned waveforms, coverage data, and Python caches."

distclean: clean
	@rm -rf -- generated
	@echo "Cleaned generated Picker artifacts. Run 'make export' before testing again."
