@echo off
REM ============================================
REM CoAct Agent Run Script for Windows
REM ============================================
REM
REM CoAct 使用 3 个模型:
REM   1. Orchestrator Model (规划模型/LLM) - 协调整体任务流程
REM   2. Coding Model (代码模型) - 执行程序化操作
REM   3. CUA Model (GUI 操作模型) - 执行界面操作
REM
REM ============================================
REM 配置说明
REM ============================================

REM Benchmark 配置
set BENCHMARK_FILE=benchmark.json
set VMX_PATH=E:\vmx\Windows0\Windows0.vmx
set MODEL_NAME=o3
set ACTION_SPACE=computer_13
set OBSERVATION_TYPE=screenshot

REM ============================================
REM 模型配置 - 请填入你的模型信息
REM ============================================

REM ------------------ API 配置 ------------------
REM API 基础地址和密钥 (用于所有 CoAct 模型)
SET API_BASE=
SET API_KEY=
REM

REM ------------------ CoAct 模型配置 ------------------
SET ORCHESTRATOR_MODEL=o3
SET CODING_MODEL=o4-mini
SET CUA_MODEL=computer-use-preview
SET CUT_OFF_STEPS=200

REM ------------------ 兼容性模式配置 ------------------
REM 兼容性模式用于不支持 tools/thinking 等高级功能的中转/代理 API
REM 只有在使用此类 API 时才需要启用 (设置为 1)
REM 官方 API (Qwen、OpenAI 等) 应保持禁用状态 (默认为 0)
REM SET COMPATIBILITY_MODE=0

REM ============================================
REM 运行命令
REM ============================================
python hf_run.py ^
    --benchmark-file %BENCHMARK_FILE% ^
    --vmx-path "%VMX_PATH%" ^
    --model-name %MODEL_NAME% ^
    --action-space %ACTION_SPACE% ^
    --observation-type %OBSERVATION_TYPE% ^
    --agent-type coact ^
    --orchestrator-model %ORCHESTRATOR_MODEL% ^
    --coding-model %CODING_MODEL% ^
    --cua-model %CUA_MODEL% ^
    --cut-off-steps %CUT_OFF_STEPS% ^
    --api-base "%API_BASE%" ^
    --api-key "%API_KEY%" ^
    --platform windows
REM 如果需要启用兼容性模式，请取消下面一行的注释，并取消上面 SET COMPATIBILITY_MODE=1 的注释
REM    --compatibility-mode

echo.
echo ============================================
echo 运行完成!
echo ============================================
pause
