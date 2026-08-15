# 课程 3：复用课程 2 的 Picker DUT，运行 Toffee/pytest 验证代码。
SHELL := /bin/bash
ENV_SCRIPT := ../../.tooling/env.sh
COURSE2_DIR := ../course2_picker_fifo

.PHONY: help prepare-dut test report clean

help:
	@echo "Toffee Course 3 commands:"
	@echo "  make prepare-dut  Generate the Picker DUT required by this lab"
	@echo "  make test         Run the completed Task 2 Toffee tests"
	@echo "  make report       Run tests and generate Toffee coverage/report artifacts"
	@echo "  make clean        Remove pytest/report artifacts only"

prepare-dut:
	@$(MAKE) -C $(COURSE2_DIR) export

test: prepare-dut
	@source $(ENV_SCRIPT); pytest -sv

report: prepare-dut
	@source $(ENV_SCRIPT); pytest -sv --toffee-report --report-dir reports --report-name course3

clean:
	@rm -f -- *.fst VSyncFIFO_coverage.dat
	@rm -rf -- .pytest_cache reports tests/__pycache__ bundle/__pycache__ agent/__pycache__ coverage/__pycache__ ref/__pycache__ env/__pycache__
	@echo "Cleaned course 3 waveforms, coverage data, pytest caches, and reports."
