#!/bin/bash
# Script to run benchmark with Agent-S3
# Usage: ./run_s3.sh

# Configuration
COUNT=1
MODEL_NAME="gpt-5-1"
ACTION_SPACE="pyautogui"
OBSERVATION_TYPE="screenshot"

# S3 Agent Configuration
AGENT_TYPE="s3"
MODEL_PROVIDER="openai"
MODEL_URL=
MODEL_API_KEY=
GROUND_PROVIDER="huggingface"
GROUND_URL="http://localhost:8080"
GROUND_MODEL="ui-tars-1.5-7b"
GROUNDING_WIDTH=1920
GROUNDING_HEIGHT=1080
PLATFORM="windows"

# Run the benchmark
python main.py \
    -c "$COUNT" \
    -m "$MODEL_NAME" \
    -a "$ACTION_SPACE" \
    -o "$OBSERVATION_TYPE" \
    --agent-type "$AGENT_TYPE" \
    --model-provider "$MODEL_PROVIDER" \
    --model-url "$MODEL_URL" \
    --model-api-key "$MODEL_API_KEY" \
    --ground-provider "$GROUND_PROVIDER" \
    --ground-url "$GROUND_URL" \
    --ground-model "$GROUND_MODEL" \
    --grounding-width "$GROUNDING_WIDTH" \
    --grounding-height "$GROUNDING_HEIGHT" \
    --platform "$PLATFORM" \
    --enable-reflection

echo "Benchmark completed."
