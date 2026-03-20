#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRATE_DIR="$ROOT_DIR/rust/taskcaptain-fastview"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo not found; install Rust first: https://rustup.rs"
  exit 1
fi

cd "$CRATE_DIR"
cargo build --release
echo "Built: $CRATE_DIR/target/release/taskcaptain-fastview"
