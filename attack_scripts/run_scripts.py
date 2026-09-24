import glob
import inspect
import json
import os
import sys
import argparse
from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser
from typing import Callable
from wasp_gitlab_attacker_goals import GITLAB_ATTACKER_GOALS
from wasp_reddit_attacker_goals import REDDIT_ATTACKER_GOALS

# ----------- LOGGING HELPER ------------ #
class Logger(object):
    """
    A helper class to redirect stdout/stderr to both the terminal and a file.
    """
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.flush() # Ensure it writes immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def load_attack_plan(config_dir: str) -> list[tuple[Callable[[Page], None], dict]]:
    """
    Reads all JSON configs from config_dir, sorts by task_id, and pairs each with
    the matching attacker goal function (gitlab configs → GITLAB_ATTACKER_GOALS,
    reddit configs → REDDIT_ATTACKER_GOALS, by order within each site).
    Returns a list of (function, config) tuples.
    """
    paths = sorted(glob.glob(os.path.join(config_dir, "*.json")))
    configs = [json.load(open(p)) for p in paths]
    configs.sort(key=lambda c: c["task_id"])

    gitlab_configs = [c for c in configs if "gitlab" in c.get("sites", [])]
    reddit_configs = [c for c in configs if "reddit" in c.get("sites", [])]

    plan: list[tuple[Callable[[Page], None], dict]] = []
    for func, cfg in zip(GITLAB_ATTACKER_GOALS, gitlab_configs):
        plan.append((func, cfg))
    for func, cfg in zip(REDDIT_ATTACKER_GOALS, reddit_configs):
        plan.append((func, cfg))
    return plan


# ----------- MAIN RUN FUNCTION ------------ #

def run(func: Callable[[Page], None], start_url: str, config: dict | None = None, log_folder: str = ".", cdp_url: str = "http://localhost:9222") -> bool:
    """
    Navigates directly to start_url and executes the attack function.
    If func declares a second 'config' parameter, the config dict is passed to it.
    Saves all visited URLs to {log_folder}/{task_id}_visited_urls.json for eval.
    Returns True if successful, False if any error occurs.
    """
    success = False
    accepts_config = "config" in inspect.signature(func).parameters
    visited_urls: list[str] = []
    browser: Browser | None = None
    page: Page | None = None

    with sync_playwright() as p:
        try:
            print(f"Connecting to existing Chrome instance at {cdp_url}...")
            browser = p.chromium.connect_over_cdp(cdp_url)
            context: BrowserContext = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.set_default_timeout(3000)
            page.on("request", lambda req: visited_urls.append(req.url))

            print(f"Navigating to: {start_url}")
            page.goto(start_url)

            print("Performing action...")
            func(page, config) if accepts_config else func(page)
            success = True

            page.wait_for_timeout(5000)

        except Exception as e:
            print(f"[Error] Exception occurred during {func.__name__}: {e}")
            success = False

        finally:
            if page:
                page.close()
            if browser:
                browser.close()
            if config:
                task_id = config.get("task_id")
                url_log_path = os.path.join(log_folder, f"{task_id}_visited_urls.json")
                with open(url_log_path, "w") as f:
                    json.dump(visited_urls, f, indent=2)
                print(f"Saved {len(visited_urls)} visited URLs to {url_log_path}")

    return success


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        type=str,
        default="wasp_attack_configs_complete/webarena_tasks_attacker",
        help="Directory containing per-task attack config JSON files.",
    )
    parser.add_argument(
        "--task-id",
        type=int,
        default=None,
        help="Run only the attack with this task_id (e.g. 1013).",
    )
    parser.add_argument(
        "--log-folder",
        type=str,
        default=".",
        help="Folder to store logs of the attack execution.",
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default="http://localhost:9222",
        help="Chrome DevTools Protocol URL of the running browser.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    log_filename = os.path.join(args.log_folder, "attack_execution_log.txt")
    sys.stdout = Logger(log_filename)
    sys.stderr = sys.stdout

    attack_plan = load_attack_plan(args.config_dir)
    if args.task_id is not None:
        attack_plan = [(f, c) for f, c in attack_plan if c["task_id"] == args.task_id]
        if not attack_plan:
            print(f"No attack found with task_id={args.task_id}")
            sys.exit(1)

    success_count = 0
    failure_count = 0

    print(f"Loaded {len(attack_plan)} attacks from {args.config_dir}\n")
    print(f"Logs will be saved to: {log_filename}\n")

    for i, (action, config) in enumerate(attack_plan):
        task_id = config["task_id"]
        start_url = config["start_url"]
        print(f"\n=== Executing action {i + 1}/{len(attack_plan)}: {action.__name__} (task_id={task_id}) ===")
        print(f"    start_url: {start_url}")

        result = run(action, start_url, config, args.log_folder, args.cdp_url)

        if result:
            print(f"✅ [COMPLETED] {action.__name__}")
            success_count += 1
        else:
            print(f"❌ [FAILED] {action.__name__}")
            failure_count += 1

    print("\n" + "="*30)
    print("       EXECUTION SUMMARY       ")
    print("="*30)
    print(f"Total Attacks Attempted: {len(attack_plan)}")
    print(f"Completed:              {success_count}")
    print(f"Failed:                  {failure_count}")
    print("This results does not reflect the success of the overall attack campaign,"
          " only whether each script ran without errors.")
    print("Please run evaluation scripts to determine actual attack success.")
    print("="*30)