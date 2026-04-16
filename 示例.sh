# 使用 4 个 VM 并行运行 Agent-S3
python main.py -c 4 -m gpt-4o -a pyautogui -o screenshot \
    --agent-type s3 \
    --model-provider openai \
    --ground-url "http://localhost:8000/v1"

# 使用 2 个 VM 运行 CoAct
python main.py -c 2 -m o3 -a computer_13 -o screenshot \
    --agent-type coact \
    --orchestrator-model o3 \
    --coding-model o4-mini

# 使用 UIPath
python main.py -c 4 -m gpt-4o -a computer_13 -o screenshot \
    --agent-type uipath \
    --max-steps 20

# 自定义 VMX 路径模板
python main.py -c 2 -m gpt-4o -a pyautogui -o screenshot \
    --vmx-template "D:\\VMs\\Win{i}\\Win{i}.vmx"