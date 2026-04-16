@echo off
REM ============================================
REM CoAct Agent 并行运行脚本 (多VM)
REM ============================================
REM
REM 使用 main.py 进行并行评测，支持多个 VM 同时运行
REM
REM ============================================
REM 配置说明
REM ============================================

REM 并行 VM 数量
set COUNT=2

REM Benchmark 配置
set BENCHMARK_FILE=benchmark.json
set VMX_TEMPLATE=C:\Users\250010095\Documents\Virtual Machines\Windows{i}\Windows{i}.vmx
set MODEL_NAME=gemini-3-flash-preview
set ACTION_SPACE=pyautogui
set OBSERVATION_TYPE=screenshot

REM ============================================
REM 模型配置 - 请填入你的模型信息
REM ============================================

REM ------------------ Orchestrator & Coding Agent API 配置 ------------------
REM 用于 Orchestrator 和 Coding Agent (使用 Gemini)
SET API_BASE=
SET API_KEY=

REM ------------------ GUI Agent (CUA) API 配置 ------------------
REM GUI Agent (CUA) 需要使用 OpenAI Computer Use API
REM 请填入你的 OpenAI API 配置
SET CUA_API_BASE=
SET CUA_API_KEY=
REM 如果使用中转 API，替换上面的配置，例如:
REM SET CUA_API_BASE=http://your-transit-api/v1
REM SET CUA_API_KEY=sk-your-transit-api-key


REM ------------------ CoAct 模型配置 ------------------
SET ORCHESTRATOR_MODEL=gemini-3-flash-preview
SET CODING_MODEL=gemini-3-flash-preview
REM CUA_MODEL 仅在使用 OpenAI Computer Use API 时有效
SET CUA_MODEL=computer-use-preview
SET CUT_OFF_STEPS=200

REM ------------------ 兼容性模式配置 ------------------
REM 兼容性模式用于不支持 tools/thinking 等高级功能的中转/代理 API
REM 只有在使用此类 API 时才需要启用 (设置为 1)
REM 官方 API (Qwen、OpenAI 等) 应保持禁用状态 (默认为 0)
SET COMPATIBILITY_MODE=1

REM ============================================
REM 运行并行评测
REM ============================================
python main.py ^
    -c %COUNT% ^
    -m %MODEL_NAME% ^
    -a %ACTION_SPACE% ^
    -o %OBSERVATION_TYPE% ^
    --agent-type coact ^
    --vmx-template "%VMX_TEMPLATE%" ^
    --orchestrator-model %ORCHESTRATOR_MODEL% ^
    --coding-model %CODING_MODEL% ^
    --cua-model %CUA_MODEL% ^
    --cut-off-steps %CUT_OFF_STEPS% ^
    --api-base "%API_BASE%" ^
    --api-key "%API_KEY%" ^
    --cua-api-base "%CUA_API_BASE%" ^
    --cua-api-key "%CUA_API_KEY%" ^
    --platform windows ^
    --compatibility-mode

echo.
echo ============================================
echo 并行运行完成!
echo ============================================
pause
