# Changes Made to WASP for Cellmate Evaluation

## Prerequisite

### Environment Variables

```bash
export GITLAB="http://3.12.226.110:8023"
export REDDIT="http://3.12.226.110:9999"
export DATASET=webarena_prompt_injections
```

## Command for End-to-End Eval

### Setup
```bash
cd webarena_prompt_injections

source venv/bin/activate
python3.10 setup_prompt_injections.py --config configs/experiment_config_cellmate.raw.json \
              --model gpt-4o-mini \
              --system-prompt configs/system_prompts/wa_p_cot_id_actree_3s.json \
              --output-dir <YOUR_OUTPUT_DIR> \
              --output-format browser_use
```

### Execute attack

#### Execute Browser-Use
```bash
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
```


#### Execute Automated Scripts
```bash
python run_scripts.py --gitlab-url http://3.12.226.110:8023  --start-issue-index <START_ISSUE_INDEX>
```

### Evaluate
#### Evaluating ASR
```bash
cd visualwebarena
source venv/bin/activate
python evaluator_final_step.py --log-folder ../attack_scripts --task-folder <CONFIG_FOLDER>/webarena_tasks_attacker --format scripts
deactivate
```
#### Evaluating Utility
```bash
cd visualwebarena
source venv/bin/activate
python evaluator_final_step.py --log-folder ../attack_scripts --task-folder <CONFIG_FOLDER>/webarena_tasks --format scripts
deactivate
```

### Cleanup
```bash
cd webarena_prompt_injections
python environment_cleanup.py --prompt-injection-config-path <CONFIG_FOLDER>/instantiated_prompt_injections_config.json --gitlab-domain $GITLAB --reddit-domain $REDDIT
```
## Changes Made to Source Code

### Disabled Reddit Benchmark

### Specific to MAC

- Skippling CUDA related packages in `requirements.txt`.
