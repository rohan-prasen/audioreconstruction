#!/bin/sh
# Run from the repository root.
set -eu
export_requirements() {
    uv export --locked --no-dev --no-hashes --no-emit-workspace --no-header "$@" > /dev/null
}
export_requirements --package audioreconstruction -o requirements.txt
export_requirements --package audioreconstruction-native --group build -o onnx/requirements.txt
export_requirements --package audioreconstruction-server --group deploy -o server/requirements.txt
