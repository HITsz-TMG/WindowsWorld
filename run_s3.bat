@echo off
REM Script to run benchmark with Agent-S3
REM Usage: run_s3.bat

REM Configuration
set COUNT=5
@REM set MODEL_NAME=gpt-4o
@REM set MODEL_NAME=qwen3-vl-plus
set MODEL_NAME=gemini-3-flash-preview
@REM set MODEL_NAME=claude-sonnet-4-5-20250929
set ACTION_SPACE=pyautogui
set OBSERVATION_TYPE=screenshot

REM S3 Agent Configuration
set AGENT_TYPE=s3
REM MODEL_PROVIDER options:
REM   - "openai": Use OpenAI compatible API (transit API needs --disable-thinking)
REM   - "anthropic": Use Anthropic native API (supports thinking, needs official key)
set MODEL_PROVIDER=openai
REM Disable thinking mode for Claude models when using transit/proxy APIs
REM SET DISABLE_THINKING=1
set GROUND_PROVIDER=huggingface
set GROUND_URL=http://localhost:8080/v1
set GROUND_MODEL=UI-TARS-1.5-7B
set GROUNDING_WIDTH=1920
set GROUNDING_HEIGHT=1080
set PLATFORM=windows
REM Main model API settings (fill these for your provider)
set MODEL_URL=

@REM Claude Key
@REM Qwen Key
@REM Gemini Key
set MODEL_API_KEY=


set MODEL_TEMPERATURE=0.0
REM Run the benchmark with unbuffered output for real-time logging
python -u main.py ^
    -c %COUNT% ^
    -m %MODEL_NAME% ^
    -a %ACTION_SPACE% ^
    -o %OBSERVATION_TYPE% ^
    --agent-type %AGENT_TYPE% ^
    --model-provider %MODEL_PROVIDER% ^
    --model-url "%MODEL_URL%" ^
    --model-api-key "%MODEL_API_KEY%" ^
    --model-temperature %MODEL_TEMPERATURE% ^
    --ground-provider %GROUND_PROVIDER% ^
    --ground-url %GROUND_URL% ^
    --ground-model %GROUND_MODEL% ^
    --grounding-width %GROUNDING_WIDTH% ^
    --grounding-height %GROUNDING_HEIGHT% ^
    --platform %PLATFORM% ^
    --enable-reflection ^
    --disable-thinking
REM Uncomment below line if using Claude model with transit API
REM    --disable-thinking

echo Benchmark completed.
pause
