import os
import time
import json
import asyncio
import argparse
import subprocess
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

from browser_use import Agent, Browser, ChatOpenAI, ChatGoogle, ChatAnthropic

# Load environment variables
load_dotenv()

extended_system_prompt = ""


def close_all_cdp_targets(cdp_url="http://localhost:9222"):
    try:
        with urllib.request.urlopen(f"{cdp_url}/json/list", timeout=5) as resp:
            targets = json.loads(resp.read())
        # Keep one target alive so Chrome doesn't exit when the last tab closes
        targets_to_close = targets[:-1] if len(targets) > 1 else []
        closed = 0
        for target in targets_to_close:
            target_id = target.get("id")
            if target_id:
                try:
                    urllib.request.urlopen(f"{cdp_url}/json/close/{target_id}", timeout=5)
                    closed += 1
                except Exception:
                    pass
        if closed:
            print(f"[CDP] Closed {closed} stale targets before task start ({len(targets)} total)")
    except Exception as e:
        print(f"[Warning] Could not purge CDP targets: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description="Run WebArena tasks with browser-use")
    parser.add_argument("--test_config_base_dir", type=str, required=True)
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    parser.add_argument("--test_start_idx", type=int, default=0)
    parser.add_argument("--test_end_idx", type=int, default=10)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--max_steps", type=int, default=30)
    parser.add_argument("--result_dir", type=str, default="results")
    parser.add_argument("--auth_dir", type=str, default=".auth")
    parser.add_argument("--extended_system_prompt", type=str)
    parser.add_argument("--visualwebarena_dir", type=str, default=None,
                        help="Path to visualwebarena directory for auto_login.py. Inferred from this script's location if not set.")
    return parser.parse_args()


def get_required_sites(task_files):
    sites = set()
    for task_file in task_files:
        with open(task_file, "r") as f:
            config = json.load(f)
        for site in config.get("sites", []):
            sites.add(site)
    return sites


def auto_login(sites, auth_dir, visualwebarena_dir):
    auth_dir = Path(auth_dir).resolve()
    auth_dir.mkdir(parents=True, exist_ok=True)

    # Skip if a matching auth file already exists
    sites_set = set(sites)
    existing = next(
        (f for f in auth_dir.glob("*_state.json")
         if set(f.stem.replace("_state", "").split(".")) == sites_set),
        None,
    )
    if existing:
        print(f"Auth file already exists ({existing.name}), skipping auto_login.")
        return

    venv_python = str(Path(visualwebarena_dir) / "venv" / "bin" / "python")
    try:
        subprocess.run(
            [venv_python, "browser_env/auto_login.py",
             "--auth_folder", str(auth_dir),
             "--site_list"] + list(sites),
            cwd=visualwebarena_dir,
            check=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("[Timeout] auto_login exceeded 300s.", flush=True)
        raise
    except subprocess.CalledProcessError as e:
        print(f"[Error] auto_login failed (exit {e.returncode}).", flush=True)
        raise


def find_auth_file(sites, auth_dir):
    sites_set = set(sites)
    auth_file = next(
        (f for f in Path(auth_dir).glob("*_state.json")
         if set(f.stem.replace("_state", "").split(".")) == sites_set),
        None,
    )
    if auth_file is None:
        raise FileNotFoundError(f"No auth file found for sites {sites} in {auth_dir}")
    return auth_file


async def run_task(
    task_config_path,
    llm,
    result_dir,
    auth_file,
    max_steps=30,
):
    global extended_system_prompt

    with open(task_config_path, "r") as f:
        config = json.load(f)

    start_url = config["start_url"]
    intent = config["intent"]
    task_id = config.get("task_id", task_config_path.stem)

    trace_path = (
        Path(result_dir)
        / f"task_{task_id}_{time.strftime('%Y%m%d_%H%M%S')}"
    )

    print(f"\n🚀 Starting Task {task_id}: {intent}")
    close_all_cdp_targets()

    browser = Browser(
        cdp_url="http://localhost:9222",
        storage_state=str(auth_file),
        minimum_wait_page_load_time=2.0,
        wait_for_network_idle_page_load_time=2.0,
        wait_between_actions=2.0,
    )

    agent = Agent(
        task=intent,
        llm=llm,
        browser=browser,
        initial_actions=[{"navigate": {"url": start_url, "new_tab": True}}],
        save_conversation_path=trace_path,
        save_conversation_encoding="utf-8",
        extend_system_message=extended_system_prompt,
    )

    result = None
    success = False
    try:
        history = await agent.run(max_steps=max_steps)
        result = history.final_result()
        success = history.is_done()
        print(f" 📝 Task {task_id} Completed. Success: {success}")

    finally:
        try:
            await asyncio.wait_for(browser.stop(), timeout=10.0)
        except Exception:
            pass

    return {
        "task_id": task_id,
        "success": success,
        "result": result,
    }


async def main():
    args = parse_args()

    # Collect task files
    task_files = []
    for i in range(args.test_start_idx, args.test_end_idx):
        p = Path(args.test_config_base_dir) / f"{i}.json"
        if p.exists():
            task_files.append(p)

    if not task_files:
        print("No task files found. Exiting.")
        return

    # Determine visualwebarena directory
    visualwebarena_dir = args.visualwebarena_dir
    if visualwebarena_dir is None:
        visualwebarena_dir = Path(__file__).resolve().parent.parent / "visualwebarena"
    visualwebarena_dir = str(visualwebarena_dir)

    # Auto-login and locate the resulting auth file
    required_sites = get_required_sites(task_files)
    print(f"Auto-logging in to sites: {required_sites}")
    auto_login(required_sites, args.auth_dir, visualwebarena_dir)
    auth_file = find_auth_file(required_sites, args.auth_dir)
    print(f"Using auth file: {auth_file}")

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    # Load extended system prompt
    global extended_system_prompt
    if args.extended_system_prompt and os.path.exists(args.extended_system_prompt):
        with open(args.extended_system_prompt, "r") as f:
            extended_system_prompt = f.read()

    # Initialize LLM
    if "gpt" in args.model.lower() or args.model.lower().startswith("o"):
        llm = ChatOpenAI(model=args.model)
    elif "claude" in args.model.lower():
        llm = ChatAnthropic(model=args.model)
    elif "gemini" in args.model.lower():
        llm = ChatGoogle(model=args.model)
    else:
        raise ValueError(f"Unsupported model: {args.model}")

    all_results = []

    task_timeout = 1200  # 20 minutes per task

    try:
        for task_idx, task_file in enumerate(task_files):
            if task_idx > 0:
                await asyncio.sleep(5)  # let CDP EventBus drain between tasks
            try:
                res = await asyncio.wait_for(
                    run_task(
                        task_file,
                        llm,
                        result_dir,
                        auth_file=auth_file,
                        max_steps=args.max_steps,
                    ),
                    timeout=task_timeout,
                )
                all_results.append(res)
            except asyncio.TimeoutError:
                print(f"\n[Timeout] Task {task_file.name} exceeded {task_timeout}s, skipping.")
                all_results.append({"task_id": task_file.stem, "success": False, "result": None, "error": "timeout"})
            except Exception as e:
                print(f"\n[Error] Task {task_file.name} failed: {e}")
                all_results.append({"task_id": task_file.stem, "success": False, "result": None, "error": str(e)})
    finally:
        with open(result_dir / "summary_results.json", "w") as f:
            json.dump(all_results, f, indent=4)
        print(f"\nExited. Results saved in: {result_dir}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
