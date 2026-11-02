#!/usr/bin/env bash
# Thin wrapper: christina observation-only audit harness.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${ROOT}/profiles/christina/tests/run_christina_audit.sh"
