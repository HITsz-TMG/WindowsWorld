"""
Multi-VM Parallel Benchmark Runner

This script manages parallel execution of benchmark tasks across multiple VMs.
It supports different agent frameworks: prompt, s3, coact, uipath.
"""

import json
import os
import sys
import shutil
import random
import time
from multiprocessing import Process, Queue, Manager
from typing import List, Dict, Any

# Disable output buffering for real-time logging
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None


def print_flush(message: str):
    """Print message with immediate flush."""
    print(message, flush=True)


def build_agent_kwargs(args) -> Dict[str, Any]:
    """Build agent-specific kwargs based on agent type."""
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
            "cua_api_base": args.cua_api_base,
            "cua_api_key": args.cua_api_key,
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

    return agent_kwargs


def run_worker(worker_id: int, benchmark_file: str, vmx_path: str, 
               model_name: str, action_space: str, observation_type: str,
               agent_type: str, agent_kwargs: Dict[str, Any],
               status_queue: Queue = None):
    """
    Worker function to run benchmark on a single VM.
    
    Args:
        worker_id: Worker identifier
        benchmark_file: Path to benchmark JSON for this worker
        vmx_path: Path to VM file
        model_name: Model name
        action_space: Action space type
        observation_type: Observation type
        agent_type: Type of agent
        agent_kwargs: Agent-specific arguments
        status_queue: Queue for status updates
    """
    # Import here to avoid circular imports and allow --help to work without all dependencies
    import hf_run
    
    # Set up worker-level logging - use TeeOutput to write to both console and file
    worker_log_dir = os.path.join("logs", f"worker_{worker_id}")
    os.makedirs(worker_log_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    worker_log_file = os.path.join(worker_log_dir, f"worker_{worker_id}_{timestamp}.log")
    
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Open log file and create TeeOutput for dual output (console + file)
    log_file_handle = open(worker_log_file, "w", encoding="utf-8", buffering=1)
    
    class TeeOutput:
        """Write to both console and file simultaneously."""
        def __init__(self, console, file):
            self.console = console
            self.file = file
        def write(self, text):
            if self.console:
                try:
                    self.console.write(text)
                    self.console.flush()
                except:
                    pass
            if self.file:
                try:
                    self.file.write(text)
                    self.file.flush()
                except:
                    pass
        def flush(self):
            if self.console:
                try:
                    self.console.flush()
                except:
                    pass
            if self.file:
                try:
                    self.file.flush()
                except:
                    pass
    
    sys.stdout = TeeOutput(original_stdout, log_file_handle)
    sys.stderr = TeeOutput(original_stderr, log_file_handle)
    
    try:
        if status_queue:
            status_queue.put({"worker_id": worker_id, "status": "starting"})
        
        print_flush(f"[Worker {worker_id}] Starting with benchmark: {benchmark_file}")
        print_flush(f"[Worker {worker_id}] VMX path: {vmx_path}")
        print_flush(f"[Worker {worker_id}] Log file: {worker_log_file}")
        
        hf_run.main(
            benchmark_path=benchmark_file,
            vmx_path=vmx_path,
            model_name=model_name,
            action_space=action_space,
            observation_type=observation_type,
            agent_type=agent_type,
            **agent_kwargs
        )
        
        if status_queue:
            status_queue.put({"worker_id": worker_id, "status": "completed"})
            
    except Exception as e:
        if status_queue:
            status_queue.put({"worker_id": worker_id, "status": "error", "error": str(e)})
        import traceback
        print_flush(f"[Worker {worker_id}] Error: {e}")
        print_flush(traceback.format_exc())
        raise
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_file_handle.close()


def prepare_benchmark_splits(data: List[dict], num_workers: int, output_dir: str = "benchmark") -> List[str]:
    """
    Split benchmark data into chunks for parallel processing.
    
    Args:
        data: Full benchmark data
        num_workers: Number of workers
        output_dir: Directory to save split files
        
    Returns:
        List of paths to split benchmark files
    """
    # Clean and recreate output directory
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    
    total = len(data)
    chunk_size = total // num_workers
    remainder = total % num_workers
    
    benchmark_files = []
    start = 0
    
    for i in range(num_workers):
        # Distribute remainder across first few workers
        end = start + chunk_size + (1 if i < remainder else 0)
        sub_data = data[start:end]
        
        output_file = os.path.join(output_dir, f"benchmark_{i}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(sub_data, f, ensure_ascii=False, indent=4)
        
        benchmark_files.append(output_file)
        start = end

        print_flush(f"[Main] Worker {i}: {len(sub_data)} tasks -> {output_file}")
    
    return benchmark_files


def get_vmx_path(worker_id: int, vmx_template: str) -> str:
    """
    Generate VMX path for a worker.
    
    Args:
        worker_id: Worker identifier
        vmx_template: Template path with {i} placeholder
        
    Returns:
        VMX path for this worker
    """
    if "{i}" in vmx_template:
        return vmx_template.format(i=worker_id)
    else:
        # Default pattern
        return f"E:\\vmx\\Windows{worker_id}\\Windows{worker_id}.vmx"


def get_parser():
    import argparse
    parser = argparse.ArgumentParser(
        description="Multi-VM Parallel Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with 4 VMs using Agent-S3
  python main.py -c 4 -m gpt-4o -a pyautogui -o screenshot --agent-type s3
  
  # Run with CoAct
  python main.py -c 2 -m o3 -a computer_13 -o screenshot --agent-type coact
  
  # Run with UIPath
  python main.py -c 4 -m gpt-4o -a pyautogui -o screenshot --agent-type uipath
        """
    )
    
    # Basic parameters
    parser.add_argument("-c", "--count", type=int, required=True,
                        help="Number of parallel VMs to run")
    parser.add_argument("-m", "--model-name", type=str, required=True,
                        help="Model name to use")
    parser.add_argument("-a", "--action-space", type=str, required=True,
                        choices=["pyautogui", "computer_13"],
                        help="Action space type")
    parser.add_argument("-o", "--observation-type", type=str, required=True,
                        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree"],
                        help="Observation type")
    
    # Benchmark and VM configuration
    parser.add_argument("-b", "--benchmark-file", type=str, default="benchmark.json",
                        help="Path to benchmark JSON file (default: benchmark.json)")
    parser.add_argument("--vmx-template", type=str, 
                        default="C:\\Users\\250010095\\Documents\\Virtual Machines\\Windows{i}\\Windows{i}.vmx",
                        help="VMX path template with {i} placeholder (default: E:\\vmx\\Windows{i}\\Windows{i}.vmx)")
    parser.add_argument("--no-shuffle", action="store_true",
                        help="Don't shuffle benchmark tasks")
    
    # Agent type selection
    parser.add_argument("--agent-type", type=str, default="prompt",
                        choices=["prompt", "s3", "coact", "uipath"],
                        help="Type of agent to use (default: prompt)")
    
    # Common parameters
    parser.add_argument("--platform", type=str, default="windows",
                        choices=["windows", "linux", "darwin"],
                        help="Operating system platform")
    parser.add_argument("--max-trajectory-length", type=int, default=None,
                        help="Maximum trajectory length")
    parser.add_argument("--client-password", type=str, default="",
                        help="Client password for sudo operations")
    
    # S3 Agent specific parameters
    s3_group = parser.add_argument_group("S3 Agent", "Parameters specific to Agent-S3")
    s3_group.add_argument("--model-provider", type=str, default="openai",
                        help="Model provider for S3 agent")
    s3_group.add_argument("--model-url", type=str, default="",
                        help="Custom API URL for the main model")
    s3_group.add_argument("--model-api-key", type=str, default="",
                        help="API key for the main model")
    s3_group.add_argument("--model-temperature", type=float, default=None,
                        help="Temperature for model generation")
    s3_group.add_argument("--ground-provider", type=str, default="huggingface",
                        help="Provider for grounding model")
    s3_group.add_argument("--ground-url", type=str, default="localhost:8000",
                        help="URL for grounding model endpoint")
    s3_group.add_argument("--ground-model", type=str, default="ui-tars-1.5-7b",
                        help="Grounding model name")
    s3_group.add_argument("--ground-api-key", type=str, default="",
                        help="API key for grounding model")
    s3_group.add_argument("--grounding-width", type=int, default=1920,
                        help="Width for grounding coordinate resolution")
    s3_group.add_argument("--grounding-height", type=int, default=1080,
                        help="Height for grounding coordinate resolution")
    s3_group.add_argument("--enable-reflection", action="store_true", default=True,
                        help="Enable reflection agent for S3")
    s3_group.add_argument("--disable-reflection", action="store_true",
                        help="Disable reflection agent for S3")
    s3_group.add_argument("--disable-thinking", action="store_true",
                        help="Disable thinking mode for Claude models (use with transit/proxy APIs)")

    # CoAct Agent specific parameters
    coact_group = parser.add_argument_group("CoAct Agent", "Parameters specific to CoAct framework")
    coact_group.add_argument("--orchestrator-model", type=str, default="",
                        help="Orchestrator model name")
    coact_group.add_argument("--coding-model", type=str, default="o4-mini",
                        help="Coding agent model name")
    coact_group.add_argument("--cua-model", type=str, default="computer-use-preview",
                        help="CUA model name")
    coact_group.add_argument("--orchestrator-max-steps", type=int, default=15,
                        help="Maximum steps for orchestrator")
    coact_group.add_argument("--coding-max-steps", type=int, default=20,
                        help="Maximum steps for coding agent")
    coact_group.add_argument("--cua-max-steps", type=int, default=25,
                        help="Maximum steps for CUA agent")
    coact_group.add_argument("--cut-off-steps", type=int, default=200,
                        help="Total cut-off steps limit")
    coact_group.add_argument("--oai-config-path", type=str, default="",
                        help="Path to OpenAI config JSON file")
    coact_group.add_argument("--api-base", type=str, default="",
                        help="API base URL for LLM requests")
    coact_group.add_argument("--api-key", type=str, default="",
                        help="API key for LLM requests")
    coact_group.add_argument("--cua-api-base", type=str, default="",
                        help="API base URL for CUA (GUI Agent) - uses OpenAI Computer Use API")
    coact_group.add_argument("--cua-api-key", type=str, default="",
                        help="API key for CUA (GUI Agent) - uses OpenAI Computer Use API")
    coact_group.add_argument("--sleep-after-execution", type=float, default=0.5,
                        help="Sleep time after action execution")
    coact_group.add_argument("--region", type=str, default="",
                        help="AWS region")
    coact_group.add_argument("--compatibility-mode", action="store_true",
                        help="Enable compatibility mode for transit/proxy APIs that don't support tools/thinking")

    # UIPath Agent specific parameters
    uipath_group = parser.add_argument_group("UIPath Agent", "Parameters specific to UIPath framework")
    uipath_group.add_argument("--uipath-model-name", type=str, default="",
                        help="UIPath model name")
    uipath_group.add_argument("--max-steps", type=int, default=15,
                        help="Maximum steps for UIPath agent")

    # UIPath Model configuration
    uipath_model_group = parser.add_argument_group("UIPath Model Config", "UIPath model service configuration")
    uipath_model_group.add_argument("--planner-url", type=str, default="",
                        help="URL for the planner LLM service (e.g., OpenAI API endpoint)")
    uipath_model_group.add_argument("--planner-api-key", type=str, default="",
                        help="API key for the planner LLM service")
    uipath_model_group.add_argument("--grounder-url", type=str, default="",
                        help="URL for the grounder/vision service (e.g., UI-TARS server)")
    uipath_model_group.add_argument("--grounder-api-key", type=str, default="",
                        help="API key for the grounder service (optional for localhost)")
    uipath_model_group.add_argument("--grounder-model", type=str, default="",
                        help="Model name for the grounder service (e.g., UI-TARS-1.5-7B)")
    # Note: --grounding-width and --grounding-height are defined in S3 Agent group and can be reused

    return parser


def main():
    """Main entry point."""
    # Import show_result here to allow --help without dependencies
    import show_result

    os.makedirs("hf_result", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Show existing results
    show_result.main()

    args = get_parser().parse_args()
    num_workers = args.count

    print_flush(f"\n{'='*60}")
    print_flush(f"Multi-VM Parallel Benchmark Runner")
    print_flush(f"{'='*60}")
    print_flush(f"Agent Type: {args.agent_type}")
    print_flush(f"Model: {args.model_name}")
    print_flush(f"Number of VMs: {num_workers}")
    print_flush(f"Action Space: {args.action_space}")
    print_flush(f"Observation Type: {args.observation_type}")
    print_flush(f"{'='*60}\n")

    # Load benchmark data
    with open(args.benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print_flush(f"[Main] Loaded {len(data)} tasks from {args.benchmark_file}")

    # Shuffle tasks for better distribution
    if not args.no_shuffle:
        random.shuffle(data)
        print_flush("[Main] Tasks shuffled for balanced distribution")

    # Prepare benchmark splits
    benchmark_files = prepare_benchmark_splits(data, num_workers)

    # Build agent kwargs
    agent_kwargs = build_agent_kwargs(args)

    # Create status queue for monitoring
    manager = Manager()
    status_queue = manager.Queue()

    # Start worker processes
    processes: List[Process] = []

    print_flush(f"\n[Main] Starting {num_workers} worker processes...")

    for i in range(num_workers):
        vmx_path = get_vmx_path(i, args.vmx_template)

        p = Process(
            target=run_worker,
            args=(
                i,
                benchmark_files[i],
                vmx_path,
                args.model_name,
                args.action_space,
                args.observation_type,
                args.agent_type,
                agent_kwargs,
                status_queue
            ),
            name=f"Worker-{i}"
        )
        p.start()
        processes.append(p)
        print_flush(f"[Main] Worker {i} started (PID: {p.pid}) -> {vmx_path}")

        # Small delay between starts to avoid resource contention
        time.sleep(2)

    print_flush(f"\n[Main] All {num_workers} workers started")
    print_flush("[Main] Waiting for workers to complete...\n")

    # Monitor progress with heartbeat
    completed = 0
    errors = []
    last_heartbeat = time.time()
    heartbeat_interval = 30  # Show heartbeat every 30 seconds

    try:
        while completed < num_workers:
            try:
                status = status_queue.get(timeout=10)
                worker_id = status["worker_id"]

                if status["status"] == "starting":
                    print_flush(f"[Worker {worker_id}] Initializing...")
                elif status["status"] == "completed":
                    completed += 1
                    print_flush(f"[Worker {worker_id}] Completed ({completed}/{num_workers})")
                elif status["status"] == "error":
                    completed += 1
                    errors.append((worker_id, status.get("error", "Unknown error")))
                    print_flush(f"[Worker {worker_id}] Error: {status.get('error', 'Unknown')}")

            except Exception:
                # Show heartbeat periodically to show script is still running
                if time.time() - last_heartbeat > heartbeat_interval:
                    active_count = sum(1 for p in processes if p.is_alive())
                    print_flush(f"[Main] Heartbeat: {active_count} workers still running...")
                    last_heartbeat = time.time()

                # Check if any process has died
                for i, p in enumerate(processes):
                    if not p.is_alive() and p.exitcode not in [0, None]:
                        if i not in [e[0] for e in errors]:
                            errors.append((i, f"Process died with exit code {p.exitcode}"))
                            completed += 1
                            print_flush(f"[Worker {i}] Process died with exit code {p.exitcode}")

    except KeyboardInterrupt:
        print_flush("\n[Main] Interrupted! Terminating workers...")
        for p in processes:
            if p.is_alive():
                p.terminate()
        sys.exit(1)

    # Wait for all processes to finish
    print_flush("\n[Main] Waiting for all processes to cleanup...")
    for p in processes:
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()

    # Print summary
    print_flush(f"\n{'='*60}")
    print_flush("Execution Summary")
    print_flush(f"{'='*60}")
    print_flush(f"Total Workers: {num_workers}")
    print_flush(f"Successful: {num_workers - len(errors)}")
    print_flush(f"Failed: {len(errors)}")

    if errors:
        print_flush("\nErrors:")
        for worker_id, error in errors:
            print_flush(f"  Worker {worker_id}: {error}")

    print_flush(f"{'='*60}\n")

    # Show final results
    show_result.main()


if __name__ == "__main__":
    main()
