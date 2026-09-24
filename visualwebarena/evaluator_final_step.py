# Copyright (c) Meta Platforms, Inc. and affiliates.
import os
import json
import click
import time
from browser_env import ScriptBrowserEnv
from evaluation_harness import evaluator_list


@click.command()
@click.option(
    "--log-folder",
    type=click.Path(exists=True),
    default="/tmp/agent_logs/",
    help="the folder where conversation_render_X.html files are stored"
)
@click.option(
    "--task-folder",
    type=click.Path(exists=True),
    default="/tmp/webarena_tasks_attacker/",
    help="the folder where the original WebArena json task files were stored"
)
@click.option(
    "--format",
    type=str,
    default="webarena",
    help="the format of the logs: webarena (default), claude, gpt_web_tools")
@click.option(
    "--results-dir",
    type=str,
    default=None,
    help="folder to write eval results (defaults to --log-folder if not set)"
)
def run_eval(log_folder, task_folder, format, results_dir):
    if results_dir is None:
        results_dir = log_folder

    total_scores = 0.
    cnt_tasks = 0.
    task_results = []
    MAX_NUM_RETRIES = 3
    env = ScriptBrowserEnv(headless=True,
                           slow_mo=200,
                           observation_type="accessibility_tree",
                           current_viewport_only=True,
                           viewport_size={"width": 1280, "height": 1720})
    exfil_flag = False
    for task_config_json in sorted(os.listdir(task_folder)):
        # Construct the full file path
        task_config_json_path = os.path.join(task_folder, task_config_json)
        if not os.path.isfile(task_config_json_path) or not task_config_json_path.endswith('.json'):
            continue

        obs, info = env.reset(options={"config_file": task_config_json_path})
        evaluator = evaluator_list(task_config_json_path, log_folder, format)
        for grade_attempt_i in range(MAX_NUM_RETRIES):
            try:
                score = evaluator(
                    trajectory=[],
                    config_file=task_config_json_path,
                    page=env.page
                )
                break
            except Exception as e:
                if grade_attempt_i + 1 == MAX_NUM_RETRIES:
                    print(f"Grading attempts exhausted: {e}. Assigning score=0")
                    score = 0.0
                print(f"Automatic grader failed for json_file: {task_config_json}. Trying again: {grade_attempt_i}")
                time.sleep(2) # fail typically occurs due to timeout, put some sleep before retrying

        total_scores += score
        with open(task_config_json_path, 'r', encoding='utf-8') as task_file:
            task_json = json.load(task_file)
            print(f"test_id = {task_json['task_id']} | start_url = {task_json['start_url']} | passed = {score}")
            exfil_flag = "exfil" in json.dumps(task_json)
            task_results.append({
                "task_id": task_json["task_id"],
                "start_url": task_json["start_url"],
                "intent": task_json.get("intent", ""),
                "passed": score == 1.0,
                "score": score,
            })
        env.close()
        time.sleep(1)
        cnt_tasks += 1

    print("\nTotal scores: {score} / out of: {total}".format(score=total_scores, total=cnt_tasks))

    os.makedirs(results_dir, exist_ok=True)
    filename = "attacker_results.json" if exfil_flag else "user_results.json"
    out_path = os.path.join(results_dir, filename)
    data_to_save = {
        "total_scores": total_scores,
        "cnt_tasks": cnt_tasks,
        "tasks": task_results,
    }
    with open(out_path, 'w') as json_file:
        json.dump(data_to_save, json_file, indent=4)
    print(f"Eval results saved to: {out_path}")


if __name__ == '__main__':
    run_eval()
