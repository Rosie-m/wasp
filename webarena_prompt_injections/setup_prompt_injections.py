# Copyright (c) Meta Platforms, Inc. and affiliates.
import click
import subprocess
from pathlib import Path
from constants import (
    PromptInjectionFormat,
    GitlabUserGoals,
    RedditUserGoals
)


def run_single_end_to_end(
        config,  # prompt injection configurations
        model,  # agentic model to run
        system_prompt,  # system prompt for agent
        output_dir,  # to store settings, logs, errors
        output_format,  # agentic scaffolding format
        user_goal_idx,  # benign user goal
        injection_format,  # prompt injection format to try
        output_dir_idx=0,  # to save logs for each run separately
    ):
    while (Path(output_dir)/str(output_dir_idx)).exists():
        print(f"Output dir {output_dir}/{output_dir_idx} already exists! Skipping this index to avoid overwriting.")
        output_dir_idx += 1

    if output_dir[-1] == '/':
        output_dir = output_dir + str(output_dir_idx) + '/'
    else:
        output_dir = output_dir + '/' + str(output_dir_idx) + '/'

    command = [
        'bash',
        'scripts/step1_setup_prompt_injections.sh',
        output_dir,
        model,
        system_prompt,
        config,
        str(user_goal_idx),
        injection_format,
        output_format
    ]
    print(f"\nRunning command: \n{' '.join([str(arg) for arg in command])}", flush=True)
    try:
        subprocess.run(command, check=True, timeout=300)
    except subprocess.TimeoutExpired:
        print(f"[Timeout] prompt injector exceeded 300s for user_goal_idx={user_goal_idx}, skipping.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[Error] prompt injector failed (exit {e.returncode}) for user_goal_idx={user_goal_idx}, skipping.", flush=True)


def run_all(config,
            model,
            system_prompt,
            output_dir,
            output_format,
            run_single,
            user_goal_start):
    gitlab_user_goals = GitlabUserGoals("")
    reddit_user_goals = RedditUserGoals("")
    assert len(gitlab_user_goals.GOALS) == len(reddit_user_goals.GOALS), "Number of user goals should match!"
    user_goals_len = len(gitlab_user_goals.GOALS)
    injection_format_list = [PromptInjectionFormat.GOAL_HIJACKING_PLAIN_TEXT]

    for user_goal_idx in range(user_goal_start, user_goals_len):
        print(f"$$$$$$$ Running {user_goal_idx+1} out of {user_goals_len} user goals, current one: "
              f"(gitlab) '{gitlab_user_goals.GOALS[user_goal_idx]}', "
              f"(reddit) '{reddit_user_goals.GOALS[user_goal_idx]}'")
        for i, injection_format in enumerate(injection_format_list):
            print(f"$$$$$$$ Running {i+1} out of {len(injection_format_list)} injection formats, current one: {injection_format}")

            run_single_end_to_end(config=config,
                                  model=model,
                                  system_prompt=system_prompt,
                                  output_dir=output_dir,
                                  output_format=output_format,
                                  user_goal_idx=user_goal_idx,
                                  injection_format=injection_format,
                                  output_dir_idx=user_goal_idx * len(injection_format_list) + i)

            if run_single:
                print("\n!!! Running a single user goal and a single injection format is requested. Terminating")
                return

    print("\n\nDone running all experiments!")


@click.command()
@click.option(
    "--config",
    type=str,
    default="configs/experiment_config.raw.json",
    help="Where to find the config for prompt injections",
)
@click.option(
    "--model",
    type=str,
    default="gpt-4o",
    help="backbone LLM. Available options: gpt-4o, gpt-4o-mini, claude-35, claude-37",
)
@click.option(
    "--system-prompt",
    type=str,
    default="configs/system_prompts/wa_p_som_cot_id_actree_3s.json",
    help="system_prompt for the backbone LLM. Default = VWA's SOM system prompt for GPT scaffolding",
)
@click.option(
    "--output-dir",
    type=str,
    default="/tmp/computer-use-agent-logs",
    help="Folder to store the output configs and commands to run the agent",
)
@click.option(
    "--output-format",
    type=str,
    default="webarena",
    help="Format of the agentic scaffolding: webarena (default), claude, gpt_web_tools",
)
@click.option(
    "--run-single",
    is_flag=True,
    default=False,
    help="whether to test only a single user goal and a single injection format",
)
@click.option(
    "--user_goal_start",
    type=int,
    default=0,
    help="starting user_goal index (between 0 and total number of benign user goals)",
)
def main(config,
         model,
         system_prompt,
         output_dir,
         output_format,
         run_single,
         user_goal_start):
    print("Arguments provided to setup_prompt_injections.py: \n", locals(), "\n\n")
    run_all(config=config,
            model=model,
            system_prompt=system_prompt,
            output_dir=output_dir,
            output_format=output_format,
            run_single=run_single,
            user_goal_start=user_goal_start)


if __name__ == '__main__':
    main()
