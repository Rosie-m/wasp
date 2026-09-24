#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# Prerequisite 1: python virtual environment and built Docker container (TODO: describe how to do these in README)
# Prerequisite 2: set the required authentication environment variables (AZURE_API_ENDPOINT and AZURE_API_KEY for GPT/WebArena and AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN for Claude)

set -e

export OUTPUT_DIR=${1:-/tmp/computer-use-agent-logs/}
export MODEL=${2:-gpt-4o}
export SYSTEM_PROMPT=${3:-configs/system_prompts/wa_p_som_cot_id_actree_3s.json}
export CONFIG_PATH=${4:-configs/experiment_config.raw.json}
export USER_GOAL_IDX=${5:-0}
export INJECTION_FORMAT=${6:-goal_hijacking_plain_text}
export OUTPUT_FORMAT=${7:-webarena}
export MAX_STEPS=${8:-20}

if [[ "${OUTPUT_DIR}" != */ ]]; then
    OUTPUT_DIR="${OUTPUT_DIR}/"
fi

if [ -d "$OUTPUT_DIR" ]; then
  echo "Deleting existing OUTPUT_DIR=${OUTPUT_DIR}"
  rm -rf "$OUTPUT_DIR"
fi

echo "Creating the new OUTPUT_DIR=${OUTPUT_DIR}"
mkdir "$OUTPUT_DIR"

# ----- cleanup after previous run
if [ -f "/tmp/run_step_by_step_asr.json" ]; then
  rm "/tmp/run_step_by_step_asr.json"
fi

if [ -f "/tmp/run_attacker_utility.json" ]; then
  rm "/tmp/run_attacker_utility.json"
fi

if [ -f "/tmp/run_user_utility.json" ]; then
  rm "/tmp/run_user_utility.json"
fi
# -----

echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "CONFIG_PATH: $CONFIG_PATH"
echo "GITLAB_DOMAIN: $GITLAB"
echo "REDDIT_DOMAIN: $REDDIT"
echo "Model: $MODEL"
echo "SYSTEM_PROMPT: $SYSTEM_PROMPT"
echo "USER_GOAL_IDX: $USER_GOAL_IDX"
echo "INJECTION_FORMAT: $INJECTION_FORMAT"
echo "OUTPUT_FORMAT: $OUTPUT_FORMAT"

##### STEP 1: Inject prompts and create tasks in web environment ######
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "SCRIPT_DIR: $SCRIPT_DIR"
cd $SCRIPT_DIR/..
cp $CONFIG_PATH "${OUTPUT_DIR}experiment_config.json"
echo "step 1 | preparing prompt injections and tasks..."
source venv/bin/activate
python prompt_injector.py --config $CONFIG_PATH \
                          --gitlab-domain $GITLAB \
                          --model $MODEL \
                          --system_prompt $SYSTEM_PROMPT \
                          --output-dir $OUTPUT_DIR \
                          --user_goal_idx $USER_GOAL_IDX \
                          --injection_format $INJECTION_FORMAT \
                          --output-format $OUTPUT_FORMAT \
                          --max-steps $MAX_STEPS
deactivate
##### -----------


##### STEP 2: Run agents on tasks ######
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "SCRIPT_DIR: $SCRIPT_DIR"
cd $SCRIPT_DIR/../../browser-use/
source venv/bin/activate
chmod -R 777 $OUTPUT_DIR
AGENT_RUN_SCRIPT="${OUTPUT_DIR}run_agent.sh"
# AGENT_RUN_SCRIPT="/Users/luoxim/Workspace/cellmate_project/wasp/output_new/16/run_agent.sh" # hardcoded for debugging
echo "step 2 | Executing agent script at $AGENT_RUN_SCRIPT"
bash "$AGENT_RUN_SCRIPT" || true
deactivate
##### -----------


##### STEP 3: Run evaluations ######
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VISUALWEBARENA_DIR="$SCRIPT_DIR/../../visualwebarena"
LOG_DIR="${OUTPUT_DIR}agent_logs_browser_use"
# LOG_DIR="/Users/luoxim/Workspace/cellmate_project/wasp/output_new/16/agent_logs_browser_use" # hardcoded for debugging
TASK_DIR="${OUTPUT_DIR}webarena_tasks"
# TASK_DIR="/Users/luoxim/Workspace/cellmate_project/wasp/output_new/16/webarena_tasks" # hardcoded for debugging
ATTACKER_TASK_DIR="${OUTPUT_DIR}webarena_tasks_attacker"
# ATTACKER_TASK_DIR="/Users/luoxim/Workspace/cellmate_project/wasp/output_new/16/webarena_tasks_attacker" # hardcoded for debugging

echo "SCRIPT_DIR: $SCRIPT_DIR"
echo "step 3 | OUTPUT_DIR: $OUTPUT_DIR"

cd "$VISUALWEBARENA_DIR"
source venv/bin/activate
set +e  # evaluation failures should not abort the experiment

bash prepare.sh

EVAL_RESULTS_DIR="${OUTPUT_DIR}eval_results"

# Evaluate attacker task performance (ASR)
python evaluator_final_step.py --log-folder "$LOG_DIR" --task-folder "$ATTACKER_TASK_DIR" --format browser_use --results-dir "$EVAL_RESULTS_DIR"
echo "Done evaluating attacker goals — score above is ASR!"

# Evaluate user task performance (utility)
python evaluator_final_step.py --log-folder "$LOG_DIR" --task-folder "$TASK_DIR" --format browser_use --results-dir "$EVAL_RESULTS_DIR"
echo "Done evaluating user objectives!"

set -e
deactivate
##### -----------


##### STEP 4: Cleanup environment ######
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "SCRIPT_DIR: $SCRIPT_DIR"
cd $SCRIPT_DIR/..
PROMPT_INJECTION_CONFIG="${OUTPUT_DIR}instantiated_prompt_injections_config.json"
# PROMPT_INJECTION_CONFIG="/Users/luoxim/Workspace/cellmate_project/wasp/output_new/16/instantiated_prompt_injections_config.json" # hardcoded for debugging
echo "step 4 | OUTPUT_DIR: $OUTPUT_DIR"
echo "step 4 | PROMPT_INJECTION_CONFIG: $PROMPT_INJECTION_CONFIG"
source venv/bin/activate
python environment_cleanup.py --prompt-injection-config-path "$PROMPT_INJECTION_CONFIG" --gitlab-domain $GITLAB --reddit-domain $REDDIT
deactivate
##### -----------
