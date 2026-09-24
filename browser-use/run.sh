#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"

source venv/bin/activate
python run.py \
    --test_start_idx 1000 \
    --test_end_idx 1016 \
    --model gpt-4o-mini \
    --result_dir /Users/luoxim/Workspace/cellmate_project/wasp/output/0/agent_logs_browser_use \
    --test_config_base_dir /Users/luoxim/Workspace/cellmate_project/wasp/output/0/webarena_tasks \
    --max_steps 15 \
    --render
deactivate
