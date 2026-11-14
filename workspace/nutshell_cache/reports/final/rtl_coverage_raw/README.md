# Raw Verilator Coverage Artifacts

These eight independent datasets were collected from source commit `8e268bda19f14ff6d587ca38d2813f69b868da97` (verification source fingerprint `552e2c15801193839282bda632b0ce250d49af255d15cc7e5f462be36300f006`). Each `*.dat.gz` is a compressed Verilator point database and its paired `*.info.gz` is the LCOV line mapping. The datasets use distinct elaborated tops and are never summed across tops.

`../rtl_coverage_dataset_manifest.json` records each top, source and dataset fingerprints, compile options, tests, metric counts, and compressed/uncompressed SHA-256 values. Validate an artifact with `gzip -t` and compare its decompressed SHA-256 with the manifest.
