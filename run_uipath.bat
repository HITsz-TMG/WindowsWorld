@echo off
REM ============================================
REM UIPath Agent Run Script for Windows
REM ============================================
REM
REM UIPath 需要 2 个模型:
REM   1. Planner Model (规划模型/LLM) - 生成动作计划
REM   2. Grounder Model (定位模型/Vision) - 在截图上定位坐标
REM
REM ============================================
REM 配置说明
REM ============================================

REM Benchmark 配置
set BENCHMARK_FILE=benchmark.json
set VMX_PATH=E:\vmx\Windows0\Windows0.vmx
set MODEL_NAME=gpt-4o
set ACTION_SPACE=computer_13
set OBSERVATION_TYPE=screenshot

REM ============================================
REM 模型配置 - 请填入你的模型信息
REM ============================================

REM ------------------ Planner Model (规划模型) ------------------
REM 用于生成动作计划的多模态 LLM
REM 示例: OpenAI-compatible API, Azure OpenAI, 或任何支持视觉的 LLM
REM
SET PLANNER_URL=https://api.openai.com/v1/chat/completions
SET PLANNER_API_KEY=sk-your-planner-api-key-here
REM

REM ------------------ Grounder Model (定位模型) ------------------
REM 用于在截图上定位坐标的视觉模型 (例如 UI-TARS)
REM
REM 示例 UI-TARS 服务器地址:
SET GROUNDER_URL=http://localhost:8080/v1/ground
SET GROUNDER_API_KEY=
REM Grounder 模型名称 (可选，用于某些支持多模型的 UI-TARS 服务)
SET GROUNDER_MODEL=UI-TARS-1.5-7B
REM 坐标分辨率设置 (需要与VM屏幕分辨率匹配)
SET GROUNDING_WIDTH=1920
SET GROUNDING_HEIGHT=1080
REM

REM UIPath 参数
set MAX_STEPS=15

REM ============================================
REM 运行命令
REM ============================================
python hf_run.py ^
    --benchmark-file %BENCHMARK_FILE% ^
    --vmx-path "%VMX_PATH%" ^
    --model-name %MODEL_NAME% ^
    --action-space %ACTION_SPACE% ^
    --observation-type %OBSERVATION_TYPE% ^
    --agent-type uipath ^
    --uipath-model-name %MODEL_NAME% ^
    --max-steps %MAX_STEPS% ^
    --planner-url "%PLANNER_URL%" ^
    --planner-api-key "%PLANNER_API_KEY%" ^
    --grounder-url "%GROUNDER_URL%" ^
    --grounder-api-key "%GROUNDER_API_KEY%" ^
    --grounder-model "%GROUNDER_MODEL%" ^
    --grounding-width %GROUNDING_WIDTH% ^
    --grounding-height %GROUNDING_HEIGHT% ^
    --platform windows

echo.
echo ============================================
echo 运行完成!
echo ============================================
pause
