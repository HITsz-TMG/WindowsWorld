import base64, os, json, time, sys, logging, datetime, json_repair
from pprint import pprint

from mm_agents.agent import PromptAgent
from desktop_env.desktop_env import DesktopEnv

logger = logging.getLogger(__name__)
logging.basicConfig(stream = sys.stdout)

class TaskLogger:
    """Context manager for task-level logging to file."""
    
    def __init__(self, task_dir: str, task_id: str):
        self.task_dir = task_dir
        self.task_id = task_id
        # Primary log in task directory
        self.log_file = os.path.join(task_dir, "output.log")
        # Also create a log file named by task_id in logs directory for easy access
        self.logs_dir = os.path.join("logs", "tasks")
        os.makedirs(self.logs_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.task_log_file = os.path.join(self.logs_dir, f"{task_id}_{timestamp}.log")
        
        self.original_stdout = None
        self.original_stderr = None
        self.log_handles = []
        
    def __enter__(self):
        """Start logging to file while keeping console output."""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Open both log files
        log_handle1 = open(self.log_file, "w", encoding="utf-8", buffering=1)
        log_handle2 = open(self.task_log_file, "w", encoding="utf-8", buffering=1)
        self.log_handles = [log_handle1, log_handle2]
        
        # Create a tee-like object that writes to console and both log files
        sys.stdout = TeeOutput(self.original_stdout, log_handle1, log_handle2)
        sys.stderr = TeeOutput(self.original_stderr, log_handle1, log_handle2)
        
        print(f"\n{'='*60}")
        print(f"Task: {self.task_id}")
        print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Log file: {self.log_file}")
        print(f"Task log: {self.task_log_file}")
        print(f"{'='*60}\n")
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original stdout/stderr and close log file."""
        print(f"\n{'='*60}")
        print(f"Task: {self.task_id} - Finished")
        print(f"Ended: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if exc_type:
            print(f"Error: {exc_val}")
        print(f"{'='*60}\n")
        
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        for handle in self.log_handles:
            if handle:
                handle.close()
        return False  # Don't suppress exceptions


class TeeOutput:
    """A file-like object that writes to multiple outputs (tee)."""
    
    def __init__(self, *outputs):
        self.outputs = outputs
        
    def write(self, text):
        for output in self.outputs:
            if output:
                try:
                    output.write(text)
                    output.flush()
                except:
                    pass
                    
    def flush(self):
        for output in self.outputs:
            if output:
                try:
                    output.flush()
                except:
                    pass


def create_agent(agent_type: str, args: dict, env: DesktopEnv = None):
    """
    Factory function to create the appropriate agent based on agent_type.
    
    Args:
        agent_type: Type of agent to create ('prompt', 's3', 'coact', 'uipath')
        args: Dictionary of agent configuration arguments
        env: DesktopEnv instance (required for S3, CoAct, UIPath agents)
    
    Returns:
        Agent instance
    """
    if agent_type == "s3":
        from mm_agents.s3_agent import S3PromptAgentWrapper
        agent = S3PromptAgentWrapper(
            model=args.get("model", "gpt-4o"),
            max_tokens=args.get("max_tokens", 10000),
            top_p=args.get("top_p", 0.9),
            temperature=args.get("temperature", 0.5),
            action_space=args.get("action_space", "pyautogui"),
            observation_type=args.get("observation_type", "screenshot"),
            max_trajectory_length=args.get("max_trajectory_length", 8),
            a11y_tree_max_tokens=args.get("a11y_tree_max_tokens", 50000),
            # S3 specific parameters
            model_provider=args.get("model_provider", "openai"),
            model_url=args.get("model_url", ""),
            model_api_key=args.get("model_api_key", ""),
            model_temperature=args.get("model_temperature", None),
            ground_provider=args.get("ground_provider", "huggingface"),
            ground_url=args.get("ground_url", ""),
            ground_model=args.get("ground_model", "ui-tars-1.5-7b"),
            ground_api_key=args.get("ground_api_key", ""),
            grounding_width=args.get("grounding_width", 1920),
            grounding_height=args.get("grounding_height", 1080),
            platform=args.get("platform", "windows"),
            screen_width=args.get("screen_width", 1920),
            screen_height=args.get("screen_height", 1080),
            enable_reflection=args.get("enable_reflection", True),
        )
        if env is not None:
            agent.initialize_with_env(env)
        return agent
    
    elif agent_type == "coact":
        from mm_agents.coact_agent import CoActPromptAgentWrapper
        agent = CoActPromptAgentWrapper(
            model=args.get("model", "o3"),
            max_tokens=args.get("max_tokens", 10000),
            top_p=args.get("top_p", 0.9),
            temperature=args.get("temperature", 0.5),
            action_space=args.get("action_space", "pyautogui"),
            observation_type=args.get("observation_type", "screenshot"),
            max_trajectory_length=args.get("max_trajectory_length", 8),
            a11y_tree_max_tokens=args.get("a11y_tree_max_tokens", 50000),
            # CoAct specific parameters
            orchestrator_model=args.get("orchestrator_model", args.get("model", "o3")),
            coding_model=args.get("coding_model", "o4-mini"),
            cua_model=args.get("cua_model", "computer-use-preview"),
            orchestrator_max_steps=args.get("orchestrator_max_steps", 15),
            coding_max_steps=args.get("coding_max_steps", 20),
            cua_max_steps=args.get("cua_max_steps", 25),
            cut_off_steps=args.get("cut_off_steps", 200),
            oai_config_path=args.get("oai_config_path", ""),
            # API configuration
            api_base=args.get("api_base", ""),
            api_key=args.get("api_key", ""),
            compatibility_mode=args.get("compatibility_mode", False),
            # Environment
            platform=args.get("platform", "windows"),
            screen_width=args.get("screen_width", 1920),
            screen_height=args.get("screen_height", 1080),
            sleep_after_execution=args.get("sleep_after_execution", 0.5),
            provider_name=args.get("provider_name", "vmware"),
            region=args.get("region", ""),
            client_password=args.get("client_password", ""),
        )
        if env is not None:
            agent.initialize_with_env(env)
        return agent
    
    elif agent_type == "uipath":
        from mm_agents.uipath_adapter import UIPathPromptAgentWrapper
        agent = UIPathPromptAgentWrapper(
            model=args.get("model", "gpt-5-mini-2025-08-07"),
            max_tokens=args.get("max_tokens", 10000),
            top_p=args.get("top_p", 0.9),
            temperature=args.get("temperature", 0.5),
            action_space=args.get("action_space", "computer_13"),
            observation_type=args.get("observation_type", "screenshot"),
            max_trajectory_length=args.get("max_trajectory_length", 8),
            a11y_tree_max_tokens=args.get("a11y_tree_max_tokens", 50000),
            # UIPath specific parameters
            uipath_model_name=args.get("uipath_model_name", args.get("model", "gpt-5-2025-08-07")),
            platform=args.get("platform", "windows"),
            client_password=args.get("client_password", ""),
            max_steps=args.get("max_steps", 15),
            # UIPath model configuration
            planner_url=args.get("planner_url", ""),
            planner_api_key=args.get("planner_api_key", ""),
            grounder_url=args.get("grounder_url", ""),
            grounder_api_key=args.get("grounder_api_key", ""),
            grounder_model=args.get("grounder_model", ""),
            grounding_width=args.get("grounding_width", 1920),
            grounding_height=args.get("grounding_height", 1080),
        )
        if env is not None:
            agent.initialize_with_env(env)
        return agent
    
    else:
        # Default to PromptAgent
        return PromptAgent(
            model=args.get("model", "gpt-4o"),
            max_tokens=args.get("max_tokens", 10000),
            top_p=args.get("top_p", 0.9),
            temperature=args.get("temperature", 0.5),
            action_space=args.get("action_space", "pyautogui"),
            observation_type=args.get("observation_type", "screenshot"),
            max_trajectory_length=args.get("max_trajectory_length", 3),
            a11y_tree_max_tokens=args.get("a11y_tree_max_tokens", 50000),
        )


def run_coact_task(task_dir: str, agent, env: DesktopEnv, task: dict) -> float:
    """
    Run a task using CoAct framework (full task execution mode).
    
    CoAct handles the complete task internally with its orchestrator.
    
    Args:
        task_dir: Directory to save task results
        agent: CoAct agent instance
        env: Desktop environment instance
        task: Task configuration dictionary
        
    Returns:
        Score for the task
    """
    pprint(f"Running CoAct task: {task['task_id']}.")
    
    # Set history directory for CoAct
    if hasattr(agent, 'set_history_dir'):
        agent.set_history_dir(task_dir)
    
    try:
        # Run the full task
        result_info = agent.run_task(task["instruction"], task_config=task)
        
        # Get actions from environment history if available
        all_actions = getattr(env, 'action_history', [])
        
        # Collect screenshots from task_dir
        all_screenshots = []
        import glob
        screenshot_files = sorted(glob.glob(os.path.join(task_dir, "*.png")))
        for ss_file in screenshot_files:
            with open(ss_file, "rb") as f:
                all_screenshots.append(f.read())
        
        # Save CoAct result info
        with open(os.path.join(task_dir, "coact_result.json"), "w") as f:
            json.dump(result_info if isinstance(result_info, dict) else {"result": str(result_info)}, f, indent=2)
        
    except Exception as e:
        pprint(f"CoAct task failed: {e}")
        import traceback
        traceback.print_exc()
        all_actions = ["FAIL"]
        all_screenshots = []
        
        with open(os.path.join(task_dir, "error.txt"), "w") as f:
            f.write(str(e))
            f.write("\n")
            f.write(traceback.format_exc())
    
    time.sleep(5)
    
    # Evaluate
    result_str = evaluate(task, all_actions, all_screenshots)
    result = json_repair.loads(result_str)
    
    completed_intermediate = 0
    intermediate_results = result.get("intermediate_results", {})
    for v in intermediate_results.values():
        if isinstance(v, dict) and v.get("result"):
            completed_intermediate += 1

    total_intermediate = len(intermediate_results)
    score = completed_intermediate / total_intermediate if total_intermediate > 0 else 0

    final_result_obj = result.get("final_result", {})
    final = 1 if isinstance(final_result_obj, dict) and final_result_obj.get("result") else 0

    pprint(f"Task: {task['task_id']}, Intermediate Score: {score}, Final Result: {final}")

    with open(os.path.join(task_dir, "result.json"), "w", encoding="utf-8") as f:
        f.write(f"Task Instruction: {task.get('instruction_cn', task['instruction'])}\nIntermediate Score: {score}, Final Result: {final}\n")
        json.dump(result, f, ensure_ascii=False, indent=4)

    return score


def run_one_task(task_dir: str, agent, env: DesktopEnv, task: dict, agent_type: str = "prompt") -> float:
    """
    Run a single benchmark task.
    
    Args:
        task_dir: Directory to save task results
        agent: Agent instance (PromptAgent, S3, CoAct, or UIPath)
        env: Desktop environment instance
        task: Task configuration dictionary
        agent_type: Type of agent being used
        
    Returns:
        Score for the task
    """
    pprint(f"Running task: {task['task_id']}.")
    env.reset()
    agent.reset(logger = logger, vm_ip = env.vm_ip)
    
    # Handle CoAct specially - it runs the full task internally
    if agent_type == "coact" and hasattr(agent, 'run_task'):
        return run_coact_task(task_dir, agent, env, task)
    
    # Standard step-by-step execution for other agents
    obs = env.get_obs()
    done = False
    step_index = 0

    all_actions = []
    all_screenshots: list[bytes] = []

    if task["task_category"] == "L1":
        max_steps = 15
    elif task["task_category"] == "L2":
        max_steps = 25
    elif task["task_category"] == "L3":
        max_steps = 40
    else:
        max_steps = 20
    
    # Set max_steps for UIPath agent if applicable
    if agent_type == "uipath" and hasattr(agent, 'set_max_steps'):
        agent.set_max_steps(max_steps)

    while not done and step_index < max_steps:
        actions: list[str]
        predict_time = datetime.datetime.now()
        response, actions = agent.predict(task["instruction"], obs)
        predict_time = datetime.datetime.now() - predict_time
        pprint(f"Step {step_index} - Response: {response}")
        
        # Handle different action formats
        if isinstance(actions, str):
            actions = [actions]
        
        all_actions.extend(actions)
        for action in actions:
            action_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pprint(f"Step {step_index} - Action: {action} at {action_time}")
            try:
                obs, reward, done, _, info = env.step(action, 0.5)

                pprint(f"Step {step_index} - Reward: {reward}, Done: {done}, Info: {info}")

                with open(os.path.join(task_dir, f"step{step_index}_{action_time}.png"),
                        "wb") as f:
                    ss = obs["screenshot"]
                    all_screenshots.append(ss)
                    f.write(ss)

                with open(os.path.join(task_dir, "traj.jsonl"), "a") as f:
                    f.write(json.dumps(
                        {
                            "step_num": step_index + 1,
                            "predict_time": str(predict_time.seconds),
                            "action": str(action),
                            "response": str(response),
                            "reward": reward,
                            "done": done,
                            "info": info,
                            "screenshot_file": f"step{step_index}_{action_time}.png"
                        }))
                    f.write('\n')

            except Exception as e:
                pprint(f"Step {step_index} - Action failed: {e}")
                with open(os.path.join(task_dir, "traj.jsonl"), "a") as f:
                    f.write(json.dumps({
                        "step_num": step_index + 1,
                        "predict_time": str(predict_time.seconds),
                        "action": str(action),
                        "response": str(response),
                        "info": "failed",
                        "screenshot_file": f"step{step_index}_{action_time}.png"
                    }))
                    f.write('\n')

            if done:
                pprint(f"Step {step_index} - DONE!")
                break
        step_index += 1
    time.sleep(5)

    result_str = evaluate(task, all_actions, all_screenshots)
    result = json_repair.loads(result_str)
    # result = json.loads(result_str)

    completed_intermediate = 0
    intermediate_results = result.get("intermediate_results", {})
    for v in intermediate_results.values():
        if isinstance(v, dict) and v.get("result"):
            completed_intermediate += 1

    total_intermediate = len(intermediate_results)
    score = completed_intermediate / total_intermediate if total_intermediate > 0 else 0

    final_result_obj = result.get("final_result", {})
    final = 1 if isinstance(final_result_obj, dict) and final_result_obj.get("result") else 0

    pprint(f"Task: {task['task_id']}, Intermediate Score: {score}, Final Result: {final}")

    with open(os.path.join(task_dir, "result.json"), "w", encoding="utf-8") as f:
        f.write(f"Task Instruction: {task['instruction_cn']}\nIntermediate Score: {score}, Final Result: {final}\n")
        json.dump(result, f, ensure_ascii=False, indent=4)

    return score

def evaluate(task: dict | None = None,
             actions: list[str] | None = None,
             screenshots: list[bytes] | None = None,
             user_content = None) -> str:
    if task["task_category"] == "L4":
        # Check if actions list is empty or last action indicates FAIL
        # Support both string "FAIL" and computer_13 dict format {"action_type": "FAIL"}
        is_fail = False
        if not actions:
            is_fail = True
        else:
            last_action = actions[-1]
            if isinstance(last_action, str):
                is_fail = "fail" in last_action.lower()
            elif isinstance(last_action, dict):
                is_fail = last_action.get("action_type", "").lower() == "fail"

        if is_fail:
            return """
{
    "intermediate_results": { },
    "final_result": {
        "result": true,
        "reason": ""
    }
}
"""
        else:
            return """
{
    "intermediate_results": { },
    "final_result": {
        "result": false,
        "reason": ""
    }
}
"""

    system_prompt = """
你是一个任务执行评估器。

你的职责是：根据给定的任务指令、模型执行过程、子任务定义以及截图证据，
判断：
1. 每一个 intermediate_check 是否已经达成
2. 最终的 success_state 是否已经达成

请遵循以下评估规则：

【评估规则】
1. success_state 与 intermediate_checks 描述的是最终或中间状态，而不是动作本身
2. actions 仅作为参考执行过程，不能单独作为成功依据
3. 如果截图中没有足够信息支持已达成，则判定为未达成
4. 如果 intermediate_checks 未全部达成，但 success_state 明确已达成，允许 success_state 判定为 true
5. 如果没有打开要求的软件而打开了相同类型的软件（比如Edge/Chrome，Outlook/Thunderbird等），判定为正确行动

【输出要求】
仅以 JSON 格式输出，示例如下：
{
    "intermediate_results": {
        "中间状态": {
            "result": true/false,
            "reason": "简要说明判断依据"
        }
        ...
    }
    "final_result": {
        "result": true/false,
        "reason": "简要说明判断依据"
    }
}
    """

    if user_content is None:
        user_prompt_text = "【输入信息】\n"
        user_prompt_text += "instruction:\n" + task['instruction'] + "\n\n"
        user_prompt_text += "actions（按时间顺序）:\n" + str(actions) + "\n\n"
        user_prompt_text += "intermediate_checks（需要逐项判断）:\n" + str(task['evaluation_metrics']['intermediate_checks']) + "\n\n"
        user_prompt_text += "success_state（最终任务目标）:\n" + task['evaluation_metrics']['success_criterion'] + "\n\n"
        user_prompt_text += "screenshots（时间顺序）:"
        user_content = [ { "type": "text", "text": user_prompt_text } ]
        for ss in screenshots:
            user_content.append({
                "type": "image_url",
                "image_url": { "url": f"data:image/png;base64,{base64.b64encode(ss).decode('utf-8')}" } })

    from openai import OpenAI
    client = OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key=os.environ.get("QWEN_API_KEY"))

    # noinspection PyTypeChecker
    response = client.chat.completions.create(
        model="qwen3-vl-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        max_tokens=4096,
        top_p=0.9,
        temperature=0.3
    )

    return response.choices[0].message.content

def main(benchmark_path: str, vmx_path: str, model_name: str, action_space: str, observation_type: str,
         agent_type: str = "prompt", **agent_kwargs):
    """
    Main function to run benchmark evaluation.
    
    Args:
        benchmark_path: Path to benchmark JSON file
        vmx_path: Path to VMware VMX file
        model_name: Model name to use
        action_space: Action space type
        observation_type: Observation type
        agent_type: Type of agent to use ('prompt', 's3', 'coact', 'uipath')
        **agent_kwargs: Additional arguments for specific agent types
    """
    os.makedirs(".\\hf_result", exist_ok = True)

    complete_dir = []
    for result_dir in os.listdir(".\\hf_result"):
        complete_dir.append(result_dir)

    all_tasks: list[dict] = []
    with open(benchmark_path, "r", encoding = "utf-8") as f:
        benchmark = json.load(f)
        for task in benchmark:

            if task['task_id'] not in complete_dir:
                all_tasks.append(task)
                pprint(f"Loaded benchmark task: {task['task_id']}")

    pprint(f"Loaded total {len(all_tasks)} tasks.")

    # Create environment first
    env = DesktopEnv(
        provider_name         = "vmware",
        path_to_vm            = vmx_path,
        action_space          = action_space,
        screen_size           = (1920, 1080),
        headless              = False,
        os_type               = "Windows",
        require_a11y_tree     = True)

    # Prepare agent configuration
    agent_args = {
        "model": model_name,
        "max_tokens": 10000,
        "top_p": 0.9,
        "temperature": 0.5,
        "action_space": action_space,
        "observation_type": observation_type,
        "max_trajectory_length": agent_kwargs.get("max_trajectory_length", 8 if agent_type in ["s3", "coact", "uipath"] else 3),
        "a11y_tree_max_tokens": 50000,
        "screen_width": 1920,
        "screen_height": 1080,
    }
    
    # Add agent-specific parameters
    if agent_type == "s3":
        agent_args.update({
            "model_provider": agent_kwargs.get("model_provider", "openai"),
            "model_url": agent_kwargs.get("model_url", ""),
            "model_api_key": agent_kwargs.get("model_api_key", ""),
            "model_temperature": agent_kwargs.get("model_temperature", None),
            "ground_provider": agent_kwargs.get("ground_provider", "huggingface"),
            "ground_url": agent_kwargs.get("ground_url", ""),
            "ground_model": agent_kwargs.get("ground_model", "ui-tars-1.5-7b"),
            "ground_api_key": agent_kwargs.get("ground_api_key", ""),
            "grounding_width": agent_kwargs.get("grounding_width", 1920),
            "grounding_height": agent_kwargs.get("grounding_height", 1080),
            "platform": agent_kwargs.get("platform", "windows"),
            "enable_reflection": agent_kwargs.get("enable_reflection", True),
        })
    elif agent_type == "coact":
        agent_args.update({
            "orchestrator_model": agent_kwargs.get("orchestrator_model", model_name),
            "coding_model": agent_kwargs.get("coding_model", "o4-mini"),
            "cua_model": agent_kwargs.get("cua_model", "computer-use-preview"),
            "orchestrator_max_steps": agent_kwargs.get("orchestrator_max_steps", 15),
            "coding_max_steps": agent_kwargs.get("coding_max_steps", 20),
            "cua_max_steps": agent_kwargs.get("cua_max_steps", 25),
            "cut_off_steps": agent_kwargs.get("cut_off_steps", 200),
            "oai_config_path": agent_kwargs.get("oai_config_path", ""),
            "api_base": agent_kwargs.get("api_base", ""),
            "api_key": agent_kwargs.get("api_key", ""),
            "platform": agent_kwargs.get("platform", "windows"),
            "sleep_after_execution": agent_kwargs.get("sleep_after_execution", 0.5),
            "provider_name": "vmware",
            "region": agent_kwargs.get("region", ""),
            "client_password": agent_kwargs.get("client_password", ""),
        })
    elif agent_type == "uipath":
        agent_args.update({
            "uipath_model_name": agent_kwargs.get("uipath_model_name", model_name),
            "platform": agent_kwargs.get("platform", "windows"),
            "client_password": agent_kwargs.get("client_password", ""),
            "max_steps": agent_kwargs.get("max_steps", 15),
            "planner_url": agent_kwargs.get("planner_url", ""),
            "planner_api_key": agent_kwargs.get("planner_api_key", ""),
            "grounder_url": agent_kwargs.get("grounder_url", ""),
            "grounder_api_key": agent_kwargs.get("grounder_api_key", ""),
            "grounder_model": agent_kwargs.get("grounder_model", ""),
            "grounding_width": agent_kwargs.get("grounding_width", 1920),
            "grounding_height": agent_kwargs.get("grounding_height", 1080),
        })

    # Create agent
    agent = create_agent(agent_type, agent_args, env=env)

    for task in all_tasks:
        task_dir = os.path.join(".\\hf_result", f"{task['task_id']}", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(task_dir, exist_ok = True)
        
        # Use TaskLogger to capture all output to task-specific log file
        with TaskLogger(task_dir, task['task_id']):
            # For CoAct, set history directory
            if agent_type == "coact" and hasattr(agent, 'set_history_dir'):
                agent.set_history_dir(task_dir)
                
            run_one_task(task_dir, agent, env, task, agent_type=agent_type)

    env.close()

def get_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Run benchmark evaluation with different agent types")
    
    # Basic parameters
    parser.add_argument("-b", "--benchmark-path",      type = str, required = True,
                        help = "Path to benchmark JSON file")
    parser.add_argument("-v", "--vmx-path",            type = str, required = True,
                        help = "Path to VMware VMX file")
    parser.add_argument("-m", "--model-name",          type = str, required = True,
                        help = "Model name to use")
    parser.add_argument("-a", "--action-space",        type = str, required = True,
                        help = "Action space type (pyautogui, computer_13)")
    parser.add_argument("-o", "--observation-type",    type = str, required = True,
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
                        help = "Maximum trajectory length (default: 8 for advanced agents, 3 for prompt)")
    parser.add_argument("--client-password",   type = str, default = "",
                        help = "Client password for sudo operations")
    
    # S3 Agent specific parameters
    s3_group = parser.add_argument_group("S3 Agent", "Parameters specific to Agent-S3")
    s3_group.add_argument("--model-provider",    type = str, default = "openai",
                        help = "Model provider for S3 agent (openai, anthropic, etc.)")
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
    s3_group.add_argument("--disable-thinking", action = "store_true",
                        help = "Disable thinking mode for Claude models (use with transit/proxy APIs)")

    # CoAct Agent specific parameters
    coact_group = parser.add_argument_group("CoAct Agent", "Parameters specific to CoAct framework")
    coact_group.add_argument("--orchestrator-model", type = str, default = "",
                        help = "Orchestrator model name (defaults to --model-name)")
    coact_group.add_argument("--coding-model",   type = str, default = "o4-mini",
                        help = "Coding agent model name")
    coact_group.add_argument("--cua-model",      type = str, default = "computer-use-preview",
                        help = "CUA (Computer Use Agent) model name")
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
    coact_group.add_argument("--api-base",       type = str, default = "",
                        help = "API base URL for LLM requests")
    coact_group.add_argument("--api-key",        type = str, default = "",
                        help = "API key for LLM requests")
    coact_group.add_argument("--sleep-after-execution", type = float, default = 0.5,
                        help = "Sleep time after action execution")
    coact_group.add_argument("--region",         type = str, default = "",
                        help = "AWS region (for cloud providers)")
    coact_group.add_argument("--compatibility-mode", action="store_true",
                        help="Enable compatibility mode for transit/proxy APIs that don't support tools/thinking")

    # UIPath Agent specific parameters
    uipath_group = parser.add_argument_group("UIPath Agent", "Parameters specific to UIPath framework")
    uipath_group.add_argument("--uipath-model-name", type = str, default = "",
                        help = "UIPath model name (defaults to --model-name)")
    uipath_group.add_argument("--max-steps",     type = int, default = 15,
                        help = "Maximum steps for UIPath agent")

    # UIPath model configuration
    uipath_model_group = parser.add_argument_group("UIPath Model Config", "UIPath model service configuration")
    uipath_model_group.add_argument("--planner-url",     type = str, default = "",
                          help = "URL for the planner LLM service (e.g., OpenAI API endpoint)")
    uipath_model_group.add_argument("--planner-api-key", type = str, default = "",
                          help = "API key for the planner LLM service")
    uipath_model_group.add_argument("--grounder-url",    type = str, default = "",
                          help = "URL for the grounder/vision service (e.g., UI-TARS server)")
    uipath_model_group.add_argument("--grounder-api-key", type = str, default = "",
                          help = "API key for the grounder service (optional for localhost)")
    uipath_model_group.add_argument("--grounder-model",   type = str, default = "",
                          help = "Model name for the grounder service (e.g., UI-TARS-1.5-7B)")
    uipath_model_group.add_argument("--grounding-width",  type = int, default = 1920,
                          help = "Screen width for grounding coordinate resolution")
    uipath_model_group.add_argument("--grounding-height", type = int, default = 1080,
                          help = "Screen height for grounding coordinate resolution")

    return parser

if __name__ == "__main__":
    args = get_parser().parse_args()
    
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
            "disable_thinking": args.disable_thinking,
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
            "api_base": args.api_base,
            "api_key": args.api_key,
            "sleep_after_execution": args.sleep_after_execution,
            "region": args.region,
            "compatibility_mode": args.compatibility_mode,
        })

    # UIPath specific kwargs
    elif args.agent_type == "uipath":
        agent_kwargs.update({
            "uipath_model_name": args.uipath_model_name if args.uipath_model_name else args.model_name,
            "max_steps": args.max_steps,
            "planner_url": args.planner_url,
            "planner_api_key": args.planner_api_key,
            "grounder_url": args.grounder_url,
            "grounder_api_key": args.grounder_api_key,
            "grounder_model": args.grounder_model,
            "grounding_width": args.grounding_width,
            "grounding_height": args.grounding_height,
        })

    main(
        benchmark_path = args.benchmark_path,
        vmx_path = args.vmx_path,
        model_name = args.model_name,
        action_space = args.action_space,
        observation_type = args.observation_type,
        agent_type = args.agent_type,
        **agent_kwargs
    )
