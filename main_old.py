import json

import hf_run, show_result

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-process benchmark evaluation runner")
    
    # Basic parameters
    parser.add_argument("-c", "--count",            type = str, required = True,
                        help = "Number of parallel VMs to run")
    parser.add_argument("-m", "--model-name",       type = str, required = True,
                        help = "Model name to use")
    parser.add_argument("-a", "--action-space",     type = str, required = True,
                        help = "Action space type (pyautogui, computer_13)")
    parser.add_argument("-o", "--observation-type", type = str, required = True,
                        help = "Observation type (screenshot, a11y_tree, screenshot_a11y_tree)")
    
    # Agent type selection
    parser.add_argument("--agent-type",        type = str, default = "prompt",
                        choices = ["prompt", "s3", "coact", "uipath"],
                        help = "Type of agent to use: 'prompt' (default), 's3' (Agent-S3), 'coact' (CoAct), 'uipath' (UIPath)")
    
    # Common parameters
    parser.add_argument("--platform",          type = str, default = "windows",
                        choices = ["windows", "linux", "darwin"],
                        help = "Operating system platform")
    parser.add_argument("--max-trajectory-length", type = int, default = None,
                        help = "Maximum trajectory length")
    parser.add_argument("--client-password",   type = str, default = "",
                        help = "Client password for sudo operations")
    
    # S3 Agent specific parameters
    s3_group = parser.add_argument_group("S3 Agent", "Parameters specific to Agent-S3")
    s3_group.add_argument("--model-provider",    type = str, default = "openai",
                        help = "Model provider for S3 agent")
    s3_group.add_argument("--model-url",         type = str, default = "",
                        help = "Custom API URL for the main model")
    s3_group.add_argument("--model-api-key",     type = str, default = "",
                        help = "API key for the main model")
    s3_group.add_argument("--model-temperature", type = float, default = None,
                        help = "Temperature for model generation")
    s3_group.add_argument("--ground-provider",   type = str, default = "huggingface",
                        help = "Provider for grounding model")
    s3_group.add_argument("--ground-url",        type = str, default = "",
                        help = "URL for grounding model endpoint")
    s3_group.add_argument("--ground-model",      type = str, default = "ui-tars-1.5-7b",
                        help = "Grounding model name")
    s3_group.add_argument("--ground-api-key",    type = str, default = "",
                        help = "API key for grounding model")
    s3_group.add_argument("--grounding-width",   type = int, default = 1920,
                        help = "Width for grounding coordinate resolution")
    s3_group.add_argument("--grounding-height",  type = int, default = 1080,
                        help = "Height for grounding coordinate resolution")
    s3_group.add_argument("--enable-reflection", action = "store_true", default = True,
                        help = "Enable reflection agent for S3")
    s3_group.add_argument("--disable-reflection", action = "store_true",
                        help = "Disable reflection agent for S3")
    
    # CoAct Agent specific parameters
    coact_group = parser.add_argument_group("CoAct Agent", "Parameters specific to CoAct framework")
    coact_group.add_argument("--orchestrator-model", type = str, default = "",
                        help = "Orchestrator model name")
    coact_group.add_argument("--coding-model",   type = str, default = "o4-mini",
                        help = "Coding agent model name")
    coact_group.add_argument("--cua-model",      type = str, default = "computer-use-preview",
                        help = "CUA model name")
    coact_group.add_argument("--orchestrator-max-steps", type = int, default = 15,
                        help = "Maximum steps for orchestrator")
    coact_group.add_argument("--coding-max-steps", type = int, default = 20,
                        help = "Maximum steps for coding agent")
    coact_group.add_argument("--cua-max-steps",  type = int, default = 25,
                        help = "Maximum steps for CUA agent")
    coact_group.add_argument("--cut-off-steps",  type = int, default = 200,
                        help = "Total cut-off steps limit")
    coact_group.add_argument("--oai-config-path", type = str, default = "",
                        help = "Path to OpenAI config JSON file")
    coact_group.add_argument("--sleep-after-execution", type = float, default = 0.5,
                        help = "Sleep time after action execution")
    coact_group.add_argument("--region",         type = str, default = "",
                        help = "AWS region")
    
    # UIPath Agent specific parameters
    uipath_group = parser.add_argument_group("UIPath Agent", "Parameters specific to UIPath framework")
    uipath_group.add_argument("--uipath-model-name", type = str, default = "",
                        help = "UIPath model name")
    uipath_group.add_argument("--max-steps",     type = int, default = 15,
                        help = "Maximum steps for UIPath agent")
    
    return parser

if __name__ == "__main__":
    show_result.main()

    args = get_parser().parse_args()

    with open("benchmark.json", "r", encoding = "utf-8") as f:
        data = json.load(f)

    import random
    random.shuffle(data)

    n = int(args.count)
    total = len(data)
    chunk_size = total // n

    import shutil, os
    shutil.rmtree("benchmark", ignore_errors = True)

    for i in range(int(args.count)):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < n - 1 else total

        sub_data = data[start:end]
        os.makedirs("benchmark", exist_ok = True)

        output_file = f".\\benchmark\\benchmark_{i}.json"
        with open(output_file, "w", encoding = "utf-8") as f:
            json.dump(sub_data, f, ensure_ascii = False, indent = 4)

    # Build agent kwargs based on agent type
    agent_kwargs = {
        "platform": args.platform,
        "client_password": args.client_password,
    }
    
    if args.max_trajectory_length is not None:
        agent_kwargs["max_trajectory_length"] = args.max_trajectory_length
    
    # S3 specific kwargs
    if args.agent_type == "s3":
        agent_kwargs.update({
            "model_provider": args.model_provider,
            "model_url": args.model_url,
            "model_api_key": args.model_api_key,
            "model_temperature": args.model_temperature,
            "ground_provider": args.ground_provider,
            "ground_url": args.ground_url,
            "ground_model": args.ground_model,
            "ground_api_key": args.ground_api_key,
            "grounding_width": args.grounding_width,
            "grounding_height": args.grounding_height,
            "enable_reflection": args.enable_reflection and not args.disable_reflection,
        })
    
    # CoAct specific kwargs
    elif args.agent_type == "coact":
        agent_kwargs.update({
            "orchestrator_model": args.orchestrator_model if args.orchestrator_model else args.model_name,
            "coding_model": args.coding_model,
            "cua_model": args.cua_model,
            "orchestrator_max_steps": args.orchestrator_max_steps,
            "coding_max_steps": args.coding_max_steps,
            "cua_max_steps": args.cua_max_steps,
            "cut_off_steps": args.cut_off_steps,
            "oai_config_path": args.oai_config_path,
            "sleep_after_execution": args.sleep_after_execution,
            "region": args.region,
        })
    
    # UIPath specific kwargs
    elif args.agent_type == "uipath":
        agent_kwargs.update({
            "uipath_model_name": args.uipath_model_name if args.uipath_model_name else args.model_name,
            "max_steps": args.max_steps,
        })

    # 并行开启多个 main
    for i in range(int(args.count)):
        from multiprocessing import Process
        p = Process(target = hf_run.main, args = (
            f".\\benchmark\\benchmark_{i}.json",
            f"E:\\vmx\\Windows{i}\\Windows{i}.vmx",
            args.model_name,
            args.action_space,
            args.observation_type,
            args.agent_type),
            kwargs = agent_kwargs)
        p.start()
