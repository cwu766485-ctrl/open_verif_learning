#!/usr/bin/env bash
# Activate this project's workspace-local Python and open-source EDA tools.
# Source from workspace/nutshell_cache; generated tool installations stay out
# of version control under the repository-root .tooling/ directory.

_cache_project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_cache_repo_root="$(cd "${_cache_project_root}/../.." && pwd)"

if [[ ! -f "${_cache_repo_root}/.tooling/venv/bin/activate" ]]; then
  echo "Missing project venv: ${_cache_repo_root}/.tooling/venv/bin/activate" >&2
  return 1
fi

source "${_cache_repo_root}/.tooling/venv/bin/activate"
export PATH="${_cache_repo_root}/.tooling/picker-install/bin:${_cache_repo_root}/.tooling/sby-install/bin:${_cache_repo_root}/.tooling/verible/bin:${PATH}"
export LD_LIBRARY_PATH="${_cache_repo_root}/.tooling/picker-install/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
export PIP_CACHE_DIR="${_cache_repo_root}/.tooling/pip-cache"

unset _cache_project_root _cache_repo_root
