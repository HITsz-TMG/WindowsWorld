#!/bin/bash
# CoAct Agent Run Script for Linux/macOS

# Configuration
BENCHMARK_FILE="benchmark.json"
VMX_PATH="E:\\vmx\\Windows0\\Windows0.vmx"
MODEL_NAME="o3"
ACTION_SPACE="computer_13"
OBSERVATION_TYPE="screenshot"

# CoAct Parameters
ORCHESTRATOR_MODEL="o3"
CODING_MODEL="o4-mini"
CUA_MODEL="computer-use-preview"
CUT_OFF_STEPS=200

# Run
python hf_run.py \
    --benchmark-file "$BENCHMARK_FILE" \
    --vmx-path "$VMX_PATH" \
    --model-name "$MODEL_NAME" \
    --action-space "$ACTION_SPACE" \
    --observation-type "$OBSERVATION_TYPE" \
    --agent-type coact \
    --orchestrator-model "$ORCHESTRATOR_MODEL" \
    --coding-model "$CODING_MODEL" \
    --cua-model "$CUA_MODEL" \
    --cut-off-steps "$CUT_OFF_STEPS" \
    --platform windows
