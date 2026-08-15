在 Ubuntu WSL 中这样启用：
```
cd /mnt/e/workspace/chip/open_verif
source .tooling/env.sh

picker --check
python -c 'import toffee, toffee_test; print("Toffee ready")'
```