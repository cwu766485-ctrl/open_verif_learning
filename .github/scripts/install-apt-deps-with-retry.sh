#!/usr/bin/env bash
set -Eeuo pipefail

# GitHub-hosted Ubuntu runners occasionally receive transient 503 responses
# from security.ubuntu.com. Keep the runner's configured Ubuntu sources intact,
# but retry both index refresh and package installation with bounded network
# retries and an outer timeout. A partial `apt-get update` is not success even
# when apt exits zero, so inspect its diagnostics as well as its exit status.

for source_file in \
  /etc/apt/sources.list \
  /etc/apt/sources.list.d/ubuntu.sources \
  /etc/apt/apt-mirrors.txt; do
  if [[ -r "$source_file" ]]; then
    echo "=== APT source configuration: $source_file ==="
    sed -n '1,200p' "$source_file"
  fi
done

log_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/nutshell-apt-install"
mkdir -p "$log_dir"

apt_options=(
  -o Acquire::Retries=2
  -o Acquire::http::Timeout=30
  -o Acquire::https::Timeout=30
  -o Dpkg::Lock::Timeout=60
)

apt_with_retry() {
  local operation="$1"
  shift
  local max_attempts=3
  local wait_seconds=10
  local attempt log_file rc

  for ((attempt = 1; attempt <= max_attempts; attempt++)); do
    log_file="$log_dir/${operation}-attempt-${attempt}.log"
    echo "=== apt ${operation}: attempt ${attempt}/${max_attempts} ==="

    if sudo timeout --signal=TERM --kill-after=20s 25m \
      apt-get "${apt_options[@]}" "$@" >"$log_file" 2>&1; then
      rc=0
    else
      rc=$?
    fi
    cat "$log_file"

    if [[ "$operation" == update ]] &&
      grep -Eiq '^(Err:|W: Failed to fetch|W: Some index files failed|E: Failed to fetch)' "$log_file"; then
      echo "APT update reported failed index downloads despite its exit code."
      rc=1
    fi

    if ((rc == 0)); then
      echo "APT ${operation} completed successfully on attempt ${attempt}."
      return 0
    fi

    if ((attempt < max_attempts)); then
      echo "APT ${operation} failed with exit ${rc}; retrying in ${wait_seconds}s."
      sleep "$wait_seconds"
      wait_seconds=$((wait_seconds * 2))
    else
      echo "APT ${operation} failed after ${max_attempts} attempts (exit ${rc})." >&2
      return "$rc"
    fi
  done
}

apt_with_retry update update
apt_with_retry install install -y \
  build-essential cmake git lcov libboost-all-dev \
  libffi-dev liblz4-dev libyaml-cpp-dev pkg-config python3-dev python3-venv \
  swig zlib1g-dev
