# Copyright (c) Meta Platforms, Inc. and affiliates.
import os
import click
import subprocess
from pathlib import Path
from constants import (
    PromptInjectionFormat,
    GitlabUserGoals,
    RedditUserGoals
)


def run_single_end_to_end(
        config,
        model,
        system_prompt,
        output_dir,
        output_format,
        user_goal_idx,
        injection_format,
        gitlab_url,
        reddit_url,
        max_steps=20,
        output_dir_idx=0,
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
        'scripts/run_end_to_end_browser_use.sh',
        output_dir,
        model,
        system_prompt,
        config,
        str(user_goal_idx),
        injection_format,
        output_format,
        str(max_steps),
    ]
    print(f"\nRunning command: \n{' '.join([str(arg) for arg in command])}", flush=True)

    env = os.environ.copy()
    env['GITLAB'] = gitlab_url
    env['REDDIT'] = reddit_url

    try:
        subprocess.run(command, check=True, env=env)
    except subprocess.TimeoutExpired:
        print(f"[Timeout] run_end_to_end exceeded timeout for user_goal_idx={user_goal_idx}, skipping.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[Error] run_end_to_end failed (exit {e.returncode}) for user_goal_idx={user_goal_idx}, skipping.", flush=True)


def run_all(config,
            model,
            system_prompt,
            output_dir,
            output_format,
            run_single,
            user_goal_start,
            gitlab_url,
            reddit_url,
            max_steps=20,
            idx_offset=0):
    gitlab_user_goals = GitlabUserGoals("")
    reddit_user_goals = RedditUserGoals("")
    assert len(gitlab_user_goals.GOALS) == len(reddit_user_goals.GOALS), "Number of user goals should match!"
    user_goals_len = len(gitlab_user_goals.GOALS)
    injection_format_list = [PromptInjectionFormat.GOAL_HIJACKING_PLAIN_TEXT]

    if user_goal_start + idx_offset >= user_goals_len:
        raise ValueError("Invalid user_goal_start or idx_offset")
    user_goal_idx = user_goal_start + idx_offset
    print(f"$$$$$$$ Running {user_goal_idx+1} out of {user_goals_len} user goals, current one: "
            f"(gitlab) '{gitlab_user_goals.GOALS[user_goal_idx]}', "
            f"(reddit) '{reddit_user_goals.GOALS[user_goal_idx]}'")
    for i, injection_format in enumerate(injection_format_list):
        print(f"$$$$$$$ Running {i+1} out of {len(injection_format_list)} injection formats, current one: {injection_format}")

        run_single_end_to_end(
            config=config,
            model=model,
            system_prompt=system_prompt,
            output_dir=output_dir,
            output_format=output_format,
            user_goal_idx=user_goal_idx,
            injection_format=injection_format,
            gitlab_url=gitlab_url,
            reddit_url=reddit_url,
            max_steps=max_steps,
            output_dir_idx=user_goal_idx * len(injection_format_list) + i,
        )

        print(f"\nDone user_goal_idx={user_goal_idx+1}, injection_format_idx={i+1}.", flush=True)

        if run_single:
            print("\n!!! Running a single user goal and a single injection format is requested. Terminating")
            return

    print("\n\nDone running all experiments!")


@click.command()
@click.option("--config", type=str, default="configs/experiment_config.raw.json")
@click.option("--model", type=str, default="gpt-4o")
@click.option("--system-prompt", type=str, default="configs/system_prompts/wa_p_som_cot_id_actree_3s.json")
@click.option("--output-dir", type=str, default="/tmp/computer-use-agent-logs")
@click.option("--output-format", type=str, default="webarena")
@click.option("--run-single", is_flag=True, default=False)
@click.option("--user_goal_start", type=int, default=0)
@click.option("--gitlab-url", type=str, default=None, help="GitLab URL (overrides $GITLAB env var)")
@click.option("--reddit-url", type=str, default=None, help="Reddit URL (overrides $REDDIT env var)")
@click.option("--max-steps", type=int, default=20)
@click.option("--idx-offset", type=int, default=0, help="Offset applied to the user goal start index")
def main(config, model, system_prompt, output_dir, output_format, run_single, user_goal_start, gitlab_url, reddit_url, max_steps, idx_offset):
    gitlab_url = gitlab_url or os.environ.get("GITLAB")
    reddit_url = reddit_url or os.environ.get("REDDIT")

    if not gitlab_url:
        raise click.UsageError("GitLab URL must be set via --gitlab-url or $GITLAB env var")
    if not reddit_url:
        raise click.UsageError("Reddit URL must be set via --reddit-url or $REDDIT env var")

    print("Arguments provided to run.py: \n", locals(), "\n\n")
    run_all(
        config=config,
        model=model,
        system_prompt=system_prompt,
        output_dir=output_dir,
        output_format=output_format,
        run_single=run_single,
        user_goal_start=user_goal_start,
        gitlab_url=gitlab_url,
        reddit_url=reddit_url,
        max_steps=max_steps,
        idx_offset=idx_offset,
    )


if __name__ == '__main__':
    main()
