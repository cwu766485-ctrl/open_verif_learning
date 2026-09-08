VSRC_DIR    = ./rtl
PICKER      = picker
NAME        = Cache
NAME_L      = cache
SIM         = verilator
WAVE_FORMAT = fst
TARGET_LANG = python
GTKWAVE 	= gtkwave

# Generate DUT
TOP_ENTRY = ./rtl/Cache.v
MODULAR_RTL_DIR = ./rtl/modular
MODULAR_FILELIST = $(MODULAR_RTL_DIR)/Cache.files.f
TL = python
WAVEFORM = -w cache.fst

gen_dut:
	@rm -rf $(NAME)
	$(PICKER) export --autobuild=true $(VSRC_DIR)/$(NAME).v \
		-w $(NAME).$(WAVE_FORMAT) \
		--sname $(NAME) \
		--tdir $(NAME) \
		--lang $(TARGET_LANG) \
		--sim $(SIM) \
		-e -c

# Produce a readable, one-module-per-file view of the generated RTL and use
# Picker's file-list support to compile that view. The default DUT remains
# unchanged, so the verification baseline is always reproducible.
split_rtl:
	pwsh -NoProfile -File tools/split_cache_rtl.ps1

gen_dut_modular: split_rtl
	@rm -rf Cache_modular
	$(PICKER) export $(MODULAR_RTL_DIR)/Cache.v \
		--fs $(MODULAR_FILELIST) \
		--sname Cache \
		-w cache_modular.$(WAVE_FORMAT) \
		--tdir Cache_modular \
		--lang $(TARGET_LANG) \
		--sim $(SIM) \
		-e -c

.PHONY: wave test coverage report split_rtl gen_dut_modular

wave:
	$(GTKWAVE) -r .gtkwaverc $(NAME_L).$(WAVE_FORMAT)
# Test
test:
	PYTHONPATH=.:./src pytest -sv

coverage: test
	mkdir -p reports/rtl
	verilator_coverage --write-info reports/cache.info VCache_coverage.dat
	genhtml reports/cache.info --output-directory reports/rtl

report: test
	PYTHONPATH=.:./src pytest -sv --toffee-report --report-dir reports --report-name cache
	$(MAKE) coverage

clean:
	-rm -rf *.dat *.fst reports
