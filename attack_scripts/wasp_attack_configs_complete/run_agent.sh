#!/bin/bash

set -e

cd /Users/luoxim/Workspace/cellmate_project/wasp/browser-use

source venv/bin/activate

python run.py \
    --test_start_idx 1000 \
    --test_end_idx 1016 \
    --model o1 \
    --result_dir /Users/luoxim/Workspace/cellmate_project/wasp/output_new/39/agent_logs_browser_use \
    --test_config_base_dir /Users/luoxim/Workspace/cellmate_project/wasp/output_new/39/webarena_tasks \
    --max_steps 20

deactivate
