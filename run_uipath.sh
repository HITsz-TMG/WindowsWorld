#!/bin/bash
# UIPath Agent Run Script for Linux/macOS

# Configuration
BENCHMARK_FILE="benchmark.json"
VMX_PATH="E:\\vmx\\Windows0\\Windows0.vmx"
MODEL_NAME="gpt-4o"
ACTION_SPACE="pyautogui"
OBSERVATION_TYPE="screenshot"

# UIPath Parameters
MAX_STEPS=15

# Run
python hf_run.py \
    --benchmark-file "$BENCHMARK_FILE" \
    --vmx-path "$VMX_PATH" \
    --model-name "$MODEL_NAME" \
    --action-space "$ACTION_SPACE" \
    --observation-type "$OBSERVATION_TYPE" \
    --agent-type uipath \
    --uipath-model-name "$MODEL_NAME" \
    --max-steps "$MAX_STEPS" \
    --platform windows
