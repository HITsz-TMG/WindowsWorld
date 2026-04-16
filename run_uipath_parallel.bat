@echo off
REM ============================================
REM UIPath Agent 并行运行脚本 (多VM)
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
set MODEL_NAME=qwen3-vl-plus
set ACTION_SPACE=computer_13
set OBSERVATION_TYPE=screenshot

REM ============================================
REM 模型配置 - 请填入你的模型信息
REM ============================================

REM ------------------ Planner Model (规划模型) ------------------
SET PLANNER_URL=
SET PLANNER_API_KEY=

SET PLANNER_URL=
SET PLANNER_API_KEY=
REM

REM ------------------ Grounder Model (定位模型) ------------------
REM 用于在截图上定位坐标的视觉模型 (例如 UI-TARS)
REM
REM 示例 UI-TARS 服务器地址:
SET GROUNDER_URL=http://localhost:8080/v1
SET GROUNDER_API_KEY=
REM Grounder 模型名称 (可选，用于某些支持多模型的 UI-TARS 服务)
SET GROUNDER_MODEL=UI-TARS-1.5-7B
REM 坐标分辨率设置 (需要与VM屏幕分辨率匹配)
SET GROUNDING_WIDTH=1920
SET GROUNDING_HEIGHT=1080
REM

REM ============================================
REM 运行并行评测
REM ============================================
python main.py ^
    -c %COUNT% ^
    -m %MODEL_NAME% ^
    -a %ACTION_SPACE% ^
    -o %OBSERVATION_TYPE% ^
    --agent-type uipath ^
    --vmx-template "%VMX_TEMPLATE%" ^
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
echo 并行运行完成!
echo ============================================
pause
